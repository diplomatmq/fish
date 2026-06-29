# -*- coding: utf-8 -*-
"""
Система выдачи наград за достижения.
Проверяет всех игроков и выдает награды за достижения асинхронно.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from database import db
from achievements import ACHIEVEMENTS, highest_reachable_tier, get_tier_reward, tier_title, format_reward_message

logger = logging.getLogger(__name__)


async def grant_achievement_reward(user_id: int, chat_id: int, achievement_id: str, tier: int) -> bool:
    """
    Выдать награду за достижение.
    
    Args:
        user_id: ID пользователя
        chat_id: ID чата
        achievement_id: ID достижения
        tier: Тир достижения
    
    Returns:
        True если награда выдана успешно
    """
    try:
        reward = get_tier_reward(achievement_id, tier)
        if not reward:
            return False
        
        # Выдаем монеты
        if "coins" in reward:
            coins = int(reward["coins"])
            db.update_player(user_id, chat_id, coins=db.get_player(user_id, chat_id)['coins'] + coins)
            logger.info(f"Granted {coins} coins to user {user_id} for achievement {achievement_id} tier {tier}")
        
        # Выдаем сети
        if "nets" in reward:
            nets = int(reward["nets"])
            current_nets = db.get_player(user_id, chat_id).get('nets', 0)
            db.update_player(user_id, chat_id, nets=current_nets + nets)
            logger.info(f"Granted {nets} nets to user {user_id} for achievement {achievement_id} tier {tier}")
        
        # Выдаем удочку (с учетом стакания)
        if "rod" in reward:
            rod_name = str(reward["rod"])
            db.grant_rod(user_id, chat_id, rod_name, stack=True)
            logger.info(f"Granted rod {rod_name} to user {user_id} for achievement {achievement_id} tier {tier}")
        
        return True
    except Exception as e:
        logger.error(f"Error granting reward for user {user_id}: {e}", exc_info=True)
        return False


async def check_and_grant_achievements_for_player(
    user_id: int,
    chat_id: int,
    bot_instance,
    send_notification: bool = True
) -> List[Dict[str, Any]]:
    """
    Проверить достижения игрока и выдать награды.
    
    Args:
        user_id: ID пользователя
        chat_id: ID чата
        bot_instance: Экземпляр бота для отправки уведомлений
        send_notification: Отправлять ли уведомление в ЛС
    
    Returns:
        Список выданных наград
    """
    granted_rewards = []
    
    try:
        player = db.get_player(user_id, chat_id)
        if not player:
            return granted_rewards
        
        # Получаем статистику
        stats = db.get_player_statistics(user_id, chat_id)
        
        # Проверяем каждое достижение
        for achievement in ACHIEVEMENTS:
            achievement_id = achievement["id"]
            stat_name = achievement["stat"]
            stat_value = stats.get(stat_name, 0)
            
            # Определяем какой тир должен быть у игрока
            target_tier = highest_reachable_tier(achievement_id, stat_value)
            
            if target_tier == 0:
                continue
            
            # Проверяем какой тир уже получен
            current_tier = db.get_achievement_tier(user_id, achievement_id)
            
            # Выдаем награды за все пропущенные тиры
            for tier in range(current_tier + 1, target_tier + 1):
                # Отмечаем достижение как полученное
                db.unlock_achievement_tier(user_id, achievement_id, tier)
                
                # Выдаем награду
                success = await grant_achievement_reward(user_id, chat_id, achievement_id, tier)
                
                if success:
                    reward = get_tier_reward(achievement_id, tier)
                    granted_rewards.append({
                        "achievement_id": achievement_id,
                        "tier": tier,
                        "reward": reward
                    })
                    
                    logger.info(f"Granted achievement {achievement_id} tier {tier} to user {user_id}")
        
        # Отправляем уведомление если есть награды
        if granted_rewards and send_notification:
            await send_achievement_notification(user_id, bot_instance, granted_rewards)
    
    except Exception as e:
        logger.error(f"Error checking achievements for user {user_id}: {e}", exc_info=True)
    
    return granted_rewards


async def send_achievement_notification(
    user_id: int,
    bot_instance,
    granted_rewards: List[Dict[str, Any]]
):
    """
    Отправить уведомление о полученных достижениях в ЛС.
    
    Args:
        user_id: ID пользователя
        bot_instance: Экземпляр бота
        granted_rewards: Список полученных наград
    """
    if not granted_rewards:
        return
    
    try:
        message_parts = ["🎉 <b>Поздравляем! Вы получили достижения:</b>\n"]
        
        for reward_info in granted_rewards:
            achievement_id = reward_info["achievement_id"]
            tier = reward_info["tier"]
            reward = reward_info["reward"]
            
            title = tier_title(achievement_id, tier)
            reward_text = format_reward_message(reward)
            
            message_parts.append(f"\n🏆 <b>{title}</b>")
            if reward_text:
                message_parts.append(f"   {reward_text}")
        
        message = "\n".join(message_parts)
        
        await bot_instance.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )
        logger.info(f"Sent achievement notification to user {user_id}")
    
    except Exception as e:
        # Если не удалось отправить (например, бот не в ЛС), просто логируем
        logger.info(f"Could not send achievement notification to user {user_id}: {e}")


async def process_all_players_achievements(bot_instance, batch_size: int = 50):
    """
    Проверить достижения для всех игроков асинхронно.
    Обрабатывает игроков батчами чтобы не перегружать систему.
    
    Args:
        bot_instance: Экземпляр бота
        batch_size: Размер батча для обработки
    """
    logger.info("Starting achievement rewards processing for all players...")
    
    try:
        # Получаем всех игроков
        all_players = db.get_all_players()
        total_players = len(all_players)
        
        logger.info(f"Found {total_players} players to process")
        
        processed = 0
        total_rewards = 0
        
        # Обрабатываем батчами
        for i in range(0, total_players, batch_size):
            batch = all_players[i:i + batch_size]
            
            # Создаем задачи для батча
            tasks = []
            for player in batch:
                user_id = player['user_id']
                chat_id = player.get('chat_id', user_id)
                
                task = check_and_grant_achievements_for_player(
                    user_id,
                    chat_id,
                    bot_instance,
                    send_notification=True
                )
                tasks.append(task)
            
            # Выполняем батч параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Подсчитываем результаты
            for result in results:
                if isinstance(result, list):
                    total_rewards += len(result)
                    processed += 1
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(total_players-1)//batch_size + 1}: {processed}/{total_players} players")
            
            # Небольшая пауза между батчами
            await asyncio.sleep(0.5)
        
        logger.info(f"Achievement processing complete: {processed} players processed, {total_rewards} rewards granted")
        
        return {
            "total_players": total_players,
            "processed": processed,
            "total_rewards": total_rewards
        }
    
    except Exception as e:
        logger.error(f"Error in process_all_players_achievements: {e}", exc_info=True)
        return None
