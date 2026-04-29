import sqlite3
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timedelta
import random
import logging
from pathlib import Path
from config import CATCH_CHANCE, NO_BITE_CHANCE, GUARANTEED_CATCH_COST, COOLDOWN_MINUTES, ROD_REPAIR_COST, CURRENT_SEASON, TRASH_CHANCE, get_current_season
from database import db, DB_PATH, BAMBOO_ROD, TEMP_ROD_RANGES
from weather import weather_system

logger = logging.getLogger(__name__)

FIGHT_ALWAYS_RARITIES = {'Легендарная', 'Мифическая', 'Аномалия'}
FIGHT_HEAVY_WEIGHT_KG = 20.0
FIGHT_MEDIUM_WEIGHT_KG = 14.0

class FishingGame:
    def __init__(self):
        self.current_season = self._get_current_season()

    def _generate_weight_by_ranges(self, min_weight: float, max_weight: float) -> float:
        """Сгенерировать вес по диапазонам: гигантский вес выпадает крайне редко."""
        min_w = float(min_weight)
        max_w = float(max_weight)

        if max_w <= min_w:
            return round(min_w, 2)

        span = max_w - min_w
        if span < 0.03:
            return round(random.uniform(min_w, max_w), 2)

        small_max = min_w + (span * 0.4)
        medium_max = min_w + (span * 0.8)
        large_max = min_w + (span * 0.95)

        # 55% малый вес, 33% средний, 10% большой, 2% гигантский
        roll = random.randint(1, 100)
        if roll <= 55:
            start, end = min_w, small_max
        elif roll <= 88:
            start, end = small_max, medium_max
        elif roll <= 98:
            start, end = medium_max, large_max
        else:
            start, end = large_max, max_w

        if end <= start:
            return round(random.uniform(min_w, max_w), 2)

        return round(random.uniform(start, end), 2)
    
    def _normalize_fish_list(self, fish_list):
        """Ensure each fish entry is a dict with keys accessible by name.

        Some DB callers may return tuples or sqlite rows; normalize defensively.
        """
        if not fish_list:
            return fish_list
        normalized = []
        # Known fish columns order used by database.get_fish... queries
        keys = ['id','name','rarity','min_weight','max_weight','min_length','max_length','price','locations','seasons','suitable_baits','max_rod_weight','required_level','sticker_id']
        for f in fish_list:
            if isinstance(f, dict):
                normalized.append(f)
                continue
            if isinstance(f, (list, tuple)):
                normalized.append(dict(zip(keys, f)))
                continue
            try:
                normalized.append(dict(f))
            except Exception:
                normalized.append({})
        return normalized
    
    def _get_current_season(self) -> str:
        """Определить текущее время года"""
        return get_current_season()
    
    def get_durability_damage(self, catch_type: str, is_guaranteed: bool = False) -> int:
        """Получить урон прочности в зависимости от типа добычи и типа ловли
        
        Обычная ловля:
        - мусор: -1
        - обычная рыба: -5
        - редкая рыба: -10
        - легендарная рыба: -15
        
        Гарантированная ловля:
        - обычная рыба: -1
        - редкая рыба: -2
        - легендарная рыба: -3
        """
        if is_guaranteed:
            if catch_type == "Обычная":
                return 1
            elif catch_type == "Редкая":
                return 2
            elif catch_type == "Легендарная":
                return 3
            elif catch_type == "Мифическая":
                return 4
            else:  # мусор или неловля при гарантированном
                return 0
        else:
            if catch_type == "trash":
                return 1
            elif catch_type == "Обычная":
                return 5
            elif catch_type == "Редкая":
                return 10
            elif catch_type == "Легендарная":
                return 15
            elif catch_type == "Мифическая":
                return 18
            else:  # неловля при обычной ловле
                return 0

    def _should_start_fight(self, fish_data: Dict[str, Any], weight: float, guaranteed: bool = False) -> bool:
        """Нужно ли запускать мини-игру борьбы перед фиксацией улова."""
        if guaranteed:
            return False

        rarity = str((fish_data or {}).get('rarity') or '')
        safe_weight = float(weight or 0.0)

        if rarity in FIGHT_ALWAYS_RARITIES:
            return True
        if safe_weight >= FIGHT_HEAVY_WEIGHT_KG:
            return True
        if safe_weight >= FIGHT_MEDIUM_WEIGHT_KG:
            return random.random() < 0.35
        return False

    def _consume_temp_rod_use(self, user_id: int, chat_id: int, rod_name: str) -> Dict[str, Any]:
        """Списать использование временной удочки и переключить на бамбук при поломке"""
        if rod_name not in TEMP_ROD_RANGES:
            return {"broken": False}

        result: Dict[str, Any] = db.consume_temp_rod_use(user_id, rod_name, chat_id)
        if result.get("broken"):
            db.update_player(user_id, chat_id, current_rod=BAMBOO_ROD)
        return result
    
    def can_fish(self, user_id: int, chat_id: int) -> Tuple[bool, str]:
        """Проверить, может ли игрок рыбачить"""
        player: Dict[str, Any] = db.get_player(user_id, chat_id)
        if not player:
            return False, "Сначала создайте профиль командой /start"

        if player.get('current_rod') == 'Гарпун':
            db.init_player_rod(user_id, BAMBOO_ROD, chat_id)
            db.update_player(user_id, chat_id, current_rod=BAMBOO_ROD)
            player = db.get_player(user_id, chat_id) or player
        
        # Проверка прочности удочки - если 0, нельзя ловить вообще
        player_rod = db.get_player_rod(user_id, player['current_rod'], chat_id)
        if player_rod:
            current_dur = player_rod.get('current_durability', 100)
            if current_dur <= 0:
                if player['current_rod'] in TEMP_ROD_RANGES:
                    return False, "Ваша удочка сломалась! Купите новую в магазине."
                return False, "Ваша удочка сломалась! Почините её командой /repair или подождите автовосстановления."
        
        # Проверка кулдауна
        last_fish = player.get('last_fish_time')
        logger.debug(f"can_fish: user={user_id} chat={chat_id} last_fish={last_fish} COOLDOWN_MINUTES={COOLDOWN_MINUTES}")
        if last_fish:
            last_time = datetime.fromisoformat(last_fish)
            time_passed = datetime.now() - last_time
            if time_passed < timedelta(minutes=COOLDOWN_MINUTES):
                remaining = timedelta(minutes=COOLDOWN_MINUTES) - time_passed
                minutes = int(remaining.total_seconds() // 60)
                seconds = int((remaining.total_seconds() % 60))
                logger.debug(f"can_fish: user={user_id} time_passed={time_passed}, remaining={remaining}")
                return False, f"Следующий заброс через {minutes}мин {seconds}сек"
        
        return True, ""
    
    def _get_time_until_repair(self, ban_until: str) -> str:
        """Получить время до починки удочки"""
        ban_time = datetime.fromisoformat(ban_until)
        remaining = ban_time - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return f"{hours}ч {minutes}мин"

    def fish_with_harpoon(self, user_id: int, chat_id: int, location: str) -> Dict[str, Any]:
        """Отдельная механика гарпуна (не удочка, отдельный инструмент)."""
        player = db.get_player(user_id, chat_id)
        if not player:
            return {
                "success": False,
                "message": "Профиль не найден. Используйте /start в этом чате.",
                "location": location,
            }

        player_level = player.get('level', 0) or 0
        self.current_season = self._get_current_season()

        fish_list = db.get_fish_by_location(location, self.current_season, min_level=player_level)
        fish_list = self._normalize_fish_list(fish_list)
        fish_list = [f for f in fish_list if float(f.get('min_weight', 0) or 0) >= 150]

        if not fish_list:
            return {
                "success": False,
                "message": "🐟 В этой локации нет рыбы для гарпуна (нужна рыба от 150 кг).",
                "location": location,
            }

        caught_fish = random.choice(fish_list)
        weight = self._generate_weight_by_ranges(float(caught_fish['min_weight']), float(caught_fish['max_weight']))
        length = round(random.uniform(float(caught_fish['min_length']), float(caught_fish['max_length'])), 1)

        if weight < 150:
            return {
                "success": False,
                "message": "Гарпун разорвал рыбу на две части 😢",
                "location": location,
            }

        db.add_caught_fish(user_id, chat_id, caught_fish['name'], weight, location, length)

        return {
            "success": True,
            "fish": caught_fish,
            "weight": weight,
            "length": length,
            "location": location,
            "harpoon": True,
        }
    
    def fish(self, user_id: int, chat_id: int, location: str = "Городской пруд", guaranteed: bool = False) -> Dict[str, Any]:
        """Основная функция ловли рыбы"""
        # Проверка на арест рыбнадзором
        player = db.get_player(user_id, chat_id)
        if not player:
            return {
                "success": False,
                "message": "Профиль не найден. Используйте /start в этом чате.",
                "location": location
            }

        if player.get('is_banned'):
            ban_until = player.get('ban_until')
            if ban_until:
                now = datetime.now()
                ban_time = datetime.fromisoformat(ban_until)
                if now < ban_time:
                    remaining = ban_time - now
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    return {
                        "success": False,
                        "message": f"⛔️ Вас арестовал рыбнадзор! До окончания ареста: {hours}ч {minutes}мин. Можно откупиться за 15 звезд командой /payfine"
                    }
                db.update_player(user_id, chat_id, is_banned=0, ban_until=None)

        # Проверка cooldown - не нужна для гарантированного улова (расплачено звездами)
        if not guaranteed:
            can_fish, message = self.can_fish(user_id, chat_id)
            if not can_fish:
                return {"success": False, "message": message}

        if player.get('current_rod') == 'Гарпун':
            db.init_player_rod(user_id, BAMBOO_ROD, chat_id)
            db.update_player(user_id, chat_id, current_rod=BAMBOO_ROD)
            player = db.get_player(user_id, chat_id) or player
        player_level = player.get('level', 0) or 0
        rod = db.get_rod(player['current_rod'])

        # Получаем бонус от наживки
        current_bait = db.get_player_baits(user_id) or []
        bait_bonus = 0
        for bait in current_bait:
            if bait['name'] == player['current_bait']:
                bait_bonus = bait['fish_bonus']
                break

        # Обновляем сезон
        self.current_season = self._get_current_season()
        feeder_bonus = db.get_active_feeder_bonus(user_id, chat_id)
        try:
            clothing_bonus_percent = max(0.0, float(db.get_clothing_bonus_percent(user_id) or 0.0))
        except Exception:
            logger.exception("Failed to load clothing bonus for user=%s", user_id)
            clothing_bonus_percent = 0.0
        try:
            beer_bonus_percent = max(0.0, float(db.get_active_beer_bonus_percent(user_id) or 0.0))
        except Exception:
            logger.exception("Failed to load beer bonus for user=%s", user_id)
            beer_bonus_percent = 0.0

        # Если гарантированный улов
        if guaranteed:
            return self._guaranteed_catch(
                user_id,
                location,
                player,
                chat_id,
                feeder_bonus,
                clothing_bonus_percent,
                beer_bonus_percent,
            )

        # Получаем погоду и применяем бонус
        weather = db.get_or_update_weather(location)
        weather_bonus = 0
        weather_condition = "Ясно"

        if weather:
            weather_condition = weather['condition']
            weather_bonus = weather_system.get_weather_bonus(weather_condition)
            logger.info(f"   🌍 Weather: {weather_condition} (bonus: {weather_bonus:+d}%)")

        # Проверяем, находится ли игрок на лодке
        active_boat = db.get_active_boat_by_user(user_id)
        is_on_boat = active_boat is not None

        eco_disaster = db.get_active_ecological_disaster(location)
        if not eco_disaster:
            eco_disaster = db.maybe_start_ecological_disaster(location)
        force_trash_only = bool(eco_disaster)
        if force_trash_only:
            logger.info(
                "   🌪️ Ecological disaster active at %s: reward_type=%s reward_x%s",
                location,
                eco_disaster.get('reward_type'),
                eco_disaster.get('reward_multiplier'),
            )

        ROLL_MAX = 20000
        
        # Регулировка шансов на основе ROLL_MAX = 20000
        if is_on_boat:
            NO_BITE_MAX = 1999
            TRASH_MAX = 3999
            COMMON_MAX = 11999
            RARE_MAX = 17999
            LEGENDARY_MAX = 18999
            AQUARIUM_MAX = 19499
            MYTHIC_MAX = 19949
            ANOMALY_MAX = 19999
            NFT_MAX = 20001
        else:
            NO_BITE_MAX = 4999
            TRASH_MAX = 9999
            COMMON_MAX = 14999
            RARE_MAX = 18999
            LEGENDARY_MAX = 19899
            AQUARIUM_MAX = 19949
            MYTHIC_MAX = 19989
            ANOMALY_MAX = 19999
            NFT_MAX = 20001

        # Единая механика для всех локаций: один бросок от 0 до 15030
        # 0-3749 = ничего не клюёт
        # 3750-7499 = мусор
        # 7500-11399 = обычная
        # 11400-14599 = редкая
        # 14600-14949 = легендарная
        # 14950-14979 = аквариумная
        # 14980-15009 = аномалия
        # 15010-15029 = мифическая
        # 15030 = NFT
        roll = random.randint(0, ROLL_MAX)
        is_lucky_rod = bool(rod and rod.get('name') == 'Удачливая удочка')

        # Применяем погодный бонус/штраф и бонус кормушки
        adjusted_roll = roll + (weather_bonus * 50) + (feeder_bonus * 250) + (clothing_bonus_percent * 50) + (beer_bonus_percent * 50)
        adjusted_roll = max(0, min(ROLL_MAX, adjusted_roll))  # Ограничиваем от 0 до 15000

        # Применяем штраф популяции (снижаем roll за перелов на одной локации)
        population_penalty = db.get_population_penalty(user_id)
        consecutive_casts = db.get_consecutive_casts(user_id)
        
        penalty_points = int((population_penalty / 100) * ROLL_MAX)  # Конвертируем % в points
        adjusted_roll = adjusted_roll - penalty_points
        adjusted_roll = max(0, min(ROLL_MAX - 1, adjusted_roll))  # Ограничиваем до 14999 для обычных расчетов
        
        logger.info(f"   🌍 Population penalty: {population_penalty:.1f}% ({penalty_points} points)")
        logger.info(f"   📊 Final adjusted roll: {adjusted_roll}/15000")

        # --- ГАРПУН: спец.логика ---
        if rod and rod['name'] == 'Гарпун':
            # Ограничение: только рыба 150кг+ (и огромные)
            # Найдём подходящую рыбу (если выпадет меньше - fail)
            # Получаем список возможной рыбы для локации и сезона
            fish_list = db.get_fish_for_location(location, self.current_season, player_level)
            fish_list = [f for f in fish_list if f['min_weight'] >= 150]
            if not fish_list:
                return {"success": False, "message": "🐟 В этой локации нет рыбы для гарпуна!"}
            # Симулируем обычный roll, но если выпала рыба < 150кг, fail
            # (остальная логика ниже, но после выбора рыбы)
            # ...existing code...
            # После выбора рыбы:
            # if caught_fish['weight'] < 150:
            #     return {"success": False, "message": "Гарпун разорвал рыбу на две части 😢"}
            # (реализация ниже в коде catch)
        
        logger.info(f"🎣 User {user_id} started fishing at location: {location}")
        logger.info(
            f"   🎲 Random roll: {roll}/{ROLL_MAX} (adjusted: {adjusted_roll}/{ROLL_MAX} "
            f"with weather {weather_condition}, feeder {feeder_bonus:+d}%, clothing +{clothing_bonus_percent:.2f}%, beer +{beer_bonus_percent:.2f}%)"
        )
        logger.info("   📊 Ranges: 0-4999=NO_BITE, 5000-9999=TRASH, 10000-14999=COMMON, 15000-18999=RARE, 19000-19899=LEGENDARY, 19900-19999=TOP_TIER, 20000=NFT")
        
        if roll == ROLL_MAX: # NFT win only on exact raw roll 15000
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "nft_win": True,
                "location": location,
                "is_on_boat": is_on_boat
            }

        force_legendary = adjusted_roll >= 19000
        if force_legendary:
            logger.info("   🎯 Forced TOP TIER (adjusted roll >= 19000)")

        if not force_legendary and not force_trash_only and adjusted_roll <= NO_BITE_MAX:
            logger.info(f"   📊 Result: NO_BITE (adjusted roll {adjusted_roll} <= {NO_BITE_MAX})")
            no_bite_messages = [
                "Рыба сегодня не клюет...",
                "Поклевки нет, попробуйте позже",
                "Рыба спит на дне",
                "Сегодня плохой клев",
                "Рыба не интересуется приманкой",
                "Попробуйте другую локацию",
                "Вода слишком холодная для рыбы",
                "Рыба ушла на глубину"
            ]
            
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": random.choice(no_bite_messages),
                "location": location,
                "no_bite": True,
                "is_on_boat": is_on_boat,
                "population_penalty": population_penalty,
                "consecutive_casts": consecutive_casts
            }
        if force_trash_only or (not force_legendary and adjusted_roll <= TRASH_MAX):  # 3750-7499
            logger.info("   📊 Result: TRASH (adjusted roll in range 3750-7499)")
            trash = db.get_random_trash(location)
            if trash:
                logger.info(f"   🗑️ Caught trash: {trash['name']}")
                
                # Применяем урон прочности удочки
                damage = self.get_durability_damage("trash", is_guaranteed=False)
                db.reduce_rod_durability(user_id, player['current_rod'], damage, chat_id)

                xp_earned = db.calculate_item_xp({
                    'rarity': 'Мусор',
                    'weight': trash.get('weight', 0),
                    'min_weight': 0,
                    'max_weight': 0,
                    'is_trash': True,
                })

                reward_type = str((eco_disaster or {}).get('reward_type') or 'xp').lower()
                reward_multiplier = max(1, int((eco_disaster or {}).get('reward_multiplier') or 1))
                bonus_coins = 0
                if force_trash_only and reward_multiplier > 1:
                    if reward_type == 'coins':
                        bonus_coins = int(trash.get('price', 0) or 0) * (reward_multiplier - 1)
                    else:
                        xp_earned *= reward_multiplier

                level_info = db.add_player_xp(user_id, chat_id, xp_earned)

                if is_on_boat:
                    db.add_boat_catch(active_boat['id'], trash['name'], trash['weight'], chat_id, location=location, user_id=user_id)
                    db.update_player(
                        user_id,
                        chat_id,
                        coins=int(player.get('coins', 0) or 0) + bonus_coins,
                        last_fish_time=datetime.now().isoformat(),
                    )
                    saved_catch = None
                else:
                    saved_catch = db.add_caught_fish(
                        user_id,
                        chat_id,
                        trash['name'],
                        float(trash.get('weight', 0) or 0),
                        location,
                        0,
                    )
                    db.update_player(
                        user_id,
                        chat_id,
                        coins=int(player.get('coins', 0) or 0) + bonus_coins,
                        last_fish_time=datetime.now().isoformat(),
                    )

                temp_rod_result = self._consume_temp_rod_use(user_id, chat_id, player['current_rod'])
                
                trash_messages = [
                    f"😑 Ловля... Из воды выловлена {trash['name']}!",
                    f"🗑️ Ловля... Поймали {trash['name']}!",
                    f"😤 Ловля... Это был {trash['name']}, а не рыба!",
                ]
                
                # ===== ВТОРОЙ РОЛ НА ДРАГОЦЕННОСТИ =====
                from treasures import TREASURES
                treasure_caught = None
                treasure_name = None
                
                # Суммируем все вероятности для нормализации
                total_probability = sum(t['probability'] for t in TREASURES.values())
                treasure_roll = random.uniform(0, 100)
                accumulated_probability = 0

                logger.info(
                    "   💎 Treasure roll #2 start: roll=%.2f/100, total_treasure_prob=%.2f%%, no_treasure_prob=%.2f%%",
                    treasure_roll,
                    total_probability,
                    max(0.0, 100.0 - total_probability),
                )
                
                for treasure_key, treasure_info in TREASURES.items():
                    chance = float(treasure_info.get('probability', 0) or 0)
                    prev_threshold = accumulated_probability
                    accumulated_probability += chance
                    logger.info(
                        "   💎 Treasure roll #2 check: item=%s chance=%.2f%% range=(%.2f..%.2f]",
                        treasure_key,
                        chance,
                        prev_threshold,
                        accumulated_probability,
                    )
                    if treasure_roll <= accumulated_probability:
                        # Treasure is considered caught only after successful DB save.
                        if db.add_treasure(user_id, treasure_key, 1, chat_id):
                            treasure_caught = treasure_info
                            treasure_name = treasure_key
                            logger.info(
                                "   💎 Treasure roll #2 result: TREASURE item=%s roll=%.2f threshold=%.2f",
                                treasure_key,
                                treasure_roll,
                                accumulated_probability,
                            )
                        else:
                            logger.error(
                                "   💎 Treasure roll #2 result: SAVE_FAILED item=%s user=%s chat=%s",
                                treasure_key,
                                user_id,
                                chat_id,
                            )
                        break

                if treasure_name is None:
                    logger.info(
                        "   💎 Treasure roll #2 result: NONE roll=%.2f > total_treasure_prob=%.2f",
                        treasure_roll,
                        accumulated_probability,
                    )
                
                return {
                    "success": False,
                    "is_trash": True,
                    "trash": trash,
                    "location": location,
                    "message": random.choice(trash_messages),
                    "earned": bonus_coins,
                    "new_balance": int(player.get('coins', 0) or 0) + bonus_coins,
                    "xp_earned": xp_earned,
                    "level_info": level_info,
                    "is_on_boat": is_on_boat,
                    "stored_in_inventory": not is_on_boat,
                    "catch_id": (saved_catch or {}).get('id') if isinstance(saved_catch, dict) else None,
                    "eco_disaster": eco_disaster,
                    "reward_type": reward_type,
                    "reward_multiplier": reward_multiplier,
                    "temp_rod_broken": temp_rod_result.get("broken", False),
                    "treasure_caught": treasure_caught,
                    "treasure_name": treasure_name,
                    "population_penalty": population_penalty,
                    "consecutive_casts": consecutive_casts
                }

            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": "В этом месте сейчас только мусор, но вы ничего не достали.",
                "location": location,
                "no_bite": True,
                "is_on_boat": is_on_boat,
            }
        
        # 7500-14999 = ловим рыбу с определением редкости
        logger.info("   📊 Result: CATCH (adjusted roll in range 7500-14999)")

        if force_legendary:
            target_rarity = "Легендарная" if adjusted_roll <= LEGENDARY_MAX else "Мифическая"
        elif adjusted_roll <= COMMON_MAX:
            target_rarity = "Обычная"
            logger.info(f"   🎯 Rarity: COMMON (adjusted roll in 7500-{COMMON_MAX})")
        elif adjusted_roll <= RARE_MAX:
            target_rarity = "Редкая"
            logger.info(f"   🎯 Rarity: RARE (adjusted roll in {COMMON_MAX+1}-{RARE_MAX})")
        elif adjusted_roll <= LEGENDARY_MAX:
            target_rarity = "Легендарная"
            logger.info(f"   🎯 Rarity: LEGENDARY (adjusted roll in {RARE_MAX+1}-{LEGENDARY_MAX})")
        elif adjusted_roll <= AQUARIUM_MAX:
            target_rarity = "Аквариумная"
            logger.info(f"   🎯 Rarity: AQUARIUM (adjusted roll in {LEGENDARY_MAX+1}-{AQUARIUM_MAX})")
        elif adjusted_roll <= MYTHIC_MAX:
            target_rarity = "Мифическая"
            logger.info(f"   🎯 Rarity: MYTHIC (adjusted roll in {AQUARIUM_MAX+1}-{MYTHIC_MAX})")
        elif adjusted_roll <= ANOMALY_MAX:
            target_rarity = "Аномалия"
            logger.info(f"   🎯 Rarity: ANOMALY (adjusted roll in {MYTHIC_MAX+1}-{ANOMALY_MAX})")
        else:
            target_rarity = "NFT"
            logger.info(f"   🎯 Rarity: NFT (adjusted roll = {NFT_MAX})")

        # Нерф легендарки: шанс легендарной редкости в 5 раз меньше.
        # Если проверка не пройдена — мгновенный срыв (без понижения редкости и без выбора рыбы).
        if target_rarity == "Легендарная" and random.randint(1, 5) != 1:
            logger.info("   🎯 Legendary roll failed -> SNAP (nerf x5)")
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "snap": True,
                "message": "🪝 Легендарная рыба сорвалась!",
                "location": location,
                "target_rarity": target_rarity
            }
        
        # Получаем список рыб для локации и сезона
        # Всегда учитывать сезон при выборе списка рыб (даже для легендарных)
        fish_list = db.get_fish_by_location(location, self.current_season, min_level=player_level)
        # Normalize rows to dicts in case some DB callers return tuples
        fish_list = self._normalize_fish_list(fish_list)
        if fish_list is None:
            fish_list = []
        if fish_list is None:
            fish_list = []
        if not fish_list:
            logger.info(f"   ⚠️ No fish available for location: {location}, season: {self.current_season}")
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": "На этой локации нет рыбы в текущее время года.",
                "location": location
            }

        if force_legendary:
            legendary_fish = [f for f in fish_list if f['rarity'] == target_rarity]
            if not legendary_fish:
                logger.info(f"   ⚠️ No fish of rarity {target_rarity} available in season {self.current_season} for location {location} - SNAP")
                db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
                return {
                    "success": False,
                    "snap": True,
                    "message": f"В этой локации нет рыбы редкости {target_rarity} в текущий сезон — срыв.",
                    "location": location
                }
            caught_fish = random.choice(legendary_fish)
        else:
            # ============ МЕХАНИКА НАЖИВКИ: 90% на нужную наживку, 10% срыв ============
            bait_success_roll = random.randint(1, 100)
            logger.info(f"   🪱 Bait roll: {bait_success_roll}/100 (1-90=right bait, 91-100=wrong bait snap)")
            
            use_correct_bait = bait_success_roll <= 90
            
            # Ищем рыбу с НУЖНОЙ наживкой И НУЖНОЙ РЕДКОСТЬЮ
            correct_bait_fish = [
                f for f in fish_list 
                if db.check_bait_suitable_for_fish(player['current_bait'], f['name'])
                and f['rarity'] == target_rarity
            ]
            
            # Если нет рыбы нужной редкости с нужной наживкой - оставляем пустой список
            # (в этом случае будет считаться, что рыба сорвалась)
            # no fallback to other rarities to avoid catching different rarity fish
            # if not correct_bait_fish: keep it empty and treat as snap below
            
            # Ищем рыбу с ЧУЖОЙ наживкой (для 10% случаев срыва)
            wrong_bait_fish = [
                f for f in fish_list
                if f['rarity'] == target_rarity
            ]
            
            # Применяем выбор на основе броска наживки
            if use_correct_bait:
                # 90% - ловим рыбу на нужную наживку
                if correct_bait_fish:
                    logger.info(f"   ✅ Using correct bait - fishing for {player['current_bait']} suitable fish")
                    caught_fish = random.choice(correct_bait_fish)
                    logger.info(f"   🐟 Caught fish: {caught_fish['name']} (rarity: {caught_fish['rarity']}, bait: {player['current_bait']})")
                else:
                    # Нет рыбы на эту наживку - СРЫВ из-за неправильной наживки
                    logger.info(f"   ⚠️ No fish for bait '{player['current_bait']}' at {location} - treating as SNAP")
                    snap_messages = [
                        f"🪝 Рыба клюнула, но наживка {player['current_bait']} ей не подошла - рыба сорвалась!",
                        f"⚠️ Поклевка была, но рыба не клюет на {player['current_bait']} - срыв!",
                        f"😤 Почти поймал! Но рыба отказалась от {player['current_bait']}...",
                        f"🎣 Срыв! Попробуйте другую наживку для этой локации.",
                    ]
                    db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
                    return {
                        "success": False,
                        "snap": True,
                        "message": random.choice(snap_messages),
                        "location": location,
                        "wrong_bait": player['current_bait'],
                        "target_rarity": target_rarity
                    }
            else:
                # 10% - попытка поймать рыбу на чужую наживку = СРЫВ
                logger.info(f"   ❌ Wrong bait attempt - SNAP/BREAK!")
                snap_messages = [
                    "🪝 Рыба интенсивно тянула, но наживка оказалась чужой - рыба сорвалась!",
                    "⚠️ Рыба клюнула агрессивно на неправильную наживку, но вырвалась!",
                    "😤 Почти поймал! Но рыба не клюет на эту наживку...",
                    "🎣 Срыв! Попытался ловить рыбу не на ту наживку!",
                ]
                db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
                return {
                    "success": False,
                    "snap": True,
                    "message": random.choice(snap_messages),
                    "location": location,
                    "wrong_bait": player['current_bait'],
                    "target_rarity": target_rarity
                }
        
        # Наживка уже учтена при выборе рыбы
        
        # Расчет веса и размера рыбы
        weight = self._generate_weight_by_ranges(caught_fish['min_weight'], caught_fish['max_weight'])
        length = round(random.uniform(caught_fish['min_length'], caught_fish['max_length']), 1)
        logger.info(f"   📏 Fish stats: weight={weight}kg, length={length}cm")

        # --- ГАРПУН: если пойманная рыба < 150кг, fail ---
        if rod and rod['name'] == 'Гарпун' and weight < 150:
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": "Гарпун разорвал рыбу на две части 😢",
                "location": location
            }

        # Проверка на превышение веса - рыба срывается если слишком тяжелая
        max_rod_weight = rod.get('max_weight', 999)
        if weight > max_rod_weight:
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": f"Рыба {caught_fish['name']} ({weight}кг) слишком тяжелая для вашей удочки и сорвалась!",
                "location": location,
                "target_rarity": target_rarity
            }

        if self._should_start_fight(caught_fish, weight, guaranteed=False):
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "fight_required": True,
                "message": "🐋 Крупная добыча сопротивляется! Нужна борьба.",
                "fish": caught_fish,
                "weight": weight,
                "length": length,
                "location": location,
                "is_on_boat": is_on_boat,
                "target_rarity": target_rarity,
            }

        # Успешная ловля - рыба больше не продается автоматически

        # ===== МЕХАНИКА РЫБНАДЗОРА =====
        fish_inspector_chance = 0.01  # 1% шанс
        if random.random() < fish_inspector_chance:
            ban_hours = 1
            ban_until = (datetime.now() + timedelta(hours=ban_hours)).isoformat()
            db.update_player(user_id, chat_id, is_banned=1, ban_until=ban_until)
            return {
                "success": False,
                "fish_inspector": True,
                "is_on_boat": is_on_boat,
                "location": location,
                "message": f"🚨 Вас поймал рыбнадзор! Ваш улов конфискован, а вы арестованы на {ban_hours} час. Можно откупиться за 15 звезд командой /payfine"
            }
        
        # Применяем урон прочности удочки в зависимости от редкости рыбы
        damage = self.get_durability_damage(caught_fish['rarity'], is_guaranteed=False)
        db.reduce_rod_durability(user_id, player['current_rod'], damage, chat_id)
        
        # Проверяем прочность после урона
        player_rod = db.get_player_rod(user_id, player['current_rod'], chat_id)
        current_dur = player_rod.get('current_durability', 0) if player_rod else 0
        max_dur = player_rod.get('max_durability', 100) if player_rod else 100
        rod_broken = current_dur <= 0
        
        if is_on_boat:
            db.add_fish_to_boat(user_id, caught_fish['id'], weight, chat_id, location=location)
        else:
            db.add_caught_fish(user_id, chat_id, caught_fish['name'], weight, location, length)
        
        # Расход наживки (только при успешной ловле и не за платный заброс!)
        if not guaranteed and player['current_bait'].lower() != 'черви':  # Черви бесконечные
            used = db.use_bait(user_id, player['current_bait'])
            # Если наживка закончилась, переключаем на черви
            if not used or db.get_bait_count(user_id, player['current_bait']) == 0:
                db.update_player_bait(user_id, chat_id, 'Черви')
            logger.info(f"   🪱 Used 1x {player['current_bait']}")

        temp_rod_result = self._consume_temp_rod_use(user_id, chat_id, player['current_rod'])

        db.update_player(user_id, chat_id,
                last_fish_time=datetime.now().isoformat())

        # Начисляем опыт за улов
        xp_earned = db.calculate_item_xp({
            'rarity': caught_fish.get('rarity', 'Обычная'),
            'weight': weight,
            'min_weight': caught_fish.get('min_weight', 0),
            'max_weight': caught_fish.get('max_weight', 0),
            'is_trash': False,
        })
        level_info = db.add_player_xp(user_id, chat_id, xp_earned)

        # Обновление популяции рыбы на локации
        self._update_fish_population(location, -1)

        fish_price = db.calculate_fish_price(caught_fish, weight, length)

        return {
            "success": True,
            "fish": caught_fish,
            "weight": weight,
            "length": length,
            "location": location,
            "earned": fish_price,
            "new_balance": player['coins'],
            "xp_earned": xp_earned,
            "level_info": level_info,
            "guaranteed": False,
            "stars_spent": 0,
            "rod_broken": rod_broken,
            "current_durability": current_dur,
            "max_durability": max_dur,
            "is_on_boat": is_on_boat,
            "temp_rod_broken": temp_rod_result.get("broken", False),
            "target_rarity": target_rarity,
            "population_penalty": population_penalty,
            "consecutive_casts": consecutive_casts
        }
    
    def _guaranteed_catch(
        self,
        user_id: int,
        location: str,
        player: Dict[str, Any],
        chat_id: int,
        feeder_bonus: int = 0,
        clothing_bonus_percent: float = 0.0,
        beer_bonus_percent: float = 0.0,
    ) -> Dict[str, Any]:
        """Гарантированный улов с фиксированными шансами."""
        ROLL_MAX = 20000
        TRASH_MAX = 7999
        COMMON_MAX = 14999   # 35% обычная (8000-14999)
        RARE_MAX = 16999     # 10% редкая (15000-16999)
        LEGENDARY_MAX = 18999 # 10% легендарная (17000-18999)
        AQUARIUM_MAX = 19499 # 2.5% аквариумная (19000-19499)
        MYTHIC_MAX = 19949   # 2.25% мифическая (19500-19949)
        ANOMALY_MAX = 19999  # 0.25% аномалия (19950-19999)

        roll = random.randint(0, ROLL_MAX)
        adjusted_roll = max(0, min(ROLL_MAX, roll + (feeder_bonus * 250) + (clothing_bonus_percent * 50) + (beer_bonus_percent * 50)))
        
        # Применяем штраф популяции для гарантированного улова
        population_penalty = db.get_population_penalty(user_id)
        penalty_points = int((population_penalty / 100) * ROLL_MAX)  # Конвертируем % в points
        adjusted_roll = adjusted_roll - penalty_points
        adjusted_roll = max(0, adjusted_roll)  # Не может быть меньше 0
        
        logger.info(
            f"   🎲 Guaranteed roll: {roll}/{ROLL_MAX} "
            f"(adjusted: {adjusted_roll}/{ROLL_MAX}, feeder {feeder_bonus:+d}%, clothing +{clothing_bonus_percent:.2f}%, beer +{beer_bonus_percent:.2f}%, population penalty: {population_penalty:.1f}%)"
        )

        is_lucky_rod_g = (player.get('current_rod') == 'Удачливая удочка')

        eco_disaster = db.get_active_ecological_disaster(location)
        if not eco_disaster:
            eco_disaster = db.maybe_start_ecological_disaster(location)
        force_trash_only = bool(eco_disaster)

        if roll == ROLL_MAX: # NFT win only on exact raw roll 20000, no buffs
            logger.info("   🏆 Guaranteed result: NFT WIN (raw roll %s, lucky_rod=%s)", roll, is_lucky_rod_g)
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "nft_win": True,
                "location": location,
            }

        if force_trash_only or adjusted_roll <= TRASH_MAX:
            # Trash branch for guaranteed cast
            logger.info("   📊 Result: TRASH (roll in range 0-7999)")
            trash = db.get_random_trash(location)
            if not trash:
                db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
                return {
                    "success": False,
                    "message": "В водоеме только мусор, но ничего не удалось вытащить.",
                    "location": location,
                    "no_bite": True,
                }
            elif trash:
                logger.info(f"   🗑️ Caught trash: {trash['name']}")
                damage = self.get_durability_damage("trash", is_guaranteed=True)
                db.reduce_rod_durability(user_id, player['current_rod'], damage, chat_id)

                xp_earned = db.calculate_item_xp({
                    'rarity': 'Мусор',
                    'weight': trash.get('weight', 0),
                    'min_weight': 0,
                    'max_weight': 0,
                    'is_trash': True,
                })
                reward_type = str((eco_disaster or {}).get('reward_type') or 'xp').lower()
                reward_multiplier = max(1, int((eco_disaster or {}).get('reward_multiplier') or 1))
                bonus_coins = 0
                if force_trash_only and reward_multiplier > 1:
                    if reward_type == 'coins':
                        bonus_coins = int(trash.get('price', 0) or 0) * (reward_multiplier - 1)
                    else:
                        xp_earned *= reward_multiplier
                level_info = db.add_player_xp(user_id, chat_id, xp_earned)

                # Проверяем, находится ли игрок на лодке
                active_boat = db.get_active_boat_by_user(user_id)
                is_on_boat = active_boat is not None

                if is_on_boat:
                    db.add_boat_catch(active_boat['id'], trash['name'], trash['weight'], chat_id, location=location, user_id=user_id)
                    saved_catch = None
                else:
                    saved_catch = db.add_caught_fish(
                        user_id,
                        chat_id,
                        trash['name'],
                        float(trash.get('weight', 0) or 0),
                        location,
                        0,
                    )

                db.update_player(
                    user_id,
                    chat_id,
                    coins=int(player.get('coins', 0) or 0) + bonus_coins,
                    last_fish_time=datetime.now().isoformat(),
                )

                temp_rod_result = self._consume_temp_rod_use(user_id, chat_id, player['current_rod'])

                trash_messages = [
                    f"😑 Ловля... Из воды выловлена {trash['name']}!",
                    f"🗑️ Ловля... Поймали {trash['name']}!",
                    f"😤 Ловля... Это был {trash['name']}, а не рыба!",
                ]
                
                # ... [treasure logic remains same, but I need to include it in the replace block if it's within range]
                # Wait, I'll use a better approach for the replacement block.
                # Actually, I'll just replace the return dict and the coins update part.
                
                # ===== ВТОРОЙ РОЛ НА ДРАГОЦЕННОСТИ =====
                from treasures import TREASURES
                treasure_caught = None
                treasure_name = None
                
                # Суммируем все вероятности для нормализации
                total_probability = sum(t['probability'] for t in TREASURES.values())
                treasure_roll = random.uniform(0, 100)
                accumulated_probability = 0

                logger.info(
                    "   💎 Treasure roll #2 start: roll=%.2f/100, total_treasure_prob=%.2f%%, no_treasure_prob=%.2f%%",
                    treasure_roll,
                    total_probability,
                    max(0.0, 100.0 - total_probability),
                )
                
                for treasure_key, treasure_info in TREASURES.items():
                    chance = float(treasure_info.get('probability', 0) or 0)
                    prev_threshold = accumulated_probability
                    accumulated_probability += chance
                    logger.info(
                        "   💎 Treasure roll #2 check: item=%s chance=%.2f%% range=(%.2f..%.2f]",
                        treasure_key,
                        chance,
                        prev_threshold,
                        accumulated_probability,
                    )
                    if treasure_roll <= accumulated_probability:
                        # Treasure is considered caught only after successful DB save.
                        if db.add_treasure(user_id, treasure_key, 1, chat_id):
                            treasure_caught = treasure_info
                            treasure_name = treasure_key
                            logger.info(
                                "   💎 Treasure roll #2 result: TREASURE item=%s roll=%.2f threshold=%.2f",
                                treasure_key,
                                treasure_roll,
                                accumulated_probability,
                            )
                        else:
                            logger.error(
                                "   💎 Treasure roll #2 result: SAVE_FAILED item=%s user=%s chat=%s",
                                treasure_key,
                                user_id,
                                chat_id,
                            )
                        break

                if treasure_name is None:
                    logger.info(
                        "   💎 Treasure roll #2 result: NONE roll=%.2f > total_treasure_prob=%.2f",
                        treasure_roll,
                        accumulated_probability,
                    )

                return {
                    "success": False,
                    "is_trash": True,
                    "trash": trash,
                    "location": location,
                    "message": random.choice(trash_messages),
                    "earned": bonus_coins,
                    "new_balance": int(player.get('coins', 0) or 0) + bonus_coins,
                    "xp_earned": xp_earned,
                    "level_info": level_info,
                    "is_on_boat": is_on_boat,
                    "stored_in_inventory": not is_on_boat,
                    "catch_id": (saved_catch or {}).get('id') if isinstance(saved_catch, dict) else None,
                    "eco_disaster": eco_disaster,
                    "reward_type": reward_type,
                    "reward_multiplier": reward_multiplier,
                    "temp_rod_broken": temp_rod_result.get("broken", False),
                    "treasure_caught": treasure_caught,
                    "treasure_name": treasure_name
                }

        elif adjusted_roll <= 700:
            target_rarity = "Обычная"
        elif adjusted_roll <= COMMON_MAX:
            target_rarity = "Обычная"
        elif adjusted_roll <= RARE_MAX:
            target_rarity = "Редкая"
        elif adjusted_roll <= LEGENDARY_MAX:
            target_rarity = "Легендарная"
        elif adjusted_roll <= AQUARIUM_MAX:
            target_rarity = "Аквариумная"
        elif adjusted_roll <= MYTHIC_MAX:
            target_rarity = "Мифическая"
        elif adjusted_roll <= ANOMALY_MAX:
            target_rarity = "Аномалия"
        else:
            target_rarity = "Мифическая"

        # Нерф легендарки: шанс легендарной редкости в 5 раз меньше.
        # В платном забросе всегда должен быть улов, поэтому при фейле
        # легендарка заменяется на обычную редкость.
        if target_rarity == "Легендарная" and random.randint(1, 10) != 1:
            logger.info("   🎯 Guaranteed legendary roll failed -> COMMON replacement (nerf x10)")
            target_rarity = "Обычная"

        logger.info(f"   🎯 Rarity: {target_rarity} (roll: {adjusted_roll})")

        # Гарантированный улов: учитывать только локацию и уровень игрока, наживка не влияет
        fish_list = db.get_fish_by_location(location, self.current_season, min_level=player.get('level', 0))
        fish_list = self._normalize_fish_list(fish_list)
        if not fish_list:
            # Расширяем поиск: игнорируем сезон — гарантия ВСЕГДА должна давать шанс, если рыба есть в локации в принципе
            logger.info(f"   ⚠️ No seasonal fish for {location}, season {self.current_season} — expanding to all seasons in this location")
            fish_list = self._normalize_fish_list(db.get_fish_by_location(location, 'Все', min_level=0))

        if not fish_list:
            # Совсем нет рыбы в локации — понятное сообщение
            logger.error(f"   ❌ No fish available in location {location} for guaranteed catch")
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": f"В локации '{location}' нет ни одной рыбы для гарантированного улова.",
                "location": location
            }
        if not fish_list:
            # Совсем нет рыбы в БД — единственный допустимый выход с ошибкой
            logger.error(f"   ❌ No fish in DB at all — guaranteed cast cannot proceed")
            db.update_player(user_id, chat_id, last_fish_time=datetime.now().isoformat())
            return {
                "success": False,
                "message": "В базе данных нет рыбы. Обратитесь к администратору.",
                "location": location
            }

        # Ищем рыбу нужной редкости; если нет — понижаем редкость до ближайшей доступной, только если вообще ничего — выдаём любую
        RARITY_ORDER = ["Обычная", "Редкая", "Легендарная", "Мифическая", "Аквариумная", "Аномалия"]
        try:
            idx = RARITY_ORDER.index(target_rarity)
        except ValueError:
            idx = 0
        found = False
        for i in range(idx, -1, -1):
            try_rarity = RARITY_ORDER[i]
            target_fish = [f for f in fish_list if f['rarity'] == try_rarity]
            if target_fish:
                caught_fish = random.choice(target_fish)
                logger.info(f"   ⚠️ No fish of rarity {target_rarity}, downgraded to {try_rarity} ({caught_fish['name']})")
                found = True
                break
        if not found:
            # Если вообще ничего — выдаём любую рыбу сезона
            caught_fish = random.choice(fish_list)
            logger.info(f"   ⚠️ No fish of any target rarity, giving any fish: {caught_fish['name']}")

        # ── Rod weight cap for guaranteed cast ──────────────────────────────
        # Fixed per-rod caps for guaranteed cast (no pay-to-win on weak rods).
        # Бамбуковая: 110 кг | Углепластик: 145 кг | Карбон: 230 кг
        # Золотая: 410 кг  | Удачливая: 710 кг
        ROD_GUARANTEED_CAPS = {
            "Бамбуковая удочка": 110.0,
            "Углепластиковая удочка": 145.0,
            "Карбоновая удочка": 230.0,
            "Золотая удочка": 410.0,
            "Удачливая удочка": 710.0,
        }
        RARITY_ORDER_GUARANTEED = ["Обычная", "Редкая", "Легендарная", "Мифическая"]
        rod_obj = db.get_rod(player['current_rod'])
        rod_max_weight = float(rod_obj.get('max_weight', 999)) if rod_obj else 999.0
        weight_cap = ROD_GUARANTEED_CAPS.get(player.get('current_rod', ''), rod_max_weight + 45.0)

        if float(caught_fish['min_weight']) > weight_cap:
            # Even minimum weight of selected fish exceeds cap → find a fitting fish
            fitting_same = [f for f in fish_list
                            if f['rarity'] == target_rarity and float(f['min_weight']) <= weight_cap]
            if fitting_same:
                caught_fish = random.choice(fitting_same)
                logger.info(f"   ⚖️ Rod weight cap {weight_cap}kg: picked {caught_fish['name']} (same rarity, fits)")
            else:
                # Drop rarity until a fitting fish is found
                current_idx = RARITY_ORDER_GUARANTEED.index(target_rarity) if target_rarity in RARITY_ORDER_GUARANTEED else 0
                found_fit = False
                for idx in range(current_idx - 1, -1, -1):
                    lower_rarity = RARITY_ORDER_GUARANTEED[idx]
                    fitting_lower = [f for f in fish_list
                                     if f['rarity'] == lower_rarity and float(f['min_weight']) <= weight_cap]
                    if fitting_lower:
                        caught_fish = random.choice(fitting_lower)
                        logger.info(f"   ⚖️ Rod weight cap {weight_cap}kg: dropped to {lower_rarity}, picked {caught_fish['name']}")
                        found_fit = True
                        break
                if not found_fit:
                    # Last resort: lightest fish available this season
                    sorted_by_weight = sorted(fish_list, key=lambda f: float(f['min_weight']))
                    caught_fish = sorted_by_weight[0]
                    logger.info(f"   ⚖️ Rod weight cap {weight_cap}kg: last resort, picked {caught_fish['name']} (min_weight={caught_fish['min_weight']})")

        # Generate weight capped by rod limit (no snaps — guaranteed cast always gives fish)
        gen_max = min(float(caught_fish['max_weight']), weight_cap)
        gen_min = float(caught_fish['min_weight'])
        weight = self._generate_weight_by_ranges(gen_min, gen_max)
        length = round(random.uniform(caught_fish['min_length'], caught_fish['max_length']), 1)
        logger.info(f"   📏 Fish stats: weight={weight}kg (cap={weight_cap}kg), length={length}cm")

        # Применяем урон прочности для гарантированного улова
        damage = self.get_durability_damage(caught_fish['rarity'], is_guaranteed=True)
        db.reduce_rod_durability(user_id, player['current_rod'], damage, chat_id)

        # Проверяем прочность после урона
        player_rod = db.get_player_rod(user_id, player['current_rod'], chat_id)
        current_dur = player_rod.get('current_durability', 0) if player_rod else 0
        max_dur = player_rod.get('max_durability', 100) if player_rod else 100
        rod_broken = current_dur <= 0

        # Проверяем, находится ли игрок на лодке
        active_boat = db.get_active_boat_by_user(user_id)
        is_on_boat = active_boat is not None

        if is_on_boat:
            # На лодке рыба идёт в общий садок (boat_catch)
            db.add_fish_to_boat(user_id, caught_fish['id'], weight, chat_id, location=location)
        else:
            db.add_caught_fish(user_id, chat_id, caught_fish['name'], weight, location, length)

        xp_earned = db.calculate_item_xp({
            'rarity': caught_fish.get('rarity', 'Обычная'),
            'weight': weight,
            'min_weight': caught_fish.get('min_weight', 0),
            'max_weight': caught_fish.get('max_weight', 0),
            'is_trash': False,
        })
        level_info = db.add_player_xp(user_id, chat_id, xp_earned)

        fish_price = db.calculate_fish_price(caught_fish, weight, length)
        db.update_player(user_id, chat_id,
                         coins=player['coins'] + (0 if is_on_boat else fish_price),
                         last_fish_time=datetime.now().isoformat())

        temp_rod_result = self._consume_temp_rod_use(user_id, chat_id, player['current_rod'])

        return {
            "success": True,
            "fish": caught_fish,
            "weight": weight,
            "length": length,
            "location": location,
            "is_on_boat": is_on_boat,
            "earned": fish_price if not is_on_boat else 0,
            "new_balance": player['coins'] + (fish_price if not is_on_boat else 0),
            "guaranteed": True,
            "stars_spent": GUARANTEED_CATCH_COST,
            "rod_broken": rod_broken,
            "current_durability": current_dur,
            "max_durability": max_dur,
            "temp_rod_broken": temp_rod_result.get("broken", False),
            "target_rarity": target_rarity,
            "population_penalty": population_penalty,
            "consecutive_casts": consecutive_casts
        }

    def finalize_fight_catch(
        self,
        user_id: int,
        chat_id: int,
        location: str,
        fish_data: Dict[str, Any],
        weight: float,
        length: float,
        target_rarity: Optional[str] = None,
        guaranteed: bool = False,
    ) -> Dict[str, Any]:
        """Завершает поимку после успешной мини-игры борьбы."""
        player = db.get_player(user_id, chat_id)
        if not player:
            return {
                "success": False,
                "message": "Профиль не найден. Используйте /start в этом чате.",
                "location": location,
            }

        if player.get('current_rod') == 'Гарпун':
            db.init_player_rod(user_id, BAMBOO_ROD, chat_id)
            db.update_player(user_id, chat_id, current_rod=BAMBOO_ROD)
            player = db.get_player(user_id, chat_id) or player

        active_boat = db.get_active_boat_by_user(user_id)
        is_on_boat = active_boat is not None

        damage = self.get_durability_damage(fish_data.get('rarity', 'Обычная'), is_guaranteed=guaranteed)
        db.reduce_rod_durability(user_id, player['current_rod'], damage, chat_id)

        player_rod = db.get_player_rod(user_id, player['current_rod'], chat_id)
        current_dur = player_rod.get('current_durability', 0) if player_rod else 0
        max_dur = player_rod.get('max_durability', 100) if player_rod else 100
        rod_broken = current_dur <= 0

        saved_catch = None
        if is_on_boat:
            db.add_fish_to_boat(user_id, fish_data['id'], float(weight), chat_id, location=location)
        else:
            saved_catch = db.add_caught_fish(
                user_id,
                chat_id,
                fish_data['name'],
                float(weight),
                location,
                float(length),
            )

        if not guaranteed and player['current_bait'].lower() != 'черви':
            used = db.use_bait(user_id, player['current_bait'])
            if not used or db.get_bait_count(user_id, player['current_bait']) == 0:
                db.update_player_bait(user_id, chat_id, 'Черви')

        temp_rod_result = self._consume_temp_rod_use(user_id, chat_id, player['current_rod'])

        xp_earned = db.calculate_item_xp({
            'rarity': fish_data.get('rarity', 'Обычная'),
            'weight': weight,
            'min_weight': fish_data.get('min_weight', 0),
            'max_weight': fish_data.get('max_weight', 0),
            'is_trash': False,
        })
        level_info = db.add_player_xp(user_id, chat_id, xp_earned)

        if not guaranteed:
            self._update_fish_population(location, -1)

        fish_price = db.calculate_fish_price(fish_data, weight, length)
        coins_before = int(player.get('coins', 0) or 0)
        coins_gain = fish_price if (guaranteed and not is_on_boat) else 0
        new_balance = coins_before + coins_gain

        db.update_player(
            user_id,
            chat_id,
            coins=new_balance,
            last_fish_time=datetime.now().isoformat(),
        )

        return {
            "success": True,
            "fish": fish_data,
            "weight": weight,
            "length": length,
            "location": location,
            "earned": coins_gain,
            "new_balance": new_balance,
            "xp_earned": xp_earned,
            "level_info": level_info,
            "guaranteed": guaranteed,
            "stars_spent": GUARANTEED_CATCH_COST if guaranteed else 0,
            "rod_broken": rod_broken,
            "current_durability": current_dur,
            "max_durability": max_dur,
            "is_on_boat": is_on_boat,
            "temp_rod_broken": temp_rod_result.get("broken", False),
            "target_rarity": target_rarity or fish_data.get('rarity'),
            "fish_price": fish_price,
            "catch_id": (saved_catch or {}).get('id') if isinstance(saved_catch, dict) else None,
        }
    
    def _update_fish_population(self, location: str, delta: int):
        """Обновить популяцию рыбы на локации"""
        db.update_location_players(location, delta)

# Глобальный экземпляр игры
game = FishingGame()
