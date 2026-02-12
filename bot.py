# -*- coding: utf-8 -*-
import logging
import html
import sqlite3
import requests
import random
import asyncio
import re
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
# --- Button style helpers for Telegram update ---
def get_button_style(text: str) -> str:
    """Return 'primary' for yes/confirm, 'destructive' for no/cancel, else None."""
    text_lower = text.lower()
    if any(x in text_lower for x in ["да", "подтверд", "yes", "ok", "confirm"]):
        return "primary"
    if any(x in text_lower for x in ["нет", "отмена", "отклон", "cancel", "no", "decline"]):
        return "destructive"
    return None
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, filters, ContextTypes, Defaults, ExtBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.stdout.write("[bot.py] Module loading started\n")
sys.stdout.flush()

# Добавляем текущую директорию в путь для поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db, DB_PATH, BAMBOO_ROD, TEMP_ROD_RANGES
from game_logic import game
from config import BOT_TOKEN, COIN_NAME, STAR_NAME, GUARANTEED_CATCH_COST, get_current_season, RULES_TEXT, RULES_LINK, INFO_LINK
from fish_stickers import FISH_INFO, FISH_STICKERS
from trash_stickers import TRASH_STICKERS
from weather import weather_system

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

COIN_EMOJI_TAG = '<tg-emoji emoji-id="5379600444098093058">🪙</tg-emoji>'
BAG_EMOJI_TAG = '<tg-emoji emoji-id="5375296873982604963">💰</tg-emoji>'
RULER_EMOJI_TAG = '<tg-emoji emoji-id="5323632458975945310">📏</tg-emoji>'
WORM_EMOJI_TAG = '<tg-emoji emoji-id="5233206123036682153">🪱</tg-emoji>'
FISHING_EMOJI_TAG = '<tg-emoji emoji-id="5343609421316521960">🎣</tg-emoji>'
SCALE_EMOJI_TAG = '<tg-emoji emoji-id="5323632458975945310">⚖️</tg-emoji>'
WAIT_EMOJI_TAG = '<tg-emoji emoji-id="5413704112220949842">⏳</tg-emoji>'
BELUGA_EMOJI_TAG = '<tg-emoji emoji-id="5222292529533167322">🐟</tg-emoji>'
WHITE_SHARK_EMOJI_TAG = '<tg-emoji emoji-id="5361632650278744629">🦈</tg-emoji>'
XP_EMOJI_TAG = '<tg-emoji emoji-id="5472164874886846699">✨</tg-emoji>'
FISH_EMOJI_TAGS = [
    '<tg-emoji emoji-id="5397842858126353661">🐟</tg-emoji>',
    '<tg-emoji emoji-id="5382210409824525356">🐟</tg-emoji>',
]
STAR_EMOJI_TAG = '<tg-emoji emoji-id="5463289097336405244">⭐</tg-emoji>'
LOCATION_EMOJI_TAG = '<tg-emoji emoji-id="5821128296217185461">📍</tg-emoji>'
PARTY_EMOJI_TAG = '<tg-emoji emoji-id="5436040291507247633">🎉</tg-emoji>'

def replace_coin_emoji(text: str) -> str:
    if not text:
        return text
    return (
        text
        .replace("🪙", COIN_EMOJI_TAG)
        .replace("💰", BAG_EMOJI_TAG)
        .replace("📏", RULER_EMOJI_TAG)
        .replace("🪱", WORM_EMOJI_TAG)
        .replace("🎣", FISHING_EMOJI_TAG)
        .replace("⚖️", SCALE_EMOJI_TAG)
        .replace("⏳", WAIT_EMOJI_TAG)
        .replace("⏰", WAIT_EMOJI_TAG)
        .replace("✨", XP_EMOJI_TAG)
        .replace("⭐", STAR_EMOJI_TAG)
        .replace("📍", LOCATION_EMOJI_TAG)
        .replace("🎉", PARTY_EMOJI_TAG)
    )


class EmojiBot(ExtBot):
    async def send_message(self, *args, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = replace_coin_emoji(kwargs['text'])
        return await super().send_message(*args, **kwargs)

    async def edit_message_text(self, *args, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = replace_coin_emoji(kwargs['text'])
        return await super().edit_message_text(*args, **kwargs)

def format_level_progress(level_info):
    if not level_info:
        return ""

    level = level_info.get('level', 0)
    next_level_xp = level_info.get('next_level_xp')
    if next_level_xp is None:
        bar = "[" + ("=" * 10) + "]"
        return f"Уровень {level}: {bar} MAX"

    progress = level_info.get('progress', 0.0)
    filled = int(progress * 10)
    filled = max(0, min(10, filled))
    bar = "[" + ("=" * filled) + ("-" * (10 - filled)) + "]"
    xp_into = level_info.get('xp_into_level', 0)
    xp_needed = level_info.get('xp_needed', 0)
    return f"Уровень {level}: {bar} {xp_into}/{xp_needed}"

def calculate_sale_summary(items):
    total_xp = 0
    total_weight_bonus = 0
    total_rarity_bonus = 0
    total_base = 0
    total_weight = 0.0
    for item in items:
        details = db.calculate_item_xp_details(item)
        total_xp += details['xp_total']
        total_weight_bonus += details['weight_bonus']
        total_rarity_bonus += details.get('rarity_bonus', 0)
        total_base += details['xp_base']
        total_weight += float(item.get('weight') or 0)
    return total_xp, total_base, total_rarity_bonus, total_weight_bonus, total_weight

def format_fish_name(name: str) -> str:
    if name == "Белуга":
        return f"{BELUGA_EMOJI_TAG} {name}"
    if name == "Белая акула":
        return f"{WHITE_SHARK_EMOJI_TAG} {name}"
    return f"{random.choice(FISH_EMOJI_TAGS)} {name}"

class FishBot:
    def __init__(self):
        self.scheduler = None  # Будет создан в main() с asyncio loop
        self.user_locations = {}  # Временное хранение локаций пользователей
        self.active_timeouts = {}  # Отслеживание активных таймеров
        self.active_invoices = {}  # Отслеживание активных инвойсов по пользователям
        self.application = None  # Будет установлено в main()

        
    async def cancel_previous_invoice(self, user_id: int):
        """Отменяет предыдущий активный инвойс пользователя"""
        if user_id in self.active_invoices:
            invoice_info = self.active_invoices[user_id]
            chat_id = invoice_info.get('group_chat_id') or invoice_info.get('chat_id')
            message_id = invoice_info.get('group_message_id') or invoice_info.get('message_id')
            
            try:
                # Обновляем предыдущий инвойс с неактивной кнопкой
                keyboard = [
                    [InlineKeyboardButton(
                        f"⏰ Срок действия истек", 
                        callback_data="invoice_cancelled"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if chat_id is not None and message_id is not None:
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="⏰ Срок действия этого инвойса истек",
                        reply_markup=reply_markup
                    )
                
                # Удаляем таймаут для старого инвойса
                timeout_key = f"payment_{chat_id}_{message_id}"
                if timeout_key in self.active_timeouts:
                    del self.active_timeouts[timeout_key]
                
                # Удаляем старый инвойс из активных
                del self.active_invoices[user_id]
                
            except Exception as e:
                # Инвойсы нельзя редактировать после оплаты или если они уже изменены
                logger.error(f"Ошибка отмены предыдущего инвойса: {e}")
                # Просто удаляем инвойс из активных, чтобы не было конфликтов
                if user_id in self.active_invoices:
                    del self.active_invoices[user_id]
    
    async def schedule_timeout(self, chat_id: int, message_id: int, timeout_message: str, timeout_seconds: int = 30, timeout_callback=None):
        """Планирует таймаут для сообщения"""
        timeout_key = f"payment_{chat_id}_{message_id}"
        
        async def handle_timeout():
            try:
                # Проверяем, что таймер все еще активен
                if timeout_key in self.active_timeouts:
                    # Если есть callback, вызываем его
                    if timeout_callback:
                        await timeout_callback(chat_id, message_id)
                    else:
                        # Если нет callback, просто редактируем сообщение
                        try:
                            await self.application.bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=message_id,
                                text=timeout_message,
                                reply_markup=None
                            )
                        except Exception as edit_error:
                            logger.error(f"Ошибка редактирования сообщения: {edit_error}")
                    
                    # Удаляем таймер из активных
                    if timeout_key in self.active_timeouts:
                        del self.active_timeouts[timeout_key]
            except Exception as e:
                logger.error(f"Error handling timeout: {e}")
        
        # Добавляем таймер в активные
        self.active_timeouts[timeout_key] = True
        
        # Планируем выполнение через указанное время
        run_time = datetime.now() + timedelta(seconds=timeout_seconds)
        self.scheduler.add_job(
            handle_timeout,
            trigger=DateTrigger(run_date=run_time),
            id=f"timeout_{chat_id}_{message_id}"
        )
    
    async def auto_recover_rods(self):
        """Автоматически восстанавливает прочность удочек игроков каждые 10 минут"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Получаем все удочки, у которых начато восстановление
                cursor.execute('''
                    SELECT user_id, rod_name, current_durability, max_durability, recovery_start_time
                    FROM player_rods
                    WHERE rod_name = ?
                      AND recovery_start_time IS NOT NULL
                      AND current_durability < max_durability
                      AND (chat_id IS NULL OR chat_id < 1)
                ''', (BAMBOO_ROD,))

                rods = cursor.fetchall()
                
                for user_id, rod_name, current_dur, max_dur, recovery_start in rods:
                    # Каждые 10 минут восстанавливается: max_dur / 30 прочности
                    # (т.е. полное восстановление за 5 часов = 300 минут = 30 интервалов по 10 минут)
                    recovery_amount = max(1, max_dur // 30)
                    
                    # Обновляем прочность
                    new_durability = min(max_dur, current_dur + recovery_amount)
                    
                    cursor.execute('''
                        UPDATE player_rods
                        SET current_durability = ?
                        WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
                    ''', (new_durability, user_id, rod_name))
                    
                    # Если удочка полностью восстановилась
                    if new_durability == max_dur:
                        cursor.execute('''
                            UPDATE player_rods
                            SET recovery_start_time = NULL
                            WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
                        ''', (user_id, rod_name))
                        
                        # Отправляем уведомление в ЛС
                        try:
                            await self.application.bot.send_message(
                                chat_id=user_id,
                                text=f"✅ Ваша удочка '{rod_name}' полностью восстановлена!"
                            )
                        except Exception as e:
                            logger.warning(f"Could not send recovery notification to {user_id}: {e}")
                
                conn.commit()
                logger.info(f"Rod recovery job completed for {len(rods)} rods")
        except Exception as e:
            logger.error(f"Error in auto_recover_rods: {e}")
        
    async def welcome_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветствие новых участников группы"""
        for new_member in update.message.new_chat_members:
            # Не приветствуем ботов
            if new_member.is_bot:
                continue

            username = f"@{new_member.username}" if new_member.username else new_member.first_name

            welcome_message = f"""
👋 Привет, рыбак {username}!

🎣 Добро пожаловать в нашу рыболовную компанию!

📝 Для начала:
1️⃣ Отправь команду /start чтобы создать профиль
2️⃣ Используй /menu для управления рыбалкой
3️⃣ Команда /fish - забросить удочку прямо в чате
4️⃣ /help - список всех команд

🐟 Удачной рыбалки!
            """

            await update.message.reply_text(welcome_message)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        # Запускаем scheduler при первом запросе
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            # Добавляем job для автоматического восстановления удочек каждые 10 минут
            self.scheduler.add_job(
                self.auto_recover_rods,
                'interval',
                minutes=10,
                id='auto_recover_rods',
                replace_existing=True
            )
            logger.info("AsyncIOScheduler запущен")

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        username = update.effective_user.username or update.effective_user.first_name

        player = db.get_player(user_id, chat_id)
        if not player:
            # Создаем нового игрока
            player = db.create_player(user_id, username, chat_id)
            welcome_text = f"""
🎣 Добро пожаловать в мир рыбалки, {username}!

🎣 Ваша рыболовная книга:
🪙 Монеты: {player['coins']} {COIN_NAME}
🎣 Удочка: {player['current_rod']}
📍 Локация: {player['current_location']}
🪱 Наживка: {player['current_bait']}

Используйте /menu чтобы начать рыбалку!
            """
        else:
            welcome_text = f"""
🎣 С возвращением, {username}!

🎣 Ваша статистика:
🪙 Монеты: {player['coins']} {COIN_NAME}
🎣 Удочка: {player['current_rod']}
📍 Локация: {player['current_location']}
🪱 Наживка: {player['current_bait']}

Используйте /menu чтобы начать рыбалку!
            """

        # Проверка целостности профиля (удочка, наживка, локация)
        if player:
            updates = {}
            if not player.get('current_rod'):
                updates['current_rod'] = 'Бамбуковая удочка'
            if not player.get('current_bait'):
                updates['current_bait'] = 'Черви'
            if not player.get('current_location'):
                updates['current_location'] = 'Городской пруд'
            if updates:
                db.update_player(user_id, chat_id, **updates)
                player = db.get_player(user_id, chat_id)
            if player:
                player_rod = db.get_player_rod(user_id, player['current_rod'], chat_id)
                if not player_rod:
                    if player['current_rod'] in TEMP_ROD_RANGES:
                        db.update_player(user_id, chat_id, current_rod=BAMBOO_ROD)
                        db.init_player_rod(user_id, BAMBOO_ROD, chat_id)
                        player = db.get_player(user_id, chat_id)
                    else:
                        db.init_player_rod(user_id, player['current_rod'], chat_id)

        await update.message.reply_text(welcome_text)
    
    async def fish_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /fish - просто забросить удочку"""
        # Команда работает только в группах/каналах, не в личных чатах
        if update.effective_chat.type == 'private':
            try:
                await update.message.reply_text("Команда /fish работает только в чатах с группой. Для платежей проверьте входящие инвойсы.")
            except Exception as e:
                logger.error(f"Error replying to fish command: {e}")
            return
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        
        if not player:
            # Автоматически создаём профиль в этом чате при первом использовании /fish
            try:
                username = update.effective_user.username or update.effective_user.first_name
                player = db.create_player(user_id, username, chat_id)
                await update.message.reply_text("✅ Профиль создан автоматически для этого чата. Продолжаем рыбалку...")
            except Exception as e:
                logger.error(f"Error creating player from fish command: {e}")
                try:
                    await update.message.reply_text("Сначала создайте профиль командой /start")
                except Exception as e:
                    logger.error(f"Error replying to fish command: {e}")
                return
        
        # Проверяем кулдаун
        can_fish, message = game.can_fish(user_id, chat_id)
        if not can_fish:
            # Отправляем сообщение с причиной и кнопкой оплаты
            keyboard = [
                [InlineKeyboardButton(
                    f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", 
                    callback_data=f"pay_telegram_star_{user_id}_{player['current_location']}"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await update.message.reply_text(
                    f"⏰ {message}", 
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Error replying to fish command: {e}")
            return
        
        # Начинаем рыбалку на текущей локации
        try:
            result = game.fish(user_id, chat_id, player['current_location'])
        except Exception as e:
            logger.exception("Unhandled exception in game.fish for user %s chat %s", user_id, chat_id)
            try:
                await update.message.reply_text("❌ Неожиданная ошибка при рыбалке. Обратитесь в поддержку.")
            except Exception:
                pass
            return

        if result.get('nft_win'):
            nft_message = (
                "🎉 Поздравляю, вы выиграли NFT.\n"
                "Какой? Секрет.\n"
                "С вами свяжется админ для передачи.\n"
                "Если в течение дня никто не отпишет вам, свяжитесь через t.me/monkeys_giveaways"
            )
            try:
                await update.message.reply_text(nft_message)
            except Exception as e:
                logger.error(f"Error sending NFT win message: {e}")

            try:
                await self.application.bot.send_message(
                    chat_id=793216884,
                    text=(
                        "NFT win detected.\n"
                        f"User: {update.effective_user.id} ({update.effective_user.username or update.effective_user.full_name})\n"
                        f"Chat: {update.effective_chat.id} ({update.effective_chat.title or ''})"
                    )
                )
            except Exception as e:
                logger.error(f"Error sending NFT admin DM: {e}")
            return
        
        if result['success']:
            if result.get('is_trash'):
                trash = result['trash']
                xp_line = ""
                progress_line = ""
                if result.get('xp_earned'):
                    xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                    progress_line = f"\n{format_level_progress(result.get('level_info'))}"
                message = f"""
{trash.get('name', 'Мусор')}

⚖️ Вес: {trash.get('weight', 0)} кг
💰 Стоимость: {trash.get('price', 0)} 🪙
📍 Место: {result['location']}
{xp_line}{progress_line}
                """

                sticker_message = None
                if trash.get('name') in TRASH_STICKERS:
                    try:
                        trash_image = TRASH_STICKERS[trash['name']]
                        image_path = Path(__file__).parent / trash_image
                        sticker_message = await self.application.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=open(image_path, 'rb'),
                            reply_to_message_id=update.message.message_id
                        )
                        if sticker_message:
                            context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                    except Exception as e:
                        logger.warning(f"Could not send trash image for {trash.get('name')}: {e}")

                if sticker_message:
                    await update.message.reply_text(message, reply_to_message_id=sticker_message.message_id)
                else:
                    await update.message.reply_text(message)

                if result.get('temp_rod_broken'):
                    await update.message.reply_text(
                        "💥 Временная удочка сломалась после удачного улова.\n"
                        "Теперь активна бамбуковая. Купить новую можно в магазине."
                    )
                return

            fish = result['fish']
            weight = result['weight']
            length = result['length']
            fish_price = result.get('fish_price', fish.get('price', 0))

            logger.info(
                "Catch: user=%s (%s) chat_id=%s chat_title=%s fish=%s location=%s bait=%s weight=%.2fkg length=%.1fcm",
                update.effective_user.id,
                update.effective_user.username or update.effective_user.full_name,
                update.effective_chat.id,
                update.effective_chat.title or "",
                fish['name'],
                result['location'],
                player['current_bait'],
                weight,
                length
            )
            
            # Формируем сообщение о пойманной рыбе
            rarity_emoji = {
                'Обычная': '⚪',
                'Редкая': '🔵',
                'Легендарная': '🟣'
            }
            fish_name_display = format_fish_name(fish['name'])
            
            message = f"""
🎉 Поздравляю! Вы поймали рыбу!
{rarity_emoji.get(fish['rarity'], '⚪')} {fish_name_display}
📏 Размер: {length}см | Вес: {weight} кг
💰 Стоимость: {fish_price} 🪙
📍 Место: {result['location']}
⭐ Редкость: {fish['rarity']}

Вы можете продать эту рыбу в лавке! 🐟
            """
            
            if result.get('guaranteed'):
                message += "\n⭐ Гарантированный улов!"
            
            # Отправляем фото рыбы если оно есть
            if fish['name'] in FISH_STICKERS:
                try:
                    fish_image = FISH_STICKERS[fish['name']]
                    image_path = Path(__file__).parent / fish_image
                    sticker_message = await self.application.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(image_path, 'rb'),
                        reply_to_message_id=update.message.message_id
                    )
                    if sticker_message:
                        context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                        context.bot_data.setdefault("sticker_fish_map", {})[sticker_message.message_id] = {
                            "fish_name": fish['name'],
                            "weight": weight,
                            "price": fish_price,
                            "location": result['location'],
                            "rarity": fish['rarity']
                        }
                except Exception as e:
                    logger.warning(f"Could not send fish image for {fish['name']}: {e}")
            
            await update.message.reply_text(message)

            if result.get('temp_rod_broken'):
                await update.message.reply_text(
                    "💥 Временная удочка сломалась после удачного улова.\n"
                    "Теперь активна бамбуковая. Купить новую можно в магазине."
                )
                return
            
            # ПОСЛЕ сообщения о рыбе проверяем и сообщаем о прочности удочки
            if player['current_rod'] == BAMBOO_ROD and result.get('rod_broken'):
                durability_message = f"""
💔 Удочка сломалась!

🔧 Прочность: 0/{result.get('max_durability', 100)}

Используйте /repair чтобы починить удочку или подождите автовосстановления.
                """
                await update.message.reply_text(durability_message)
            elif player['current_rod'] == BAMBOO_ROD and result.get('current_durability', 100) < result.get('max_durability', 100):
                # Показываем текущую прочность если она уменьшилась
                current = result.get('current_durability', 100)
                maximum = result.get('max_durability', 100)
                durability_message = f"🔧 Прочность удочки: {current}/{maximum}"
                await update.message.reply_text(durability_message)
            return
        else:
            if result.get('rod_broken'):
                message = f"""
💔 Удочка сломалась!

{result['message']}

Используйте /repair чтобы починить удочку.
                """
                await update.message.reply_text(message)
                return
            elif result.get('is_trash'):
                # Мусор пойман
                xp_line = ""
                progress_line = ""
                if result.get('xp_earned'):
                    xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                    progress_line = f"\n{format_level_progress(result.get('level_info'))}"
                message = f"""
{result['message']}

📦 Мусор: {result['trash']['name']}
⚖️ Вес: {result['trash']['weight']} кг
💰 Стоимость: {result['trash']['price']} 🪙
{xp_line}{progress_line}

Ваш баланс: {result['new_balance']} 🪙
                """
                
                # Отправляем фото мусора если оно есть
                if result['trash']['name'] in TRASH_STICKERS:
                    try:
                        trash_image = TRASH_STICKERS[result['trash']['name']]
                        image_path = Path(__file__).parent / trash_image
                        sticker_message = await self.application.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=open(image_path, 'rb')
                        )
                        if sticker_message:
                            context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                    except Exception as e:
                        logger.warning(f"Could not send trash image for {result['trash']['name']}: {e}")
                
                await update.message.reply_text(message)
                if result.get('temp_rod_broken'):
                    await update.message.reply_text(
                        "💥 Временная удочка сломалась после удачного улова.\n"
                        "Теперь активна бамбуковая. Купить новую можно в магазине."
                    )
                return
            elif result.get('no_bite'):
                # Отправляем сообщение с причиной и кнопкой оплаты
                keyboard = [
                    [InlineKeyboardButton(
                        f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", 
                        callback_data=f"pay_telegram_star_{user_id}_{result['location']}"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"😔 {result['message']}", 
                    reply_markup=reply_markup
                )
                return
            else:
                # Отправляем сообщение с причиной и кнопкой оплаты
                keyboard = [
                    [InlineKeyboardButton(
                        f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", 
                        callback_data=f"pay_telegram_star_{user_id}_{result['location']}"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"😔 {result['message']}", 
                    reply_markup=reply_markup
                )
                return
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /menu - показать меню рыбалки"""
        # Команда работает только в группах/каналах, не в личных чатах
        if update.effective_chat.type == 'private':
            await update.message.reply_text("Команда /menu работает только в чатах с группой. Для платежей проверьте входящие инвойсы.")
            return
        
        chat_id = update.effective_chat.id
        player = db.get_player(update.effective_user.id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        await self.show_fishing_menu(update, context)

    async def show_fishing_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню рыбалки"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        player = db.get_player(user_id, chat_id)
        if not player:
            if update.message:
                await update.message.reply_text("Сначала создайте профиль командой /start")
            else:
                await update.callback_query.answer("Сначала создайте профиль командой /start", show_alert=True)
            return

        rod_name = player['current_rod']
        player_rod = db.get_player_rod(user_id, rod_name, chat_id)
        if not player_rod:
            if rod_name in TEMP_ROD_RANGES:
                db.update_player(user_id, chat_id, current_rod=BAMBOO_ROD)
                db.init_player_rod(user_id, BAMBOO_ROD, chat_id)
                player = db.get_player(user_id, chat_id)
                rod_name = player['current_rod']
                player_rod = db.get_player_rod(user_id, rod_name, chat_id)
            else:
                db.init_player_rod(user_id, rod_name, chat_id)
                player_rod = db.get_player_rod(user_id, rod_name, chat_id)
        durability_line = ""
        if player_rod and rod_name == BAMBOO_ROD:
            durability_line = f"🔧 Прочность: {player_rod['current_durability']}/{player_rod['max_durability']}\n"

        coin_emoji = '<tg-emoji emoji-id="5379600444098093058">⭐</tg-emoji>'
        menu_text = f"""
    🎣 Меню рыбалки

    {coin_emoji} Монеты: {player['coins']} {COIN_NAME}
    🎣 Удочка: {player['current_rod']}
    📍 Локация: {player['current_location']}
    🪱 Наживка: {player['current_bait']}
    {durability_line}
        """

        keyboard = [
            [InlineKeyboardButton("🎣 Начать рыбалку", callback_data=f"start_fishing_{user_id}")],
            [InlineKeyboardButton("📍 Сменить локацию", callback_data=f"change_location_{user_id}")],
            [InlineKeyboardButton("🪱 Сменить наживку", callback_data=f"change_bait_{user_id}")],
            [InlineKeyboardButton("🧺 Лавка", callback_data=f"sell_fish_{user_id}"), InlineKeyboardButton("🛒 Магазин", callback_data=f"shop_{user_id}")],
            [InlineKeyboardButton("📊 Статистика", callback_data=f"stats_{user_id}"), InlineKeyboardButton("🎒 Инвентарь", callback_data=f"inventory_{user_id}")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode="HTML")
    
    async def handle_change_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка смены локации"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        locations = db.get_locations()
        keyboard = []
        
        for loc in locations:
            # Показываем актуальное количество человек в чате
            players_count = db.get_location_players_count(loc['name'], chat_id)
            players_info = f"👥 {players_count}"
            
            keyboard.append([InlineKeyboardButton(
                f"📍 {loc['name']} {players_info}",
                callback_data=f"select_location_{loc['name']}_{user_id}"
            )])
        
        # Добавляем кнопку возврата
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "📍 Выберите новую локацию:"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_change_bait(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка смены наживки - выбор между локацией/удочкой"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}") and not query.data.startswith(f"change_bait_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Получаем все локации
        locations = db.get_locations()
        
        keyboard = []
        for idx, location in enumerate(locations):
            keyboard.append([InlineKeyboardButton(
                f"📍 {location['name']}",
                callback_data=f"change_bait_loc_{idx}_{user_id}"
            )])
        
        # Добавляем кнопку выбора удочки
        keyboard.append([InlineKeyboardButton(
            "🎣 Выбрать удочку",
            callback_data=f"change_rod_{user_id}"
        )])
        
        # Добавляем кнопку выбора сети
        keyboard.append([InlineKeyboardButton(
            "🕸️ Выбрать сеть",
            callback_data=f"select_net_{user_id}"
        )])
        
        keyboard.append([InlineKeyboardButton("🔙 Меню", callback_data=f"back_to_menu_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🪱 Сменить наживку, удочку или сеть\n\nВыберите локацию для выбора наживки или используйте кнопки ниже:"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка: {e}")
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=message,
                        reply_markup=reply_markup
                    )
                except Exception as e2:
                    logger.error(f"Failed to send change_bait menu: {e2}")
    
    async def handle_change_bait_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать наживки игрока для выбранной локации"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Разбор: change_bait_loc_{loc_idx}_{user_id}_{page}
        parts = query.data.split('_')
        loc_idx = int(parts[3])
        page = int(parts[5]) if len(parts) > 5 else 1
        
        await query.answer()
        
        # Получаем локацию
        locations = db.get_locations()
        if loc_idx >= len(locations):
            await query.edit_message_text("❌ Локация не найдена!")
            return
        location = locations[loc_idx]['name']
        
        # Получаем наживки игрока для этой локации
        baits = db.get_player_baits_for_location(user_id, location)
        
        if not baits:
            keyboard = [
                [InlineKeyboardButton("🪱 Черви (∞)", callback_data=f"select_bait_Черви_{user_id}")],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data=f"change_bait_{user_id}"),
                    InlineKeyboardButton("🛒 В магазин", callback_data=f"shop_baits_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"❌ У вас нет наживок для {location}!\n\nМожно использовать червей или купить наживки в магазине.",
                reply_markup=reply_markup
            )
            return
        
        page_size = 5
        total_pages = max(1, (len(baits) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = start + page_size
        page_baits = baits[start:end]
        
        # Кнопки наживок с количеством (используем ID, чтобы не ломаться на пробелах)
        keyboard = []
        for bait in page_baits:
            cb_data = f"select_bait_id_{bait['id']}_{user_id}"
            if len(cb_data.encode('utf-8')) > 64:
                cb_data = f"sbi_{bait['id']}_{user_id}"

            keyboard.append([InlineKeyboardButton(
                f"🪱 {bait['name']} ({bait['player_quantity']} шт)",
                callback_data=cb_data
            )])
        
        # Добавляем бесконечные черви отдельной кнопкой
        keyboard.append([InlineKeyboardButton(
            "🪱 Черви (∞)",
            callback_data=f"select_bait_Черви_{user_id}"
        )])

        # Навигация
        nav_buttons = []
        if total_pages > 1:
            prev_page = page - 1 if page > 1 else total_pages
            next_page = page + 1 if page < total_pages else 1
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"change_bait_loc_{loc_idx}_{user_id}_{prev_page}"))
        
        nav_buttons.append(InlineKeyboardButton("🔙 Назад", callback_data=f"change_bait_{user_id}"))
        
        if total_pages > 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"change_bait_loc_{loc_idx}_{user_id}_{next_page}"))
        
        keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"🪱 Выберите наживку для {location} ({page}/{total_pages}):"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка изменения меню наживок: {e}")
                logger.error(f"Callback data: {query.data}")
                for i, row in enumerate(keyboard):
                    for j, btn in enumerate(row):
                        logger.error(f"Button [{i}][{j}]: text='{btn.text}', callback_data='{btn.callback_data}' (len={len(btn.callback_data)})")
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=message,
                        reply_markup=reply_markup
                    )
                except Exception as e2:
                    logger.error(f"Failed to send change_bait_location as new message: {e2}")

    async def handle_change_rod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка смены удочки"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        player = db.get_player(user_id, chat_id)
        all_rods = db.get_rods()
        
        keyboard = []
        
        # Добавляем бамбуковую удочку (всегда есть)
        bamboo_rod = db.get_rod("Бамбуковая удочка")
        if bamboo_rod:
            current = "✅" if player['current_rod'] == "Бамбуковая удочка" else ""
            kb_data = f"select_rod_Бамбуковая удочка_{user_id}"
            if len(kb_data.encode('utf-8')) > 64:
                kb_data = f"sr_bamboo_{user_id}"
            keyboard.append([InlineKeyboardButton(
                f"🎣 Бамбуковая удочка (всегда есть) {current}",
                callback_data=kb_data
            )])
        
        # Добавляем остальные удочки
        for rod in all_rods:
            if rod['name'] != "Бамбуковая удочка":  # Исключаем, так как уже выше добавили
                current = "✅" if player['current_rod'] == rod['name'] else ""
                # Получаем текущую прочность удочки
                durability_str = ""
                if rod['name'] == BAMBOO_ROD:
                    player_rod = db.get_player_rod(user_id, rod['name'], chat_id)
                    if player_rod:
                        durability_str = f" ({player_rod['current_durability']}/{player_rod['max_durability']})"
                
                cb_data = f"select_rod_{rod['name']}_{user_id}"
                if len(cb_data.encode('utf-8')) > 64:
                    cb_data = f"sr_{rod['id']}_{user_id}"
                
                keyboard.append([InlineKeyboardButton(
                    f"🎣 {rod['name']}{durability_str} {current}",
                    callback_data=cb_data
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"change_bait_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🎣 Выберите удочку:"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка смены удочки: {e}")
    
    async def handle_select_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора локации"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Извлекаем название локации (убираем префикс и user_id)
        location_name = query.data.replace(f"select_location_", "").replace(f"_{user_id}", "")
        
        # Обновляем локацию игрока
        db.update_player_location(user_id, chat_id, location_name)

        keyboard = [[
            InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}"),
            InlineKeyboardButton(f"{LOCATION_EMOJI_TAG} Сменить локацию", callback_data=f"change_location_{user_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📍 Локация изменена на: {location_name}",
            reply_markup=reply_markup
        )
    
    async def handle_select_bait(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора наживки"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Поддержка форматов: select_bait_id_{id}_{user_id}, sbi_{id}_{user_id}, select_bait_{name}_{user_id}
        bait_name = None
        if query.data.startswith("select_bait_id_") or query.data.startswith("sbi_"):
            parts = query.data.split('_')
            bait_id = None
            if query.data.startswith("select_bait_id_"):
                # Формат: select_bait_id_{id}_{user_id}
                if len(parts) >= 5:
                    try:
                        bait_id = int(parts[3])
                    except ValueError:
                        bait_id = None
            else:
                # Формат: sbi_{id}_{user_id}
                if len(parts) >= 3:
                    try:
                        bait_id = int(parts[1])
                    except ValueError:
                        bait_id = None

            if bait_id is not None:
                baits = db.get_baits()
                bait = next((b for b in baits if b['id'] == bait_id), None)
                if bait:
                    bait_name = bait['name']
        else:
            bait_name = query.data.replace("select_bait_", "").replace(f"_{user_id}", "")

        if not bait_name:
            await query.edit_message_text("❌ Наживка не найдена!")
            return

        # Обновляем наживку игрока
        db.update_player_bait(user_id, chat_id, bait_name)

        await query.edit_message_text(f"🪱 Наживка изменена на: {bait_name}")
    
    async def handle_select_net(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора сети в меню"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Показываем доступные сети игрока
        player_nets = db.get_player_nets(user_id, chat_id)
        if not player_nets:
            db.init_player_net(user_id, 'Базовая сеть', chat_id)
            player_nets = db.get_player_nets(user_id, chat_id)
        
        if not player_nets:
            keyboard = [
                [InlineKeyboardButton("🛒 Купить сети", callback_data=f"shop_nets_{user_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data=f"change_bait_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ У вас нет сетей!\n\n"
                "Используйте магазин чтобы купить сети.",
                reply_markup=reply_markup
            )
            return
        
        # Показываем список сетей
        keyboard = []
        for net in player_nets:
            # Проверяем кулдаун
            cooldown = db.get_net_cooldown_remaining(user_id, net['net_name'], chat_id)
            
            if cooldown > 0:
                hours = cooldown // 3600
                minutes = (cooldown % 3600) // 60
                time_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
                status = f"⏳ {time_str}"
            elif net['max_uses'] != -1 and net['uses_left'] <= 0:
                status = "❌ Использовано"
            else:
                uses_str = "∞" if net['max_uses'] == -1 else f"{net['uses_left']}"
                status = f"✅ ({uses_str} исп.)"
            
            button_text = f"🕸️ {net['net_name']} - {status}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_net_{net['net_name']}_{user_id}")])
        
        keyboard.append([
            InlineKeyboardButton("🛒 Купить сети", callback_data=f"shop_nets_{user_id}"),
            InlineKeyboardButton("🔙 Назад", callback_data=f"change_bait_{user_id}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🕸️ Ваши сети:\n\nВыберите сеть для просмотра информации:"
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def handle_use_net(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка использования сети"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        # Формат: use_net_{net_name}_{user_id}
        parts = query.data.split('_')
        net_name = '_'.join(parts[2:-1])  # Все части между use_net и user_id
        
        player = db.get_player(user_id, chat_id)
        if not player:
            await query.answer("Профиль не найден", show_alert=True)
            return
        
        # Проверяем наличие сети у игрока
        player_net = db.get_player_net(user_id, net_name, chat_id)
        if not player_net:
            await query.answer("❌ У вас нет этой сети!", show_alert=True)
            return
        
        # Проверяем кулдаун
        cooldown = db.get_net_cooldown_remaining(user_id, net_name, chat_id)
        if cooldown > 0:
            hours = cooldown // 3600
            minutes = (cooldown % 3600) // 60
            time_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
            await query.answer(f"⏳ Сеть можно использовать через {time_str}", show_alert=True)
            return
        
        # Проверяем использования
        if player_net['max_uses'] != -1 and player_net['uses_left'] <= 0:
            await query.answer("❌ У этой сети закончились использования!", show_alert=True)
            return
        
        await query.answer()
        
        # Используем сеть
        location = player['current_location']
        season = get_current_season()
        fish_count = player_net['fish_count']
        
        # Получаем рыбу для текущей локации и сезона
        available_fish = db.get_fish_by_location(location, season, min_level=player.get('level', 0) or 0)
        
        # Получаем мусор для локации
        available_trash = db.get_trash_by_location(location)
        
        if not available_fish and not available_trash:
            await query.edit_message_text(
                f"❌ В локации {location} нет доступного контента в сезон {season}!"
            )
            return
        
        # Вытаскиваем случайные рыбы и мусор
        catch_results = []
        total_value = 0
        
        for i in range(fish_count):
            # 80% шанс рыбы, 20% шанс мусора
            is_trash = random.randint(1, 100) <= 20
            
            if is_trash and available_trash:
                # Ловим мусор
                trash = random.choice(available_trash)
                db.add_caught_fish(user_id, chat_id, trash['name'], trash['weight'], location, 0)

                logger.info(
                    "Net catch (trash): user=%s chat_id=%s chat_title=%s item=%s weight=%.2fkg location=%s",
                    user_id,
                    chat_id,
                    update.effective_chat.title or "",
                    trash['name'],
                    trash['weight'],
                    location
                )
                
                catch_results.append({
                    'type': 'trash',
                    'name': trash['name'],
                    'weight': trash['weight'],
                    'price': trash['price']
                })
                total_value += trash['price']
            elif available_fish:
                # Ловим рыбу
                fish = random.choice(available_fish)
                # Генерируем вес и длину рыбы
                weight = round(random.uniform(fish['min_weight'], fish['max_weight']), 2)
                length = round(random.uniform(fish['min_length'], fish['max_length']), 1)
                
                # Добавляем рыбу в улов игрока
                db.add_caught_fish(user_id, chat_id, fish['name'], weight, location, length)

                logger.info(
                    "Net catch (fish): user=%s chat_id=%s chat_title=%s fish=%s weight=%.2fkg length=%.1fcm location=%s",
                    user_id,
                    chat_id,
                    update.effective_chat.title or "",
                    fish['name'],
                    weight,
                    length,
                    location
                )
                
                fish_price = db.calculate_fish_price(fish, weight, length)

                catch_results.append({
                    'type': 'fish',
                    'name': fish['name'],
                    'weight': weight,
                    'length': length,
                    'price': fish_price
                })
                total_value += fish_price
        
        # Используем сеть
        db.use_net(user_id, net_name, chat_id)
        
        # Формируем сообщение
        message = f"🕸️ Сеть '{net_name}' использована!\n"
        message += f"📍 Локация: {location}\n"
        message += f"📦 Улов: {len(catch_results)} предметов\n\n"
        message += "─" * 30 + "\n"
        
        for i, item in enumerate(catch_results, 1):
            if item['type'] == 'fish':
                fish_name_display = format_fish_name(item['name'])
                message += f"{i}. {fish_name_display} - {item['weight']}кг, {item['length']}см\n"
            else:
                message += f"{i}. {item['name']} - {item['weight']}кг\n"
        
        message += "─" * 30 + "\n"
        message += f"💰 Итого: {total_value} {COIN_NAME}\n"
        
        # Обновляем оставшиеся использования
        player_net = db.get_player_net(user_id, net_name, chat_id)
        if player_net['max_uses'] != -1:
            message += f"🕸️ Осталось использований: {player_net['uses_left']}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔙 Меню", callback_data=f"back_to_menu_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def handle_select_rod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора удочки"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Поддержка форматов: select_rod_{name}_{user_id}, sr_{rod_id}_{user_id}, sr_bamboo_{user_id}
        rod_name = None
        
        if query.data.startswith("select_rod_"):
            # Формат: select_rod_{name}_{user_id}
            rod_name = query.data.replace("select_rod_", "").replace(f"_{user_id}", "")
        elif query.data.startswith("sr_"):
            # Формат: sr_{rod_id}_{user_id} или sr_bamboo_{user_id}
            parts = query.data.split('_')
            if parts[1] == "bamboo":
                rod_name = "Бамбуковая удочка"
            else:
                try:
                    rod_id = int(parts[1])
                    rod = db.get_rod_by_id(rod_id)
                    if rod:
                        rod_name = rod['name']
                except (ValueError, IndexError):
                    pass
        
        if not rod_name:
            await query.edit_message_text("❌ Удочка не найдена!")
            return
        
        # Проверяем, что удочка есть у игрока (или бамбуковая)
        if rod_name != "Бамбуковая удочка":
            # Нужно проверить, куплена ли удочка
            player_rod = db.get_player_rod(user_id, rod_name, chat_id)
            if not player_rod:
                await query.edit_message_text("❌ Эта удочка не куплена!")
                return
        else:
            # Инициализируем бамбуковую удочку если её нет
            db.init_player_rod(user_id, "Бамбуковая удочка", chat_id)
        
        # Обновляем удочку игрока
        db.update_player(user_id, chat_id, current_rod=rod_name)
        
        # Возвращаемся в меню выбора удочек с подтверждением
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"change_rod_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(f"✅ Удочка '{rod_name}' выбрана!", reply_markup=reply_markup)

    async def handle_instant_repair(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка мгновенного ремонта удочки"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Формат: instant_repair_{rod_name}_{user_id}
        rod_name = query.data.replace("instant_repair_", "").replace(f"_{user_id}", "")

        if rod_name in TEMP_ROD_RANGES:
            await query.edit_message_text("❌ Эта удочка одноразовая и не ремонтируется.")
            return
        
        # Получаем информацию об удочке
        player_rod = db.get_player_rod(user_id, rod_name, chat_id)
        if not player_rod:
            await query.edit_message_text("❌ Удочка не найдена!")
            return
        
        current_dur = player_rod['current_durability']
        max_dur = player_rod['max_durability']
        missing_durability = max_dur - current_dur
        
        if missing_durability <= 0:
            await query.edit_message_text("✅ Ваша удочка уже в идеальном состоянии!")
            return
        
        # Вычисляем стоимость
        repair_cost = max(1, int(20 * missing_durability / max_dur))
        
        # Отправляем инвойс на оплату
        await self.send_rod_repair_invoice(query, user_id, rod_name, repair_cost)
    
    async def send_rod_repair_invoice(self, query, user_id: int, rod_name: str, repair_cost: int):
        """Отправить инвойс на оплату ремонта удочки"""
        try:
            # Отправляем invoice в ЛС пользователю
            await self.application.bot.send_invoice(
                chat_id=user_id,
                title=f"⚡ Мгновенный ремонт удочки",
                description=f"Восстановить '{rod_name}' до полной прочности",
                payload=f"repair_rod_{rod_name}",
                provider_token="",  # Пустой для Telegram Stars
                currency="XTR",  # Telegram Stars
                prices=[LabeledPrice(label=f"Ремонт {rod_name}", amount=repair_cost)]
            )
            
            await query.edit_message_text(
                f"💳 Счёт на {repair_cost} ⭐ отправлен вам в личные сообщения.\n"
                f"Оплатите для мгновенного восстановления удочки."
            )
        except Exception as e:
            logger.error(f"Error sending repair invoice: {e}")
            await query.edit_message_text(
                f"❌ Не удалось отправить счёт.\n"
                f"Убедитесь, что вы написали боту в личку (/start в ЛС)."
            )

        
    async def handle_back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в главное меню"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        await self.show_fishing_menu(update, context)
    
    async def handle_shop_rods(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка магазина удочек"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_shop_rods")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        rods = db.get_rods()
        keyboard = []
        
        for rod in rods:
            keyboard.append([InlineKeyboardButton(
                f"🎣 {rod['name']} - {rod['price']} 🪙",
                callback_data=f"buy_rod_{rod['id']}_{user_id}"
            )])
        
        # Добавляем кнопку возврата в магазин
        keyboard.append([InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🛒 Магазин удочек:"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка редактирования магазина удочек: {e}")
    
    async def handle_buy_rod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка покупки удочки"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_buy_rod")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        # Извлекаем ID удочки
        # Формат: buy_rod_{id}_{user_id}
        parts = query.data.split('_')
        rod_id = int(parts[2])
        
        await query.answer()
        
        # Получаем название удочки по ID
        rods = db.get_rods()
        rod_name = None
        for rod in rods:
            if rod['id'] == rod_id:
                rod_name = rod['name']
                break
        
        if not rod_name:
            await query.edit_message_text("❌ Удочка не найдена!")
            return
        
        # Покупаем удочку
        result = db.buy_rod(user_id, chat_id, rod_name)
        
        if result:
            await query.edit_message_text(f"✅ Удочка {rod_name} куплена!")
        else:
            await query.edit_message_text("❌ Недостаточно монет!")
    
    async def send_rod_repair_invoice(self, user_id: int, rod_name: str):
        """Отправить инвойс для восстановления удочки в личное сообщение"""
        try:
            rod = db.get_rod(rod_name)
            if not rod:
                logger.error(f"Rod not found: {rod_name}")
                return
            
            # Отправляем инвойс в ЛС
            prices = [LabeledPrice(label=f"Восстановление удочки '{rod_name}'", amount=20 * 100)]  # 20 звезд = 20 * 100 копеек
            
            await self.application.bot.send_invoice(
                chat_id=user_id,
                title=f"Восстановление удочки",
                description=f"Полное восстановление прочности удочки '{rod_name}'",
                payload=f"repair_rod_{rod_name}",
                provider_token="",  # Пусто для Telegram Stars
                currency="XTR",
                prices=prices,
                is_flexible=False
            )
            logger.info(f"Sent repair invoice for {rod_name} to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending repair invoice to {user_id}: {e}")
    
    async def handle_shop_baits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка магазина наживок - сначала выбор локации"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_shop_baits")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        if 'waiting_bait_quantity' in context.user_data:
            del context.user_data['waiting_bait_quantity']
        
        await query.answer()
        
        # Получаем все локации
        locations = db.get_locations()
        
        keyboard = []
        for idx, location in enumerate(locations):
            keyboard.append([InlineKeyboardButton(
                f"📍 {location['name']}",
                callback_data=f"shop_baits_loc_{idx}_{user_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"shop_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🛒 Магазин наживок\n\nВыберите локацию:"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка редактирования магазина наживок: {e}")
    
    async def handle_shop_baits_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать наживки для выбранной локации с пагинацией"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_shop_baits_location")
            return
        
        # Разбор: shop_baits_loc_{loc_idx}_{user_id}_{page}
        parts = query.data.split('_')
        loc_idx = int(parts[3])
        callback_user_id = int(parts[4])
        page = int(parts[5]) if len(parts) > 5 else 1
        
        # Проверка прав доступа
        if user_id != callback_user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        if 'waiting_bait_quantity' in context.user_data:
            del context.user_data['waiting_bait_quantity']
        
        # Получаем название локации по индексу
        locations = db.get_locations()
        if loc_idx >= len(locations):
            await query.edit_message_text("❌ Локация не найдена!")
            return
        location = locations[loc_idx]['name']
        
        await query.answer()
        
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        baits = db.get_baits_for_location(location)
        
        # Исключаем бесконечную наживку (черви) из магазина
        baits = [b for b in baits if b['name'].strip().lower() != 'черви']
        
        if not baits:
            await query.edit_message_text(f"❌ Нет наживок для локации {location}")
            return
        
        page_size = 5
        total_pages = max(1, (len(baits) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = start + page_size
        page_baits = baits[start:end]
        
        # Кнопки наживок с ценой
        keyboard = []
        for idx, bait in enumerate(page_baits):
            bait_id = bait.get('id')
            cb_data = f"select_bait_buy_{loc_idx}_{bait_id}_{user_id}"
            # Проверяем длину callback_data (максимум 64 байта)
            if len(cb_data.encode('utf-8')) > 64:
                logger.warning(f"Callback data too long: {cb_data}")
                cb_data = f"sb_{loc_idx}_{bait_id}_{user_id}"
            
            keyboard.append([InlineKeyboardButton(
                f"🪱 {bait['name']} - {bait['price']} 🪙",
                callback_data=cb_data
            )])
        
        # Навигация
        nav_buttons = []
        if total_pages > 1:
            prev_page = page - 1 if page > 1 else total_pages
            next_page = page + 1 if page < total_pages else 1
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"shop_baits_loc_{loc_idx}_{user_id}_{prev_page}"))
        
        nav_buttons.append(InlineKeyboardButton("🔙 Назад", callback_data=f"shop_baits_{user_id}"))
        
        if total_pages > 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"shop_baits_loc_{loc_idx}_{user_id}_{next_page}"))
        
        keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"🛒 Наживки для {location} ({page}/{total_pages})\n💰 Баланс: {player['coins']} 🪙"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error editing shop_baits_location: {e}")
            if "Message is not modified" not in str(e):
                # Попробуем отправить как обычное сообщение
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                except Exception as e2:
                    logger.error(f"Failed to send as new message too: {e2}")
    
    async def handle_shop_nets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка магазина сетей"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_shop_nets")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        nets = db.get_nets()
        nets_for_sale = [net for net in nets if net.get('price', 0) > 0]
        
        keyboard = []
        
        for net in nets_for_sale:
            # Проверяем, есть ли сеть у игрока
            player_net = db.get_player_net(user_id, net['name'], chat_id)
            
            if player_net:
                # Сеть уже куплена - показываем количество использований
                if net['max_uses'] == -1:
                    status = "✅ Бесконечная"
                else:
                    status = f"✅ ({player_net['uses_left']} исп.)"
                button_text = f"🕸️ {net['name']} - {status}"
                callback_data = f"buy_net_{net['name']}_{user_id}"  # Можно докупить
            else:
                # Сеть не куплена
                button_text = f"🕸️ {net['name']} - {net['price']} 🪙"
                callback_data = f"buy_net_{net['name']}_{user_id}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"🛒 Магазин сетей\n💰 Баланс: {player['coins']} 🪙\n\n"
        message += "🕸️ Сети позволяют ловить несколько рыб за раз!\n\n"
        
        for net in nets_for_sale:
            message += f"• {net['name']}: {net['fish_count']} рыб, кулдаун {net['cooldown_hours']}ч"
            if net['max_uses'] == -1:
                message += " (∞ использований)"
            else:
                message += f" ({net['max_uses']} использований)"
            message += f", цена {net['price']} 🪙"
            message += "\n"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка редактирования магазина сетей: {e}")
    
    async def handle_buy_net(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка покупки сети"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_buy_net")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        # Формат: buy_net_{net_name}_{user_id}
        parts = query.data.split('_')
        net_name = '_'.join(parts[2:-1])  # Все части между buy_net и user_id
        
        await query.answer()
        
        chat_id = update.effective_chat.id
        # Покупаем сеть
        result = db.buy_net(user_id, net_name, chat_id)
        
        if result:
            net = db.get_net(net_name)
            message = f"✅ Сеть '{net_name}' куплена!\n\n"
            message += f"🐟 Вытаскивает: {net['fish_count']} рыб\n"
            message += f"⏰ Кулдаун: {net['cooldown_hours']} часов\n"
            if net['max_uses'] == -1:
                message += "♾️ Использований: бесконечно"
            else:
                player_net = db.get_player_net(user_id, net_name, chat_id)
                message += f"📦 Использований: {player_net['uses_left']}"
        else:
            player = db.get_player(user_id, chat_id)
            net = db.get_net(net_name)
            if not net:
                message = "❌ Сеть не найдена!"
            elif player['coins'] < net['price']:
                message = f"❌ Недостаточно монет!\nНужно: {net['price']} 🪙\nУ вас: {player['coins']} 🪙"
            else:
                message = "❌ Эта сеть уже куплена (бесконечная)!"
        
        keyboard = [[InlineKeyboardButton("🔙 Магазин сетей", callback_data=f"shop_nets_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_select_bait_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор наживки для покупки - запрос количества"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            return
        
        # Разбор: select_bait_buy_{loc_idx}_{bait_id}_{user_id} или sb_{loc_idx}_{bait_id}_{user_id}
        parts = query.data.split('_')
        if parts[0] == 'sb':
            # Короткий формат: sb_{loc_idx}_{bait_idx}_{user_id}
            loc_idx = int(parts[1])
            bait_id = int(parts[2])
            button_user_id = int(parts[3])
        else:
            # Полный формат: select_bait_buy_{loc_idx}_{bait_idx}_{user_id}
            loc_idx = int(parts[3])
            bait_id = int(parts[4])
            button_user_id = int(parts[5])
        
        # Проверка прав доступа
        if user_id != button_user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Получаем локацию
        locations = db.get_locations()
        if loc_idx >= len(locations):
            await query.edit_message_text("❌ Локация не найдена!")
            return
        location = locations[loc_idx]['name']
        
        # Получаем наживку
        baits = db.get_baits_for_location(location)
        baits = [b for b in baits if b['name'].strip().lower() != 'черви']
        bait = next((b for b in baits if b.get('id') == bait_id), None)
        if not bait:
            await query.edit_message_text("❌ Наживка не найдена!")
            return
        
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        
        # Рассчитываем максимальное количество
        max_qty = min(999, player['coins'] // bait['price'])
        
        if max_qty == 0:
            await query.edit_message_text(f"❌ Недостаточно монет для покупки {bait['name']}!\n\nЦена: {bait['price']} 🪙\nВаш баланс: {player['coins']} 🪙")
            return
        
        # Сохраняем состояние в context.user_data
        context.user_data['waiting_bait_quantity'] = {
            'bait_name': bait['name'],
            'loc_idx': loc_idx,
            'price': bait['price'],
            'max_qty': max_qty,
            'balance': player['coins']
        }
        
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"shop_baits_loc_{loc_idx}_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""🪱 {bait['name']}

💰 Цена: {bait['price']} 🪙
💰 Ваш баланс: {player['coins']} 🪙
📦 Максимум: {max_qty} шт

✍️ Напишите в чат количество для покупки (1-{max_qty}):"""
        
        try:
            logger.info(f"Showing bait buy prompt for {bait['name']}, callback_data: {query.data}")
            await query.edit_message_text(
                message,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in handle_select_bait_buy: {e}")
            logger.error(f"Callback data: {query.data}")
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"Failed to send as new message: {e2}")
    
    async def handle_buy_bait(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка покупки наживки - обработка текстового ввода количества"""
        # Проверяем, ждём ли мы ввод количества от этого пользователя
        if 'waiting_bait_quantity' not in context.user_data:
            return  # Не обрабатываем, если не ждём ввода
        
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_buy_bait")
            return
        
        # Получаем данные из context
        bait_data = context.user_data['waiting_bait_quantity']
        bait_name = bait_data['bait_name']
        price = bait_data['price']
        max_qty = bait_data['max_qty']
        
        # Получаем текст сообщения
        message = update.effective_message
        if not message or not message.text:
            return
        text = message.text.strip()
        
        # Проверяем, что это число
        try:
            qty = int(text)
        except ValueError:
            await update.message.reply_text(f"❌ Введите число от 1 до {max_qty}!")
            return
        
        # Проверяем диапазон
        if qty < 1 or qty > max_qty:
            await update.message.reply_text(f"❌ Количество должно быть от 1 до {max_qty}!")
            return
        
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        total_cost = price * qty
        
        if player['coins'] < total_cost:
            await update.message.reply_text(f"❌ Недостаточно монет!\n\nНужно: {total_cost} 🪙\nУ вас: {player['coins']} 🪙")
            return
        
        # Покупаем
        db.add_bait_to_inventory(user_id, bait_name, qty)
        db.update_player(user_id, chat_id, coins=player['coins'] - total_cost)
        
        # Автоматически применяем купленную наживку
        db.update_player_bait(user_id, chat_id, bait_name)
        
        new_balance = player['coins'] - total_cost
        
        # Очищаем состояние
        del context.user_data['waiting_bait_quantity']
        
        await update.message.reply_text(
            f"✅ Куплено: {bait_name} x{qty}\n"
            f"🪱 Наживка автоматически применена!\n\n"
            f"💰 Потрачено: {total_cost} 🪙\n"
            f"💰 Баланс: {new_balance} 🪙"
        )
    
    async def handle_shop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка магазина"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except AttributeError:
            logger.error("update.effective_user not found or id not accessible")
            return
        
        # Проверяем, это callback query или command
        if update.callback_query:
            query = update.callback_query
            # Проверка прав доступа
            if not query.data.endswith(f"_{user_id}"):
                await query.answer("Эта кнопка не для вас", show_alert=True)
                return
            await query.answer()
            is_callback = True
        else:
            # Это текстовая команда /shop
            is_callback = False
            query = None
        
        keyboard = [
            [InlineKeyboardButton("🎣 Удочки", callback_data=f"shop_rods_{user_id}")],
            [InlineKeyboardButton("🪱 Наживки", callback_data=f"shop_baits_{user_id}")],
            [InlineKeyboardButton("�️ Сети", callback_data=f"shop_nets_{user_id}")],
            [InlineKeyboardButton("�🔙 Назад", callback_data=f"back_to_menu_{user_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🛒 Магазин:\n\nВыберите категорию:"
        
        if is_callback:
            try:
                await query.edit_message_text(message, reply_markup=reply_markup)
            except Exception as e:
                # Если сообщение уже отредактировано с тем же контентом, просто ничего не делаем
                if "Message is not modified" not in str(e):
                    logger.error(f"Ошибка редактирования сообщения магазина: {e}")
        else:
            # Это команда, отправляем новое сообщение
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=reply_markup
            )
    
    async def handle_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка покупки"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        callback_data = query.data
        
        # Проверка прав доступа
        if not callback_data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        if callback_data.startswith("buy_rod_"):
            # Извлекаем ID удочки (убираем префикс и user_id)
            # Формат: buy_rod_{id}_{user_id}
            parts = callback_data.split('_')
            rod_id = int(parts[2])
            
            # Получаем название удочки по ID
            rods = db.get_rods()
            rod_name = None
            for rod in rods:
                if rod['id'] == rod_id:
                    rod_name = rod['name']
                    break
            
            if not rod_name:
                await query.edit_message_text("❌ Удочка не найдена!")
                return
            
            # Покупаем удочку
            result = db.buy_rod(user_id, chat_id, rod_name)
            
            if result:
                await query.edit_message_text(f"✅ Удочка {rod_name} куплена!")
            else:
                await query.edit_message_text("❌ Недостаточно монет!")
        elif callback_data.startswith("buy_bait_"):
            # Извлекаем ID наживки (убираем префикс и user_id)
            # Формат: buy_bait_{id}_{user_id}
            parts = callback_data.split('_')
            bait_id = int(parts[2])
            
            # Получаем название наживки по ID
            baits = db.get_baits()
            bait_name = None
            for bait in baits:
                if bait['id'] == bait_id:
                    bait_name = bait['name']
                    break
            
            if not bait_name:
                await query.edit_message_text("❌ Наживка не найдена!")
                return

            if bait_name.strip().lower() == 'черви':
                await query.edit_message_text("❌ Черви бесконечные и не продаются.")
                return
            
            # Покупаем наживку
            result = db.add_bait_to_inventory(user_id, bait_name)
            
            if result:
                await query.edit_message_text(f"✅ Наживка {bait_name} куплена!")
            else:
                await query.edit_message_text("❌ Недостаточно монет!")
        else:
            await query.edit_message_text("❌ Неизвестный товар!")
    
    async def handle_repair_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка починки удочки"""
        query = update.callback_query
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        player = db.get_player(user_id, chat_id)
        if player:
            if player['current_rod'] in TEMP_ROD_RANGES:
                await query.edit_message_text("❌ Эта удочка одноразовая и не ремонтируется.")
                return
            db.repair_rod(user_id, player['current_rod'], chat_id)
            await query.edit_message_text("✅ Удочка починена!")
        else:
            await query.edit_message_text("❌ Ошибка: профиль не найден!")
    
    async def handle_sell_fish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка лавки продажи рыбы"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_sell_fish")
            return
        
        if update.callback_query:
            query = update.callback_query
            # Проверка прав доступа
            if not query.data.endswith(f"_{user_id}"):
                await query.answer("Эта кнопка не для вас", show_alert=True)
                return
            await query.answer()
        else:
            query = None
        
        # Получаем всю пойманную рыбу пользователя
        caught_fish = db.get_caught_fish(user_id, chat_id)
        
        # Фильтруем только непроданную рыбу (sold=0)
        unsold_fish = [f for f in caught_fish if f.get('sold', 0) == 0]
        
        if not unsold_fish:
            message = "🐟 Лавка рыбы\n\nУ вас нет непроданной рыбы для продажи."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
            return
        
        # Группируем рыбу по названию и считаем количество/стоимость
        fish_counts = {}
        total_value = 0
        for fish in unsold_fish:
            name = fish['fish_name']
            if name not in fish_counts:
                fish_counts[name] = {
                    'count': 0,
                    'total_price': 0,
                    'fish_id': fish['id']
                }
            fish_counts[name]['count'] += 1
            fish_counts[name]['total_price'] += fish['price']
            total_value += fish['price']
        
        # Создаем кнопки для продажи каждого вида рыбы
        keyboard = []
        for fish_name, info in sorted(fish_counts.items()):
            button_text = f"{fish_name} (×{info['count']}) - {info['total_price']} 🪙"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"sell_species_{fish_name.replace(' ', '_')}_{user_id}")])
        
        # Добавляем кнопку продажи всего
        if total_value > 0:
            keyboard.append([InlineKeyboardButton(f"💰 Продать всё ({total_value} 🪙)", callback_data=f"sell_all_{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"""🐟 Лавка рыбы

    Всего рыбы к продаже: {len(unsold_fish)}
Общая стоимость: {total_value} 🪙

Выберите что продать:"""
        
        if query:
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка инвентаря с показом локаций"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory")
            return
        
        if update.callback_query:
            query = update.callback_query
            # Проверка прав доступа
            if not query.data.endswith(f"_{user_id}"):
                await query.answer("Эта кнопка не для вас", show_alert=True)
                return
            await query.answer()
        else:
            query = None
        
        # Получаем все пойманные рыбы и их локации (только непроданные)
        caught_fish = db.get_caught_fish(user_id, chat_id)
        unsold_fish = [f for f in caught_fish if f.get('sold', 0) == 0]

        if not unsold_fish:
            message = "🎒 Инвентарь\n\nУ вас нет пойманной рыбы."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
            return
        
        # Группируем по локациям (с фильтром на корректные названия)
        valid_locations = {loc['name'] for loc in db.get_locations()}
        locations = {}
        for fish in unsold_fish:
            loc = fish.get('location')
            if loc not in valid_locations:
                length_loc = str(fish.get('length'))
                if length_loc in valid_locations:
                    loc = length_loc
                else:
                    continue
            if loc not in locations:
                locations[loc] = []
            locations[loc].append(fish)

        if not locations:
            message = "🎒 Инвентарь\n\nУ вас нет рыбы с корректной локацией."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
            return
        
        # Создаем кнопки для каждой локации
        keyboard = []
        for location in sorted(locations.keys(), key=lambda v: str(v)):
            fish_count = len(locations[location])
            button_text = f"📍 {location} ({fish_count} рыб)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"inv_location_{location.replace(' ', '_')}_{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"""🎒 Инвентарь

Всего пойманной рыбы: {len(unsold_fish)}

Выберите локацию для просмотра:"""
        
        if query:
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_inventory_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рыбу с определенной локации в инвентаре"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_location")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        # Извлекаем локацию из callback_data
        # Формат: inv_location_{location}_{user_id}
        parts = query.data.split('_')
        # Локация может содержать подчеркивания, поэтому берем все до последнего user_id
        location = '_'.join(parts[2:-1]).replace('_', ' ')
        
        await query.answer()
        
        # Получаем рыбу с этой локации
        caught_fish = db.get_caught_fish(user_id, chat_id)
        location_fish = [f for f in caught_fish if f['location'] == location and f.get('sold', 0) == 0]
        
        if not location_fish:
            await query.edit_message_text(f"На локации {location} нет пойманной рыбы.")
            return
        
        # Форматируем список рыбы (цитата + спойлер)
        lines = []
        for i, fish in enumerate(location_fish, 1):
            rarity_emoji = {
                'Обычная': '⚪',
                'Редкая': '🔵',
                'Легендарная': '🟣'
            }
            fish_name = html.escape(str(fish.get('fish_name', '')))
            weight = html.escape(str(fish.get('weight', 0)))
            length_val = fish.get('length', 0)
            length_str = f" | Размер: {length_val} см" if length_val and length_val > 0 else ""
            if fish.get('is_trash'):
                lines.append(
                    f"{i}. 🗑️ {fish_name}\n"
                    f"   Вес: {weight} кг\n"
                )
            else:
                rarity = fish.get('rarity', 'Обычная')
                lines.append(
                    f"{i}. {fish_name}\n"
                    f"   Вес: {weight} кг{html.escape(length_str)}\n"
                    f"   {rarity_emoji.get(rarity, '⚪')} {html.escape(rarity)}\n"
                )
        fish_list = "\n".join(lines).strip()
        location_text = html.escape(str(location))
        message = (
            f"📍 {location_text}\n\n"
            "Рыба, поймана на этой локации:\n\n"
            f"<blockquote><span class=\"tg-spoiler\">{fish_list}</span></blockquote>\n\n"
            f"Всего рыбы: {len(location_fish)}"
        )
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад к локациям", callback_data=f"inventory_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error editing inventory message: {e}")
            await query.edit_message_text(f"Ошибка при показе инвентаря: {e}")
    
    async def handle_sell_species(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Продажа конкретного вида рыбы"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_sell_species")
            return
        
        # Проверка прав доступа - извлекаем user_id из callback_data
        # Формат: sell_species_{fish_name}_{user_id}
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        # Извлекаем название вида рыбы из callback_data
        parts = query.data.split('_')
        fish_name = '_'.join(parts[2:-1]).replace('_', ' ')
        
        await query.answer()
        
        # Получаем всю рыбу этого вида
        caught_fish = db.get_caught_fish(user_id, chat_id)
        species_fish = [f for f in caught_fish if f['fish_name'] == fish_name and f.get('sold', 0) == 0]
        
        if not species_fish:
            await query.edit_message_text("Рыба этого вида не найдена.")
            return
        
        if len(species_fish) == 1:
            total_value = species_fish[0]['price']
            player = db.get_player(user_id, chat_id)
            db.mark_fish_as_sold([species_fish[0]['id']])
            db.update_player(user_id, chat_id, coins=player['coins'] + total_value)

            xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary([species_fish[0]])
            level_info = db.add_player_xp(user_id, chat_id, xp_earned)
            progress_line = format_level_progress(level_info)
            total_xp_now = level_info.get('xp_total', 0)
            
            message = f"""✅ Продажа успешна!

🐟 Продано: {fish_name} (×1)
💰 Получено: {total_value} 🪙
⚖️ Вес продано: {total_weight:.2f} кг
🎯 Бонус за вес: +{weight_bonus} XP
✨ Опыт итого: +{xp_earned}
📈 Всего опыта: {total_xp_now}
{progress_line}
Новый баланс: {player['coins'] + total_value} 🪙"""
            
            keyboard = [
                [InlineKeyboardButton("🐟 Назад в лавку", callback_data=f"sell_fish_{user_id}")],
                [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")
            return

        context.user_data['waiting_sell_quantity'] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "fish_name": fish_name,
            "max_qty": len(species_fish),
            "rarity": species_fish[0].get('rarity')
        }

        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data=f"sell_quantity_cancel_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Сколько хотите продать?\nМаксимум: {len(species_fish)}\n\n"
            "Отправьте число в чат.",
            reply_markup=reply_markup
        )
    
    async def handle_sell_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Продажа всей рыбы"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_sell_all")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        # Получаем всю рыбу пользователя (только непроданную)
        caught_fish = db.get_caught_fish(user_id, chat_id)
        unsold_fish = [f for f in caught_fish if f.get('sold', 0) == 0]
        
        if not unsold_fish:
            await query.edit_message_text("У вас нет рыбы для продажи.")
            return
        
        total_value = sum(f['price'] for f in unsold_fish)
        fish_count = len(unsold_fish)

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Да", callback_data=f"confirm_sell_all_{user_id}"
                ),
                InlineKeyboardButton(
                    "❌ Нет", callback_data=f"cancel_sell_all_{user_id}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Вы уверены, что хотите продать всю рыбу?\n\n"
            f"🐟 Количество: {fish_count}\n"
            f"💰 Сумма: {total_value} 🪙",
            reply_markup=reply_markup
        )
        
    async def handle_confirm_sell_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение продажи всей рыбы"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_confirm_sell_all")
            return
        
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        caught_fish = db.get_caught_fish(user_id, chat_id)
        unsold_fish = [f for f in caught_fish if f.get('sold', 0) == 0]
        if not unsold_fish:
            await query.edit_message_text("У вас нет рыбы для продажи.")
            return
        
        total_value = sum(f['price'] for f in unsold_fish)
        fish_count = len(unsold_fish)
        
        player = db.get_player(user_id, chat_id)
        fish_ids = [f['id'] for f in unsold_fish]
        db.mark_fish_as_sold(fish_ids)
        db.update_player(user_id, chat_id, coins=player['coins'] + total_value)

        xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary(unsold_fish)
        level_info = db.add_player_xp(user_id, chat_id, xp_earned)
        progress_line = format_level_progress(level_info)
        total_xp_now = level_info.get('xp_total', 0)
        
        message = f"""✅ Продажа успешна!

🐟 Продано: {fish_count} рыб
💰 Получено: {total_value} 🪙
⚖️ Вес продано: {total_weight:.2f} кг
🎯 Бонус за вес: +{weight_bonus} XP
✨ Опыт итого: +{xp_earned}
📈 Всего опыта: {total_xp_now}
    {progress_line}
Новый баланс: {player['coins'] + total_value} 🪙"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def handle_cancel_sell_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена продажи всей рыбы"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_cancel_sell_all")
            return
        
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🐟 Назад в лавку", callback_data=f"sell_fish_{user_id}")],
            [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("Продажа отменена.", reply_markup=reply_markup)

    async def handle_sell_quantity_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена продажи выбранного вида рыбы"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_sell_quantity_cancel")
            return
        
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        context.user_data.pop('waiting_sell_quantity', None)
        
        keyboard = [
            [InlineKeyboardButton("🐟 Назад в лавку", callback_data=f"sell_fish_{user_id}")],
            [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("Продажа отменена.", reply_markup=reply_markup)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - показать статистику"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        stats = db.get_player_stats(user_id, chat_id)
        caught_fish = db.get_caught_fish(user_id, chat_id)
        
        message = f"""
📊 Ваша статистика

🎣 Всего поймано рыбы: {stats['total_fish']}
📏 Общий вес: {stats['total_weight']} кг
🗑️ Мусорный вес: {stats.get('trash_weight', 0)} кг
💰 Продано: {stats.get('sold_fish_count', 0)} рыб ({stats.get('sold_fish_weight', 0)} кг)
🔢 Уникальных видов: {stats['unique_fish']}
🏆 Самая большая рыба: {stats['biggest_fish']} ({stats['biggest_weight']} кг)

💰 Баланс: {player['coins']} 🪙
🏅 Уровень: {player.get('level', 0)} ({player.get('xp', 0)} XP)
🎣 Текущая удочка: {player['current_rod']}
📍 Текущая локация: {player['current_location']}
🪱 Текущая наживка: {player['current_bait']}
        """

        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

    async def rules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /rules - показать правила"""
        message = f"Привет, рыбак! Правила можно прочитать по этой ссылке: {RULES_LINK}"
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.edit_message_text(message)

    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info - показать ссылку с информацией"""
        message = f"Привет, рыбак! Информацию можно прочитать по этой ссылке: {INFO_LINK}"
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.edit_message_text(message)

    async def topl_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /topl - топ по уровню (глобально)"""
        rows = db.get_level_leaderboard(limit=10)
        if not rows:
            body = "Нет данных"
        else:
            lines = []
            for i, row in enumerate(rows, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                username = html.escape(str(row.get('username') or 'Неизвестно'))
                level = row.get('level', 0)
                xp = row.get('xp', 0)
                lines.append(f"{medal} {username}: {level} ур. ({xp} XP)")
            body = "\n".join(lines)

        message = f"""
🏆 Топ по уровню (глобально)
<blockquote><span class="tg-spoiler">{body}</span></blockquote>
        """
        if update.message:
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(message, parse_mode="HTML")
    
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /leaderboard - таблица лидеров"""
        from datetime import datetime, timedelta

        chat_id = update.effective_chat.id
        now = datetime.now()
        week_since = now - timedelta(days=7)
        day_since = now - timedelta(days=1)

        def format_leaderboard(title: str, rows: list) -> str:
            if not rows:
                body = "Нет уловов"
            else:
                filtered = []
                for player in rows:
                    raw_username = str(player.get('username') or '').strip()
                    if not raw_username or raw_username == 'Неизвестно':
                        continue
                    filtered.append((raw_username, player.get('total_weight', 0)))

                if not filtered:
                    body = "Нет уловов"
                else:
                    lines = []
                    for i, (raw_username, total_weight) in enumerate(filtered, 1):
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        username = html.escape(raw_username)
                        weight_value = float(total_weight or 0)
                        lines.append(f"{medal} {username}: {weight_value:.2f} кг")
                    body = "\n".join(lines)
            return f"{title}\n<blockquote><span class=\"tg-spoiler\">{body}</span></blockquote>"

        global_week = db.get_leaderboard_period(limit=10, since=week_since)
        global_day = db.get_leaderboard_period(limit=10, since=day_since)

        chat_week = db.get_leaderboard_period(limit=10, since=week_since, chat_id=chat_id)
        chat_day = db.get_leaderboard_period(limit=10, since=day_since, chat_id=chat_id)

        message = "🏆 Таблица лидеров\n\n"
        message += "🌍 Глобальный топ\n"
        message += format_leaderboard("За неделю", global_week)
        message += "\n"
        message += format_leaderboard("За день", global_day)
        message += "\n\n"
        message += "🏠 Топ чата\n"
        message += format_leaderboard("За неделю", chat_week)
        message += "\n"
        message += format_leaderboard("За день", chat_day)

        if update.message:
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(message, parse_mode="HTML")
    
    async def repair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /repair - показать информацию о ремонте удочки"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        player = db.get_player(user_id, chat_id)
        if not player:
            await update.message.reply_text("❌ Профиль не найден!")
            return
        
        # Получаем информацию об удочке
        rod_name = player['current_rod']
        if not rod_name or not db.get_rod(rod_name):
            rod_name = BAMBOO_ROD
            db.update_player(user_id, chat_id, current_rod=rod_name)

        if rod_name in TEMP_ROD_RANGES:
            await update.message.reply_text(
                "❌ Эта удочка одноразовая и не ремонтируется.\n"
                "Купите новую в магазине."
            )
            return
        player_rod = db.get_player_rod(user_id, rod_name, chat_id)
        
        if not player_rod:
            # Инициализируем удочку, если записи нет
            db.init_player_rod(user_id, rod_name, chat_id)
            player_rod = db.get_player_rod(user_id, rod_name, chat_id)
        if not player_rod:
            await update.message.reply_text("❌ Ошибка: удочка не найдена.")
            return
        
        current_dur = player_rod['current_durability']
        max_dur = player_rod['max_durability']
        recovery_start = player_rod.get('recovery_start_time')
        
        # Вычисляем стоимость ремонта
        missing_durability = max_dur - current_dur
        if missing_durability <= 0:
            await update.message.reply_text("✅ Ваша удочка в идеальном состоянии! Ремонт не требуется.")
            return
        
        # Стоимость: 20 звезд за 100% урона, пропорционально меньше
        repair_cost = max(1, int(20 * missing_durability / max_dur))
        
        # Формируем сообщение
        message = f"🔧 Ремонт удочки\n\n"
        message += f"🎣 Удочка: {rod_name}\n"
        message += f"💪 Прочность: {current_dur}/{max_dur}\n"
        
        # Рассчитываем время до полного восстановления
        if recovery_start:
            from datetime import datetime
            recovery_started = datetime.fromisoformat(recovery_start)
            recovery_per_10min = max(1, max_dur // 30)
            intervals_needed = (missing_durability + recovery_per_10min - 1) // recovery_per_10min
            total_minutes = intervals_needed * 10
            
            hours = total_minutes // 60
            minutes = total_minutes % 60
            message += f"⏱ Автовосстановление: {hours}ч {minutes}мин\n\n"
        else:
            # Начинаем восстановление, если еще не начато
            if current_dur < max_dur:
                db.start_rod_recovery(user_id, rod_name, chat_id)
            
            recovery_per_10min = max(1, max_dur // 30)
            intervals_needed = (missing_durability + recovery_per_10min - 1) // recovery_per_10min
            total_minutes = intervals_needed * 10
            
            hours = total_minutes // 60
            minutes = total_minutes % 60
            message += f"⏱ До полного восстановления: {hours}ч {minutes}мин\n\n"
        
        message += f"💰 Мгновенный ремонт: {repair_cost} ⭐\n"
        message += f"(Восстановит до {max_dur}/{max_dur})"
        
        # Кнопка оплаты
        keyboard = [[InlineKeyboardButton(
            f"⚡ Починить за {repair_cost} ⭐", 
            callback_data=f"instant_repair_{rod_name}_{user_id}"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Тестовая команда для проверки всех функций"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            # Тест получения игрока
            player = db.get_player(user_id, chat_id)
            if player:
                await update.message.reply_text(f"✅ Игрок найден: {player['username']}")
            else:
                await update.message.reply_text("❌ Игрок не найден")
                return
            
            # Тест получения локаций
            locations = db.get_locations()
            await update.message.reply_text(f"✅ Локаций найдено: {len(locations)}")
            
            # Тест получения удочек
            rods = db.get_rods()
            await update.message.reply_text(f"✅ Удочек найдено: {len(rods)}")
            
            # Тест получения наживок
            baits = db.get_baits()
            await update.message.reply_text(f"✅ Наживок найдено: {len(baits)}")
            
            # Тест проверки возможности рыбалки
            can_fish, message = game.can_fish(user_id, chat_id)
            await update.message.reply_text(f"✅ Проверка рыбалки: {can_fish} - {message}")
            
            await update.message.reply_text("🎉 Все тесты пройдены!")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка в тесте: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - помощь"""
        help_text = """
🎣 Помощь по боту для рыбалки

Команды:
/start - создать профиль
/menu - меню рыбалки
/fish - начать рыбалку
/net - использовать сеть
/shop - магазин
/weather - погода на локации
/stats - ваша статистика
/leaderboard - таблица лидеров
/repair - починить удочку
/help - эта помощь

Как играть:
1. Используйте /fish чтобы начать рыбалку
2. Если рыба сорвалась, можете оплатить гарантированный улов
3. Собирайте разные виды рыбы
4. Улучшайте снасти в магазине
5. Используйте сети для массового улова

Удачной рыбалки! 🎣
        """
        
        await update.message.reply_text(help_text)
    
    async def net_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /net - использовать сеть"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        # Показываем доступные сети игрока
        player_nets = db.get_player_nets(user_id, chat_id)
        if not player_nets:
            db.init_player_net(user_id, 'Базовая сеть', chat_id)
            player_nets = db.get_player_nets(user_id, chat_id)
        
        if not player_nets:
            await update.message.reply_text(
                "❌ У вас нет сетей!\n\n"
                "Используйте /shop чтобы купить сети."
            )
            return
        
        # Показываем меню выбора сети
        keyboard = []
        for net in player_nets:
            cooldown = db.get_net_cooldown_remaining(user_id, net['net_name'], chat_id)
            if cooldown > 0:
                hours = cooldown // 3600
                minutes = (cooldown % 3600) // 60
                time_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
                status = f"⏳ {time_str}"
                callback_disabled = True
            elif net['max_uses'] != -1 and net['uses_left'] <= 0:
                status = "❌ Использовано"
                callback_disabled = True
            else:
                uses_str = "∞" if net['max_uses'] == -1 else f"{net['uses_left']}"
                status = f"✅ ({uses_str} исп.)"
                callback_disabled = False
            button_text = f"🕸️ {net['net_name']} - {status}"
            callback_data = f"use_net_{net['net_name']}_{user_id}" if not callback_disabled else "net_disabled"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        keyboard.append([InlineKeyboardButton("🔙 Меню", callback_data=f"back_to_menu_{user_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"🕸️ Выберите сеть для использования:\n\n📍 Локация: {player['current_location']}"
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_fish_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщения 'рыбалка' и других текстовых сообщений"""
        if 'waiting_sell_selection' in context.user_data:
            data = context.user_data['waiting_sell_selection']
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            if data.get('user_id') != user_id:
                return

            message = update.effective_message
            if not message or not message.text:
                return

            raw_value = message.text.strip()
            indices = [int(x) for x in re.findall(r"\d+", raw_value)]
            required_qty = int(data.get('qty', 0))
            items = data.get('items', [])

            if not indices or len(indices) != required_qty or len(set(indices)) != len(indices):
                await update.message.reply_text(
                    f"Введите ровно {required_qty} номер(ов) из списка, например: 1 3"
                )
                return

            if any(idx < 1 or idx > len(items) for idx in indices):
                await update.message.reply_text("Номера вне диапазона списка.")
                return

            selected = [items[idx - 1] for idx in indices]
            fish_ids = [f['id'] for f in selected]
            total_value = sum(f['price'] for f in selected)
            player = db.get_player(user_id, chat_id)
            db.mark_fish_as_sold(fish_ids)
            db.update_player(user_id, chat_id, coins=player['coins'] + total_value)

            xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary(selected)
            level_info = db.add_player_xp(user_id, chat_id, xp_earned)
            progress_line = format_level_progress(level_info)
            total_xp_now = level_info.get('xp_total', 0)

            context.user_data.pop('waiting_sell_selection', None)
            context.user_data.pop('waiting_sell_quantity', None)

            keyboard = [
                [InlineKeyboardButton("🐟 Назад в лавку", callback_data=f"sell_fish_{user_id}")],
                [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Продажа успешна!\n\n"
                f"🐟 Продано: {data.get('fish_name')} (×{required_qty})\n"
                f"💰 Получено: {total_value} 🪙\n"
                f"⚖️ Вес продано: {total_weight:.2f} кг\n"
                f"🎯 Бонус за вес: +{weight_bonus} XP\n"
                f"✨ Опыт итого: +{xp_earned}\n"
                f"📈 Всего опыта: {total_xp_now}\n"
                f"{progress_line}\n"
                f"Новый баланс: {player['coins'] + total_value} 🪙",
                reply_markup=reply_markup
            )
            return

        if 'waiting_sell_quantity' in context.user_data:
            data = context.user_data['waiting_sell_quantity']
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            if data.get('user_id') != user_id:
                return

            message = update.effective_message
            if not message or not message.text:
                return

            raw_value = message.text.strip().lower()
            if raw_value in ("все", "all", "max", "макс"):
                qty = int(data.get('max_qty', 0))
            elif raw_value.isdigit():
                qty = int(raw_value)
            else:
                await update.message.reply_text(
                    f"Введите число от 1 до {data.get('max_qty', 0)} или слово 'все'."
                )
                return

            max_qty = int(data.get('max_qty', 0))
            if qty < 1 or qty > max_qty:
                await update.message.reply_text(
                    f"Введите число от 1 до {max_qty} или слово 'все'."
                )
                return

            fish_name = data.get('fish_name')
            caught_fish = db.get_caught_fish(user_id, chat_id)
            species_fish = [f for f in caught_fish if f['fish_name'] == fish_name and f.get('sold', 0) == 0]
            if not species_fish:
                context.user_data.pop('waiting_sell_quantity', None)
                await update.message.reply_text("Рыба этого вида не найдена.")
                return

            rarity = data.get('rarity')
            if rarity == 'Легендарная' and qty < len(species_fish):
                items = sorted(species_fish, key=lambda f: float(f.get('weight') or 0), reverse=True)
                lines = []
                for idx, item in enumerate(items, 1):
                    details = db.calculate_item_xp_details(item)
                    lines.append(
                        f"{idx}. {item.get('weight', 0)} кг — {details['xp_total']} XP (+{details['rarity_bonus']} редк., +{details['weight_bonus']} вес)"
                    )

                context.user_data.pop('waiting_sell_quantity', None)
                context.user_data['waiting_sell_selection'] = {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "fish_name": fish_name,
                    "qty": qty,
                    "items": items
                }

                await update.message.reply_text(
                    "Выберите рыбу для продажи (введите номера через пробел):\n\n"
                    + "\n".join(lines)
                )
                return

            fish_ids = [f['id'] for f in species_fish[:qty]]
            total_value = sum(f['price'] for f in species_fish[:qty])
            player = db.get_player(user_id, chat_id)
            db.mark_fish_as_sold(fish_ids)
            db.update_player(user_id, chat_id, coins=player['coins'] + total_value)

            xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary(species_fish[:qty])
            level_info = db.add_player_xp(user_id, chat_id, xp_earned)
            progress_line = format_level_progress(level_info)
            total_xp_now = level_info.get('xp_total', 0)

            context.user_data.pop('waiting_sell_quantity', None)

            keyboard = [
                [InlineKeyboardButton("🐟 Назад в лавку", callback_data=f"sell_fish_{user_id}")],
                [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Продажа успешна!\n\n"
                f"🐟 Продано: {fish_name} (×{qty})\n"
                f"💰 Получено: {total_value} 🪙\n"
                f"⚖️ Вес продано: {total_weight:.2f} кг\n"
                f"🎯 Бонус за вес: +{weight_bonus} XP\n"
                f"✨ Опыт итого: +{xp_earned}\n"
                f"📈 Всего опыта: {total_xp_now}\n"
                f"{progress_line}\n"
                f"Новый баланс: {player['coins'] + total_value} 🪙",
                reply_markup=reply_markup
            )
            return

        # Сначала проверяем, не ждём ли мы ввод количества наживки
        if 'waiting_bait_quantity' in context.user_data:
            await self.handle_buy_bait(update, context)
            return
        
        # Обычная обработка текстовых сообщений
        message = update.effective_message
        if not message or not message.text:
            return
        message_text = message.text.lower()
        if re.match(r"^\s*меню\b", message_text):
            await self.show_fishing_menu(update, context)
            return
        if re.match(r"^\s*(фиш|fish)\b", message_text):
            await self.fish_command(update, context)
            return
        if re.match(r"^\s*(погода|weather)\b", message_text):
            await self.weather_command(update, context)
            return
        if re.match(r"^\s*сеть\b", message_text):
            await self.net_command(update, context)
            return
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /weather и слова 'погода'"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        location = player['current_location']
        weather = db.get_or_update_weather(location)
        
        season = get_current_season()
        weather_info = weather_system.get_weather_info(weather['condition'], weather['temperature'], season)
        weather_desc = weather_system.get_weather_description(weather['condition'])
        bonus = weather_system.get_weather_bonus(weather['condition'])
        
        message = f"""🌍 Погода в локации {location}

{weather_info}
Сезон: {season}

{weather_desc}

💡 Влияние на клёв: {bonus:+d}%

Погода обновляется несколько раз в день."""
        
        await update.message.reply_text(message)
    
    async def test_weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Тестовая команда для проверки влияния погоды на броски"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = db.get_player(user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        location = player['current_location']
        weather = db.get_or_update_weather(location)
        
        bonus = weather_system.get_weather_bonus(weather['condition'])
        
        # Симулируем броски
        message = f"""🧪 Тестирование влияния погоды

📍 Локация: {location}
🌦️ Погода: {weather['condition']} ({bonus:+d}%)
🌡️ Температура: {weather['temperature']}°C

Диапазоны:
• 1-30: Ничего не клюёт (NO_BITE)
• 31-50: Мусор (TRASH)
• 51-100: Рыба (CATCH)

Примеры бросков с текущей погодой:
"""
        
        test_rolls = [10, 25, 35, 50, 60, 80, 95]
        
        for roll in test_rolls:
            adjusted = roll + bonus
            adjusted = max(1, min(100, adjusted))
            
            if adjusted <= 30:
                result = "❌ Ничего не клюёт"
            elif adjusted <= 50:
                result = "🗑️ Мусор"
            else:
                if adjusted <= 80:
                    result = "🐟 Рыба (обычная)"
                elif adjusted <= 95:
                    result = "🐟 Рыба (редкая)"
                else:
                    result = "🐟 Рыба (легендарная)"
            
            message += f"\nБросок {roll}: → {adjusted} = {result}"
        
        message += f"""

Как это работает:
1. Сначала выпадает случайный бросок (1-100)
2. К нему прибавляется бонус/штраф погоды ({bonus:+d}%)
3. Результат ограничивается от 1 до 100
4. По результату определяется исход"""
        
        await update.message.reply_text(message)
    
    async def handle_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки статистики"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        player = db.get_player(user_id, chat_id)
        
        if not player:
            await query.edit_message_text("Сначала создайте профиль командой /start")
            return
        
        stats = db.get_player_stats(user_id, chat_id)
        caught_fish = db.get_caught_fish(user_id, chat_id)
        
        message = f"""
📊 Ваша статистика

🎣 Всего поймано рыбы: {stats['total_fish']}
📏 Общий вес: {stats['total_weight']} кг
💰 Продано: {stats.get('sold_fish_count', 0)} рыб ({stats.get('sold_fish_weight', 0)} кг)
🔢 Уникальных видов: {stats['unique_fish']}
🏆 Самая большая рыба: {stats['biggest_fish']} ({stats['biggest_weight']} кг)

💰 Баланс: {player['coins']} 🪙
🏅 Уровень: {player.get('level', 0)} ({player.get('xp', 0)} XP)
🎣 Текущая удочка: {player['current_rod']}
📍 Текущая локация: {player['current_location']}
🪱 Текущая наживка: {player['current_bait']}
        """
        
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_leaderboard_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки таблицы лидеров"""
        query = update.callback_query
        await query.answer()
        await self.leaderboard_command(update, context)
    
    async def handle_start_fishing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка начала рыбалки"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        player = db.get_player(user_id, chat_id)
        
        # Проверяем кулдаун
        can_fish, message = game.can_fish(user_id, chat_id)
        if not can_fish:
            # Отправляем сообщение с причиной и кнопкой оплаты
            keyboard = [
                [InlineKeyboardButton(
                    f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", 
                    callback_data=f"pay_telegram_star_{user_id}_{player['current_location']}"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⏰ {message}", 
                reply_markup=reply_markup
            )
            return
        
        # Начинаем рыбалку на текущей локации
        result = game.fish(user_id, chat_id, player['current_location'])
        
        if result['success']:
            if result.get('is_trash'):
                trash = result.get('trash') or {}
                trash_name = (trash.get('name') or '').strip()
                location_val = result.get('location') or player.get('current_location') or chat_id
                message = f"""
{trash_name or 'Мусор'}

📏 Вес: {trash.get('weight', 0)} кг
💰 Стоимость: {trash.get('price', 0)} 🪙
📍 Место: {location_val}
                """
                sticker_message = None
                # Нормализуем имя мусора для поиска
                trash_name_normalized = trash_name.strip().title()
                trash_sticker_file = TRASH_STICKERS.get(trash_name) or TRASH_STICKERS.get(trash_name_normalized)

                if trash_sticker_file:
                    try:
                        trash_image = trash_sticker_file
                        image_path = Path(__file__).parent / trash_image
                        if image_path.exists():
                            reply_to_id = query.message.message_id if query and query.message else None
                            try:
                                sticker_message = await self.application.bot.send_document(
                                    chat_id=update.effective_chat.id,
                                    document=open(image_path, 'rb'),
                                    reply_to_message_id=reply_to_id
                                )
                                if sticker_message:
                                    context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                            except Exception as send_exc:
                                logger.error(f"[TRASH SEND ERROR] Could not send trash image for '{trash_name}' (file: {image_path}): {send_exc}")
                        else:
                            logger.error(f"[TRASH FILE MISSING] Trash sticker file missing: {image_path}")
                    except Exception as e:
                        logger.error(f"[TRASH LOGIC ERROR] Unexpected error preparing trash image for '{trash_name}': {e}")
                else:
                    logger.warning(f"Trash sticker not found for name: '{trash_name}' (normalized: '{trash_name_normalized}')")

                await query.edit_message_text(message)
                return

            fish = result.get('fish')
            if not fish:
                logger.error("Guaranteed catch missing fish data for user %s", user_id)
                await self.application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Не удалось получить данные улова. Звезды будут возвращены."
                )
                telegram_payment_charge_id_val = context.user_data.get('telegram_payment_charge_id')
                await self.refund_star_payment(user_id, telegram_payment_charge_id_val)
                return

            weight = result['weight']
            length = result['length']

            logger.info(
                "Catch: user=%s (%s) fish=%s location=%s bait=%s weight=%.2fkg length=%.1fcm",
                update.effective_user.id,
                update.effective_user.username or update.effective_user.full_name,
                fish['name'],
                result['location'],
                player['current_bait'],
                weight,
                length
            )
            
            # Формируем сообщение о пойманной рыбе
            rarity_emoji = {
                'Обычная': '⚪',
                'Редкая': '🔵',
                'Легендарная': '🟣'
            }
            fish_name_display = format_fish_name(fish['name'])
            
            message = f"""
🎉 Поздравляю! Вы поймали рыбу!

{rarity_emoji.get(fish['rarity'], '⚪')} {fish_name_display}
📏 Размер: {length}см | Вес: {weight} кг
💰 Стоимость: {fish['price']} 🪙
📍 Место: {result['location']}
⭐ Редкость: {fish['rarity']}

Ваш баланс: {result['new_balance']} 🪙
            """
            
            if result.get('guaranteed'):
                message += "\n⭐ Гарантированный улов!"
            
            # Отправляем стикер рыбы если он есть
            if fish['name'] in FISH_STICKERS:
                try:
                    fish_image = FISH_STICKERS[fish['name']]
                    image_path = Path(__file__).parent / fish_image
                    sticker_message = await self.application.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(image_path, 'rb'),
                        reply_to_message_id=query.message.reply_to_message.message_id if query.message.reply_to_message else None
                    )
                    if sticker_message:
                        context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                        context.bot_data.setdefault("sticker_fish_map", {})[sticker_message.message_id] = {
                            "fish_name": fish['name'],
                            "weight": weight,
                            "price": fish['price'],
                            "location": result['location'],
                            "rarity": fish['rarity']
                        }
                except Exception as e:
                    logger.warning(f"Could not send fish image for {fish['name']}: {e}")
            
            await query.edit_message_text(message)

            if result.get('temp_rod_broken'):
                await self.application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        "💥 Временная удочка сломалась после удачного улова.\n"
                        "Теперь активна бамбуковая. Купить новую можно в магазине."
                    )
                )
                return
            
            # ПОСЛЕ сообщения о рыбе проверяем и сообщаем о прочности удочки
            if player['current_rod'] == BAMBOO_ROD and result.get('rod_broken'):
                durability_message = f"""
💔 Удочка сломалась!

🔧 Прочность: 0/{result.get('max_durability', 100)}

Используйте /repair чтобы починить удочку или подождите автовосстановления.
                """
                await self.application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=durability_message
                )
            elif player['current_rod'] == BAMBOO_ROD and result.get('current_durability', 100) < result.get('max_durability', 100):
                # Показываем текущую прочность если она уменьшилась
                current = result.get('current_durability', 100)
                maximum = result.get('max_durability', 100)
                durability_message = f"🔧 Прочность удочки: {current}/{maximum}"
                await self.application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=durability_message
                )
            return
        else:
            if result.get('snap'):
                # Срыв на неправильной наживке
                snap_message = f"""
⚠️ СРЫВ РЫБЫ!

{result['message']}

🪱 Вы использовали: {result['wrong_bait']}
📍 Локация: {result['location']}

💡 Совет: Попробуйте другую наживку!
                """
                
                await query.edit_message_text(snap_message)
                return
            elif result.get('rod_broken'):
                message = f"""
💔 Удочка сломалась!

{result['message']}

Используйте /repair чтобы починить удочку.
                """
            elif result.get('is_trash'):
                # Мусор пойман
                xp_line = ""
                progress_line = ""
                if result.get('xp_earned'):
                    xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                    progress_line = f"\n{format_level_progress(result.get('level_info'))}"
                message = f"""
{result['message']}

📦 Мусор: {result['trash']['name']}
⚖️ Вес: {result['trash']['weight']} кг
💰 Стоимость: {result['trash']['price']} 🪙
{xp_line}{progress_line}

Ваш баланс: {result['new_balance']} 🪙
                """
                
                # Отправляем стикер мусора если он есть
                if result['trash']['name'] in TRASH_STICKERS:
                    try:
                        trash_image = TRASH_STICKERS[result['trash']['name']]
                        image_path = Path(__file__).parent / trash_image
                        sticker_message = await self.application.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=open(image_path, 'rb')
                        )
                        if sticker_message:
                            context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                    except Exception as e:
                        logger.warning(f"Could not send trash image for {result['trash']['name']}: {e}")
                
                await query.edit_message_text(message)
                if result.get('temp_rod_broken'):
                    await self.application.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=(
                            "💥 Временная удочка сломалась после удачного улова.\n"
                            "Теперь активна бамбуковая. Купить новую можно в магазине."
                        )
                    )
                return
            elif result.get('no_bite'):
                # Отправляем сообщение с причиной и кнопкой оплаты
                keyboard = [
                    [InlineKeyboardButton(
                        f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", 
                        callback_data=f"pay_telegram_star_{user_id}_{result['location']}"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"""
😔 {result['message']}

📍 Локация: {result['location']}
                """
                
                await query.edit_message_text(message, reply_markup=reply_markup)
                return
            else:
                # Отправляем сообщение с причиной и кнопкой оплаты
                keyboard = [
                    [InlineKeyboardButton(
                        f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", 
                        callback_data=f"pay_telegram_star_{user_id}_{result['location']}"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"""
😔 {result['message']}

📍 Локация: {result['location']}
                """
                
                await query.edit_message_text(message, reply_markup=reply_markup)
                return
        
        await query.edit_message_text(message)
    
    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка precheckout для Telegram Stars"""
        query = update.pre_checkout_query
        payload = getattr(query, "invoice_payload", "") or ""
        if payload.startswith("guaranteed_"):
            user_id = query.from_user.id
            active = self.active_invoices.get(user_id)
            if not active or active.get("payload") != payload:
                await query.answer(ok=False, error_message="Инвойс устарел. Запросите новый.")
                return
        await query.answer(ok=True)
    
    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка успешной оплаты через Telegram Stars"""
        payment = update.message.successful_payment
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        telegram_payment_charge_id = getattr(payment, "telegram_payment_charge_id", None)
        total_amount = getattr(payment, "total_amount", 0)

        # Сохраняем транзакцию
        if telegram_payment_charge_id:
            db.add_star_transaction(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                total_amount=total_amount,
                refund_status="none"
            )
        
        # Убираем запланированный таймаут для этого сообщения
        timeout_key = f"payment_{update.effective_chat.id}_{update.message.message_id}"
        if timeout_key in self.active_timeouts:
            del self.active_timeouts[timeout_key]
        
        # Извлекаем локацию и chat_id из payload (если есть) или используем текущую
        payload = payment.invoice_payload
        if payload and payload.startswith("repair_rod_"):
            # Обработка восстановления удочки
            rod_name = payload.replace("repair_rod_", "")
            if rod_name in TEMP_ROD_RANGES:
                try:
                    await update.message.reply_text(
                        "❌ Эта удочка одноразовая и не ремонтируется."
                    )
                except Exception as e:
                    logger.warning(f"Could not send temp rod repair rejection to {user_id}: {e}")
                return
            db.repair_rod(user_id, rod_name, update.effective_chat.id)
            
            # Отправляем подтверждение в ЛС
            try:
                await update.message.reply_text(
                    f"✅ Удочка '{rod_name}' полностью восстановлена!"
                )
            except Exception as e:
                logger.warning(f"Could not send repair confirmation to {user_id}: {e}")
            return
        elif payload and payload.startswith("guaranteed_"):
            parts = payload.replace("guaranteed_", "").rsplit("_", 2)
            if len(parts) >= 3:
                location = parts[0]
                group_chat_id = int(parts[1])
            elif len(parts) == 2:
                location = parts[0]
                group_chat_id = int(parts[1])
            else:
                location = "Неизвестно"
                group_chat_id = update.effective_chat.id
        else:
            # Получаем текущую локацию игрока
            player = db.get_player(user_id, chat_id)
            location = player['current_location']
            group_chat_id = update.effective_chat.id
        
        # Получаем и сохраняем информацию о сообщении с кнопкой ДО удаления из active_invoices
        group_message_id = None
        if user_id in self.active_invoices:
            group_message_id = self.active_invoices[user_id].get('group_message_id')
            # Теперь удаляем инвойс из активных
            del self.active_invoices[user_id]
        
        # Выполняем гарантированный улов (все проверки уже пройдены в precheckout)
        try:
            result = game.fish(user_id, group_chat_id, location, guaranteed=True)
        except Exception as e:
            logger.error(f"Critical error in guaranteed catch for user {user_id}: {e}", exc_info=True)
            message = f"❌ Произошла критическая ошибка при выполнении улова: {str(e)}. Пожалуйста, обратитесь в поддержку."
            await self.application.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message
            )

            # Возвращаем звезды, если оплата прошла, но улов не был обработан
            await self.refund_star_payment(user_id, telegram_payment_charge_id)
            return
        
        # If result indicates trash (even when success==False in game logic), handle it here
        if result.get('is_trash'):
            trash = result.get('trash') or {}
            message = f"""
{trash.get('name', 'Мусор')}

📏 Вес: {trash.get('weight', 0)} кг
💰 Стоимость: {trash.get('price', 0)} 🪙
📍 Место: {result.get('location', location)}
            """

            # Try to send trash sticker in reply to the original group message (invoice button)
            sticker_message = None
            try:
                trash_name = trash.get('name')
                if trash_name in TRASH_STICKERS:
                    trash_image = TRASH_STICKERS[trash_name]
                    image_path = Path(__file__).parent / trash_image
                    if group_message_id:
                        sticker_message = await self.application.bot.send_document(
                            chat_id=group_chat_id,
                            document=open(image_path, 'rb'),
                            reply_to_message_id=group_message_id
                        )
                    else:
                        sticker_message = await self.application.bot.send_document(
                            chat_id=group_chat_id,
                            document=open(image_path, 'rb')
                        )

                    if sticker_message:
                        context.bot_data.setdefault('last_bot_stickers', {})[group_chat_id] = sticker_message.message_id
                        context.bot_data.setdefault('sticker_fish_map', {})[sticker_message.message_id] = {
                            'fish_name': trash_name,
                            'weight': trash.get('weight', 0),
                            'price': trash.get('price', 0),
                            'location': result.get('location', location),
                            'rarity': 'Мусор'
                        }
            except Exception as e:
                logger.warning(f"Could not send trash image for {trash.get('name')}: {e}")

            # If we had a sticker, reply with info to the sticker; otherwise reply to the original group message
            if sticker_message:
                await self.application.bot.send_message(
                    chat_id=group_chat_id,
                    text=message,
                    reply_to_message_id=sticker_message.message_id
                )
            else:
                await self.application.bot.send_message(
                    chat_id=group_chat_id,
                    text=message,
                    reply_to_message_id=group_message_id
                )
            return

        fish = result.get('fish')
        if not fish:
            logger.error("Guaranteed catch missing fish data for user %s", user_id)
            await self.application.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось получить данные улова. Звезды будут возвращены."
            )
            await self.refund_star_payment(user_id, telegram_payment_charge_id)
            return

        weight = result['weight']
        length = result['length']

        player = db.get_player(user_id, chat_id)
        logger.info(
            "Catch: user=%s (%s) fish=%s location=%s bait=%s weight=%.2fkg length=%.1fcm guaranteed=True",
            update.effective_user.id,
            update.effective_user.username or update.effective_user.full_name,
            fish['name'],
            result['location'],
            player['current_bait'] if player else "",
            weight,
            length
        )

        # Отправляем сообщение с характеристиками рыбы
        fish_name_display = format_fish_name(fish['name'])
        message = f"""
🐟 {fish_name_display}

📏 Размер: {length}см | Вес: {weight} кг
💰 Стоимость: {fish['price']} 🪙
📍 Место: {result['location']}
⭐ Редкость: {fish['rarity']}
        """

        # Получаем информацию о сообщении с кнопкой (уже получена выше перед удалением из active_invoices)
        logger.info(f"Using group_message_id for user {user_id}: {group_message_id}")

        # Отправляем стикер рыбы если он есть - в ответ на сообщение с кнопкой
        sticker_message = None
        if fish['name'] in FISH_STICKERS:
            try:
                fish_image = FISH_STICKERS[fish['name']]
                image_path = Path(__file__).parent / fish_image
                # Отправляем в ответ на исходное сообщение с кнопкой
                if group_message_id:
                    sticker_message = await self.application.bot.send_document(
                        chat_id=group_chat_id,
                        document=open(image_path, 'rb'),
                        reply_to_message_id=group_message_id
                    )
                else:
                    # Если нет group_message_id, отправляем просто так
                    sticker_message = await self.application.bot.send_document(
                        chat_id=group_chat_id,
                        document=open(image_path, 'rb')
                    )
                if sticker_message:
                    context.bot_data.setdefault("last_bot_stickers", {})[group_chat_id] = sticker_message.message_id
                    context.bot_data.setdefault("sticker_fish_map", {})[sticker_message.message_id] = {
                        "fish_name": fish['name'],
                        "weight": weight,
                        "price": fish['price'],
                        "location": result['location'],
                        "rarity": fish['rarity']
                    }
            except Exception as e:
                logger.warning(f"Could not send fish image for {fish['name']}: {e}")

        # Отправляем сообщение в ответ на стикер
        if sticker_message:
            await self.application.bot.send_message(
                chat_id=group_chat_id,
                text=message,
                reply_to_message_id=sticker_message.message_id
            )
        else:
            # Если стикера не было, отправляем обычное сообщение в ответ на исходное
            await self.application.bot.send_message(
                chat_id=group_chat_id,
                text=message,
                reply_to_message_id=group_message_id
            )

        if result.get('temp_rod_broken'):
            await self.application.bot.send_message(
                chat_id=group_chat_id,
                text=(
                    "💥 Временная удочка сломалась после удачного улова.\n"
                    "Теперь активна бамбуковая. Купить новую можно в магазине."
                )
            )

    async def refund_star_payment(self, user_id: int, telegram_payment_charge_id: str) -> bool:
        """Возврат Telegram Stars пользователю"""
        if not telegram_payment_charge_id:
            logger.error("refund_star_payment: отсутствует telegram_payment_charge_id")
            return False

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/refundStarPayment"
        payload = {
            "user_id": user_id,
            "telegram_payment_charge_id": telegram_payment_charge_id
        }

        try:
            response = await asyncio.to_thread(requests.post, url, data=payload, timeout=15)
            data = response.json() if response is not None else {}
            if response is not None and response.status_code == 200 and data.get("ok"):
                db.update_star_refund_status(telegram_payment_charge_id, "ref")
                logger.info("Stars refund successful for user=%s, charge_id=%s", user_id, telegram_payment_charge_id)
                return True

            logger.error("Stars refund failed: status=%s, response=%s", response.status_code if response else None, data)
            return False
        except Exception as e:
            logger.error("Stars refund exception: %s", e)
            return False

    async def refunded_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка возврата оплаты (если пользователь вернул звезды сам)"""
        message = update.message
        refunded_payment = getattr(message, "refunded_payment", None) if message else None
        if not refunded_payment:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        telegram_payment_charge_id = getattr(refunded_payment, "telegram_payment_charge_id", None)
        total_amount = getattr(refunded_payment, "total_amount", 0)

        existing = db.get_star_transaction(telegram_payment_charge_id)
        if not existing:
            db.add_star_transaction(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                total_amount=total_amount,
                refund_status="need to ban"
            )
        else:
            if existing.get("refund_status") != "ref":
                db.update_star_refund_status(telegram_payment_charge_id, "need to ban")
    
    async def handle_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученного стикера - отправка информации о рыбе"""
        if not update.message.sticker:
            return

        reply = update.message.reply_to_message
        if not reply or not reply.sticker or not reply.from_user:
            return

        # Реагируем только на стикер рыбы бота
        if not reply.from_user.is_bot:
            return

        last_bot_stickers = context.bot_data.get("last_bot_stickers", {})
        if last_bot_stickers.get(update.effective_chat.id) != reply.message_id:
            return

        fish_info_map = context.bot_data.get("sticker_fish_map", {})
        fish_info = fish_info_map.get(reply.message_id)
        if not fish_info:
            return

        fish_name_display = format_fish_name(fish_info.get('fish_name', 'Неизвестно'))
        message = f"""
    {fish_name_display}

📏 Ваш размер: {fish_info.get('weight', 'N/A')} кг
💰 Стоимость: {fish_info.get('price', 'N/A')} 🪙
📍 Место ловли: {fish_info.get('location', 'N/A')}
⭐ Редкость: {fish_info.get('rarity', 'N/A')}
            """
        await update.message.reply_text(message)
    
    async def handle_pay_telegram_star_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия на кнопку оплаты Telegram Stars"""
        query = update.callback_query
        try:
            await query.answer()
        except BadRequest as exc:
            if "Query is too old" not in str(exc):
                raise
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Извлекаем локацию из callback_data
        callback_data = query.data
        if callback_data.startswith("pay_telegram_star_"):
            parts = callback_data.split("_", 4)
            if len(parts) < 5:
                await query.answer("Некорректные данные кнопки", show_alert=True)
                return
            target_user_id = parts[3]
            location = parts[4]
            if str(user_id) != str(target_user_id):
                await query.answer("Эта кнопка не для вас", show_alert=True)
                return
        else:
            location = "Неизвестно"

        existing_invoice = self.active_invoices.get(user_id)
        if existing_invoice:
            created_at = existing_invoice.get("created_at")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at)
                except ValueError:
                    created_time = None
            else:
                created_time = None

            if created_time:
                age_seconds = (datetime.now() - created_time).total_seconds()
                if age_seconds < 120:
                    await query.answer("Инвойс уже отправлен в личные сообщения", show_alert=True)
                    return

            await self.cancel_previous_invoice(user_id)
        
        # Создаем ссылку на чат
        if update.effective_chat.type == 'private':
            chat_link = f"Личные сообщения с @{update.effective_user.username or 'user'}"
        else:
            chat_link = f"Чат: {update.effective_chat.title}"
        
        # Создаем инвойс для оплаты в личные сообщения
        from telegram import LabeledPrice
        
        prices = [
            LabeledPrice('Гарантированный улов', GUARANTEED_CATCH_COST)
        ]
        
        description = f"Гарантированный улов рыбы на локации: {location}\n\n📍 {chat_link}"
        
        # Отправляем инвойс в личные сообщения пользователю
        invoice_payload = f"guaranteed_{location}_{chat_id}_{int(datetime.now().timestamp())}"
        try:
            await context.bot.send_invoice(
                chat_id=user_id,  # Отправляем в личку
                title=f"Закинуть сейчас",
                description=description,
                payload=invoice_payload,
                provider_token="",  # Пусто для Telegram Stars
                currency='XTR',
                prices=prices
            )
        except Exception as e:
            logger.error(f"Failed to send invoice to user {user_id}: {e}")
            await query.answer("❌ Ошибка: чат со мной не начат. Сначала напишите /start в личные сообщения боту (@MDfish_bot)", show_alert=True)
            return
        
        # Сохраняем информацию о сообщении с кнопкой для последующей отправки стикера в ответ
        self.active_invoices[user_id] = {
            'group_chat_id': chat_id,
            'group_message_id': query.message.message_id,  # Сообщение с кнопкой в группе
            'location': location,
            'payload': invoice_payload,
            'created_at': datetime.now().isoformat()
        }
        logger.info(f"Saved invoice info for user {user_id}: group_chat_id={chat_id}, group_message_id={query.message.message_id}")

        await self.schedule_timeout(
            chat_id,
            query.message.message_id,
            "Время для оплаты истекло",
            timeout_seconds=120,
            timeout_callback=self.handle_payment_timeout
        )
        
        # Редактируем сообщение с кнопкой чтобы показать что инвойс отправлен
        await query.edit_message_text(
            f"💳 Инвойс для оплаты отправлен вам в личные сообщения!\n\n⭐ Оплатите {GUARANTEED_CATCH_COST} Telegram Stars для гарантированного улова на локации: {location}"
        )
    
    async def handle_invoice_sent_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия на сообщение об отправленном инвойсе"""
        query = update.callback_query
        try:
            await query.answer("Инвойс уже отправлен в личные сообщения", show_alert=True)
        except BadRequest as exc:
            if "Query is too old" not in str(exc):
                raise
    
    async def handle_payment_timeout(self, chat_id: int, message_id: int):
        """Обработка таймаута платежа - делаем кнопку неактивной"""
        try:
            # Находим сообщение с инвойсом и делаем кнопку неактивной
            keyboard = [
                [InlineKeyboardButton(
                    f"⏰ Время оплаты вышло", 
                    callback_data="payment_expired"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Обновляем сообщение с неактивной кнопкой
            await self.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Время для оплаты истекло",
                reply_markup=reply_markup
            )
            for user_id, invoice_info in list(self.active_invoices.items()):
                if invoice_info.get('group_message_id') == message_id:
                    del self.active_invoices[user_id]
        except Exception as e:
            # Инвойсы нельзя редактировать после оплаты или если они уже изменены
            logger.error(f"Ошибка обновления сообщения с таймаутом: {e}")
            # Просто удаляем таймер, ничего не делаем с сообщением
    
    async def handle_payment_expired_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия на просроченную кнопку оплаты"""
        query = update.callback_query
        await query.answer("Время для оплаты истекло", show_alert=True)
    
    async def handle_invoice_cancelled_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия на отмененный инвойс"""
        query = update.callback_query
        await query.answer("Срок действия инвойса истек", show_alert=True)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок с улучшенным логированием"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Проверяем тип ошибки
        error = context.error
        
        if isinstance(error, requests.exceptions.ConnectionError):
            logger.error("Проблема с подключением к Telegram API. Проверьте интернет-соединение.")
        elif isinstance(error, requests.exceptions.Timeout):
            logger.error("Таймаут подключения к Telegram API. Попробуйте позже.")
        elif isinstance(error, requests.exceptions.HTTPError):
            logger.error(f"HTTP ошибка: {error}")
        else:
            logger.error(f"Неизвестная ошибка: {type(error).__name__}: {error}")
        
        # Пытаемся отправить сообщение пользователю об ошибке
        if update and hasattr(update, 'effective_chat'):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ Произошла ошибка. Попробуйте позже."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

def main():
    """Основная функция"""
    # Парсинг аргументов командной строки
    import argparse
    parser = argparse.ArgumentParser(description='Бот для рыбалки')
    parser.add_argument('--proxy', help='URL прокси (например: socks5://127.0.0.1:1080)')
    parser.add_argument('--offline', action='store_true', help='Офлайн режим для тестирования')
    parser.add_argument('--check-only', action='store_true', help='Только проверить соединение')
    
    args = parser.parse_args()
    
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("Ошибка: Укажите токен бота в config.py или в переменной окружения BOT_TOKEN")
        return
    
    # Устанавливаем переменные окружения из аргументов
    if args.proxy:
        os.environ['TELEGRAM_PROXY'] = args.proxy
    if args.offline:
        os.environ['OFFLINE_MODE'] = '1'
    
    # Проверка соединения
    if args.check_only:
        print("🔍 Проверка соединения с Telegram API...")
        try:
            import requests
            response = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
                timeout=10
            )
            if response.status_code == 200:
                bot_info = response.json()
                print(f"✅ Соединение успешно! Бот: @{bot_info['result']['username']}")
                return
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")
            return
    
    # Проверяем офлайн режим
    offline_mode = os.environ.get('OFFLINE_MODE') == '1'
    if offline_mode:
        print("🔧 Офлайн режим - пропускаем проверку API")
    else:
        # Проверяем подключение к Telegram API
        print("🔍 Проверка подключения к Telegram API...")
        try:
            import requests
            response = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
                timeout=10
            )
            if response.status_code == 200:
                bot_info = response.json()
                print(f"✅ Подключение успешно! Бот: @{bot_info['result']['username']}")
            else:
                print(f"❌ Ошибка подключения: {response.status_code}")
                print(f"Ответ: {response.text}")
                return
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка подключения к Telegram API: {e}")
            print("Проверьте интернет-соединение или используйте прокси:")
            print("python bot.py --proxy socks5://127.0.0.1:1080")
            return
        except Exception as e:
            print(f"❌ Неизвестная ошибка: {e}")
            return
    
    # Создаем экземпляр бота
    bot_instance = FishBot()
    
    # Создаем приложение
    defaults = Defaults(parse_mode="HTML")
    emoji_bot = EmojiBot(token=BOT_TOKEN, defaults=defaults)
    application = Application.builder().bot(emoji_bot).build()
    
    # Устанавливаем приложение в экземпляр бота
    bot_instance.application = application
    
    # Создаем asyncio scheduler
    bot_instance.scheduler = AsyncIOScheduler()
    # Scheduler будет запущен после запуска приложения
    print("✅ Application создана успешно")
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CommandHandler("fish", bot_instance.fish_command))
    application.add_handler(CommandHandler("menu", bot_instance.menu_command))
    application.add_handler(CommandHandler("shop", bot_instance.handle_shop))
    application.add_handler(CommandHandler("net", bot_instance.net_command))
    application.add_handler(CommandHandler("weather", bot_instance.weather_command))
    application.add_handler(CommandHandler("testweather", bot_instance.test_weather_command))
    application.add_handler(CommandHandler("stats", bot_instance.stats_command))
    application.add_handler(CommandHandler("rules", bot_instance.rules_command))
    application.add_handler(CommandHandler("info", bot_instance.info_command))
    application.add_handler(CommandHandler("topl", bot_instance.topl_command))
    application.add_handler(CommandHandler("leaderboard", bot_instance.leaderboard_command))
    application.add_handler(CommandHandler("repair", bot_instance.repair_command))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    application.add_handler(CommandHandler("test", bot_instance.test_command))
    
    # Обработчики платежей
    application.add_handler(PreCheckoutQueryHandler(bot_instance.precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, bot_instance.successful_payment_callback))
    
    # Обработчик новых участников группы (ДОЛЖЕН БЫТЬ ДО filters.ALL!)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_instance.welcome_new_member))
    
    # Обработчик сообщений о рыбалке и покупке наживки (должен быть перед filters.ALL)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_fish_message))
    
    # Обработчик стикеров
    application.add_handler(MessageHandler(filters.Sticker.ALL, bot_instance.handle_sticker))
    
    # Обработчик возврата платежей (использует refunded_payment)
    application.add_handler(MessageHandler(filters.ALL, bot_instance.refunded_payment_callback))
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(bot_instance.handle_start_fishing, pattern="^start_fishing_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_change_location, pattern="^change_location_"))
    # Важно: более специфичные паттерны должны идти первыми
    application.add_handler(CallbackQueryHandler(bot_instance.handle_change_bait_location, pattern="^change_bait_loc_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_change_rod, pattern="^change_rod_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_change_bait, pattern=r"^change_bait_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_location, pattern="^select_location_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_rod, pattern="^select_rod_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_rod, pattern="^sr_"))  # Короткий формат
    application.add_handler(CallbackQueryHandler(bot_instance.handle_instant_repair, pattern="^instant_repair_"))  # Мгновенный ремонт
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_bait_buy, pattern="^select_bait_buy_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_bait_buy, pattern="^sb_"))  # Короткий формат
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_bait, pattern="^select_bait_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_bait, pattern="^sbi_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_net, pattern="^select_net_"))  # Выбор сети в меню
    application.add_handler(CallbackQueryHandler(bot_instance.handle_use_net, pattern="^use_net_"))  # Использование сетей
    application.add_handler(CallbackQueryHandler(bot_instance.handle_back_to_menu, pattern="^back_to_menu_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_fish, pattern=r"^sell_fish_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_species, pattern="^sell_species_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_all, pattern=r"^sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_confirm_sell_all, pattern=r"^confirm_sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_cancel_sell_all, pattern=r"^cancel_sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_quantity_cancel, pattern=r"^sell_quantity_cancel_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory, pattern=r"^inventory_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_location, pattern="^inv_location_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop, pattern=r"^shop_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_rods, pattern="^shop_rods_"))
    # Важно: более специфичные паттерны должны идти первыми
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_baits_location, pattern="^shop_baits_loc_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_baits, pattern="^shop_baits_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_nets, pattern="^shop_nets_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_rod, pattern="^buy_rod_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_net, pattern="^buy_net_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_repair_callback, pattern="^repair_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_stats_callback, pattern="^stats_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_leaderboard_callback, pattern="^leaderboard$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_payment_expired_callback, pattern="^payment_expired$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_invoice_cancelled_callback, pattern="^invoice_cancelled$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_pay_telegram_star_callback, pattern="^pay_telegram_star_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_invoice_sent_callback, pattern="^invoice_sent$"))
    
    # Обработчик ошибок
    application.add_error_handler(bot_instance.error_handler)
    
    print("🎣 Бот для рыбалки запущен!")
    
    # Запуск бота с обработкой ошибок
    try:
        application.run_polling()
        print("✅ Polling запущен успешно")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        return

if __name__ == '__main__':
    main()
