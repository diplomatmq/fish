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
import time
from typing import Any, Dict, List, Tuple, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Кастомные эмодзи для игры
EMOJI_DEFAULT = "5463406036410969564"  # Базовый эмодзи (волна)
EMOJI_FISH = "5411555580600936946"     # Рыба
EMOJI_MISS = "5210952531676504517"     # Промах
EMOJI_DIAMOND = "5366124516055487969"  # Бриллиант на поле
EMOJI_BEAR = "5427168083074628963"     # Медведь (кастомный эмодзи)

DIAMOND_CELL_HTML = '<tg-emoji emoji-id="5366124516055487969">💎</tg-emoji>'
BEAR_CELL_HTML = '<tg-emoji emoji-id="5427168083074628963">🐻</tg-emoji>'

SPECIAL_BEAR_CHANCE = 0.15  # иначе 85% — бриллиант

# Состав поля (всего 25 клеток)
FIELD_SIZE = 5
TOTAL_CELLS = FIELD_SIZE * FIELD_SIZE

# Время активности кнопок (секунды)
GAME_ACTIVE_SECONDS = 60

# Бесплатная рыбалка: 11 рыб + 13 промахов + 1 особая клетка (💎 или медведь)
FREE_MISS_COUNT = 13
FREE_FISH_COUNT = 11

# Платная рыбалка: 24 рыбы + 1 особая клетка
PAID_FISH_COUNT = 24

# Хранилище активных игр: {user_id: GameState}
active_games: Dict[int, 'SeaHunterGame'] = {}


class SeaHunterGame:
    """Состояние одной игры"""
    
    def __init__(
        self,
        user_id: int,
        username: str,
        location: str,
        is_paid: bool = False,
        pending_catch_result: Optional[Dict[str, Any]] = None,
        paid_delivery: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.location = location
        self.is_paid = is_paid  # Платная рыбалка (гарантированный улов)
        self.pending_catch_result = pending_catch_result
        self.paid_delivery = paid_delivery or {}
        self.field: List[str] = []  # Скрытое поле с типами клеток
        self.revealed: List[bool] = [False] * TOTAL_CELLS  # Открыты ли клетки
        self.game_over = False
        self.result_type: Optional[str] = None  # 'fish', 'diamond', 'bear', 'miss'
        self.selected_position: Optional[int] = None
        self.started_at = time.time()
        
        self._generate_field()
    
    def is_expired(self) -> bool:
        """Истекло ли время выбора (кнопки остаются, но не принимают ход)."""
        return (time.time() - self.started_at) >= GAME_ACTIVE_SECONDS
    
    def _generate_field(self):
        """Генерирует случайное поле с заданным составом"""
        special_cell = 'bear' if random.random() < SPECIAL_BEAR_CHANCE else 'diamond'

        if self.is_paid:
            cells = ['fish'] * PAID_FISH_COUNT + [special_cell]
        else:
            cells = (
                ['miss'] * FREE_MISS_COUNT +
                ['fish'] * FREE_FISH_COUNT +
                [special_cell]
            )
        
        if len(cells) != TOTAL_CELLS:
            raise ValueError(f"Invalid field composition: {len(cells)} != {TOTAL_CELLS}")
        
        random.shuffle(cells)
        self.field = cells
    
    def get_emoji_for_cell(self, position: int, revealed: bool = False) -> str:
        """Возвращает эмодзи для клетки"""
        if not revealed:
            return EMOJI_DEFAULT
        
        cell_type = self.field[position]
        if cell_type == 'fish':
            return EMOJI_FISH
        elif cell_type == 'diamond':
            return EMOJI_DIAMOND
        elif cell_type == 'bear':
            return EMOJI_BEAR
        elif cell_type == 'miss':
            return EMOJI_MISS
        else:
            return EMOJI_DEFAULT
    
    def make_choice(self, position: int) -> Tuple[str, str]:
        """
        Обрабатывает выбор клетки
        Возвращает: (result_type, message)
        """
        if self.game_over:
            return self.result_type or 'finished', "Игра уже завершена"

        if self.is_expired():
            return 'expired', "⏱ Время вышло! Кнопки больше не активны."
        
        if position < 0 or position >= TOTAL_CELLS:
            return 'error', "Неверная позиция"
        
        self.selected_position = position
        self.revealed = [True] * TOTAL_CELLS  # Открываем все клетки
        self.game_over = True
        
        cell_type = self.field[position]
        self.result_type = cell_type
        
        if cell_type == 'fish':
            return 'fish', "🎣 Вы поймали рыбу!"
        elif cell_type == 'diamond':
            return 'diamond', f"{DIAMOND_CELL_HTML} Поздравляю! Вы поймали бриллиант!"
        elif cell_type == 'bear':
            return 'bear', f"{BEAR_CELL_HTML} Поздравляю! Вы выбили медведя!"
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
                
                # Определяем стиль кнопки
                if self.selected_position == position:
                    button_style = 'success'  # Зеленая для выбранной
                else:
                    button_style = 'primary'  # Синяя для остальных
                
                button = InlineKeyboardButton(
                    text=" ",
                    callback_data=f"sea_hunter:{self.user_id}:{position}",
                    icon_custom_emoji_id=emoji_id,
                    style=button_style,
                )
                row_buttons.append(button)
            
            keyboard.append(row_buttons)
        
        return InlineKeyboardMarkup(keyboard)


def should_trigger_minigame() -> bool:
    """Проверяет, должна ли мини-игра сработать (30% шанс)"""
    return random.random() < 0.30


def start_game(
    user_id: int,
    username: str,
    location: str,
    is_paid: bool = False,
    pending_catch_result: Optional[Dict[str, Any]] = None,
    paid_delivery: Optional[Dict[str, Any]] = None,
) -> SeaHunterGame:
    """Начинает новую игру для пользователя"""
    game = SeaHunterGame(
        user_id,
        username,
        location,
        is_paid=is_paid,
        pending_catch_result=pending_catch_result,
        paid_delivery=paid_delivery,
    )
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
    special_line = (
        f"Особая клетка (1 шт.): {DIAMOND_CELL_HTML} бриллиант/"
        f"{BEAR_CELL_HTML} медведь\n"
    )
    if not game.game_over:
        if game.is_paid:
            return (
                "🎯 <b>Морской охотник (Гарантированный улов)</b>\n\n"
                "Выберите одну клетку на поле!\n"
                "У вас <b>1 минута</b> на выбор — после этого кнопки останутся, но не будут реагировать.\n\n"
                "В поле спрятаны:\n"
                "🐟 24 рыбы — получите улов\n"
                f"{special_line}"
                "⭐ Промахов нет — результат гарантирован!\n\n"
                "Удачи! 🍀"
            )
        else:
            return (
                "🎯 <b>Морской охотник</b>\n\n"
                "Выберите одну клетку на поле!\n"
                "У вас <b>1 минута</b> на выбор — после этого кнопки останутся, но не будут реагировать.\n\n"
                "В поле спрятаны:\n"
                "🐟 11 рыб — получите улов\n"
                "💨 13 промахов — ничего не получите\n"
                f"{special_line}"
                "Удачи! 🍀"
            )
    else:
        return (
            f"🎯 <b>Морской охотник - Результат</b>\n\n"
            f"{game.result_type.upper()}"
        )
