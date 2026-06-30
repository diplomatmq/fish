# -*- coding: utf-8 -*-
"""
Система событий на локациях для рыбалки.
Включает: эко-катастрофа, нерест, убийство, стайный инстинкт.

ВАЖНЫЕ ПРАВИЛА:
1. На одной локации может быть активно только ОДНО событие одновременно
2. Каждый тип события может быть активен только на ОДНОЙ локации
3. Это обеспечивается логикой в database.py (maybe_start_location_event)
"""
import random
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

# ===== КОНСТАНТЫ СОБЫТИЙ =====

# Эко-катастрофа (уже существующее событие)
ECO_DISASTER_TYPE = "eco_disaster"
ECO_DISASTER_CHANCE = 0.0005  # 0.05%
ECO_DISASTER_MIN_DURATION = 60  # минут
ECO_DISASTER_MAX_DURATION = 120  # минут
ECO_DISASTER_COOLDOWN_HOURS = 3

# Нерест - +20% к улову
SPAWN_EVENT_TYPE = "spawn"
SPAWN_EVENT_CHANCE = 0.001  # 0.1%
SPAWN_CATCH_BONUS = 20  # +20% к шансу поймать рыбу (не мусор)
SPAWN_MIN_DURATION = 45  # минут
SPAWN_MAX_DURATION = 90  # минут
SPAWN_COOLDOWN_HOURS = 6

# Убийство - рандомно выбирает рыбу, падает только она
MURDER_EVENT_TYPE = "murder"
MURDER_EVENT_CHANCE = 0.0003  # 0.03% - очень редкое
MURDER_MIN_DURATION = 30  # минут
MURDER_MAX_DURATION = 60  # минут
MURDER_COOLDOWN_HOURS = 12

# Стайный инстинкт - бонус к весу за цепочку одного вида
SCHOOL_EVENT_TYPE = "school_instinct"
SCHOOL_EVENT_CHANCE = 0.0008  # 0.08%
SCHOOL_MIN_DURATION = 60  # минут
SCHOOL_MAX_DURATION = 120  # минут
SCHOOL_COOLDOWN_HOURS = 8
SCHOOL_WEIGHT_BONUS_PER_CATCH = 10  # +10% за каждую рыбу
SCHOOL_MAX_BONUS = 50  # максимум +50%
SCHOOL_MAX_CHAIN = 5  # 5 рыб подряд для макс. бонуса


@dataclass
class LocationEvent:
    """Структура для описания события на локации."""
    event_id: int
    event_type: str
    location: str
    started_at: datetime
    ends_at: datetime
    is_active: bool
    # Дополнительные параметры (JSON)
    params: Dict[str, Any]


# ===== ОПИСАНИЕ СОБЫТИЙ =====

EVENT_DESCRIPTIONS = {
    ECO_DISASTER_TYPE: {
        "name": "🌪️ Эко-катастрофа",
        "description": "Клюёт только мусор, но награда за него увеличена!",
    },
    SPAWN_EVENT_TYPE: {
        "name": "🐟 Нерест",
        "description": "Рыба активно клюёт! Шанс поймать рыбу увеличен на +20%.",
    },
    MURDER_EVENT_TYPE: {
        "name": "☠️ Убийство",
        "description": "В воде замечена только одна особь... Ловится только один вид рыбы!",
    },
    SCHOOL_EVENT_TYPE: {
        "name": "🐠 Стайный инстинкт",
        "description": "Огромная стая одного вида! Ловите одну рыбу подряд, чтобы получить бонус к весу (+10% за каждую, до +50%).",
    },
}


def get_event_description(event_type: str) -> Dict[str, str]:
    """Получить описание события."""
    return EVENT_DESCRIPTIONS.get(event_type, {
        "name": "Неизвестное событие",
        "description": "Что-то происходит на локации...",
    })


def calculate_event_chance(event_type: str) -> float:
    """Получить базовый шанс срабатывания события."""
    chances = {
        ECO_DISASTER_TYPE: ECO_DISASTER_CHANCE,
        SPAWN_EVENT_TYPE: SPAWN_EVENT_CHANCE,
        MURDER_EVENT_TYPE: MURDER_EVENT_CHANCE,
        SCHOOL_EVENT_TYPE: SCHOOL_EVENT_CHANCE,
    }
    return chances.get(event_type, 0.0)


def calculate_event_duration(event_type: str) -> int:
    """Вычислить случайную длительность события в минутах."""
    durations = {
        ECO_DISASTER_TYPE: (ECO_DISASTER_MIN_DURATION, ECO_DISASTER_MAX_DURATION),
        SPAWN_EVENT_TYPE: (SPAWN_MIN_DURATION, SPAWN_MAX_DURATION),
        MURDER_EVENT_TYPE: (MURDER_MIN_DURATION, MURDER_MAX_DURATION),
        SCHOOL_EVENT_TYPE: (SCHOOL_MIN_DURATION, SCHOOL_MAX_DURATION),
    }
    min_dur, max_dur = durations.get(event_type, (60, 120))
    return random.randint(min_dur, max_dur)


def calculate_event_cooldown_hours(event_type: str) -> int:
    """Получить время восстановления (cooldown) события в часах."""
    cooldowns = {
        ECO_DISASTER_TYPE: ECO_DISASTER_COOLDOWN_HOURS,
        SPAWN_EVENT_TYPE: SPAWN_COOLDOWN_HOURS,
        MURDER_EVENT_TYPE: MURDER_COOLDOWN_HOURS,
        SCHOOL_EVENT_TYPE: SCHOOL_COOLDOWN_HOURS,
    }
    return cooldowns.get(event_type, 6)


def generate_event_params(event_type: str, location_fish: list) -> Dict[str, Any]:
    """
    Генерировать параметры события в зависимости от типа.
    
    Args:
        event_type: тип события
        location_fish: список рыб на локации (для убийства и стайного инстинкта)
    
    Returns:
        словарь с параметрами события
    """
    if event_type == ECO_DISASTER_TYPE:
        return {
            "reward_type": random.choice(['xp', 'coins']),
            "reward_multiplier": random.randint(3, 7),
        }
    
    elif event_type == SPAWN_EVENT_TYPE:
        return {
            "catch_bonus_percent": SPAWN_CATCH_BONUS,
        }
    
    elif event_type == MURDER_EVENT_TYPE:
        # Выбираем случайную рыбу из локации
        if location_fish:
            chosen_fish = random.choice(location_fish)
            return {
                "forced_fish": chosen_fish,
            }
        return {}
    
    elif event_type == SCHOOL_EVENT_TYPE:
        # Выбираем случайный вид рыбы для стаи
        if location_fish:
            chosen_fish = random.choice(location_fish)
            return {
                "school_fish": chosen_fish,
                "weight_bonus_per_catch": SCHOOL_WEIGHT_BONUS_PER_CATCH,
                "max_bonus": SCHOOL_MAX_BONUS,
                "max_chain": SCHOOL_MAX_CHAIN,
            }
        return {}
    
    return {}


def format_event_info(event: LocationEvent) -> str:
    """
    Форматировать информацию о событии для отображения игроку.
    
    Args:
        event: объект события
    
    Returns:
        строка с описанием события
    """
    desc = get_event_description(event.event_type)
    name = desc.get("name", "Событие")
    description = desc.get("description", "")
    
    # Время окончания
    now = datetime.utcnow()
    remaining = event.ends_at - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    
    time_str = ""
    if hours > 0:
        time_str = f"{hours}ч {minutes}м"
    else:
        time_str = f"{minutes}м"
    
    result = f"{name}\n{description}\nОсталось: {time_str}"
    
    # Добавляем специфичную информацию
    if event.event_type == ECO_DISASTER_TYPE:
        reward_type = event.params.get("reward_type", "xp")
        multiplier = event.params.get("reward_multiplier", 1)
        reward_name = "опыт" if reward_type == "xp" else "монеты"
        result += f"\nМножитель: x{multiplier} на {reward_name}"
    
    elif event.event_type == SPAWN_EVENT_TYPE:
        bonus = event.params.get("catch_bonus_percent", SPAWN_CATCH_BONUS)
        result += f"\nБонус к улову: +{bonus}%"
    
    elif event.event_type == MURDER_EVENT_TYPE:
        fish = event.params.get("forced_fish", "неизвестная рыба")
        result += f"\nЛовится только: {fish}"
    
    elif event.event_type == SCHOOL_EVENT_TYPE:
        fish = event.params.get("school_fish", "неизвестная рыба")
        bonus = event.params.get("weight_bonus_per_catch", SCHOOL_WEIGHT_BONUS_PER_CATCH)
        max_bonus = event.params.get("max_bonus", SCHOOL_MAX_BONUS)
        result += f"\nСтая: {fish}\nБонус: +{bonus}% за рыбу (макс. +{max_bonus}%)"
    
    return result


def should_apply_spawn_bonus(event: Optional[Dict[str, Any]]) -> Tuple[bool, int]:
    """
    Проверить, нужно ли применять бонус нереста.
    
    Returns:
        (применять ли бонус, процент бонуса)
    """
    if not event or event.get('event_type') != SPAWN_EVENT_TYPE:
        return False, 0
    
    bonus = event.get('params', {}).get("catch_bonus_percent", SPAWN_CATCH_BONUS)
    return True, bonus


def should_force_murder_fish(event: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Проверить, нужно ли принудительно выдавать определенную рыбу (убийство).
    
    Returns:
        (принудительно ли, название рыбы)
    """
    if not event or event.get('event_type') != MURDER_EVENT_TYPE:
        return False, ""
    
    forced_fish = event.get('params', {}).get("forced_fish", "")
    return bool(forced_fish), forced_fish


def calculate_school_weight_bonus(
    event: Optional[Dict[str, Any]],
    caught_fish_name: str,
    current_chain: int
) -> Tuple[int, bool]:
    """
    Вычислить бонус к весу для стайного инстинкта.
    
    Args:
        event: событие на локации (dict)
        caught_fish_name: название пойманной рыбы
        current_chain: текущая цепочка (сколько рыб поймано подряд)
    
    Returns:
        (процент бонуса к весу, продолжается ли цепочка)
    """
    if not event or event.get('event_type') != SCHOOL_EVENT_TYPE:
        return 0, False
    
    school_fish = event.get('params', {}).get("school_fish", "")
    if not school_fish or caught_fish_name != school_fish:
        # Цепочка прервана
        return 0, False
    
    # Цепочка продолжается
    bonus_per_catch = event.get('params', {}).get("weight_bonus_per_catch", SCHOOL_WEIGHT_BONUS_PER_CATCH)
    max_bonus = event.get('params', {}).get("max_bonus", SCHOOL_MAX_BONUS)
    
    bonus = min(current_chain * bonus_per_catch, max_bonus)
    return bonus, True
