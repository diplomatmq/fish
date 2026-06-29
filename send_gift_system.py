# -*- coding: utf-8 -*-
"""
Система отправки подарков между игроками через команду /send.
Требует оплату 25 звезд для отправки.
"""

import logging
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Константы
SEND_GIFT_STARS = 25
SEND_GIFT_TITLE = "Отправка подарка"
SEND_GIFT_DESCRIPTION = "Оплата за отправку подарка другому игроку"

# Типы подарков
GIFT_TYPE_COINS = "coins"
GIFT_TYPE_RODS = "rods"
GIFT_TYPE_BAITS = "baits"
GIFT_TYPE_NETS = "nets"
GIFT_TYPE_CLOTHING = "clothing"

# Названия для отображения
GIFT_TYPE_NAMES = {
    GIFT_TYPE_COINS: "💰 Монеты",
    GIFT_TYPE_RODS: "🎣 Удочки",
    GIFT_TYPE_BAITS: "🪱 Наживки",
    GIFT_TYPE_NETS: "🕸️ Сети",
    GIFT_TYPE_CLOTHING: "👕 Одежда",
}


def get_send_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню отправки подарков."""
    keyboard = [
        [InlineKeyboardButton(GIFT_TYPE_NAMES[GIFT_TYPE_COINS], callback_data=f"send_select_{GIFT_TYPE_COINS}")],
        [InlineKeyboardButton(GIFT_TYPE_NAMES[GIFT_TYPE_RODS], callback_data=f"send_select_{GIFT_TYPE_RODS}")],
        [InlineKeyboardButton(GIFT_TYPE_NAMES[GIFT_TYPE_BAITS], callback_data=f"send_select_{GIFT_TYPE_BAITS}")],
        [InlineKeyboardButton(GIFT_TYPE_NAMES[GIFT_TYPE_NETS], callback_data=f"send_select_{GIFT_TYPE_NETS}")],
        [InlineKeyboardButton(GIFT_TYPE_NAMES[GIFT_TYPE_CLOTHING], callback_data=f"send_select_{GIFT_TYPE_CLOTHING}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="send_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_rods_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора удочки."""
    from database import db
    
    # Получаем все удочки
    all_rods = db.get_all_rods()
    
    # Пагинация
    page_size = 8
    start = page * page_size
    end = start + page_size
    page_rods = all_rods[start:end]
    
    keyboard = []
    for rod in page_rods:
        rod_name = rod['name']
        rod_price = rod.get('price', 0)
        button_text = f"{rod_name} ({rod_price} 🪙)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"send_rod_{rod_name}")])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"send_rods_page_{page-1}"))
    if end < len(all_rods):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"send_rods_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="send_back_main")])
    
    return InlineKeyboardMarkup(keyboard)


def get_clothing_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора одежды."""
    import bot
    
    # Пагинация
    page_size = 8
    start = page * page_size
    end = start + page_size
    page_items = bot.CLOTHING_ITEMS[start:end]
    
    keyboard = []
    for item in page_items:
        item_code = item['code']
        item_name = item['name']
        item_price = item['price_diamonds']
        button_text = f"{item_name} ({item_price} 💎)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"send_clothing_{item_code}")])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"send_clothing_page_{page-1}"))
    if end < len(bot.CLOTHING_ITEMS):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"send_clothing_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="send_back_main")])
    
    return InlineKeyboardMarkup(keyboard)


def get_bait_locations_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора локации для наживок."""
    from database import db
    
    locations = db.get_all_locations()
    
    keyboard = []
    for location in locations[:10]:  # Первые 10 локаций
        keyboard.append([InlineKeyboardButton(location, callback_data=f"send_bait_loc_{location}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="send_back_main")])
    
    return InlineKeyboardMarkup(keyboard)


def get_baits_for_location_keyboard(location: str, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора наживки для локации."""
    from database import db
    
    # Получаем наживки для локации
    all_baits = db.get_baits_for_location(location)
    
    # Пагинация
    page_size = 8
    start = page * page_size
    end = start + page_size
    page_baits = all_baits[start:end]
    
    keyboard = []
    for bait in page_baits:
        bait_name = bait['name']
        bait_price = bait.get('price', 0)
        button_text = f"{bait_name} ({bait_price} 🪙)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"send_bait_{bait_name}")])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"send_baits_page_{location}_{page-1}"))
    if end < len(all_baits):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"send_baits_page_{location}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Выбор локации", callback_data="send_select_baits")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="send_back_main")])
    
    return InlineKeyboardMarkup(keyboard)


def validate_gift_item(user_id: int, chat_id: int, gift_type: str, item_name: str, quantity: int = 1) -> tuple[bool, str]:
    """
    Проверить может ли пользователь отправить подарок.
    
    Returns:
        (success, error_message)
    """
    from database import db
    import bot
    
    player = db.get_player(user_id, chat_id)
    if not player:
        return False, "Профиль не найден"
    
    if gift_type == GIFT_TYPE_COINS:
        if player.get('coins', 0) < quantity:
            return False, f"Недостаточно монет. У вас: {player.get('coins', 0)} 🪙"
        return True, ""
    
    elif gift_type == GIFT_TYPE_NETS:
        if player.get('nets', 0) < quantity:
            return False, f"Недостаточно сетей. У вас: {player.get('nets', 0)}"
        return True, ""
    
    elif gift_type == GIFT_TYPE_RODS:
        # Проверяем наличие удочки
        rod = db.get_player_rod(user_id, item_name, chat_id)
        if not rod:
            return False, f"У вас нет удочки {item_name}"
        
        # Проверяем стоимость удочки
        rod_data = db.get_rod(item_name)
        if not rod_data:
            return False, "Удочка не найдена в базе"
        
        rod_price = rod_data.get('price', 0)
        if player.get('coins', 0) < rod_price:
            return False, f"Недостаточно монет. Нужно: {rod_price} 🪙, у вас: {player.get('coins', 0)} 🪙"
        
        return True, ""
    
    elif gift_type == GIFT_TYPE_BAITS:
        bait_count = db.get_bait_count(user_id, item_name)
        if bait_count < quantity:
            return False, f"Недостаточно наживки {item_name}. У вас: {bait_count}"
        
        # Проверяем стоимость наживки
        bait_data = db.get_bait(item_name)
        if not bait_data:
            return False, "Наживка не найдена в базе"
        
        bait_price = bait_data.get('price', 0) * quantity
        if player.get('coins', 0) < bait_price:
            return False, f"Недостаточно монет. Нужно: {bait_price} 🪙, у вас: {player.get('coins', 0)} 🪙"
        
        return True, ""
    
    elif gift_type == GIFT_TYPE_CLOTHING:
        # Проверяем наличие одежды
        clothing = db.get_player_clothing(user_id, item_name)
        if not clothing:
            return False, f"У вас нет одежды {item_name}"
        
        # Проверяем стоимость
        clothing_data = bot.CLOTHING_ITEM_BY_CODE.get(item_name)
        if not clothing_data:
            return False, "Одежда не найдена"
        
        price_diamonds = clothing_data.get('price_diamonds', 0)
        if player.get('diamonds', 0) < price_diamonds:
            return False, f"Недостаточно бриллиантов. Нужно: {price_diamonds} 💎, у вас: {player.get('diamonds', 0)} 💎"
        
        return True, ""
    
    return False, "Неизвестный тип подарка"


def execute_gift_transfer(
    sender_id: int,
    sender_chat_id: int,
    recipient_id: int,
    recipient_chat_id: int,
    gift_type: str,
    item_name: str,
    quantity: int = 1
) -> tuple[bool, str]:
    """
    Выполнить передачу подарка.
    
    Returns:
        (success, message)
    """
    from database import db
    import bot
    
    try:
        if gift_type == GIFT_TYPE_COINS:
            # Списываем у отправителя
            sender = db.get_player(sender_id, sender_chat_id)
            db.update_player(sender_id, sender_chat_id, coins=sender['coins'] - quantity)
            
            # Добавляем получателю
            recipient = db.get_player(recipient_id, recipient_chat_id)
            db.update_player(recipient_id, recipient_chat_id, coins=recipient['coins'] + quantity)
            
            return True, f"Отправлено {quantity} 🪙 монет"
        
        elif gift_type == GIFT_TYPE_NETS:
            # Списываем у отправителя
            sender = db.get_player(sender_id, sender_chat_id)
            db.update_player(sender_id, sender_chat_id, nets=sender['nets'] - quantity)
            
            # Добавляем получателю
            recipient = db.get_player(recipient_id, recipient_chat_id)
            db.update_player(recipient_id, recipient_chat_id, nets=recipient['nets'] + quantity)
            
            return True, f"Отправлено {quantity} сетей"
        
        elif gift_type == GIFT_TYPE_RODS:
            # Списываем монеты у отправителя
            rod_data = db.get_rod(item_name)
            rod_price = rod_data.get('price', 0)
            sender = db.get_player(sender_id, sender_chat_id)
            db.update_player(sender_id, sender_chat_id, coins=sender['coins'] - rod_price)
            
            # Выдаем удочку получателю (с стаканием)
            db.grant_rod(recipient_id, item_name, recipient_chat_id, stack=True)
            
            return True, f"Отправлена удочка {item_name}"
        
        elif gift_type == GIFT_TYPE_BAITS:
            # Списываем наживку у отправителя
            db.remove_bait(sender_id, item_name, quantity)
            
            # Списываем монеты
            bait_data = db.get_bait(item_name)
            bait_price = bait_data.get('price', 0) * quantity
            sender = db.get_player(sender_id, sender_chat_id)
            db.update_player(sender_id, sender_chat_id, coins=sender['coins'] - bait_price)
            
            # Добавляем наживку получателю
            db.add_bait(recipient_id, item_name, quantity)
            
            return True, f"Отправлено {quantity}x {item_name}"
        
        elif gift_type == GIFT_TYPE_CLOTHING:
            # Списываем бриллианты у отправителя
            clothing_data = bot.CLOTHING_ITEM_BY_CODE.get(item_name)
            price_diamonds = clothing_data.get('price_diamonds', 0)
            sender = db.get_player(sender_id, sender_chat_id)
            db.update_player(sender_id, sender_chat_id, diamonds=sender['diamonds'] - price_diamonds)
            
            # Выдаем одежду получателю
            db.add_clothing(recipient_id, item_name)
            
            return True, f"Отправлена одежда {clothing_data['name']}"
        
        return False, "Неизвестный тип подарка"
    
    except Exception as e:
        logger.error(f"Error executing gift transfer: {e}", exc_info=True)
        return False, f"Ошибка при передаче: {str(e)}"


def find_user_by_username_or_id(username_or_id: str) -> Optional[Dict[str, Any]]:
    """
    Найти пользователя по username или ID.
    
    Args:
        username_or_id: @username или ID пользователя
    
    Returns:
        Словарь с данными пользователя или None
    """
    from database import db
    
    # Убираем @ если есть
    clean_input = username_or_id.lstrip('@').strip()
    
    # Пробуем как ID
    if clean_input.isdigit():
        user_id = int(clean_input)
        # Проверяем существование профиля
        if db.has_any_player_profile(user_id):
            return {"user_id": user_id, "found_by": "id"}
    
    # Пробуем как username
    player = db.get_player_by_username(clean_input)
    if player:
        return {"user_id": player['user_id'], "found_by": "username", "username": clean_input}
    
    return None
