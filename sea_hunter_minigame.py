#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мини-игра "Морской охотник" - поле 5x5 с кнопками
Случайно появляется при рыбалке (30% шанс)

Работает для:
- Бесплатной рыбалки (команда /fish)
- Оплаченной рыбалки (гарантированный улов за 1 звезду)

ВАЖНО: Эта мини-игра работает ТОЛЬКО в текстовой части Telegram бота,
       НЕ в мини-приложении (chat_id != -1)
"""
import random
from typing import Dict, List, Tuple, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Кастомные эмодзи для игры
EMOJI_DEFAULT = "5463406036410969564"  # Базовый эмодзи (волна)
EMOJI_FISH = "5411555580600936946"     # Рыба
EMOJI_MISS = "5210952531676504517"     # Промах
EMOJI_BEAR = "5397915559037785261"     # Медведь

# Состав поля (всего 25 клеток)
FIELD_SIZE = 5
TOTAL_CELLS = FIELD_SIZE * FIELD_SIZE

# Бесплатная рыбалка
BEAR_COUNT = 1
MISS_COUNT = 13
FISH_COUNT = 11

# Платная рыбалка (гарантированный улов)
PAID_BEAR_COUNT = 1
PAID_FISH_COUNT = 24  # Все остальные клетки - рыба

# Хранилище активных игр: {user_id: GameState}
active_games: Dict[int, 'SeaHunterGame'] = {}


class SeaHunterGame:
    """Состояние одной игры"""
    
    def __init__(self, user_id: int, username: str, location: str, is_paid: bool = False):
        self.user_id = user_id
        self.username = username
        self.location = location
        self.is_paid = is_paid  # Платная рыбалка (гарантированный улов)
        self.field: List[str] = []  # Скрытое поле с типами клеток
        self.revealed: List[bool] = [False] * TOTAL_CELLS  # Открыты ли клетки
        self.game_over = False
        self.result_type: Optional[str] = None  # 'fish', 'bear', 'miss'
        self.selected_position: Optional[int] = None
        
        self._generate_field()
    
    def _generate_field(self):
        """Генерирует случайное поле с заданным составом"""
        if self.is_paid:
            # Платная рыбалка: 24 рыбы + 1 медведь (БЕЗ промахов)
            cells = (
                ['bear'] * PAID_BEAR_COUNT +
                ['fish'] * PAID_FISH_COUNT
            )
        else:
            # Бесплатная рыбалка: 11 рыб + 13 промахов + 1 медведь
            cells = (
                ['bear'] * BEAR_COUNT +
                ['miss'] * MISS_COUNT +
                ['fish'] * FISH_COUNT
            )
        
        # Проверка правильности количества
        if len(cells) != TOTAL_CELLS:
            raise ValueError(f"Invalid field composition: {len(cells)} != {TOTAL_CELLS}")
        
        # Перемешиваем
        random.shuffle(cells)
        self.field = cells
    
    def get_emoji_for_cell(self, position: int, revealed: bool = False) -> str:
        """Возвращает эмодзи для клетки"""
        if not revealed:
            return EMOJI_DEFAULT
        
        cell_type = self.field[position]
        if cell_type == 'fish':
            return EMOJI_FISH
        elif cell_type == 'bear':
            return EMOJI_BEAR
        elif cell_type == 'miss':
            return EMOJI_MISS
        else:
            return EMOJI_DEFAULT
    
    def get_button_style(self, position: int) -> str:
        """Возвращает стиль кнопки (PRIMARY или SUCCESS)"""
        if self.selected_position == position:
            return 'SUCCESS'  # Зеленая кнопка для выбранной клетки
        return 'PRIMARY'  # Синяя кнопка для всех остальных
    
    def make_choice(self, position: int) -> Tuple[str, str]:
        """
        Обрабатывает выбор клетки
        Возвращает: (result_type, message)
        """
        if self.game_over:
            return self.result_type, "Игра уже завершена"
        
        if position < 0 or position >= TOTAL_CELLS:
            return 'error', "Неверная позиция"
        
        self.selected_position = position
        self.revealed = [True] * TOTAL_CELLS  # Открываем все клетки
        self.game_over = True
        
        cell_type = self.field[position]
        self.result_type = cell_type
        
        if cell_type == 'fish':
            return 'fish', "🎣 Вы поймали рыбу!"
        elif cell_type == 'bear':
            return 'bear', "🐻 Поздравляю! Вы выбили медведя!"
        elif cell_type == 'miss':
            return 'miss', "💨 Промах! Попробуйте еще раз в следующий раз."
        else:
            return 'error', "Неизвестный тип клетки"
    
    def build_keyboard(self) -> InlineKeyboardMarkup:
        """Строит клавиатуру 5x5"""
        keyboard = []
        
        for row in range(FIELD_SIZE):
            row_buttons = []
            for col in range(FIELD_SIZE):
                position = row * FIELD_SIZE + col
                emoji_id = self.get_emoji_for_cell(position, self.revealed[position])
                style = self.get_button_style(position)
                
                # Формируем кнопку
                button = InlineKeyboardButton(
                    text=" ",  # Текст кнопки (можно пустой, т.к. эмодзи в custom_emoji_id)
                    callback_data=f"sea_hunter:{self.user_id}:{position}",
                )
                
                # Добавляем кастомные параметры (требуется python-telegram-bot >= 22.8)
                button.custom_emoji_id = emoji_id
                
                # Устанавливаем стиль кнопки
                if style == 'SUCCESS':
                    button.style = 'success'  # Зеленая
                else:
                    button.style = 'primary'  # Синяя (по умолчанию)
                
                row_buttons.append(button)
            
            keyboard.append(row_buttons)
        
        return InlineKeyboardMarkup(keyboard)


def should_trigger_minigame() -> bool:
    """Проверяет, должна ли мини-игра сработать (30% шанс)"""
    return random.random() < 0.30


def start_game(user_id: int, username: str, location: str, is_paid: bool = False) -> SeaHunterGame:
    """Начинает новую игру для пользователя"""
    game = SeaHunterGame(user_id, username, location, is_paid=is_paid)
    active_games[user_id] = game
    return game


def get_game(user_id: int) -> Optional[SeaHunterGame]:
    """Получает активную игру пользователя"""
    return active_games.get(user_id)


def end_game(user_id: int):
    """Завершает игру пользователя"""
    if user_id in active_games:
        del active_games[user_id]


def format_game_message(game: SeaHunterGame) -> str:
    """Форматирует текст сообщения игры"""
    if not game.game_over:
        if game.is_paid:
            # Платная рыбалка
            return (
                "🎯 <b>Морской охотник (Гарантированный улов)</b>\n\n"
                "Выберите одну клетку на поле!\n"
                "В поле спрятаны:\n"
                "🐟 24 рыбы - получите улов\n"
                "🐻 1 медведь - редкий приз!\n\n"
                "⭐ Промахов нет - результат гарантирован!\n\n"
                "Удачи! 🍀"
            )
        else:
            # Бесплатная рыбалка
            return (
                "🎯 <b>Морской охотник</b>\n\n"
                "Выберите одну клетку на поле!\n"
                "В поле спрятаны:\n"
                "🐟 11 рыб - получите улов\n"
                "💨 13 промахов - ничего не получите\n"
                "🐻 1 медведь - редкий приз!\n\n"
                "Удачи! 🍀"
            )
    else:
        return (
            f"🎯 <b>Морской охотник - Результат</b>\n\n"
            f"{game.result_type.upper()}"
        )
