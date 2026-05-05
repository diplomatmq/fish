# -*- coding: utf-8 -*-
import logging
import html
import random
import asyncio
import functools
import time
import re
import shlex
import uuid
import collections
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse, urlunparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, WebAppInfo
import aiofiles
import aiohttp
import aiosqlite
import asyncpg
import redis.asyncio as aioredis
# --- Button style helpers for Telegram update ---
def get_button_style(text: str) -> str:
    """Return 'primary' for yes/confirm, 'destructive' for no/cancel, else None."""
    text_lower = text.lower()
    if any(x in text_lower for x in ["да", "подтверд", "yes", "ok", "confirm"]):
        return "primary"
    if any(x in text_lower for x in ["нет", "отмена", "отклон", "cancel", "no", "decline"]):
        return "destructive"
    return None
from telegram.error import BadRequest, Forbidden, RetryAfter, TimedOut, NetworkError, Conflict, ChatMigrated
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, TypeHandler, filters, ContextTypes, Defaults, ExtBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Добавляем текущую директорию в путь для поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db, DB_PATH, BAMBOO_ROD, TEMP_ROD_RANGES

# --- TelegramBotAPI for invoice link creation ---
import httpx
from typing import Any, Optional, Dict, List

HTTP_SESSION: Optional[aiohttp.ClientSession] = None
ASYNC_PG_POOL: Optional[asyncpg.Pool] = None
ASYNC_SQLITE_CONN: Optional[aiosqlite.Connection] = None
ASYNC_REDIS: Optional[aioredis.Redis] = None
_SEND_SEMAPHORE: Optional[asyncio.Semaphore] = None
SLOW_OPERATION_SECONDS = float(os.getenv("SLOW_OPERATION_SECONDS", "2.0"))


def get_send_semaphore() -> asyncio.Semaphore:
    global _SEND_SEMAPHORE
    if _SEND_SEMAPHORE is None:
        _SEND_SEMAPHORE = asyncio.Semaphore(int(os.getenv("TG_SEND_SEMAPHORE_LIMIT", "256")))
    return _SEND_SEMAPHORE


async def get_http_session() -> aiohttp.ClientSession:
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        timeout = aiohttp.ClientTimeout(total=90, connect=30, sock_read=60, sock_connect=30)
        connector = aiohttp.TCPConnector(
            limit=int(os.getenv("AIOHTTP_LIMIT", "512")),
            limit_per_host=int(os.getenv("AIOHTTP_LIMIT_PER_HOST", "256")),
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        HTTP_SESSION = aiohttp.ClientSession(timeout=timeout, connector=connector)
    return HTTP_SESSION


async def close_global_clients() -> None:
    global HTTP_SESSION, ASYNC_PG_POOL, ASYNC_SQLITE_CONN, ASYNC_REDIS
    if HTTP_SESSION and not HTTP_SESSION.closed:
        await HTTP_SESSION.close()
    HTTP_SESSION = None
    if ASYNC_REDIS is not None:
        await ASYNC_REDIS.aclose()
    ASYNC_REDIS = None
    if ASYNC_PG_POOL is not None:
        await ASYNC_PG_POOL.close()
    ASYNC_PG_POOL = None
    if ASYNC_SQLITE_CONN is not None:
        await ASYNC_SQLITE_CONN.close()
    ASYNC_SQLITE_CONN = None


async def init_async_storage() -> None:
    """Optional async DB clients for new code paths: PostgreSQL, SQLite and Redis."""
    global ASYNC_PG_POOL, ASYNC_SQLITE_CONN, ASYNC_REDIS
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url.startswith(("postgres://", "postgresql://")) and ASYNC_PG_POOL is None:
        ASYNC_PG_POOL = await asyncpg.create_pool(
            dsn=database_url,
            min_size=int(os.getenv("ASYNCPG_MIN_SIZE", "1")),
            max_size=int(os.getenv("ASYNCPG_MAX_SIZE", "20")),
            command_timeout=float(os.getenv("ASYNCPG_COMMAND_TIMEOUT", "60")),
        )
    if os.getenv("ENABLE_ASYNC_SQLITE", "0") == "1" and ASYNC_SQLITE_CONN is None:
        ASYNC_SQLITE_CONN = await aiosqlite.connect(os.getenv("FISHBOT_DB_PATH", DB_PATH))
        ASYNC_SQLITE_CONN.row_factory = aiosqlite.Row
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url and ASYNC_REDIS is None:
        ASYNC_REDIS = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
        )
        await ASYNC_REDIS.ping()


async def async_file_bytes(path: Path | str) -> BytesIO:
    source = Path(path)
    async with aiofiles.open(source, "rb") as file_obj:
        data = await file_obj.read()
    if not data:
        raise ValueError(f"File is empty: {source}")
    bio = BytesIO(data)
    bio.name = source.name
    bio.seek(0)
    return bio


async def gzip_copy_async(source: Path | str, destination: Path | str) -> None:
    import gzip

    async with aiofiles.open(source, "rb") as f_in:
        data = await f_in.read()
    compressed = await asyncio.to_thread(gzip.compress, data)
    async with aiofiles.open(destination, "wb") as f_out:
        await f_out.write(compressed)


def slow_operation(name: Optional[str] = None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - started
                if elapsed >= SLOW_OPERATION_SECONDS:
                    logger.warning("Slow operation %.3fs: %s", elapsed, name or getattr(func, "__qualname__", repr(func)))
        return wrapper
    return decorator


def trace_application_handlers(application: Application) -> None:
    for handlers in application.handlers.values():
        for handler in handlers:
            callback = getattr(handler, "callback", None)
            if callback and asyncio.iscoroutinefunction(callback) and not getattr(callback, "_slow_wrapped", False):
                wrapped = slow_operation(getattr(callback, "__qualname__", repr(callback)))(callback)
                setattr(wrapped, "_slow_wrapped", True)
                handler.callback = wrapped


class TelegramBotAPI:
    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def create_invoice_link(self, **kwargs: Any) -> Optional[str]:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[INVOICE] CALL create_invoice_link with kwargs: {kwargs}")
        try:
            session = await get_http_session()
            async with session.post(f"{self.base_url}/createInvoiceLink", json=kwargs) as response:
                text = await response.text()
                logger.info(f"[INVOICE] Telegram API status: {response.status}")
                logger.info(f"[INVOICE] Telegram API response: {text}")
                if response.status == 200:
                    try:
                        result = await response.json()
                    except Exception as e:
                        logger.error(f"[INVOICE] Failed to parse JSON: {e}, text: {text}")
                        return None
                    if result.get("ok"):
                        logger.info(f"[INVOICE] Got invoice_url: {result.get('result')}")
                        return result.get("result")
                    logger.error(f"[INVOICE] Telegram API error: {result.get('description')}, full response: {text}")
                    return None
                logger.error(f"[INVOICE] HTTP error: {response.status}, text: {text}")
                return None
        except Exception as e:
            logger.error(f"[INVOICE] Exception in create_invoice_link: {e}")
            return None
from game_logic import game
from config import BOT_TOKEN, COIN_NAME, STAR_NAME, GUARANTEED_CATCH_COST, get_current_season, RULES_TEXT, RULES_LINK, INFO_LINK
import notifications
from fish_stickers import FISH_INFO, FISH_STICKERS
from trash_stickers import TRASH_STICKERS
from treasures_stickers import TREASURES_STICKERS
from treasures import DIAMOND_BUY_PRICE, DIAMOND_SELL_PRICE
from weather import weather_system

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

for noisy_logger_name in ("httpx", "telegram", "apscheduler"):
    logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class RefundedPaymentFilter(filters.MessageFilter):
    def filter(self, message: Message) -> bool:
        return bool(getattr(message, "refunded_payment", None))


REFUNDED_PAYMENT_FILTER = RefundedPaymentFilter()
FISH_MESSAGE_TRIGGER_RE = re.compile(
    r"^\s*(?:меню|menu|фиш|fish|рыбалка|сеть|net|лимит|limit|погода|weather|динамит|dynamite)\b",
    re.IGNORECASE,
)

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
DIAMOND_EMOJI_TAG = '<tg-emoji emoji-id="5366124516055487969">💎</tg-emoji>'
TG_EMOJI_TAG_RE = re.compile(r'<tg-emoji\s+emoji-id="[^"]+">(.*?)</tg-emoji>')

HARPOON_NAME = "Гарпун"
HARPOON_COOLDOWN_MINUTES = 20
HARPOON_SKIP_COST_STARS = 2

# Booster catalog used by the feeders/echosounder shop.
FEEDER_ITEMS = [
    {
        "code": "feeder_3",
        "name": "Кормушка базовая",
        "bonus": 3,
        "duration_minutes": 60,
        "price_coins": 3000,
        "price_stars": 0,
    },
    {
        "code": "feeder_7",
        "name": "Кормушка усиленная",
        "bonus": 5,
        "duration_minutes": 60,
        "price_coins": 5000,
        "price_stars": 0,
    },
    {
        "code": "feeder_10",
        "name": "Кормушка звёздная",
        "bonus": 7,
        "duration_minutes": 60,
        "price_coins": 0,
        "price_stars": 10,
    },
]

ECHOSOUNDER_CODE = "echosounder"
ECHOSOUNDER_COST_STARS = 20
ECHOSOUNDER_DURATION_HOURS = 24

BEER_PRICE_COINS = 1000
BEER_DRUNK_EFFECT = "beer_drunk"
BEER_TRACE_EFFECT = "beer_trace"
BEER_DRUNK_DURATION_MINUTES = 20
BEER_TRACE_DURATION_MINUTES = 90
BEER_DRUNK_BASE_CHANCE = 0.12
BEER_DRUNK_PER_TRACE_CHANCE = 0.08
BEER_DRUNK_MAX_CHANCE = 0.62
BEER_POSITIVE_EFFECTS = [
    {
        "effect_type": "beer_courage",
        "name": "Кураж",
        "bonus_percent": 5,
        "duration_minutes": 15,
    },
    {
        "effect_type": "beer_lucky_wave",
        "name": "Пенная волна",
        "bonus_percent": 3,
        "duration_minutes": 25,
    },
    {
        "effect_type": "beer_foamy_focus",
        "name": "Пенный фокус",
        "bonus_percent": 7,
        "duration_minutes": 10,
    },
]
BEER_FAKE_GOOD_RESULTS = [
    "✨ Ого! Пойман редкий вайб: +12% к удаче на 20 минут!",
    "🔥 Пивной крит! Шанс на крупную рыбу заметно вырос!",
    "🎉 Бонус активирован: легендарный клев вот-вот начнётся!",
    "⭐ Рыба в восторге от вашего настроя. Клев должен быть супер!",
]
DRUNK_GIBBERISH_SYLLABLES = [
    "брр", "фшш", "кхм", "ллл", "жжж", "трр", "пхп", "мрр", "глп", "хрм", "шлк", "дрд"
]
STORM_EVENT_CHANCE_ON_BOAT = 0.01
STORM_EVENT_COOLDOWN_HOURS = 18

ANTI_BOT_RHYTHM_MIN_SECONDS = 8 * 60
ANTI_BOT_RHYTHM_MAX_SECONDS = 12 * 60
ANTI_BOT_RHYTHM_TRIGGER_STREAK = 5
ANTI_BOT_CAPTCHA_TTL_SECONDS = 180
ANTI_BOT_PENALTY_HOURS = 6

DUEL_FREE_INVITES_PER_DAY = 3
DUEL_INVITE_TIMEOUT_SECONDS = 60
DUEL_ACTIVE_TIMEOUT_SECONDS = 3600
DUEL_PAID_INVITE_STARS = 5

LIVE_BAIT_NAME = "Живец"
SMALL_BAIT_FISH_NAMES = ("Плотва", "Верховка")

FIGHT_TIMEOUT_SECONDS = 15
FIGHT_ACTIONS = ("jerk", "hold", "slack")
FIGHT_ACTION_LABELS = {
    "jerk": "🪝 Подсечь",
    "hold": "💪 Держать натяжение",
    "slack": "🎛️ Ослабить леску",
}

CLAN_DONATABLE_ITEMS = {
    "доска": "Деревянная доска",
    "доски": "Деревянная доска",
    "удочка": "Поломанная удочка",
    "удочки": "Поломанная удочка",
    "rod": "Поломанная удочка",
    "board": "Деревянная доска",
    "коряга": "Коряга",
    "шина": "Старая шина",
    "банка": "Консервная банка",
    "ботинок": "Ботинок",
    "бутылка": "Пластиковая бутылка",
    "крючок": "Ржавый крючок",
    "труба": "Кусок трубы",
    "сетка": "Рыболовная сетка",
    "якорь": "Старый якорь",
    "веревка": "Веревка",
}

DYNAMITE_COOLDOWN_HOURS = 8
DYNAMITE_BATCH_ROLLS = 12
DYNAMITE_SKIP_COST_STARS = 15
DYNAMITE_GUARD_CHANCE = 0.001
DYNAMITE_GUARD_BAN_HOURS = 24
DYNAMITE_GUARD_FINE_STARS = 20


def _env_sticker_file_id(*env_names: str, default: str) -> str:
    for env_name in env_names:
        raw_value = os.getenv(env_name)
        if raw_value is None:
            continue
        normalized = str(raw_value).strip().strip('"').strip("'")
        if normalized:
            return normalized
    return default


DYNAMITE_STICKER_FILE_ID = "CAACAgEAAxkBAAEcHQlptoOhA4B-LV0g-vv7Orrwg4UZfgACXgIAAg60IEQze4zUaM3_bzoE"
DYNAMITE_GRENADE_STICKER_FILE_ID = _env_sticker_file_id(
    "DYNAMITE_GRENADE_STICKER_FILE_ID",
    "GRENADE_STICKER_FILE_ID",
    "DYNAMITE_LEVEL2_STICKER_FILE_ID",
    default=DYNAMITE_STICKER_FILE_ID,
)
DYNAMITE_BOMB_STICKER_FILE_ID = _env_sticker_file_id(
    "DYNAMITE_BOMB_STICKER_FILE_ID",
    "BOMB_STICKER_FILE_ID",
    "DYNAMITE_LEVEL3_STICKER_FILE_ID",
    default=DYNAMITE_STICKER_FILE_ID,
)
DYNAMITE_NAME_BY_LEVEL = {
    1: "Динамит",
    2: "Граната",
    3: "Бомба",
}
DYNAMITE_MAX_WEIGHT_BY_LEVEL = {
    1: 550.0,
    2: 750.0,
    3: 1100.0,
}
DYNAMITE_UPGRADE_COST_BY_LEVEL = {
    1: 2,
    2: 8,
}
DYNAMITE_STICKER_BY_LEVEL = {
    1: DYNAMITE_STICKER_FILE_ID,
    2: DYNAMITE_GRENADE_STICKER_FILE_ID,
    3: DYNAMITE_BOMB_STICKER_FILE_ID,
}

CLOTHING_ITEMS = [
    {
        "code": "boots",
        "name": "Сапоги рыбака",
        "price_diamonds": 5,
        "bonus_percent": 0.05,
    },
    {
        "code": "raincoat",
        "name": "Штормовой плащ",
        "price_diamonds": 8,
        "bonus_percent": 0.07,
    },
    {
        "code": "gloves",
        "name": "Рыбацкие перчатки",
        "price_diamonds": 10,
        "bonus_percent": 0.09,
    },
    {
        "code": "hat",
        "name": "Кепка капитана",
        "price_diamonds": 12,
        "bonus_percent": 0.11,
    },
    {
        "code": "overalls",
        "name": "Морской комбинезон",
        "price_diamonds": 15,
        "bonus_percent": 0.14,
    },
    {
        "code": "thermal_suit",
        "name": "Термокостюм",
        "price_diamonds": 20,
        "bonus_percent": 0.18,
    },
    {
        "code": "captain_coat",
        "name": "Китель адмирала",
        "price_diamonds": 30,
        "bonus_percent": 0.25,
    },
    {
        "code": "abyss_set",
        "name": "Костюм бездны",
        "price_diamonds": 45,
        "bonus_percent": 0.35,
    },
]
CLOTHING_ITEM_BY_CODE = {item["code"]: item for item in CLOTHING_ITEMS}

TROPHY_CREATE_COST_COINS = 10000
TROPHY_LIST_PAGE_SIZE = 8
TROPHY_ADD_PAGE_SIZE = 8

def _replace_plain_emoji_segment(text: str) -> str:
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
        .replace("💎", DIAMOND_EMOJI_TAG)
    )


def replace_coin_emoji(text: str) -> str:
    if not text:
        return text
    if '<tg-emoji' not in text:
        return _replace_plain_emoji_segment(text)

    # Preserve existing <tg-emoji> tags and only replace plain emoji outside them.
    result_parts = []
    last_pos = 0
    for match in TG_EMOJI_TAG_RE.finditer(text):
        result_parts.append(_replace_plain_emoji_segment(text[last_pos:match.start()]))
        result_parts.append(match.group(0))
        last_pos = match.end()
    result_parts.append(_replace_plain_emoji_segment(text[last_pos:]))
    return ''.join(result_parts)

def strip_tg_emoji_tags(text: str) -> str:
    if not text or '<tg-emoji' not in text:
        return text
    return TG_EMOJI_TAG_RE.sub(r'\1', text)


def format_percent_value(value: float) -> str:
    try:
        normalized = float(value)
    except Exception:
        normalized = 0.0
    formatted = f"{normalized:.2f}".rstrip('0').rstrip('.')
    return formatted if formatted else "0"


# Thread pool for blocking DB / game logic so the asyncio event loop stays responsive
from concurrent.futures import ThreadPoolExecutor
_DB_WORKERS = max(4, int(os.getenv('TG_DB_WORKERS', '300')))
_db_executor = ThreadPoolExecutor(max_workers=_DB_WORKERS, thread_name_prefix="db_worker")

_action_locks = collections.defaultdict(asyncio.Lock)

def require_action_lock(func):
    """Обеспечивает последовательное выполнение команд для одного пользователя."""
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = getattr(update, 'effective_user', None)
        if hasattr(user, 'id'):
            user_id = user.id
            async with _action_locks[user_id]:
                return await func(self, update, context, *args, **kwargs)
        return await func(self, update, context, *args, **kwargs)
    return wrapper

async def _run_sync(func, *args, **kwargs):
    """Run a sync function in a background thread and await the result."""
    import functools
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_db_executor, functools.partial(func, *args, **kwargs))
    if asyncio.iscoroutine(result):
        return await result
    return result


class EmojiBot(ExtBot):
    API_CALL_TIMEOUT = float(os.getenv('TG_API_CALL_TIMEOUT', '12'))
    API_CALL_RETRIES = int(os.getenv('TG_API_CALL_RETRIES', '3'))
    RETRY_BACKOFF_SEC = float(os.getenv('TG_API_RETRY_BACKOFF', '1.5'))

    async def _call_with_timeout(self, method_name: str, coro_factory):
        last_exc = None
        for attempt in range(self.API_CALL_RETRIES + 1):
            try:
                # Ограничиваем количество одновременных сетевых запросов
                async with get_send_semaphore():
                    coro = coro_factory()
                    return await asyncio.wait_for(coro, timeout=self.API_CALL_TIMEOUT)
            except RetryAfter as exc:
                last_exc = exc
                wait = float(getattr(exc, 'retry_after', 1) or 1)
                logger.warning("EmojiBot.%s flood limit, waiting %.2fs (attempt %s/%s)", method_name, wait, attempt + 1, self.API_CALL_RETRIES + 1)
                await asyncio.sleep(wait + 1)
            except (BadRequest, Forbidden) as exc:
                # Ошибки Telegram API (например, Chat not found, Forbidden) не лечатся retry'ем
                exc_str = str(exc)
                exc_lower = exc_str.lower()
                if "Message is not modified" in exc_str:
                    return None
                if (
                    "query is too old" in exc_lower
                    or "query id is invalid" in exc_lower
                    or "response timeout expired" in exc_lower
                ):
                    logger.info("EmojiBot.%s stale callback query ignored: %s", method_name, exc)
                    return None
                if any(fragment in exc_str for fragment in ("Not enough rights", "Chat not found", "Forbidden")):
                    return None
                logger.warning("EmojiBot.%s non-retryable error: %s", method_name, exc)
                raise
            except (TimedOut, NetworkError, asyncio.TimeoutError) as exc:
                last_exc = exc
                if attempt < self.API_CALL_RETRIES:
                    backoff = self.RETRY_BACKOFF_SEC * (attempt + 1)
                    logger.warning("EmojiBot.%s timeout/network error (%s), retry in %.2fs (attempt %s/%s)", method_name, type(exc).__name__, backoff, attempt + 1, self.API_CALL_RETRIES + 1)
                    await asyncio.sleep(backoff)
                    continue
                logger.error("EmojiBot.%s failed after retries due to timeout/network error: %s", method_name, exc)
                raise
            except ChatMigrated:
                # Retried at send_message level with the new chat_id.
                raise
            except Exception as exc:
                # Не скрываем неизвестные ошибки логики Telegram API
                logger.error("EmojiBot.%s unexpected error: %s", method_name, exc)
                raise

        if last_exc is not None:
            raise last_exc

    @staticmethod
    def _should_retry_without_custom_emoji(exc: Exception, text: str) -> bool:
        if not text or '<tg-emoji' not in text:
            return False
        error_text = str(exc).lower()
        return any(fragment in error_text for fragment in (
            'document_invalid',
            'can\'t parse entities',
            'cant parse entities',
            'unsupported start tag',
            'custom emoji',
            'entity',
        ))

    async def _send_with_custom_emoji_fallback(self, method_name: str, sender, *args, **kwargs):
        converted_kwargs = dict(kwargs)
        original_text = converted_kwargs.get('text')
        if isinstance(original_text, str):
            converted_kwargs['text'] = replace_coin_emoji(original_text)

        try:
            return await self._call_with_timeout(method_name, lambda: sender(*args, **converted_kwargs))
        except BadRequest as exc:
            converted_text = converted_kwargs.get('text')
            if not isinstance(converted_text, str) or not self._should_retry_without_custom_emoji(exc, converted_text):
                raise

            fallback_kwargs = dict(converted_kwargs)
            fallback_kwargs['text'] = strip_tg_emoji_tags(converted_text)
            logger.warning(
                "EmojiBot.%s rejected custom emoji markup, retrying with plain Unicode: %s",
                method_name,
                exc,
            )
            return await self._call_with_timeout(method_name, lambda: sender(*args, **fallback_kwargs))

    @staticmethod
    def _extract_migrated_chat_id(exc: Exception) -> Optional[int]:
        new_chat_id = getattr(exc, 'new_chat_id', None)
        if isinstance(new_chat_id, int):
            return int(new_chat_id)

        match = re.search(r'new\s+chat\s+id:\s*(-?\d+)', str(exc), flags=re.IGNORECASE)
        if not match:
            return None

        try:
            return int(match.group(1))
        except Exception:
            return None

    async def send_message(self, *args, **kwargs):
        try:
            return await self._send_with_custom_emoji_fallback(
                "send_message",
                super(EmojiBot, self).send_message,
                *args,
                **kwargs,
            )
        except ChatMigrated as exc:
            migrated_chat_id = self._extract_migrated_chat_id(exc)
            if migrated_chat_id is None:
                raise

            retry_kwargs = dict(kwargs)
            retry_kwargs['chat_id'] = migrated_chat_id
            logger.warning("EmojiBot.send_message retrying after chat migration to %s", migrated_chat_id)
            return await self._send_with_custom_emoji_fallback(
                "send_message",
                super(EmojiBot, self).send_message,
                *args,
                **retry_kwargs,
            )
        except BadRequest as exc:
            migrated_chat_id = self._extract_migrated_chat_id(exc)
            if migrated_chat_id is None:
                raise

            retry_kwargs = dict(kwargs)
            retry_kwargs['chat_id'] = migrated_chat_id
            logger.warning("EmojiBot.send_message retrying after BadRequest migration to %s", migrated_chat_id)
            return await self._send_with_custom_emoji_fallback(
                "send_message",
                super(EmojiBot, self).send_message,
                *args,
                **retry_kwargs,
            )

    async def edit_message_text(self, *args, **kwargs):
        return await self._send_with_custom_emoji_fallback(
            "edit_message_text",
            super(EmojiBot, self).edit_message_text,
            *args,
            **kwargs,
        )

    async def send_document(self, *args, **kwargs):
        return await self._call_with_timeout("send_document", lambda: super(EmojiBot, self).send_document(*args, **kwargs))

    async def send_invoice(self, *args, **kwargs):
        return await self._call_with_timeout("send_invoice", lambda: super(EmojiBot, self).send_invoice(*args, **kwargs))

    async def get_chat(self, *args, **kwargs):
        return await self._call_with_timeout("get_chat", lambda: super(EmojiBot, self).get_chat(*args, **kwargs))

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
    def _parse_guaranteed_payload(self, payload: str) -> dict:
        """
        Парсит payload вида guaranteed_{user_id}_{chat_id}_{ts}[_location]
        Возвращает dict с ключами: payload_user_id, group_chat_id, created_ts, location (если есть)
        """
        # Пример payload: guaranteed_2011062098_-1003716809697_1774724390
        # или guaranteed_2011062098_-1003716809697_1774724390_Lake
        try:
            parts = payload.split("_", 4)
            if len(parts) < 4:
                return {}
            payload_user_id = int(parts[1])
            group_chat_id = int(parts[2])
            created_ts = int(parts[3])
            location = parts[4] if len(parts) > 4 else None
            return {
                "payload_user_id": payload_user_id,
                "group_chat_id": group_chat_id,
                "created_ts": created_ts,
                "location": location,
            }
        except Exception as e:
            logger.warning(f"_parse_guaranteed_payload: failed to parse '{payload}': {e}")
            return {}

    async def skip_boat_cooldown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /skip_boat_cd — сбросить КД лодки за звёзды."""
        user_id = update.effective_user.id
        price = 20  # Цена сброса КД (пример)
        ok = await _run_sync(db.skip_boat_cooldown, user_id, price)
        if ok:
            await update.message.reply_text(f"⏩ КД лодки сброшен за {price} ⭐! Можно выплывать снова.")
        else:
            await update.message.reply_text("❌ Не удалось сбросить КД лодки. Возможно, нет КД или не хватает звёзд.")

    async def cure_seasick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /cure_seasick — вылечить морскую болезнь за звёзды."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if not await _run_sync(db.is_user_seasick, user_id):
            await update.message.reply_text("❌ У вас нет морской болезни.")
            return

        price = 15  # Цена лечения 15 звезд
        
        try:
            from bot import TelegramBotAPI as _TelegramBotAPI
            tg_api = _TelegramBotAPI(BOT_TOKEN)
            invoice_url = await tg_api.create_invoice_link(
                title="Лечение морской болезни",
                description=f"Мгновенное излечение от морской болезни ({price} {STAR_NAME})",
                payload=f"cure_seasick_{user_id}",
                currency="XTR",
                prices=[{"label": "Лечение", "amount": price}]
            )
            
            if invoice_url:
                await self.send_invoice_url_button(
                    chat_id=chat_id,
                    invoice_url=invoice_url,
                    text=f"🚑 Вас сильно укачало? Оплатите {price} {STAR_NAME}, чтобы мгновенно прийти в себя и продолжить рыбалку!",
                    user_id=user_id,
                    reply_to_message_id=update.effective_message.message_id if update.effective_message else None
                )
            else:
                await update.message.reply_text("❌ Не удалось создать ссылку на оплату. Попробуйте позже.")
        except Exception as e:
            logger.error(f"[INVOICE] Failed to create cure_seasick invoice: {e}")
            await update.message.reply_text("❌ Ошибка при создании инвойса.")

    async def buy_paid_boat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /buy_boat — купить платную лодку за звёзды."""
        user_id = update.effective_user.id
        price = 50  # Цена платной лодки (пример)
        ok = await _run_sync(db.buy_paid_boat, user_id, price)
        if ok:
            await update.message.reply_text(f"⛵ Платная лодка куплена за {price} ⭐! Теперь вы можете выплывать без ограничений.")
        else:
            await update.message.reply_text("❌ Не удалось купить лодку. Возможно, не хватает звёзд или лодка уже есть.")

    async def handle_buy_paid_boat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка покупки платной лодки по кнопке в меню."""
        query = update.callback_query
        user_id = update.effective_user.id
        if not query or not str(query.data or "").endswith(f"_{user_id}"):
            if query:
                await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        price = 50  # Цена платной лодки (пример)
        ok = await _run_sync(db.buy_paid_boat, user_id, price)
        if ok:
            await update.callback_query.answer(f"⛵ Платная лодка куплена за {price} ⭐!", show_alert=True)
            await self.show_fishing_menu(update, context)
        else:
            await update.callback_query.answer("❌ Не удалось купить лодку. Возможно, не хватает звёзд или лодка уже есть.", show_alert=True)

    async def invite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /invite <id или username> — приглашение в лодку."""
        user_id = update.effective_user.id
        args = context.args
        if not args:
            await update.message.reply_text("Укажите id или username для приглашения.")
            return
        to_user = args[0]
        # Попробуем найти пользователя по username или id
        if to_user.isdigit():
            to_user_id = int(to_user)
        else:
            # Поиск по username среди игроков
            to_user_id = await _run_sync(db.get_user_id_by_username, to_user)
            if not to_user_id:
                await update.message.reply_text("Пользователь не найден.")
                return
        # Создать приглашение
        ok = await _run_sync(db.create_boat_invite, user_id, to_user_id)
        if not ok:
            await update.message.reply_text("Ошибка: нельзя пригласить (вы не в плавании, нет лодки или она переполнена).")
            return
        # Отправить приглашённому сообщение с кнопками
        username = update.effective_user.username or update.effective_user.first_name
        keyboard = [
              [InlineKeyboardButton("✅ Принять", callback_data=f"boat_invite_accept_{user_id}_{to_user_id}"),
               InlineKeyboardButton("❌ Отклонить", callback_data=f"boat_invite_decline_{user_id}_{to_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await self.application.bot.send_message(
                chat_id=to_user_id,
                text=f"Вас приглашает в лодку @{username}",
                reply_markup=reply_markup
            )
            await update.message.reply_text("Приглашение отправлено!")
        except Exception as e:
            await update.message.reply_text("Не удалось отправить приглашение: пользователь не найден или не писал боту.")

    async def handle_boat_invite_accept(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка принятия приглашения в лодку."""
        query = update.callback_query
        user_id = update.effective_user.id

        data = str(query.data or "") if query else ""
        match = re.match(r"^boat_invite_accept_(\d+)(?:_(\d+))?$", data)
        if not match:
            if query:
                await query.answer("Некорректная кнопка", show_alert=True)
            return

        target_id_raw = match.group(2)
        if target_id_raw and int(target_id_raw) != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        # Найти последнее приглашение к этому пользователю
        invite_id = await _run_sync(db.get_last_pending_invite_id, user_id)
        if not invite_id:
            await update.callback_query.answer("Нет активного приглашения.", show_alert=True)
            return
        success = await _run_sync(db.respond_boat_invite, invite_id, accept=True)
        if success:
            await update.callback_query.answer("Вы присоединились к лодке!")
        else:
            await update.callback_query.answer("❌ Не удалось присоединиться: лодка полна или недоступна.", show_alert=True)
        await self.show_fishing_menu(update, context)

    async def handle_boat_invite_decline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка отклонения приглашения в лодку."""
        query = update.callback_query
        user_id = update.effective_user.id

        data = str(query.data or "") if query else ""
        match = re.match(r"^boat_invite_decline_(\d+)(?:_(\d+))?$", data)
        if not match:
            if query:
                await query.answer("Некорректная кнопка", show_alert=True)
            return

        target_id_raw = match.group(2)
        if target_id_raw and int(target_id_raw) != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        invite_id = await _run_sync(db.get_last_pending_invite_id, user_id)
        if not invite_id:
            await update.callback_query.answer("Нет активного приглашения.", show_alert=True)
            return
        await _run_sync(db.respond_boat_invite, invite_id, accept=False)
        await update.callback_query.answer("Приглашение отклонено.")

    async def duel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /duel @username — вызов на дуэль в текущем чате."""
        if update.effective_chat.type == 'private':
            await update.message.reply_text("Команда /duel работает только в групповых чатах.")
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        inviter_username = update.effective_user.username or update.effective_user.first_name or str(user_id)

        inviter_player = await _run_sync(db.get_player, user_id, chat_id)
        if not inviter_player:
            try:
                inviter_player = await _run_sync(db.create_player, user_id, inviter_username, chat_id)
            except Exception:
                logger.exception("duel_command: failed to create player user=%s chat=%s", user_id, chat_id)
                inviter_player = None
        if not inviter_player:
            await update.message.reply_text("Сначала создайте профиль командой /start.")
            return

        if not context.args:
            await update.message.reply_text("Использование: /duel @username")
            return

        raw_target = str(context.args[0] or '').strip()
        if not raw_target.startswith('@'):
            await update.message.reply_text("Укажите соперника через @username, например: /duel @fisher")
            return

        target_username_arg = re.sub(r'[^A-Za-z0-9_]', '', raw_target.lstrip('@'))
        if not target_username_arg:
            await update.message.reply_text("Некорректный username для дуэли.")
            return

        target_id = await _run_sync(db.get_user_id_by_username, target_username_arg)
        if not target_id:
            await update.message.reply_text("Пользователь не найден в базе. Он должен хотя бы раз начать игру.")
            return

        if int(target_id) == int(user_id):
            await update.message.reply_text("Нельзя вызвать самого себя на дуэль.")
            return

        target_username = await _run_sync(db.get_username_by_user_id, int(target_id)) or target_username_arg

        if self._is_user_beer_drunk(int(user_id)):
            await update.message.reply_text("Нельзя начать дуэль: вы находитесь в опьянении.")
            return

        if self._is_user_beer_drunk(int(target_id)):
            await update.message.reply_text(
                f"Нельзя начать дуэль: {self._duel_user_label(int(target_id), target_username)} находится в опьянении."
            )
            return

        try:
            await _run_sync(db.expire_pending_duels)
        except Exception:
            logger.exception("duel_command: failed to expire pending duels")

        active_for_inviter = await _run_sync(db.get_active_duel_for_user, user_id)
        if active_for_inviter:
            await update.message.reply_text("У вас уже есть активная/ожидающая дуэль. Завершите её перед новым вызовом.")
            return

        active_for_target = await _run_sync(db.get_active_duel_for_user, int(target_id))
        if active_for_target:
            await update.message.reply_text(
                f"{self._duel_user_label(int(target_id), target_username)} уже участвует в другой активной дуэли."
            )
            return

        attempts = await _run_sync(db.get_duel_attempts_status, user_id, free_limit=DUEL_FREE_INVITES_PER_DAY)
        free_left = int(attempts.get('left') or 0)

        if free_left > 0:
            create_result = await _run_sync(db.create_duel_invitation, chat_id=chat_id,
                inviter_id=user_id,
                target_id=int(target_id),
                inviter_username=inviter_username,
                target_username=target_username,
                attempt_type='free',
                invite_timeout_seconds=DUEL_INVITE_TIMEOUT_SECONDS,
                free_limit=DUEL_FREE_INVITES_PER_DAY,
            )

            if not create_result.get('ok'):
                error_code = str(create_result.get('error') or 'duel_create_failed')
                if error_code in {'inviter_has_active_duel', 'target_has_active_duel'}:
                    await update.message.reply_text("Сейчас нельзя создать дуэль: у одного из игроков уже есть активная/ожидающая дуэль.")
                elif error_code == 'no_free_attempts':
                    await update.message.reply_text(
                        f"Бесплатные попытки закончились. Оплатите {DUEL_PAID_INVITE_STARS} ⭐ для дополнительного вызова."
                    )
                else:
                    await update.message.reply_text("Не удалось создать дуэль. Попробуйте ещё раз.")
                return

            duel = create_result.get('duel') or {}
            sent_message = await self._send_duel_invitation_message(
                chat_id=chat_id,
                duel=duel,
                attempts_left_after=create_result.get('attempts_left_after'),
                reply_to_message_id=update.message.message_id if update.message else None,
            )

            if not sent_message:
                try:
                    force_now = datetime.now(timezone.utc) + timedelta(seconds=DUEL_INVITE_TIMEOUT_SECONDS + 1)
                    await _run_sync(db.expire_duel_invitation_by_id, int(duel.get('id') or 0), now=force_now)
                except Exception:
                    logger.exception("duel_command: failed to rollback duel after send error duel_id=%s", duel.get('id'))
                await update.message.reply_text("Не удалось отправить приглашение на дуэль. Попробуйте ещё раз.")
            return

        from config import BOT_TOKEN
        tg_api = TelegramBotAPI(BOT_TOKEN)
        payload = self._build_duel_invite_payload(
            user_id,
            int(target_id),
            chat_id,
            target_username=target_username,
        )

        try:
            invoice_url = await tg_api.create_invoice_link(
                title="Вызов на дуэль",
                description=(
                    f"Платное приглашение в дуэль для {self._duel_user_label(int(target_id), target_username)} "
                    f"({DUEL_PAID_INVITE_STARS} ⭐)"
                ),
                payload=payload,
                currency="XTR",
                prices=[{"label": "Платная дуэль", "amount": DUEL_PAID_INVITE_STARS}],
            )
        except Exception:
            logger.exception("duel_command: failed to create duel invoice user=%s target=%s", user_id, target_id)
            invoice_url = None

        if not invoice_url:
            await update.message.reply_text("Не удалось создать ссылку оплаты дуэли. Попробуйте позже.")
            return

        await self.send_invoice_url_button(
            chat_id=chat_id,
            invoice_url=invoice_url,
            text=(
                f"🎟 Бесплатные приглашения закончились ({DUEL_FREE_INVITES_PER_DAY}/{DUEL_FREE_INVITES_PER_DAY}).\n"
                f"Чтобы вызвать {self._duel_user_label(int(target_id), target_username)}, оплатите {DUEL_PAID_INVITE_STARS} ⭐.\n"
                "После оплаты бот автоматически отправит приглашение в этот чат."
            ),
            user_id=user_id,
            reply_to_message_id=update.message.message_id if update.message else None,
        )

    async def notduel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /notduel — отменить текущую дуэль пользователя в этом чате."""
        if update.effective_chat.type == 'private':
            await update.message.reply_text("Команда /notduel работает только в групповых чатах.")
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        try:
            cancel_result = await _run_sync(db.cancel_duel_for_user, user_id=int(user_id), chat_id=int(chat_id))
        except Exception:
            logger.exception("notduel_command: failed to cancel duel user=%s chat=%s", user_id, chat_id)
            await update.message.reply_text("Не удалось отменить дуэль. Попробуйте ещё раз.")
            return

        if not cancel_result.get('ok'):
            error_code = str(cancel_result.get('error') or 'cancel_failed')
            if error_code == 'duel_not_found':
                await update.message.reply_text("У вас нет активной или ожидающей дуэли в этом чате.")
            elif error_code == 'duel_in_other_chat':
                await update.message.reply_text("Ваша активная или ожидающая дуэль находится в другом чате.")
            else:
                await update.message.reply_text("Не удалось отменить дуэль. Попробуйте ещё раз.")
            return

        duel = cancel_result.get('duel') or {}
        duel_id = int(duel.get('id') or 0)
        if duel_id > 0:
            self._cancel_duel_invite_timeout_job(duel_id)
            self._cancel_duel_active_timeout_job(duel_id)

        inviter_id = int(duel.get('inviter_id') or 0)
        target_id = int(duel.get('target_id') or 0)
        inviter_label = self._duel_user_label(inviter_id, duel.get('inviter_username'))
        target_label = self._duel_user_label(target_id, duel.get('target_username'))
        actor_username = duel.get('inviter_username') if int(user_id) == inviter_id else duel.get('target_username')
        actor_label = self._duel_user_label(int(user_id), actor_username)
        refund_note = "\n🎟 Бесплатная попытка возвращена пригласившему." if cancel_result.get('refunded') else ""

        await update.message.reply_text(
            "🛑 Дуэль отменена командой /notduel.\n\n"
            f"{inviter_label} vs {target_label}\n"
            f"Отменил: {actor_label}.{refund_note}"
        )

    async def handle_duel_accept(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Принятие приглашения в дуэль (только приглашённый игрок)."""
        query = update.callback_query
        data = query.data or ""
        match = re.match(r"^duel_accept_(\d+)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        duel_id = int(match.group(1))
        target_id = int(match.group(2))
        user_id = update.effective_user.id

        if int(user_id) != target_id:
            await query.answer("Эта кнопка только для приглашённого игрока.", show_alert=True)
            return

        await query.answer()

        duel_snapshot = None
        try:
            duel_snapshot = await _run_sync(db.get_duel_by_id, duel_id)
        except Exception:
            logger.exception("handle_duel_accept: failed to load duel snapshot duel_id=%s", duel_id)

        if duel_snapshot and str(duel_snapshot.get('status') or '') == 'pending':
            inviter_id_snapshot = int(duel_snapshot.get('inviter_id') or 0)
            target_id_snapshot = int(duel_snapshot.get('target_id') or target_id)

            if inviter_id_snapshot > 0 and self._is_user_beer_drunk(inviter_id_snapshot):
                inviter_label = self._duel_user_label(inviter_id_snapshot, duel_snapshot.get('inviter_username'))
                await query.answer(f"{inviter_label} в состоянии опьянения. Дуэль пока нельзя начать.", show_alert=True)
                return

            if target_id_snapshot > 0 and self._is_user_beer_drunk(target_id_snapshot):
                await query.answer("Вы в состоянии опьянения. Дуэль пока нельзя начать.", show_alert=True)
                return

        accept_result = await _run_sync(db.accept_duel_invitation, duel_id, user_id)
        if not accept_result.get('ok'):
            error_code = str(accept_result.get('error') or 'accept_failed')
            if error_code == 'expired':
                await query.edit_message_text("⏱ Время на принятие дуэли истекло.")
            elif error_code == 'not_pending':
                await query.edit_message_text("Эта дуэль уже неактивна.")
            elif error_code == 'not_target':
                await query.answer("Эта кнопка не для вас.", show_alert=True)
            else:
                await query.edit_message_text("Не удалось принять дуэль. Попробуйте ещё раз.")
            return

        self._cancel_duel_invite_timeout_job(duel_id)

        duel = accept_result.get('duel') or {}
        duel_chat_id = int(duel.get('chat_id') or update.effective_chat.id)
        self._schedule_duel_active_timeout_job(duel_id=duel_id, chat_id=duel_chat_id)

        inviter_label = self._duel_user_label(int(duel.get('inviter_id') or 0), duel.get('inviter_username'))
        target_label = self._duel_user_label(int(duel.get('target_id') or 0), duel.get('target_username'))

        await query.edit_message_text(
            "⚔️ Дуэль принята!\n\n"
            f"{inviter_label} vs {target_label}\n"
            "Теперь у обоих есть 1 час, чтобы написать /fish в этом чате.\n"
            "Когда оба сделают улов, бот автоматически определит победителя."
        )

    async def handle_duel_decline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отклонение приглашения в дуэль (только приглашённый игрок)."""
        query = update.callback_query
        data = query.data or ""
        match = re.match(r"^duel_decline_(\d+)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        duel_id = int(match.group(1))
        target_id = int(match.group(2))
        user_id = update.effective_user.id

        if int(user_id) != target_id:
            await query.answer("Эта кнопка только для приглашённого игрока.", show_alert=True)
            return

        await query.answer()
        decline_result = await _run_sync(db.decline_duel_invitation, duel_id, user_id)
        if not decline_result.get('ok'):
            error_code = str(decline_result.get('error') or 'decline_failed')
            if error_code == 'not_pending':
                await query.edit_message_text("Эта дуэль уже неактивна.")
            elif error_code == 'not_target':
                await query.answer("Эта кнопка не для вас.", show_alert=True)
            else:
                await query.edit_message_text("Не удалось отклонить дуэль. Попробуйте ещё раз.")
            return

        self._cancel_duel_invite_timeout_job(duel_id)
        duel = decline_result.get('duel') or {}
        inviter_label = self._duel_user_label(int(duel.get('inviter_id') or 0), duel.get('inviter_username'))
        target_label = self._duel_user_label(int(duel.get('target_id') or 0), duel.get('target_username'))

        await query.edit_message_text(
            "❌ Дуэль отклонена.\n\n"
            f"{target_label} отказался от вызова {inviter_label}."
        )

    async def ref_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /ref: показать статистику и обработать вывод звёзд"""
        user_id = update.effective_user.id
        # Получаем разрешённые чаты для пользователя
        allowed_chats = await _run_sync(db.get_ref_access_chats, user_id)
        if not allowed_chats:
            await update.message.reply_text("Нет разрешённых чатов для просмотра дохода.")
            return
        # Собираем статистику по каждому чату
        lines = []
        for ref_chat_id in allowed_chats:
            chat_title = await _run_sync(db.get_chat_title, ref_chat_id) or f"Чат {ref_chat_id}"
            stars_total = await _run_sync(db.get_chat_stars_total, ref_chat_id)
            matured_stars_total = await _run_sync(db.get_chat_stars_total, ref_chat_id, min_age_days=21)
            refunds_total = await _run_sync(db.get_chat_refunds_total, ref_chat_id)
            percent_sum = int((matured_stars_total * 0.85) / 2)
            available_stars = await _run_sync(db.get_available_stars_for_withdraw, user_id, ref_chat_id)
            withdrawn_stars = await _run_sync(db.get_withdrawn_stars, user_id, ref_chat_id)
            lines.append(
                f"{chat_title}\nВсего звёзд: {stars_total}\nЗвёзд старше 21 дня: {matured_stars_total}\nРефаунды: {refunds_total}\nВаш процент: {percent_sum}\nДоступно к выводу: {available_stars}\nУже выведено: {withdrawn_stars}"
            )
        keyboard = [
            [InlineKeyboardButton("💸 Вывод", callback_data=f"withdraw_stars_{user_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_ref_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("\n\n".join(lines), reply_markup=reply_markup)

    async def handle_cancel_ref_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия на кнопку Отмена в /ref"""
        query = update.callback_query
        user_id = update.effective_user.id
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        await query.answer("Отменено")
        await query.edit_message_text("❌ Просмотр дохода отменен.")
        context.user_data.pop('waiting_withdraw_stars', None)

    async def handle_withdraw_stars_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия на кнопку вывода звёзд"""
        query = update.callback_query
        user_id = update.effective_user.id
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        await query.answer()
        context.user_data['waiting_withdraw_stars'] = True
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_ref_{user_id}")]]
        await query.message.reply_text("Введите количество звёзд для вывода:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_withdraw_stars_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода количества звёзд для вывода"""
        if not context.user_data.get('waiting_withdraw_stars'):
            return
        user_id = update.effective_user.id
        try:
            amount = int(update.message.text.strip())
        except Exception:
            await update.message.reply_text("Ошибка: введите число.")
            return

        context.user_data.pop('waiting_withdraw_stars', None)

        allowed_chats = await _run_sync(db.get_ref_access_chats, user_id)
        available_stars = sum(await _run_sync(db.get_available_stars_for_withdraw, user_id, chat_id) for chat_id in allowed_chats)
        if amount < 1000:
            await update.message.reply_text("Ошибка: минимальный вывод 1000 звёзд.")
            return
        if amount > available_stars:
            await update.message.reply_text("Ошибка: недостаточно звёзд для вывода.")
            return

        admin_id = 793216884
        await self.application.bot.send_message(
            chat_id=admin_id,
            text=(
                f"Пользователь {user_id} запросил вывод {amount} звёзд.\n"
                f"Доступно: {available_stars}.\n"
                f"Одобрить?"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Одобрено", callback_data=f"approve_withdraw_{user_id}_{amount}")]
            ])
        )
        await update.message.reply_text("Запрос отправлен на одобрение админу.")
        context.user_data.pop('waiting_withdraw_stars', None)

    async def handle_approve_withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка одобрения вывода звёзд админом"""
        query = update.callback_query
        admin_id = 793216884
        if update.effective_user.id != admin_id:
            await query.answer("Нет доступа", show_alert=True)
            return
        parts = query.data.split('_')
        if len(parts) != 4:
            await query.answer("Ошибка данных", show_alert=True)
            return
        _, _, user_id, amount = parts
        user_id = int(user_id)
        amount = int(amount)

        allowed_chats = await _run_sync(db.get_ref_access_chats, user_id)
        if not allowed_chats:
            await query.answer("Нет доступных чатов для вывода", show_alert=True)
            return

        remaining = amount
        for chat_id in allowed_chats:
            if remaining <= 0:
                break
            chat_available = await _run_sync(db.get_available_stars_for_withdraw, user_id, chat_id)
            if chat_available <= 0:
                continue
            chunk = min(remaining, chat_available)
            if chunk > 0:
                await _run_sync(db.mark_stars_withdrawn, user_id, chunk, chat_id=chat_id)
                remaining -= chunk

        if remaining > 0:
            await query.answer("Недостаточно доступных звёзд на момент одобрения", show_alert=True)
            return

        await query.answer("Одобрено!")
        await self.application.bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваш вывод {amount} звёзд одобрен и обработан!"
        )

    async def new_ref_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /new_ref: добавить реферала с доступом к доходу чата по ссылке"""
        user_id = update.effective_user.id
        if not self._is_owner(user_id):
            await update.message.reply_text("Команда доступна только владельцу бота.")
            return

        await update.message.reply_text(
            "Введите ID пользователя, которому дать доступ, и ссылку на чат (через пробел):\n"
            "Примеры:\n"
            "123456789 -1001234567890\n"
            "123456789 @channel_or_group_username\n"
            "123456789 https://t.me/channel_or_group_username"
        )
        context.user_data['waiting_new_ref'] = True

    async def handle_new_ref_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода для /new_ref"""
        if not context.user_data.get('waiting_new_ref'):
            return
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("Ошибка: введите ID и ссылку через пробел.")
            return
        ref_user_id_raw, chat_link = parts

        try:
            ref_user_id = int(ref_user_id_raw)
        except ValueError:
            await update.message.reply_text("Ошибка: ID пользователя должен быть числом.")
            return

        chat_id = None

        # 1) t.me/c/<id>/<msg_id> -> преобразуем в -100<id> (проверяем первым,
        #    иначе regex на числа выхватит голый id из URL без -100)
        m_c = re.search(r't\.me/c/(\d+)', chat_link, flags=re.IGNORECASE)
        if m_c:
            chat_id = int(f"-100{m_c.group(1)}")
        else:
            # 2) Прямой числовой chat_id (например: -1001234567890 или просто число)
            m = re.search(r'-?\d{9,}', chat_link)
            if m:
                chat_id = int(m.group(0))

        # 3) username / @username / t.me/username[/msg_id] -> resolve через get_chat
        if chat_id is None:
            username = None
            m_user = re.search(r't\.me/([A-Za-z0-9_]{5,})(?:/\d+)?/?$', chat_link, flags=re.IGNORECASE)
            if m_user:
                username = m_user.group(1)
            elif re.fullmatch(r'@?[A-Za-z0-9_]{5,}', chat_link):
                username = chat_link.lstrip('@')

            if username:
                try:
                    chat = await context.bot.get_chat(f"@{username}")
                    chat_id = chat.id
                except Exception as e:
                    logger.warning("/new_ref: failed to resolve @%s: %s", username, e)

        if chat_id is None:
            await update.message.reply_text(
                "Не удалось определить chat_id. Используйте -100... или @username (бот должен быть в этом чате)."
            )
            return
        try:
            await _run_sync(db.add_ref_access, ref_user_id, chat_id)
            await update.message.reply_text(f"✅ Доступ для пользователя {ref_user_id} к чату {chat_id} сохранён.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при сохранении: {e}")
        context.user_data.pop('waiting_new_ref', None)

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /check — топ пользователей по весу улова за период (только для владельца)."""
        user_id = update.effective_user.id
        if not self._is_owner(user_id):
            await update.message.reply_text("Команда доступна только владельцу бота.")
            return
        context.user_data['check_step'] = 'ids'
        await update.message.reply_text(
            "Введите ID пользователей через запятую:\n"
            "Пример: 123456789, 987654321"
        )

    async def handle_check_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пошаговый ввод для /check."""
        step = context.user_data.get('check_step')
        if not step:
            return
        text = update.message.text.strip()

        if step == 'ids':
            try:
                ids = [int(x.strip()) for x in text.split(',') if x.strip()]
            except ValueError:
                await update.message.reply_text("Ошибка: все ID должны быть числами. Попробуйте ещё раз.")
                return
            if not ids:
                await update.message.reply_text("Список ID пуст. Попробуйте ещё раз.")
                return
            context.user_data['check_ids'] = ids
            context.user_data['check_step'] = 'since'
            await update.message.reply_text(
                "Введите дату/время начала:\n"
                "Формат: ДД.ММ.ГГГГ ЧЧ:ММ  или  ГГГГ-ММ-ДД ЧЧ:ММ"
            )

        elif step == 'since':
            dt = self._parse_datetime_input(text)
            if dt is None:
                await update.message.reply_text("Не удалось распознать дату. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ")
                return
            context.user_data['check_since'] = dt
            context.user_data['check_step'] = 'until'
            await update.message.reply_text(
                "Введите дату/время конца:\n"
                "Формат: ДД.ММ.ГГГГ ЧЧ:ММ  или  ГГГГ-ММ-ДД ЧЧ:ММ"
            )

        elif step == 'until':
            dt = self._parse_datetime_input(text)
            if dt is None:
                await update.message.reply_text("Не удалось распознать дату. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ")
                return
            ids = context.user_data.pop('check_ids', [])
            since = context.user_data.pop('check_since', None)
            context.user_data.pop('check_step', None)

            rows = await _run_sync(db.get_users_weight_leaderboard, user_ids=ids, since=since, until=dt)

            since_str = since.strftime('%d.%m.%Y %H:%M') if since else '?'
            until_str = dt.strftime('%d.%m.%Y %H:%M')
            lines = [f"📊 Топ по весу улова\n🕐 {since_str} — {until_str}\n"]
            if not rows:
                lines.append("Нет уловов за указанный период.")
            else:
                for i, r in enumerate(rows, 1):
                    medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
                    name = html.escape(str(r.get('username') or '').strip() or f"id{r['user_id']}")
                    lines.append(f"{medal} {name}: {r['total_weight']:.2f} кг ({r['total_fish']} шт.)")
            # Добавляем тех, кого нет в результатах — у них 0
            found_ids = {r['user_id'] for r in rows}
            for uid in ids:
                if uid not in found_ids:
                    lines.append(f"— id{uid}: 0.00 кг (0 шт.)")  # id как fallback если username неизвестен

            await update.message.reply_text('\n'.join(lines))

    async def new_tour_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание турнира: выбор типа и ввод параметров."""
        user_id = update.effective_user.id
        if not self._is_owner(user_id):
            await update.message.reply_text("Команда доступна только владельцу бота.")
            return

        context.user_data['new_tour'] = {
            'chat_id': update.effective_chat.id,
            'created_by': user_id,
            'step': 'type',
        }

        keyboard = [
            [InlineKeyboardButton(self.TOUR_TYPES['longest_fish'], callback_data='tour_type_longest_fish')],
            [InlineKeyboardButton(self.TOUR_TYPES['biggest_weight'], callback_data='tour_type_biggest_weight')],
            [InlineKeyboardButton(self.TOUR_TYPES['total_weight'], callback_data='tour_type_total_weight')],
            [InlineKeyboardButton(self.TOUR_TYPES['total_length'], callback_data='tour_type_total_length')],
            [InlineKeyboardButton(self.TOUR_TYPES['specific_fish'], callback_data='tour_type_specific_fish')],
        ]
        await update.message.reply_text("Выберите тип турнира:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_tour_type_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа турнира через inline-кнопки."""
        query = update.callback_query
        await query.answer()

        if not self._is_owner(update.effective_user.id):
            await query.answer("Нет доступа", show_alert=True)
            return

        draft = context.user_data.get('new_tour')
        if not draft:
            await query.edit_message_text("Сессия создания турнира не найдена. Запустите /new_tour заново.")
            return

        selected_type = query.data.replace('tour_type_', '').strip()
        if selected_type not in self.TOUR_TYPES:
            await query.answer("Неизвестный тип", show_alert=True)
            return

        draft['tournament_type'] = selected_type
        if selected_type == 'specific_fish':
            # Для specific_fish: сначала локация, потом критерий, потом рыба
            locations = await _run_sync(db.get_locations)
            keyboard = [
                [InlineKeyboardButton(loc['name'], callback_data=f'tour_location_{loc["name"]}')]
                for loc in locations
            ]
            draft['step'] = 'location'
            context.user_data['new_tour'] = draft
            await query.edit_message_text(
                f"Выбран тип: {self.TOUR_TYPES[selected_type]}\n\nВыберите локацию:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if selected_type in ('longest_fish', 'biggest_weight'):
            locations = await _run_sync(db.get_locations)
            keyboard = [
                [InlineKeyboardButton(loc['name'], callback_data=f'tour_location_{loc["name"]}')]
                for loc in locations
            ]
            draft['step'] = 'location'
            context.user_data['new_tour'] = draft
            await query.edit_message_text(
                f"Выбран тип: {self.TOUR_TYPES[selected_type]}\n\nВыберите локацию:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        draft['step'] = 'title'
        context.user_data['new_tour'] = draft
        await query.edit_message_text(
            f"Выбран тип: {self.TOUR_TYPES[selected_type]}\n\nВведите название турнира:"
        )

    async def handle_tour_location_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор локации для турнира 'Улов определённой рыбы'."""
        query = update.callback_query
        await query.answer()

        if not self._is_owner(update.effective_user.id):
            await query.answer("Нет доступа", show_alert=True)
            return

        draft = context.user_data.get('new_tour')
        if not draft or draft.get('step') != 'location':
            await query.edit_message_text("Сессия не найдена. Запустите /new_tour заново.")
            return

        location_name = query.data.replace('tour_location_', '', 1)
        draft['target_location'] = location_name
        # Новый шаг: выбор критерия
        draft['step'] = 'criteria'
        context.user_data['new_tour'] = draft
        keyboard = [
            [InlineKeyboardButton("Общий вес рыбы", callback_data='tour_criteria_weight')],
            [InlineKeyboardButton("Количество рыбы", callback_data='tour_criteria_count')],
        ]
        await query.edit_message_text(
            f"📍 Локация: {location_name}\n\nВыберите критерий турнира:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_tour_criteria_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор критерия турнира (вес/количество) после локации."""
        query = update.callback_query
        await query.answer()

        if not self._is_owner(update.effective_user.id):
            await query.answer("Нет доступа", show_alert=True)
            return

        draft = context.user_data.get('new_tour')
        if not draft or draft.get('step') != 'criteria':
            await query.edit_message_text("Сессия не найдена. Запустите /new_tour заново.")
            return

        criteria = query.data.replace('tour_criteria_', '', 1)
        if criteria not in ('weight', 'count'):
            await query.answer("Неизвестный критерий", show_alert=True)
            return
        draft['criteria'] = criteria
        draft['step'] = 'target_fish'
        context.user_data['new_tour'] = draft
        await query.edit_message_text(
            f"Выбран критерий: {'Общий вес' if criteria == 'weight' else 'Количество'}\n\nВведите название рыбы (точно как в игре):"
        )

    async def handle_new_tour_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Пошаговый ввод параметров для нового турнира."""
        draft = context.user_data.get('new_tour')
        if not draft:
            return False

        if not self._is_owner(update.effective_user.id):
            context.user_data.pop('new_tour', None)
            return False

        message = update.effective_message
        if not message or not message.text:
            return True

        text = message.text.strip()
        step = draft.get('step')

        if step == 'target_fish':
            if len(text) < 2:
                await update.message.reply_text("Название рыбы слишком короткое. Введите снова:")
                return True
            draft['target_fish'] = text
            draft['step'] = 'title'
            context.user_data['new_tour'] = draft
            await update.message.reply_text("Введите название турнира:")
            return True

        if step == 'title':
            draft['title'] = text[:120]
            draft['step'] = 'starts_at'
            context.user_data['new_tour'] = draft
            await update.message.reply_text(
                "Введите дату/время начала\n"
                "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "или: YYYY-MM-DD HH:MM"
            )
            return True

        if step == 'starts_at':
            starts_at = self._parse_datetime_input(text)
            if not starts_at:
                await update.message.reply_text("Неверный формат даты. Пример: 05.03.2026 19:30")
                return True
            draft['starts_at'] = starts_at
            draft['step'] = 'ends_at'
            context.user_data['new_tour'] = draft
            await update.message.reply_text("Введите дату/время окончания в том же формате:")
            return True

        if step == 'ends_at':
            ends_at = self._parse_datetime_input(text)
            if not ends_at:
                await update.message.reply_text("Неверный формат даты. Пример: 06.03.2026 19:30")
                return True

            starts_at = draft.get('starts_at')
            if not starts_at or ends_at <= starts_at:
                await update.message.reply_text("Дата окончания должна быть позже даты начала.")
                return True

            draft['ends_at'] = ends_at
            draft['step'] = 'prize_places'
            context.user_data['new_tour'] = draft
            await update.message.reply_text(
                "Введите количество призовых мест (по умолчанию 10):\n"
                "Пример: 5\n"
                "Или отправьте '-' чтобы оставить 10"
            )
            return True

        if step == 'prize_places':
            prize_places = 10
            lowered = (text or "").strip().lower()
            if lowered not in {"", "-", "default", "дефолт", "по умолчанию"}:
                try:
                    prize_places = int(text)
                except Exception:
                    await update.message.reply_text("Введите целое число от 1 до 100, либо '-' для значения 10.")
                    return True

            if prize_places < 1 or prize_places > 100:
                await update.message.reply_text("Количество призовых мест должно быть от 1 до 100.")
                return True

            starts_at = draft.get('starts_at')
            ends_at = draft.get('ends_at')
            if not starts_at or not ends_at:
                await update.message.reply_text("Сессия создания турнира повреждена. Запустите /new_tour заново.")
                context.user_data.pop('new_tour', None)
                return True

            # criteria сохраняем в title (или target_fish) если тип specific_fish
            extra_title = ''
            if draft.get('tournament_type') == 'specific_fish' and draft.get('criteria'):
                extra_title = f" ({'вес' if draft['criteria']=='weight' else 'кол-во'})"
            tournament_id = await _run_sync(db.create_tournament,
                chat_id=int(draft['chat_id']),
                created_by=int(draft['created_by']),
                title=(draft.get('title') or 'Турнир') + extra_title,
                tournament_type=draft.get('tournament_type'),
                starts_at=starts_at,
                ends_at=ends_at,
                target_fish=draft.get('target_fish'),
                target_location=draft.get('target_location'),
                prize_places=prize_places,
            )

            if tournament_id:
                created = await _run_sync(db.get_tournament, tournament_id) or {}
                t_type = created.get('tournament_type') or draft.get('tournament_type')
                t_type_name = self.TOUR_TYPES.get(t_type, t_type)
                fish_line = ""
                fish_name = created.get('target_fish') or draft.get('target_fish')
                if fish_name:
                    fish_line = f"\n🎯 Рыба: {fish_name}"
                places_count = int(created.get('prize_places') or prize_places or 10)
                await update.message.reply_text(
                    f"✅ Турнир создан (ID: {tournament_id})\n"
                    f"🏆 {created.get('title') or draft.get('title')}\n"
                    f"📌 Тип: {t_type_name}{fish_line}\n"
                    f"🏅 Призовых мест: {places_count}\n"
                    f"🕒 {starts_at.strftime('%d.%m.%Y %H:%M')} — {ends_at.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                await update.message.reply_text("❌ Не удалось создать турнир.")

            context.user_data.pop('new_tour', None)
            return True

        return False

    async def tour_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать топ-10 игроков в активном турнире."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id if update.effective_chat else 0
        cache_key = ("tour", chat_id, user_id)
        cached = self._tour_response_cache.get(cache_key)
        now_ts = time.monotonic()
        if cached and cached[0] > now_ts:
            await update.message.reply_text(cached[1])
            return

        loading_message = await update.message.reply_text("Считаю турнир...")
        tour = await _run_sync(db.get_active_tournament)
        if not tour:
            await loading_message.edit_text("Сейчас нет активных турниров.")
            return
            await update.message.reply_text("🏁 Сейчас нет активных турниров.")
            return

        medals = ['🥇', '🥈', '🥉']
        starts_str = tour['starts_at'].strftime('%d.%m.%Y %H:%M') if hasattr(tour['starts_at'], 'strftime') else str(tour['starts_at'])[:16]
        ends_str = tour['ends_at'].strftime('%d.%m.%Y %H:%M') if hasattr(tour['ends_at'], 'strftime') else str(tour['ends_at'])[:16]
        t_type = tour.get('tournament_type', 'total_weight')
        target_location = tour.get('target_location')
        top_limit = int(tour.get('prize_places') or 10)

        lines = [
            f"🏆 <b>Турнир: {tour['title']}</b>",
            f"📅 {starts_str} — {ends_str}",
            f"🏅 Призовых мест: {top_limit}",
            "",
        ]

        user_row = None
        user_place = None
        if target_location:
            if t_type == 'longest_fish':
                rows = await _run_sync(db.get_location_leaderboard_length, target_location, tour['starts_at'], tour['ends_at'], top_limit)
                all_rows = await _run_sync(db.get_location_leaderboard_length, target_location, tour['starts_at'], tour['ends_at'], 1000)
            elif t_type == 'biggest_weight':
                rows = await _run_sync(db.get_location_leaderboard_weight, target_location, tour['starts_at'], tour['ends_at'], top_limit)
                all_rows = await _run_sync(db.get_location_leaderboard_weight, target_location, tour['starts_at'], tour['ends_at'], 1000)
            else:
                rows = []
                all_rows = []
            lines.insert(1, f"📍 Локация: {target_location}")
            if not rows:
                lines.append("Пока никто не поймал рыбу на этой локации.")
            else:
                for i, r in enumerate(rows, 1):
                    medal = medals[i - 1] if i <= 3 else f"{i}."
                    name = html.escape(r.get('username') or str(r['user_id']))
                    fish = html.escape(r.get('fish_name', '?'))
                    if t_type == 'longest_fish':
                        length = round(float(r.get('best_length') or 0), 1)
                        lines.append(f"{medal} {name} — {fish} — {length} см")
                    else:
                        weight = round(float(r.get('best_weight') or 0), 2)
                        lines.append(f"{medal} {name} — {fish} — {weight} кг")
                # Поиск пользователя вне топа
                for idx, r in enumerate(all_rows, 1):
                    if r.get('user_id') == user_id:
                        user_row = r
                        user_place = idx
                        break
                if user_row and user_place > top_limit:
                    name = html.escape(user_row.get('username') or str(user_row['user_id']))
                    fish = html.escape(user_row.get('fish_name', '?'))
                    lines.append("")
                    if t_type == 'longest_fish':
                        length = round(float(user_row.get('best_length') or 0), 1)
                        lines.append(f"<i>Ваше место: {user_place}. {name} — {fish} — {length} см</i>")
                    else:
                        weight = round(float(user_row.get('best_weight') or 0), 2)
                        lines.append(f"<i>Ваше место: {user_place}. {name} — {fish} — {weight} кг</i>")
        else:
            if t_type == 'total_length':
                rows = await _run_sync(db.get_tour_leaderboard_length, tour['starts_at'], tour['ends_at'], top_limit)
                all_rows = await _run_sync(db.get_tour_leaderboard_length, tour['starts_at'], tour['ends_at'], 1000)
            else:
                rows = await _run_sync(db.get_tour_leaderboard_weight, tour['starts_at'], tour['ends_at'], top_limit)
                all_rows = await _run_sync(db.get_tour_leaderboard_weight, tour['starts_at'], tour['ends_at'], 1000)
            if not rows:
                lines.append("Пока никто не поймал рыбу.")
            else:
                for i, r in enumerate(rows, 1):
                    medal = medals[i - 1] if i <= 3 else f"{i}."
                    name = html.escape(r.get('username') or str(r['user_id']))
                    if t_type == 'total_length':
                        length = round(float(r.get('total_length') or 0), 1)
                        lines.append(f"{medal} {name} — {length} см")
                    else:
                        weight = round(float(r['total_weight']), 2)
                        lines.append(f"{medal} {name} — {weight} кг")
                # Поиск пользователя вне топа
                for idx, r in enumerate(all_rows, 1):
                    if r.get('user_id') == user_id:
                        user_row = r
                        user_place = idx
                        break
                if user_row and user_place > top_limit:
                    name = html.escape(user_row.get('username') or str(user_row['user_id']))
                    lines.append("")
                    if t_type == 'total_length':
                        length = round(float(user_row.get('total_length') or 0), 1)
                        lines.append(f"<i>Ваше место: {user_place}. {name} — {length} см</i>")
                    else:
                        weight = round(float(user_row.get('total_weight') or 0), 2)
                        lines.append(f"<i>Ваше место: {user_place}. {name} — {weight} кг</i>")

        response_text = "\n".join(lines)
        self._tour_response_cache[cache_key] = (time.monotonic() + self._tour_cache_ttl, response_text)
        if len(self._tour_response_cache) > 500:
            expired_keys = [key for key, value in self._tour_response_cache.items() if value[0] <= time.monotonic()]
            for key in expired_keys[:250]:
                self._tour_response_cache.pop(key, None)
        await loading_message.edit_text(response_text)

    async def _location_leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, location_name: str):
        """Топ-10 по самой длинной рыбе на локации в рамках активного турнира."""
        try:
            tour = await _run_sync(db.get_active_tournament_for_location, location_name)
            if not tour:
                await update.message.reply_text(f"🏁 Нет активного турнира для этой локации.")
                return
            top_limit = int(tour.get('prize_places') or 10)
            medals = ['🥇', '🥈', '🥉']
            starts_str = tour['starts_at'].strftime('%d.%m.%Y %H:%M') if hasattr(tour['starts_at'], 'strftime') else str(tour['starts_at'])[:16]
            ends_str = tour['ends_at'].strftime('%d.%m.%Y %H:%M') if hasattr(tour['ends_at'], 'strftime') else str(tour['ends_at'])[:16]
            lines = [
                f"🕸️ <b>Топ локации: {location_name}</b>",
                f"📅 {starts_str} — {ends_str}",
                f"🏅 Призовых мест: {top_limit}",
                "",
            ]
            user_id = update.effective_user.id
            user_row = None
            user_place = None
            # Получаем параметры турнира
            target_fish = tour.get('target_fish')
            criteria = tour.get('criteria', 'weight')
            
            logger.info(f"Tournament found for {location_name}: fish={target_fish}, criteria={criteria}")
            
            if not target_fish:
                lines.append("Ошибка: не указана целевая рыба для турнира.")
                await update.message.reply_text("\n".join(lines), parse_mode='HTML')
                return
            if criteria == 'weight':
                rows = await _run_sync(db.get_location_fish_leaderboard_weight, location_name, target_fish, tour['starts_at'], tour['ends_at'], top_limit)
                all_rows = await _run_sync(db.get_location_fish_leaderboard_weight, location_name, target_fish, tour['starts_at'], tour['ends_at'], 1000)
                logger.info(f"Rows found for {location_name} (weight): {len(rows)}")
                if not rows:
                    lines.append(f"Пока никто не поймал рыбу '{target_fish}' на этой локации.")
                else:
                    for i, r in enumerate(rows, 1):
                        medal = medals[i - 1] if i <= 3 else f"{i}."
                        name = html.escape(r.get('username') or str(r['user_id']))
                        weight = round(float(r.get('total_weight') or 0), 2)
                        lines.append(f"{medal} {name} — {weight} кг")
                    # Поиск пользователя вне топа
                    for idx, r in enumerate(all_rows, 1):
                        if r.get('user_id') == user_id:
                            user_row = r
                            user_place = idx
                            break
                    if user_row and user_place > top_limit:
                        name = html.escape(user_row.get('username') or str(user_row['user_id']))
                        weight = round(float(user_row.get('total_weight') or 0), 2)
                        lines.append("")
                        lines.append(f"<i>Ваше место: {user_place}. {name} — {weight} кг</i>")
            elif criteria == 'count':
                rows = await _run_sync(db.get_location_fish_leaderboard_count, location_name, target_fish, tour['starts_at'], tour['ends_at'], top_limit)
                all_rows = await _run_sync(db.get_location_fish_leaderboard_count, location_name, target_fish, tour['starts_at'], tour['ends_at'], 1000)
                if not rows:
                    lines.append(f"Пока никто не поймал рыбу '{target_fish}' на этой локации.")
                else:
                    for i, r in enumerate(rows, 1):
                        medal = medals[i - 1] if i <= 3 else f"{i}."
                        name = html.escape(r.get('username') or str(r['user_id']))
                        count = int(r.get('total_fish') or 0)
                        lines.append(f"{medal} {name} — {count} шт.")
                    # Поиск пользователя вне топа
                    for idx, r in enumerate(all_rows, 1):
                        if r.get('user_id') == user_id:
                            user_row = r
                            user_place = idx
                            break
                    if user_row and user_place > top_limit:
                        name = html.escape(user_row.get('username') or str(user_row['user_id']))
                        count = int(user_row.get('total_fish') or 0)
                        lines.append("")
                        lines.append(f"<i>Ваше место: {user_place}. {name} — {count} шт.</i>")
            else:
                lines.append("Тип турнира для этой локации не поддерживается отображением.")
            await update.message.reply_text("\n".join(lines), parse_mode='HTML')
        except Exception as e:
            logger.exception("_location_leaderboard_command failed for %s: %s", location_name, e)
            await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")

    async def ozero_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._location_leaderboard_command(update, context, "Озеро")

    async def reka_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._location_leaderboard_command(update, context, "Река")

    async def more_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._location_leaderboard_command(update, context, "Море")

    async def prud_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._location_leaderboard_command(update, context, "Городской пруд")

    async def mes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправить сообщение во все чаты (только для владельца)."""
        if not self._is_owner(update.effective_user.id):
            await update.message.reply_text("❌ Только для владельца.")
            return
        if not context.args:
            await update.message.reply_text("Использование: /mes <текст>")
            return
        text = " ".join(context.args)
        chat_ids = await _run_sync(db.get_all_chat_ids)
        sent = 0
        failed = 0
        for cid in chat_ids:
            try:
                await context.bot.send_message(chat_id=cid, text=text)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"✅ Отправлено: {sent}, ❌ Ошибки: {failed}")

    async def send_invoice_url_button(self, chat_id, invoice_url, text, user_id=None, invoice_id=None, timeout_sec=60, reply_to_message_id=None):
        """Отправить кнопку оплаты со ссылкой инвойса, с автоотключением."""
        logger.info(f"[INVOICE] Sending invoice button to chat_id={chat_id}, url={invoice_url}, user_id={user_id}, invoice_id={invoice_id}")
        if user_id is None:
            raise ValueError("user_id обязателен для send_invoice_url_button")
        if invoice_id is None:
            invoice_id = f"{user_id}_{int(datetime.now().timestamp())}"
        keyboard = [[InlineKeyboardButton(
            "💳 Оплатить Telegram Stars",
            url=invoice_url
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        send_kwargs = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
        }
        if reply_to_message_id is not None:
            send_kwargs["reply_to_message_id"] = reply_to_message_id

        msg = await self._safe_send_message(**send_kwargs)
        if not msg:
            logger.warning("[INVOICE] Failed to send invoice button message chat_id=%s user_id=%s", chat_id, user_id)
            return None
        # Сохраняем активный инвойс для пользователя
        self._store_active_invoice_context(
            user_id=user_id,
            chat_id=chat_id,
            message_id=msg.message_id,
            invoice_url=invoice_url,
            invoice_id=invoice_id,
        )
        return msg
        # If you want to handle errors here, add try/except and proper indentation.
        # Example:
        # try:
        #     ...
        # except Exception:
        #     await update.message.reply_text("\u26A0\uFE0F Произошла ошибка. Попробуйте позже.")

    def _store_active_invoice_context(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        invoice_url: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ) -> None:
        """Сохраняет chat/message якорь инвойса для корректных reply после оплаты."""
        if invoice_id is None:
            invoice_id = f"{user_id}_{int(datetime.now().timestamp())}"
        self.active_invoices[user_id] = {
            "invoice_id": invoice_id,
            "invoice_url": invoice_url,
            "msg_id": message_id,
            "message_id": message_id,
            "group_message_id": message_id,
            "created_at": datetime.now(),
            "chat_id": chat_id,
            "group_chat_id": chat_id,
        }


    def _build_guaranteed_payload(self, user_id: int, chat_id: int) -> str:
        """Payload для гарантированного улова (инвойс)."""
        return f"guaranteed_{user_id}_{chat_id}_{int(datetime.now().timestamp())}"


    def _build_dynamite_skip_payload(self, user_id: int, chat_id: int) -> str:
        """Payload для мгновенного взрыва динамита (инвойс)."""
        return f"dynamite_skip_{user_id}_{chat_id}_{int(datetime.now().timestamp())}"

    def _parse_dynamite_skip_payload(self, payload: str) -> Optional[dict]:
        """Парсит payload вида dynamite_skip_{user_id}_{chat_id}_{ts}"""
        if not payload or not payload.startswith("dynamite_skip_"):
            return None
        body = payload[len("dynamite_skip_"):]
        parts = body.rsplit("_", 2)
        if len(parts) != 3:
            return None
        user_part, chat_part, ts_part = parts
        try:
            return {
                "payload_user_id": int(user_part),
                "group_chat_id": int(chat_part),
                "created_ts": int(ts_part),
            }
        except (TypeError, ValueError):
            return None

    def _build_dynamite_fine_payload(self, user_id: int, chat_id: int) -> str:
        return f"dynamite_fine_{user_id}_{chat_id}_{int(datetime.now().timestamp())}"

    def _parse_dynamite_fine_payload(self, payload: str) -> Optional[Dict[str, int]]:
        if not payload or not payload.startswith("dynamite_fine_"):
            return None

        body = payload[len("dynamite_fine_"):]
        parts = body.rsplit("_", 2)
        if len(parts) != 3:
            return None

        user_part, chat_part, ts_part = parts
        try:
            return {
                "payload_user_id": int(user_part),
                "group_chat_id": int(chat_part),
                "created_ts": int(ts_part),
            }
        except (TypeError, ValueError):
            return None

    def _parse_booster_payload(self, payload: str) -> Optional[Dict[str, Any]]:
        if not payload or not payload.startswith("booster_"):
            return None

        body = payload[len("booster_"):]
        parts = body.rsplit("_", 3)
        if len(parts) != 4:
            return None

        booster_code, user_part, chat_part, ts_part = parts
        try:
            return {
                "booster_code": booster_code,
                "payload_user_id": int(user_part),
                "group_chat_id": int(chat_part),
                "created_ts": int(ts_part),
            }
        except (TypeError, ValueError):
            return None

    def _build_booster_payload(self, code: str, user_id: int, chat_id: int) -> str:
        """Payload для покупки бустера (кормушки/эхолота) (инвойс)."""
        return f"booster_{code}_{user_id}_{chat_id}_{int(datetime.now().timestamp())}"

    def _build_harpoon_skip_payload(self, user_id: int, chat_id: int) -> str:
        """Payload для мгновенного использования гарпуна (инвойс)."""
        return f"harpoon_skip_{user_id}_{chat_id}_{int(datetime.now().timestamp())}"

    def _parse_harpoon_skip_payload(self, payload: str) -> Optional[Dict[str, int]]:
        """Парсит payload вида harpoon_skip_{user_id}_{chat_id}_{ts}"""
        if not payload or not payload.startswith("harpoon_skip_"):
            return None
        body = payload[len("harpoon_skip_"):]
        parts = body.rsplit("_", 2)
        if len(parts) != 3:
            return None
        user_part, chat_part, ts_part = parts
        try:
            return {
                "payload_user_id": int(user_part),
                "group_chat_id": int(chat_part),
                "created_ts": int(ts_part),
            }
        except (TypeError, ValueError):
            return None

    def _build_raf_create_payload(self, user_id: int, event_id: int) -> str:
        """Payload для оплаты создания RAF-ивента."""
        return f"raf_create_{event_id}_{user_id}_{int(datetime.now().timestamp())}"

    def _parse_raf_create_payload(self, payload: str) -> Optional[Dict[str, int]]:
        """Парсит payload вида raf_create_{event_id}_{user_id}_{ts}."""
        if not payload or not payload.startswith("raf_create_"):
            return None
        body = payload[len("raf_create_"):]
        parts = body.rsplit("_", 2)
        if len(parts) != 3:
            return None
        event_part, user_part, ts_part = parts
        try:
            return {
                "event_id": int(event_part),
                "payload_user_id": int(user_part),
                "created_ts": int(ts_part),
            }
        except (TypeError, ValueError):
            return None

    def _build_duel_invite_payload(
        self,
        inviter_id: int,
        target_id: int,
        chat_id: int,
        target_username: Optional[str] = None,
    ) -> str:
        """Payload для оплаты приглашения в дуэль."""
        ts = int(datetime.now().timestamp())
        safe_username = re.sub(r'[^A-Za-z0-9_]', '', str(target_username or '').lstrip('@'))
        if safe_username:
            return f"duel_invite_{inviter_id}_{target_id}_{chat_id}_{safe_username}_{ts}"
        return f"duel_invite_{inviter_id}_{target_id}_{chat_id}_{ts}"

    def _parse_duel_invite_payload(self, payload: str) -> Optional[Dict[str, Any]]:
        """Парсит payload дуэли с поддержкой legacy и расширенного формата."""
        if not payload or not payload.startswith("duel_invite_"):
            return None
        body = payload[len("duel_invite_"):]

        extended = re.match(r"^(-?\d+)_(-?\d+)_(-?\d+)_([A-Za-z0-9_]{1,64})_(-?\d+)$", body)
        if extended:
            try:
                return {
                    "payload_user_id": int(extended.group(1)),
                    "target_user_id": int(extended.group(2)),
                    "group_chat_id": int(extended.group(3)),
                    "target_username": extended.group(4),
                    "created_ts": int(extended.group(5)),
                }
            except (TypeError, ValueError):
                return None

        legacy = re.match(r"^(-?\d+)_(-?\d+)_(-?\d+)_(-?\d+)$", body)
        if not legacy:
            return None

        try:
            return {
                "payload_user_id": int(legacy.group(1)),
                "target_user_id": int(legacy.group(2)),
                "group_chat_id": int(legacy.group(3)),
                "created_ts": int(legacy.group(4)),
            }
        except (TypeError, ValueError):
            return None

    def _duel_user_label(self, user_id: int, username: Optional[str]) -> str:
        normalized = str(username or '').strip()
        if normalized.startswith('@'):
            normalized = normalized[1:]
        if normalized:
            return f"@{normalized}"
        return f"id{int(user_id)}"

    async def _send_duel_invitation_message(
        self,
        chat_id: int,
        duel: Dict[str, Any],
        attempts_left_after: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> Optional[Message]:
        duel_id = int(duel.get('id') or 0)
        target_id = int(duel.get('target_id') or 0)
        inviter_id = int(duel.get('inviter_id') or 0)

        inviter_label = self._duel_user_label(inviter_id, duel.get('inviter_username'))
        target_label = self._duel_user_label(target_id, duel.get('target_username'))

        attempts_line = ""
        if attempts_left_after is not None:
            attempts_line = f"\n🎟 Бесплатных приглашений сегодня осталось: {attempts_left_after}/{DUEL_FREE_INVITES_PER_DAY}"

        text = (
            "⚔️ Вызов на дуэль!\n\n"
            f"{inviter_label} вызывает {target_label}.\n"
            f"{target_label}, у вас 1 минута, чтобы принять решение.{attempts_line}\n\n"
            "После принятия у обоих есть 1 час, чтобы написать /fish в этом чате.\n"
            "Чей улов лучше, тот победит и заберет улов соперника."
        )

        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Согласиться", callback_data=f"duel_accept_{duel_id}_{target_id}"),
                InlineKeyboardButton("❌ Отказаться", callback_data=f"duel_decline_{duel_id}_{target_id}"),
            ]]
        )

        send_kwargs = {
            'chat_id': int(chat_id),
            'text': text,
            'reply_markup': keyboard,
        }
        if reply_to_message_id is not None:
            send_kwargs['reply_to_message_id'] = int(reply_to_message_id)

        msg = await self._safe_send_message(**send_kwargs)
        if msg and self.scheduler:
            try:
                run_at = datetime.now() + timedelta(seconds=DUEL_INVITE_TIMEOUT_SECONDS)
                self.scheduler.add_job(
                    self._handle_duel_invite_timeout,
                    trigger=DateTrigger(run_date=run_at),
                    kwargs={'duel_id': duel_id, 'chat_id': int(chat_id)},
                    id=f"duel_invite_{duel_id}",
                    replace_existing=True,
                )
            except Exception:
                logger.exception("Failed to schedule duel timeout for duel_id=%s", duel_id)
        return msg

    def _cancel_duel_invite_timeout_job(self, duel_id: int) -> None:
        if not self.scheduler:
            return
        try:
            self.scheduler.remove_job(f"duel_invite_{int(duel_id)}")
        except Exception:
            pass

    def _schedule_duel_active_timeout_job(self, duel_id: int, chat_id: int) -> None:
        if not self.scheduler:
            return
        try:
            run_at = datetime.now(timezone.utc) + timedelta(seconds=DUEL_ACTIVE_TIMEOUT_SECONDS)
            self.scheduler.add_job(
                self._handle_duel_active_timeout,
                trigger=DateTrigger(run_date=run_at),
                kwargs={'duel_id': int(duel_id), 'chat_id': int(chat_id)},
                id=f"duel_active_{int(duel_id)}",
                replace_existing=True,
            )
        except Exception:
            logger.exception("Failed to schedule active duel timeout for duel_id=%s", duel_id)

    def _cancel_duel_active_timeout_job(self, duel_id: int) -> None:
        if not self.scheduler:
            return
        try:
            self.scheduler.remove_job(f"duel_active_{int(duel_id)}")
        except Exception:
            pass

    async def _handle_duel_invite_timeout(self, duel_id: int, chat_id: int):
        try:
            result = await _run_sync(db.expire_duel_invitation_by_id, int(duel_id))
        except Exception:
            logger.exception("Failed to expire duel invite by timeout duel_id=%s", duel_id)
            return

        if not result.get('ok') or not result.get('expired'):
            return

        duel = result.get('duel') or {}
        inviter_label = self._duel_user_label(int(duel.get('inviter_id') or 0), duel.get('inviter_username'))
        target_label = self._duel_user_label(int(duel.get('target_id') or 0), duel.get('target_username'))
        refund_note = "\n🎟 Бесплатная попытка возвращена." if str(duel.get('attempt_type') or '') == 'free' else ""

        await self._safe_send_message(
            chat_id=int(chat_id),
            text=(
                f"⏱ Дуэль не состоялась: {target_label} не ответил вовремя.\n"
                f"{inviter_label} может отправить новый вызов.{refund_note}"
            ),
        )

    async def _handle_duel_active_timeout(self, duel_id: int, chat_id: int):
        try:
            result = await _run_sync(db.expire_active_duel_by_id, int(duel_id),
                timeout_seconds=DUEL_ACTIVE_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("Failed to expire active duel by timeout duel_id=%s", duel_id)
            return

        if not result.get('ok') or not result.get('expired'):
            return

        duel = result.get('duel') or {}
        inviter_label = self._duel_user_label(int(duel.get('inviter_id') or 0), duel.get('inviter_username'))
        target_label = self._duel_user_label(int(duel.get('target_id') or 0), duel.get('target_username'))
        inviter_done = bool(result.get('inviter_done'))
        target_done = bool(result.get('target_done'))

        if not inviter_done and not target_done:
            reason_line = "Никто не сделал заброс за 1 час после принятия."
        elif not inviter_done:
            reason_line = f"{inviter_label} не сделал заброс за 1 час."
        else:
            reason_line = f"{target_label} не сделал заброс за 1 час."

        refund_note = "\n🎟 Бесплатная попытка возвращена пригласившему." if str(duel.get('attempt_type') or '') == 'free' else ""

        await self._safe_send_message(
            chat_id=int(chat_id),
            text=(
                "⏱ Дуэль завершена по таймауту.\n"
                f"{reason_line}{refund_note}"
            ),
        )

    @staticmethod
    def _format_duel_catch_text(fish_name: str, weight: Any, length: Any) -> str:
        safe_name = str(fish_name or 'Неизвестная рыба')
        try:
            weight_val = float(weight)
        except (TypeError, ValueError):
            weight_val = 0.0
        try:
            length_val = float(length)
        except (TypeError, ValueError):
            length_val = 0.0
        return f"{safe_name} — {weight_val:.2f} кг, {length_val:.1f} см"

    async def _maybe_process_duel_catch(
        self,
        user_id: int,
        chat_id: int,
        fish_name: str,
        weight: float,
        length: float,
        catch_id: Optional[int] = None,
        resolve_latest_catch: bool = True,
    ) -> None:
        """Если у пользователя активная дуэль в этом чате, засчитать улов и объявить результат."""
        duel = await _run_sync(db.get_active_duel_for_user, int(user_id))
        if not duel or str(duel.get('status') or '') != 'active':
            return

        duel_chat_id = int(duel.get('chat_id') or 0)
        if duel_chat_id and duel_chat_id != int(chat_id):
            return

        duel_id = int(duel.get('id') or 0)
        if duel_id <= 0:
            return

        normalized_catch_id = int(catch_id) if catch_id is not None else None
        if normalized_catch_id is None and resolve_latest_catch:
            try:
                latest_catch = await _run_sync(db.get_latest_unsold_catch, int(user_id), int(chat_id))
                if latest_catch and latest_catch.get('id') is not None:
                    normalized_catch_id = int(latest_catch.get('id'))
            except Exception:
                logger.exception("Failed to load latest catch for duel user=%s chat=%s", user_id, chat_id)

        record_result = await _run_sync(db.record_duel_catch, duel_id=duel_id,
            user_id=int(user_id),
            fish_name=fish_name,
            weight=weight,
            length=length,
            catch_id=normalized_catch_id,
        )

        if not record_result.get('ok'):
            error_code = str(record_result.get('error') or 'record_failed')
            if error_code not in {'already_submitted', 'duel_not_active', 'not_participant'}:
                logger.warning(
                    "Failed to record duel catch duel_id=%s user=%s error=%s",
                    duel_id,
                    user_id,
                    error_code,
                )
            return

        duel_data = record_result.get('duel') or duel
        inviter_id = int(duel_data.get('inviter_id') or 0)
        target_id = int(duel_data.get('target_id') or 0)
        inviter_label = self._duel_user_label(inviter_id, duel_data.get('inviter_username'))
        target_label = self._duel_user_label(target_id, duel_data.get('target_username'))
        actor_label = inviter_label if int(user_id) == inviter_id else target_label

        catch_line = self._format_duel_catch_text(fish_name, weight, length)
        duel_chat = int(duel_data.get('chat_id') or chat_id)

        if not record_result.get('completed'):
            opponent_label = target_label if int(user_id) == inviter_id else inviter_label
            await self._safe_send_message(
                chat_id=duel_chat,
                text=(
                    f"⚔️ Дуэль: улов засчитан для {actor_label}.\n"
                    f"🐟 {catch_line}\n"
                    f"Ожидаем улов от {opponent_label}."
                ),
            )
            return

        self._cancel_duel_active_timeout_job(duel_id)

        inviter_catch_line = self._format_duel_catch_text(
            str(duel_data.get('inviter_fish_name') or 'Неизвестная рыба'),
            duel_data.get('inviter_weight'),
            duel_data.get('inviter_length'),
        )
        target_catch_line = self._format_duel_catch_text(
            str(duel_data.get('target_fish_name') or 'Неизвестная рыба'),
            duel_data.get('target_weight'),
            duel_data.get('target_length'),
        )

        if bool(record_result.get('draw')):
            await self._safe_send_message(
                chat_id=duel_chat,
                text=(
                    "⚖️ Дуэль завершилась ничьей!\n\n"
                    f"{inviter_label}: {inviter_catch_line}\n"
                    f"{target_label}: {target_catch_line}\n\n"
                    "Передача улова не требуется."
                ),
            )
            return

        winner_id = int(duel_data.get('winner_id') or 0)
        loser_id = int(duel_data.get('loser_id') or 0)

        winner_username = duel_data.get('inviter_username') if winner_id == inviter_id else duel_data.get('target_username')
        loser_username = duel_data.get('inviter_username') if loser_id == inviter_id else duel_data.get('target_username')
        winner_label = self._duel_user_label(winner_id, winner_username)
        loser_label = self._duel_user_label(loser_id, loser_username)

        loser_catch_id = duel_data.get('inviter_catch_id') if loser_id == inviter_id else duel_data.get('target_catch_id')
        transfer_done = False
        transfer_possible = loser_catch_id is not None
        if loser_catch_id is not None:
            try:
                transfer_done = await _run_sync(db.move_caught_fish_to_user, fish_id=int(loser_catch_id),
                    from_user_id=int(loser_id),
                    to_user_id=int(winner_id),
                    to_chat_id=duel_chat,
                )
            except Exception:
                logger.exception(
                    "Failed to transfer duel catch duel_id=%s fish_id=%s loser=%s winner=%s",
                    duel_id,
                    loser_catch_id,
                    loser_id,
                    winner_id,
                )

        if transfer_done:
            transfer_line = f"✅ Улов {loser_label} передан победителю {winner_label}."
        elif transfer_possible:
            transfer_line = "⚠️ Не удалось автоматически передать улов проигравшего."
        else:
            transfer_line = "ℹ️ Передача улова не требуется (у проигравшего не было пойманной рыбы)."

        await self._safe_send_message(
            chat_id=duel_chat,
            text=(
                "🏁 Дуэль завершена!\n\n"
                f"{inviter_label}: {inviter_catch_line}\n"
                f"{target_label}: {target_catch_line}\n\n"
                f"🏆 Победитель: {winner_label}\n"
                f"💥 Проигравший: {loser_label}\n"
                f"{transfer_line}"
            ),
        )

    def _get_feeder_by_code(self, feeder_code: str) -> Optional[Dict[str, Any]]:
        legacy_aliases = {
            "feeder_basic": "feeder_3",
            "feeder_pro": "feeder_7",
            "feeder_premium": "feeder_10",
            "feeder_5": "feeder_7",
        }
        feeder_code = legacy_aliases.get(feeder_code, feeder_code)
        for item in FEEDER_ITEMS:
            if item["code"] == feeder_code:
                return item
        return None

    def _format_seconds_compact(self, seconds: int) -> str:
        total = max(0, int(seconds))
        minutes, sec = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}ч {minutes}м {sec}с"
        return f"{minutes}м {sec}с"

    async def _execute_harpoon_catch(self, user_id: int, group_chat_id: int, reply_to_message_id: Optional[int] = None) -> None:
        player = await _run_sync(db.get_player, user_id, group_chat_id)
        if not player:
            await self._safe_send_message(
                chat_id=group_chat_id,
                text="❌ Профиль не найден. Используйте /start в этом чате.",
                reply_to_message_id=reply_to_message_id,
            )
            return

        location = player.get('current_location') or "Городской пруд"
        result = game.fish_with_harpoon(user_id, group_chat_id, location)

        await _run_sync(db.mark_harpoon_used, user_id, group_chat_id)

        if not result.get("success"):
            await self._safe_send_message(
                chat_id=group_chat_id,
                text=result.get("message", "❌ Гарпун не сработал."),
                reply_to_message_id=reply_to_message_id,
            )
            return

        fish = result.get('fish') or {}
        weight = result.get('weight', 0)
        length = result.get('length', 0)
        fish_name = fish.get('name', 'Неизвестная рыба')
        fish_price = await _run_sync(db.calculate_fish_price, fish, weight, length) if fish else 0

        fish_name_display = format_fish_name(fish_name)
        message = (
            f"🗡️ Гарпун сработал!\n\n"
            f"🐟 {fish_name_display}\n"
            f"📏 Размер: {length}см | Вес: {weight} кг\n"
            f"💰 Стоимость: {fish_price} 🪙\n"
            f"📍 Место: {result.get('location', location)}\n"
            f"⭐ Редкость: {fish.get('rarity', 'Обычная')}"
        )

        await self._safe_send_message(
            chat_id=group_chat_id,
            text=message,
            reply_to_message_id=reply_to_message_id,
        )

    async def _create_guaranteed_invoice_url(self, user_id: int, chat_id: int) -> Optional[str]:
        """Создать ссылку инвойса для гарантированного улова."""
        from config import BOT_TOKEN, STAR_NAME

        tg_api = TelegramBotAPI(BOT_TOKEN)
        return await tg_api.create_invoice_link(
            title="Гарантированный улов",
            description=f"Гарантированный улов — подтвердите оплату (1 {STAR_NAME})",
            payload=self._build_guaranteed_payload(user_id, chat_id),
            currency="XTR",
            prices=[{"label": "Вход", "amount": 1}],
        )

    async def _build_guaranteed_invoice_markup(self, user_id: int, chat_id: int) -> Optional[InlineKeyboardMarkup]:
        """Собрать inline-кнопку со ссылкой на оплату гарантированного улова."""
        try:
            invoice_url = await self._create_guaranteed_invoice_url(user_id, chat_id)
        except Exception as e:
            logger.error(f"[INVOICE] Failed to create guaranteed invoice link: {e}")
            return None

        if not invoice_url:
            return None

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⭐ Оплатить {GUARANTEED_CATCH_COST} Telegram Stars", url=invoice_url)]
        ])

    async def _create_skip_boat_cd_invoice_url(self, user_id: int, chat_id: int) -> Optional[str]:
        """Создать ссылку инвойса для сброса КД лодки."""
        from config import BOT_TOKEN, STAR_NAME
        tg_api = TelegramBotAPI(BOT_TOKEN)
        return await tg_api.create_invoice_link(
            title="Сброс КД лодки",
            description=f"Мгновенный сброс КД лодки (20 {STAR_NAME})",
            payload=f"skip_boat_cd_{user_id}_{chat_id}_{int(datetime.now().timestamp())}",
            currency="XTR",
            prices=[{"label": "Сброс КД", "amount": 20}],
        )

    async def _build_skip_boat_cd_invoice_markup(self, user_id: int, chat_id: int) -> Optional[InlineKeyboardMarkup]:
        """Собрать inline-кнопку со ссылкой на оплату сброса КД."""
        try:
            invoice_url = await self._create_skip_boat_cd_invoice_url(user_id, chat_id)
        except Exception as e:
            logger.error(f"[INVOICE] Failed to create boat cd skip invoice: {e}")
            return None
        if not invoice_url:
            return None
        return InlineKeyboardMarkup([[InlineKeyboardButton("⭐ Сбросить КД за 20 Stars", url=invoice_url)]])

    async def handle_pay_invoice_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return

        data = str(query.data or "")
        parts = data.split(":")
        if len(parts) != 3:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        _, owner_id, invoice_id = parts
        user_id = update.effective_user.id
        if str(user_id) != owner_id:
            await query.answer("Эта кнопка только для вас!", show_alert=True)
            return

        invoice_info = self.active_invoices.get(int(owner_id))
        if not invoice_info or invoice_info.get('invoice_id') != invoice_id:
            await query.answer("Инвойс уже неактивен", show_alert=True)
            return

        invoice_url = invoice_info.get('invoice_url')
        await query.answer()
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        if invoice_url:
            await query.message.reply_text(f"Откройте ссылку для оплаты: {invoice_url}")
        del self.active_invoices[int(owner_id)]

    def __init__(self):
        self.is_global_stopped = False
        self.scheduler = None  # Будет создан в main() с asyncio loop
        self.user_locations = {}  # Временное хранение локаций пользователей
        self.active_timeouts = {}  # Отслеживание активных таймеров
        self.active_invoices = {}  # Отслеживание активных инвойсов по пользователям
        self.application = None  # Будет установлено в main()
        self._tour_response_cache = {}
        self._tour_cache_ttl = float(os.getenv("TOUR_CACHE_TTL_SECONDS", "10"))
        self._telegram_document_file_id_cache = {}
        self.OWNER_ID = 793216884
        self.webapp_url = (os.getenv("WEBAPP_URL") or "https://fish.monkeysdynasty.website").strip()
        # Множество уже оплаченных payload'ов — защита от двойной оплаты одного инвойса
        # Ограничено 5000 записями — при переполнении удаляем половину (старые записи)
        self.paid_payloads: set = set()
        self._paid_payloads_max: int = 5000
        # Время запуска бота — сообщения, отправленные ДО этого времени, игнорируются
        self.bot_start_time = datetime.utcnow()
        self.RAF_CREATE_COST_STARS = 10
        self.RAF_RARITY_OPTIONS = [
            "срыв",
            "мусор",
            "обычная",
            "редкая",
            "легендарная",
            "аквариумная",
            "мифическая",
            "аномалия",
        ]
        self.RAF_RARITY_ALIASES = {
            "срыв": "срыв",
            "snap": "срыв",
            "no_bite": "срыв",
            "не клюет": "срыв",
            "не клюёт": "срыв",
            "мусор": "мусор",
            "trash": "мусор",
            "обычная": "обычная",
            "common": "обычная",
            "редкая": "редкая",
            "rare": "редкая",
            "легендарная": "легендарная",
            "legendary": "легендарная",
            "аквариумная": "аквариумная",
            "aquarium": "аквариумная",
            "мифическая": "мифическая",
            "mythic": "мифическая",
            "аномалия": "аномалия",
            "anomaly": "аномалия",
        }
        self.RAF_RESPONSIBILITY_NOTE = (
            "⚠️ Ответственность за выдачу призов несёт создатель ивента. "
            "Создатель бота не отвечает за выдачу призов."
        )
        self.TICKET_POINTS = {
            'snap': 1,
            'no_bite': 1,
            'trash': 2,
            'Обычная': 3,
            'Редкая': 5,
            'Легендарная': 7,
            'Аквариумная': 7,
            'Мифическая': 8,
            'Аномалия': 9,
        }
        self.TICKET_JACKPOT_CHANCE = 0.05
        self.TICKET_JACKPOT_MIN = 10
        self.TICKET_JACKPOT_MAX = 15
        self.RAF_ALLOWED_TRIGGER_SOURCES = {
            'fish_command',
            'start_fishing_callback',
            'guaranteed_fish',
        }
        self.TOUR_TYPES = {
            'longest_fish': 'Самая длинная рыба',
            'biggest_weight': 'Самая большая рыба (вес)',
            'total_weight': 'Общий вес улова',
            'total_length': 'Суммарная длина улова',
            'specific_fish': 'Улов определённой рыбы',
        }
        self.fight_sessions: Dict[str, Dict[str, Any]] = {}
        self.fight_timeout_tasks: Dict[str, asyncio.Task] = {}

    def _is_owner(self, user_id: int) -> bool:
        return int(user_id) == self.OWNER_ID

    def _is_restricted_and_block(self, chat_id: int) -> bool:
        """ заглушка для проверки ограничений по чатам """
        return False

    def _parse_datetime_input(self, raw_text: str) -> Optional[datetime]:
        value = (raw_text or '').strip()
        if not value:
            return None
        for fmt in ('%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M'):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
        return None

    def _normalize_raf_rarity(self, raw_value: str) -> Optional[str]:
        key = str(raw_value or '').strip().lower()
        if not key:
            return None
        return self.RAF_RARITY_ALIASES.get(key)

    async def _parse_raf_chat_target(self, raw_value: str) -> Optional[Dict[str, Any]]:
        """Нормализует chat_id из id/ссылки. Для приватных c/<id> приводит к -100<id>."""
        value = str(raw_value or '').strip()
        if not value:
            return None

        # Приватная ссылка вида https://t.me/c/<internal_chat_id>/<message_id>
        m_private = re.match(r'^https?://t\.me/c/(\d+)/(\d+)$', value, flags=re.IGNORECASE)
        if m_private:
            internal_id = m_private.group(1)
            return {
                "chat_id": int(f"-100{internal_id}"),
                "message_link": value,
            }

        # Публичная ссылка вида https://t.me/<username>/<message_id>
        m_public = re.match(r'^https?://t\.me/([A-Za-z0-9_]{4,})/(\d+)$', value, flags=re.IGNORECASE)
        if m_public:
            username = m_public.group(1)
            try:
                chat_obj = await self.application.bot.get_chat(f"@{username}")
                return {
                    "chat_id": int(chat_obj.id),
                    "message_link": value,
                }
            except Exception:
                return None

        # Чистый chat_id
        if re.fullmatch(r'-?\d+', value):
            if value.startswith('-100'):
                return {"chat_id": int(value), "message_link": None}
            if value.startswith('-'):
                return {"chat_id": int(value), "message_link": None}
            # Если префикса нет, считаем private/supergroup id и добавляем -100
            return {"chat_id": int(f"-100{value}"), "message_link": None}

        return None

    def _extract_raf_outcome_rarity(self, result: Dict[str, Any]) -> Optional[str]:
        if result.get('is_trash'):
            return 'мусор'
        if result.get('snap') or result.get('no_bite'):
            return 'срыв'
        fish = result.get('fish') or {}
        raw_rarity = fish.get('rarity') or result.get('target_rarity')
        return self._normalize_raf_rarity(str(raw_rarity or ''))

    def _calculate_tickets_for_result(self, result: Dict[str, Any]) -> int:
        if result.get('snap'):
            return int(self.TICKET_POINTS['snap'])
        if result.get('no_bite'):
            return int(self.TICKET_POINTS['no_bite'])
        if result.get('is_trash'):
            return int(self.TICKET_POINTS['trash'])

        fish = result.get('fish') or {}
        rarity = fish.get('rarity') or result.get('target_rarity')
        if rarity in self.TICKET_POINTS:
            return int(self.TICKET_POINTS[rarity])
        return 0

    def _calculate_tickets_for_rarity(self, rarity: str) -> int:
        return int(self.TICKET_POINTS.get(str(rarity or ''), 0))

    def _award_tickets(
        self,
        user_id: int,
        base_tickets: int,
        username: str,
        source_type: str,
        source_ref: Optional[str] = None,
    ):
        base = int(base_tickets or 0)
        if base <= 0:
            return 0, 0, db.get_user_tickets(user_id)

        jackpot = 0
        if random.random() < self.TICKET_JACKPOT_CHANCE:
            jackpot = random.randint(self.TICKET_JACKPOT_MIN, self.TICKET_JACKPOT_MAX)

        total_awarded = base + jackpot
        new_total = db.add_tickets(
            user_id,
            total_awarded,
            username=username,
            source_type=source_type,
            source_ref=source_ref,
            jackpot_amount=jackpot,
        )
        return total_awarded, jackpot, new_total

    def _format_tickets_award_line(self, awarded: int, jackpot: int, total_tickets: int) -> str:
        if awarded <= 0:
            return ""
        if jackpot > 0:
            return f"\n🎟 Билеты: +{awarded} (джекпот +{jackpot})\n🎫 Всего билетов: {total_tickets}"
        return f"\n🎟 Билеты: +{awarded}\n🎫 Всего билетов: {total_tickets}"

    def _get_market_offer_snapshot(self, create_if_missing: bool = False) -> Optional[Dict[str, Any]]:
        """Нормализованный снимок предложения рынка дня (с fallback на авто-генерацию)."""
        try:
            offer = db.get_today_market_offer()
        except Exception:
            logger.exception("Failed to load market offer via get_today_market_offer")
            offer = None

        if offer:
            return offer

        daily_offer_getter = getattr(db, 'get_daily_market_offer', None)
        if not callable(daily_offer_getter):
            return None

        try:
            fallback = daily_offer_getter(create_if_missing=create_if_missing)
        except TypeError:
            fallback = daily_offer_getter()
        except Exception:
            logger.exception("Failed to load market offer via get_daily_market_offer")
            return None

        if not fallback:
            return None

        sold_weight = float(fallback.get('sold_weight') or 0.0)
        target_weight = float(fallback.get('target_weight') or 0.0)
        return {
            'id': fallback.get('id'),
            'market_day': str(fallback.get('market_day') or ''),
            'fish_name': str(fallback.get('fish_name') or ''),
            'multiplier': float(fallback.get('multiplier') or 1.0),
            'target_weight': target_weight,
            'sold_weight': sold_weight,
            'remaining_weight': max(0.0, target_weight - sold_weight),
            'active': sold_weight < target_weight,
            'created_at': fallback.get('created_at'),
        }

    def _build_fight_keyboard(self, session_id: str, user_id: int) -> InlineKeyboardMarkup:
        buttons = [
            InlineKeyboardButton(
                FIGHT_ACTION_LABELS[action],
                callback_data=f"fight_{session_id}_{action}_{user_id}",
            )
            for action in FIGHT_ACTIONS
        ]
        return InlineKeyboardMarkup([buttons])

    def _cleanup_fight_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.fight_sessions.pop(session_id, None)
        timeout_task = self.fight_timeout_tasks.pop(session_id, None)
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
        return session

    async def _fight_timeout_worker(self, session_id: str):
        try:
            await asyncio.sleep(FIGHT_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return

        session = self.fight_sessions.get(session_id)
        if not session:
            return

        self._cleanup_fight_session(session_id)

        chat_id = int(session['chat_id'])
        message_id = session.get('message_id')
        user_id = int(session['user_id'])

        if message_id:
            try:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="⏰ Время борьбы вышло. Крупная рыба сорвалась!",
                )
            except Exception:
                pass

        try:
            await self._maybe_process_duel_catch(
                user_id=user_id,
                chat_id=chat_id,
                fish_name="Срыв борьбы",
                weight=0.0,
                length=0.0,
                catch_id=None,
                resolve_latest_catch=False,
            )
        except Exception:
            logger.exception("Failed to process duel timeout from fight session=%s", session_id)

    async def _start_fight_session(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        result: Dict[str, Any],
        source_type: str,
        source_ref: str,
        reply_to_message_id: Optional[int],
    ) -> bool:
        fish = result.get('fish') or {}
        if not fish:
            return False

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        session_id = uuid.uuid4().hex[:10]
        expected_action = random.choice(FIGHT_ACTIONS)
        fish_name = str(fish.get('name') or 'Неизвестная рыба')
        weight = float(result.get('weight') or 0)
        length = float(result.get('length') or 0)

        self.fight_sessions[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'chat_id': chat_id,
            'fish': fish,
            'weight': weight,
            'length': length,
            'location': result.get('location'),
            'target_rarity': result.get('target_rarity'),
            'expected_action': expected_action,
            'source_type': source_type,
            'source_ref': source_ref,
            'reply_to_message_id': reply_to_message_id,
            'created_at': datetime.utcnow().isoformat(),
            'message_id': None,
        }

        prompt_text = (
            "⚔️ Началась борьба с крупной рыбой!\n\n"
            f"🐟 Цель: {fish_name}\n"
            f"⚖️ Вес: {weight:.2f} кг | 📏 Длина: {length:.1f} см\n"
            f"⏳ У вас {FIGHT_TIMEOUT_SECONDS} секунд: выберите правильное действие."
        )

        prompt_message = await self._safe_send_message(
            chat_id=chat_id,
            text=prompt_text,
            reply_markup=self._build_fight_keyboard(session_id, user_id),
            reply_to_message_id=reply_to_message_id,
        )
        if not prompt_message:
            self._cleanup_fight_session(session_id)
            return False

        self.fight_sessions[session_id]['message_id'] = prompt_message.message_id
        self.fight_timeout_tasks[session_id] = asyncio.create_task(self._fight_timeout_worker(session_id))
        return True

    async def handle_fight_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data or ""
        match = re.match(r"^fight_([a-f0-9]{10})_(jerk|hold|slack)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        session_id, action, owner_id_raw = match.groups()
        owner_id = int(owner_id_raw)
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if user_id != owner_id:
            await query.answer("Эта борьба не для вас", show_alert=True)
            return

        session = self.fight_sessions.get(session_id)
        if not session:
            await query.answer("Борьба уже завершена", show_alert=True)
            return

        await query.answer()

        expected_action = str(session.get('expected_action') or '')
        if action != expected_action:
            self._cleanup_fight_session(session_id)
            try:
                await query.edit_message_text("❌ Неверное действие. Рыба сорвалась во время борьбы!")
            except Exception:
                pass

            try:
                await self._maybe_process_duel_catch(
                    user_id=user_id,
                    chat_id=chat_id,
                    fish_name="Срыв борьбы",
                    weight=0.0,
                    length=0.0,
                    catch_id=None,
                    resolve_latest_catch=False,
                )
            except Exception:
                logger.exception("Failed to process duel failed-fight session=%s", session_id)
            return

        self._cleanup_fight_session(session_id)

        fight_result = game.finalize_fight_catch(
            user_id=user_id,
            chat_id=chat_id,
            location=str(session.get('location') or ''),
            fish_data=session.get('fish') or {},
            weight=float(session.get('weight') or 0),
            length=float(session.get('length') or 0),
            target_rarity=session.get('target_rarity'),
            guaranteed=False,
        )

        if not fight_result.get('success'):
            fail_text = str(fight_result.get('message') or '❌ Борьба завершилась неудачей.')
            try:
                await query.edit_message_text(fail_text)
            except Exception:
                pass
            return

        fish = fight_result.get('fish') or {}
        weight = float(fight_result.get('weight') or 0)
        length = float(fight_result.get('length') or 0)
        fish_price = int(fight_result.get('fish_price') or fish.get('price') or 0)

        tickets_awarded, tickets_jackpot, tickets_total = self._award_tickets(
            user_id,
            self._calculate_tickets_for_result(fight_result),
            username=update.effective_user.username or update.effective_user.first_name or str(user_id),
            source_type=str(session.get('source_type') or 'fight'),
            source_ref=str(session.get('source_ref') or ''),
        )
        tickets_line = self._format_tickets_award_line(tickets_awarded, tickets_jackpot, tickets_total)

        rarity_emoji = {
            'Обычная': '⚪',
            'Редкая': '🔵',
            'Легендарная': '🟡',
            'Мифическая': '🔴',
            'Аквариумная': '🟢',
            'Аномалия': '🟣',
        }
        fish_name_display = format_fish_name(str(fish.get('name') or 'Неизвестная рыба'))
        message = (
            "✅ Борьба выиграна!\n\n"
            f"{rarity_emoji.get(fish.get('rarity'), '⚪')} {fish_name_display}\n"
            f"📏 Размер: {length:.1f} см | ⚖️ Вес: {weight:.2f} кг\n"
            f"💰 Стоимость: {fish_price} 🪙\n"
            f"⭐ Редкость: {fish.get('rarity', 'Обычная')}"
        )
        if fight_result.get('xp_earned'):
            message += f"\n✨ Опыт: +{fight_result['xp_earned']}\n{format_level_progress(fight_result.get('level_info'))}"
        message += tickets_line

        try:
            await query.edit_message_text("✅ Верное действие! Рыба у вас на крючке.")
        except Exception:
            pass

        sticker_message = await self._send_catch_image(
            chat_id=chat_id,
            item_name=str(fish.get('name') or ''),
            item_type="fish",
            reply_to_message_id=session.get('reply_to_message_id'),
        )

        await self._safe_send_message(
            chat_id=chat_id,
            text=message,
            reply_to_message_id=(
                sticker_message.message_id
                if sticker_message
                else session.get('reply_to_message_id')
            ),
        )

        try:
            await self._maybe_process_duel_catch(
                user_id=user_id,
                chat_id=chat_id,
                fish_name=str(fish.get('name') or 'Неизвестная рыба'),
                weight=weight,
                length=length,
                catch_id=fight_result.get('catch_id'),
                resolve_latest_catch=not bool(fight_result.get('catch_id')),
            )
        except Exception:
            logger.exception("Failed to process duel success from fight session=%s", session_id)

        if fight_result.get('temp_rod_broken'):
            await self._safe_send_message(
                chat_id=chat_id,
                text=(
                    "💥 Временная удочка сломалась после удачного улова.\n"
                    "Теперь активна бамбуковая. Купить новую можно в магазине."
                ),
                reply_to_message_id=session.get('reply_to_message_id'),
            )

    def _format_raf_prizes_summary(self, prizes: List[Dict[str, Any]]) -> str:
        lines = []
        for idx, prize in enumerate(prizes, start=1):
            prize_text = html.escape(str(prize.get('prize_text') or 'Приз'))
            rarity_key = html.escape(str(prize.get('rarity_key') or ''))
            try:
                chance = float(prize.get('chance_percent') or 0)
            except (TypeError, ValueError):
                chance = 0.0
            lines.append(f"{idx}. {prize_text} — {rarity_key} ({chance:.2f}%)")
        return "\n".join(lines) if lines else "—"

    def _format_raf_datetime(self, value: Any) -> str:
        """Форматирует datetime/ISO-строку в вид DD.MM.YYYY HH:MM."""
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y %H:%M")

        text = str(value).strip()
        if not text:
            return "-"

        # Часто из БД приходит ISO, включая вариант с timezone/Z.
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return text

    async def _process_raf_event_roll(
        self,
        chat_id: int,
        user_id: int,
        username: str,
        chat_title: Optional[str],
        result: Dict[str, Any],
        trigger_source: str,
    ) -> bool:
        if trigger_source not in self.RAF_ALLOWED_TRIGGER_SOURCES:
            logger.info(
                "[RAF_LOG] Skip roll: source=%s is not eligible for RAF event participation",
                trigger_source,
            )
            return False

        rarity_key = self._extract_raf_outcome_rarity(result)
        if not rarity_key:
            return False

        winner_username = str(username or '').strip()
        won_location = result.get('location')
        try:
            won_prize = await _run_sync(db.try_roll_raf_prize, chat_id=chat_id,
                rarity_key=rarity_key,
                winner_user_id=user_id,
                winner_username=winner_username,
                won_location=won_location,
                trigger_source=trigger_source,
            )
        except Exception:
            logger.exception("[RAF_LOG] try_roll_raf_prize failed chat_id=%s user_id=%s", chat_id, user_id)
            return False

        if not won_prize:
            return False

        rollback_info = {}
        try:
            rollback_info = await _run_sync(db.rollback_reward_after_raf_win, user_id, chat_id, result)
        except Exception:
            logger.exception("[RAF_LOG] rollback failed after prize win user=%s chat=%s", user_id, chat_id)

        event_title_raw = str(won_prize.get('event_title') or 'RAF-ивент')
        prize_raw = str(won_prize.get('prize_text') or 'Приз')
        event_title = html.escape(event_title_raw)
        prize_text = html.escape(prize_raw)
        chance = float(won_prize.get('chance_percent') or 0)
        roll_value = float(won_prize.get('roll_value') or 0)
        rarity_label = html.escape(rarity_key)

        chat_prize_text = f"🎁 Приз найден — {prize_raw}"
        chat_win_msg = await self._safe_send_message(chat_id=chat_id, text=chat_prize_text)

        logger.info(
            "[RAF_LOG] Winner announced: event_id=%s prize_id=%s user_id=%s username=%s chance=%.2f roll=%.4f sent_to_chat=%s rollback=%s",
            won_prize.get('event_id'),
            won_prize.get('prize_id'),
            user_id,
            winner_username,
            chance,
            roll_value,
            bool(chat_win_msg),
            rollback_info,
        )

        creator_id = won_prize.get('creator_user_id')
        creator_int = None
        if creator_id:
            try:
                creator_int = int(creator_id)
            except (TypeError, ValueError):
                creator_int = None
            if creator_int:
                winner_display = f"@{winner_username}" if winner_username else f"id{user_id}"
                winner_display_safe = html.escape(winner_display)
                chat_display_safe = html.escape(str(chat_title or chat_id))
                owner_text = (
                    f"🎉 <b>Победа в RAF-ивенте!</b>\n\n"
                    f"🏷 Ивент: {event_title}\n"
                    f"🎁 Приз: {prize_text}\n"
                    f"👤 Победитель: {winner_display_safe} (ID: {user_id})\n"
                    f"📍 Чат: {chat_display_safe}\n"
                    f"🎯 Редкость: {rarity_label}\n"
                    f"📊 Шанс: {chance:.2f}% (ролл {roll_value:.2f})\n\n"
                    f"{html.escape(self.RAF_RESPONSIBILITY_NOTE)}"
                )
                owner_win_msg = await self._safe_send_message(chat_id=creator_int, text=owner_text, parse_mode="HTML")
                logger.info(
                    "[RAF_LOG] Owner DM sent: event_id=%s creator_id=%s winner_id=%s sent=%s",
                    won_prize.get('event_id'),
                    creator_int,
                    user_id,
                    bool(owner_win_msg),
                )

        remaining_prizes = int(won_prize.get('remaining_prizes') or 0)
        if remaining_prizes <= 0:
            finish_text = (
                f"🏁 <b>RAF-ивент завершен!</b>\n\n"
                f"🏷 Ивент: {event_title}\n"
                f"✅ Все призы были разыграны.\n\n"
                f"{html.escape(self.RAF_RESPONSIBILITY_NOTE)}"
            )
            finish_chat_msg = await self._safe_send_message(chat_id=chat_id, text=finish_text, parse_mode="HTML")
            logger.info(
                "[RAF_LOG] Event completion announced in chat: event_id=%s chat_id=%s sent=%s",
                won_prize.get('event_id'),
                chat_id,
                bool(finish_chat_msg),
            )

            if creator_int:
                owner_finish_text = (
                    f"🏁 Ваш RAF-ивент завершен.\n\n"
                    f"🏷 Ивент: {event_title}\n"
                    "✅ Все призы были разыграны."
                )
                finish_owner_msg = await self._safe_send_message(
                    chat_id=creator_int,
                    text=owner_finish_text,
                    parse_mode="HTML",
                )
                logger.info(
                    "[RAF_LOG] Event completion DM sent: event_id=%s creator_id=%s sent=%s",
                    won_prize.get('event_id'),
                    creator_int,
                    bool(finish_owner_msg),
                )

        return True

    async def raf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание RAF-ивента через личный wizard."""
        if update.effective_chat.type != 'private':
            await update.message.reply_text("Команда /raf работает только в личных сообщениях с ботом.")
            return

        user_id = update.effective_user.id
        context.user_data['raf_draft'] = {
            'step': 'title',
            'creator_user_id': user_id,
            'creator_private_chat_id': update.effective_chat.id,
            'title': None,
            'duration_hours': None,
            'target_chat_id': None,
            'source_message_link': None,
            'prizes_total': 0,
            'current_prize_index': 0,
            'current_prize_text': None,
            'current_prize_rarity': None,
            'prizes': [],
            'event_id': None,
        }

        await update.message.reply_text(
            "🎯 Создание RAF-ивента\n\n"
            "Шаг 1/5: Введите название ивента."
        )

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить создание RAF-ивента."""
        if update.effective_chat.type != 'private':
            await update.message.reply_text("Команда /cancel работает только в личных сообщениях с ботом.")
            return

        user_id = update.effective_user.id
        draft = context.user_data.pop('raf_draft', None)
        cancelled = False
        event_id = None

        if draft:
            event_id = draft.get('event_id')
            if event_id:
                cancelled = await _run_sync(db.cancel_raf_event_creation, int(event_id), int(user_id))
            else:
                cancelled = True
        else:
            pending = await _run_sync(db.get_latest_raf_pending_event, int(user_id))
            if pending:
                event_id = pending.get('id')
                cancelled = await _run_sync(db.cancel_raf_event_creation, int(event_id), int(user_id))

        if cancelled:
            if event_id:
                await update.message.reply_text(f"✅ Создание RAF-ивента отменено (ID: {event_id}).")
            else:
                await update.message.reply_text("✅ Создание RAF-ивента отменено.")
        else:
            await update.message.reply_text("Нет активного создания RAF-ивента для отмены.")

    async def handle_raf_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Пошаговый ввод параметров RAF-ивента."""
        draft = context.user_data.get('raf_draft')
        if not draft:
            return False

        if update.effective_chat.type != 'private':
            return False

        if int(draft.get('creator_user_id') or 0) != int(update.effective_user.id):
            return False

        message = update.effective_message
        if not message or not message.text:
            return True

        text = message.text.strip()
        step = draft.get('step')

        if step == 'title':
            if len(text) < 2:
                await update.message.reply_text("Название слишком короткое. Введите название ивента ещё раз.")
                return True
            draft['title'] = text[:200]
            draft['duration_hours'] = None
            draft['step'] = 'target_chat'
            context.user_data['raf_draft'] = draft
            await update.message.reply_text(
                "Шаг 2/5: Отправьте chat_id или ссылку на сообщение в чате, где будет ивент.\n"
                "Примеры:\n"
                "-1003716809697\n"
                "https://t.me/c/1234567890/555"
            )
            return True

        if step == 'duration':
            # Backward compatibility for drafts created before removing duration step.
            draft['duration_hours'] = None
            draft['step'] = 'target_chat'
            context.user_data['raf_draft'] = draft
            step = 'target_chat'

        if step == 'target_chat':
            parsed = await self._parse_raf_chat_target(text)
            if not parsed:
                await update.message.reply_text(
                    "Не удалось распознать чат. Отправьте chat_id или ссылку вида https://t.me/c/<id>/<msg>."
                )
                return True

            draft['target_chat_id'] = int(parsed['chat_id'])
            draft['source_message_link'] = parsed.get('message_link')
            draft['step'] = 'prizes_total'
            context.user_data['raf_draft'] = draft
            await update.message.reply_text("Шаг 3/5: Введите количество призов (1-20).")
            return True

        if step == 'prizes_total':
            try:
                prizes_total = int(text)
            except Exception:
                await update.message.reply_text("Введите целое число от 1 до 20.")
                return True

            if prizes_total < 1 or prizes_total > 20:
                await update.message.reply_text("Количество призов должно быть от 1 до 20.")
                return True

            draft['prizes_total'] = prizes_total
            draft['current_prize_index'] = 1
            draft['step'] = 'prize_text'
            context.user_data['raf_draft'] = draft
            await update.message.reply_text("Шаг 4/5: Введите описание приза #1 (текст или ссылка).")
            return True

        if step == 'prize_text':
            if len(text) < 1:
                await update.message.reply_text("Описание приза не может быть пустым. Введите снова.")
                return True

            draft['current_prize_text'] = text[:1000]
            draft['step'] = 'prize_rarity'
            context.user_data['raf_draft'] = draft
            await update.message.reply_text(
                "Введите редкость для этого приза:\n"
                "срыв, мусор, обычная, редкая, легендарная, аквариумная, мифическая, аномалия"
            )
            return True

        if step == 'prize_rarity':
            rarity_key = self._normalize_raf_rarity(text)
            if not rarity_key or rarity_key not in self.RAF_RARITY_OPTIONS:
                await update.message.reply_text(
                    "Неверная редкость. Допустимо:\n"
                    "срыв, мусор, обычная, редкая, легендарная, аквариумная, мифическая, аномалия"
                )
                return True

            draft['current_prize_rarity'] = rarity_key
            draft['step'] = 'prize_chance'
            context.user_data['raf_draft'] = draft
            await update.message.reply_text("Введите шанс этого приза в процентах (например, 7.5).")
            return True

        if step == 'prize_chance':
            try:
                chance_percent = float(text.replace(',', '.'))
            except Exception:
                await update.message.reply_text("Введите число от 0 до 100 (например, 7 или 7.5).")
                return True

            if chance_percent <= 0 or chance_percent > 100:
                await update.message.reply_text("Шанс должен быть больше 0 и не больше 100.")
                return True

            prizes = draft.get('prizes') or []
            prizes.append(
                {
                    'prize_text': draft.get('current_prize_text'),
                    'rarity_key': draft.get('current_prize_rarity'),
                    'chance_percent': chance_percent,
                }
            )
            draft['prizes'] = prizes
            draft['current_prize_text'] = None
            draft['current_prize_rarity'] = None

            current_idx = int(draft.get('current_prize_index') or 1)
            total = int(draft.get('prizes_total') or 1)
            if current_idx < total:
                draft['current_prize_index'] = current_idx + 1
                draft['step'] = 'prize_text'
                context.user_data['raf_draft'] = draft
                await update.message.reply_text(
                    f"Введите описание приза #{current_idx + 1} (текст или ссылка)."
                )
                return True

            event_id = await _run_sync(db.create_raf_event_draft, creator_user_id=int(draft['creator_user_id']),
                creator_username=update.effective_user.username or update.effective_user.first_name,
                title=str(draft.get('title') or 'RAF Event'),
                target_chat_id=int(draft.get('target_chat_id')),
                source_message_link=draft.get('source_message_link'),
                duration_hours=draft.get('duration_hours'),
                prizes=prizes,
            )
            if not event_id:
                context.user_data.pop('raf_draft', None)
                await update.message.reply_text("❌ Не удалось создать черновик RAF-ивента. Попробуйте снова.")
                return True

            draft['event_id'] = int(event_id)
            draft['step'] = 'await_payment'
            context.user_data['raf_draft'] = draft

            from config import BOT_TOKEN, STAR_NAME
            tg_api = TelegramBotAPI(BOT_TOKEN)
            payload = self._build_raf_create_payload(int(draft['creator_user_id']), int(event_id))

            invoice_url = await tg_api.create_invoice_link(
                title="Создание RAF-ивента",
                description=f"Оплата создания RAF-ивента ({self.RAF_CREATE_COST_STARS} {STAR_NAME})",
                payload=payload,
                currency="XTR",
                prices=[{"label": "Создание RAF-ивента", "amount": self.RAF_CREATE_COST_STARS}],
            )
            if not invoice_url:
                await update.message.reply_text(
                    "❌ Не удалось создать инвойс на оплату. Повторите /raf или отмените через /cancel."
                )
                return True

            await self.send_invoice_url_button(
                chat_id=update.effective_chat.id,
                invoice_url=invoice_url,
                text=(
                    f"✅ Черновик RAF-ивента создан (ID: {event_id}).\n"
                    f"Теперь оплатите {self.RAF_CREATE_COST_STARS} ⭐ для продолжения."
                ),
                user_id=int(draft['creator_user_id']),
                reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
            )
            return True

        if step == 'await_payment':
            await update.message.reply_text(
                "Ожидается оплата создания RAF-ивента. После оплаты я пришлю кнопку 'Начать'.\n"
                "Если хотите прервать создание — /cancel"
            )
            return True

        return False

    async def handle_raf_start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск оплаченного RAF-ивента (кнопка из лички)."""
        query = update.callback_query
        await query.answer()

        parts = (query.data or '').split('_')
        if len(parts) != 4:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        try:
            event_id = int(parts[2])
            owner_id = int(parts[3])
        except (TypeError, ValueError):
            await query.answer("Некорректные данные", show_alert=True)
            return

        user_id = update.effective_user.id
        if user_id != owner_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        event = await _run_sync(db.get_raf_event, event_id)
        if not event or int(event.get('creator_user_id') or 0) != user_id:
            await query.answer("Ивент не найден", show_alert=True)
            return

        activated = await _run_sync(db.activate_raf_event, event_id, user_id)
        if not activated:
            await query.answer("Ивент уже запущен или не оплачен", show_alert=True)
            return

        prizes = await _run_sync(db.get_raf_event_prizes, event_id)
        prizes_text = self._format_raf_prizes_summary(prizes)

        starts_at = activated.get('starts_at') or activated.get('activated_at')
        ends_at = activated.get('ends_at')
        starts_at_text = self._format_raf_datetime(starts_at)
        ends_at_text = self._format_raf_datetime(ends_at) if ends_at else "-"

        event_time_line = f"⏱ Время ивента: с {starts_at_text} по {ends_at_text}"
        if not ends_at:
            event_time_line += " (без ограничения, до выдачи всех призов)"

        announce_text = (
            f"🎉 <b>Стартовал RAF-ивент!</b>\n\n"
            f"🏷 Название: {html.escape(str(activated.get('title') or 'RAF-ивент'))}\n"
            f"{event_time_line}\n\n"
            f"🎁 Призы:\n{prizes_text}\n\n"
            f"🎣 Ловите как обычно. Для каждого приза работает своя редкость и шанс.\n\n"
            f"{html.escape(self.RAF_RESPONSIBILITY_NOTE)}"
        )

        target_chat_id = int(activated.get('target_chat_id'))
        sent_msg = await self._safe_send_message(
            chat_id=target_chat_id,
            text=announce_text,
            parse_mode="HTML",
        )

        if sent_msg:
            await query.edit_message_text(
                f"✅ Ивент запущен и опубликован в чате {target_chat_id}.",
                reply_markup=None,
            )
        else:
            await query.edit_message_text(
                f"⚠️ Ивент запущен, но не удалось отправить анонс в чат {target_chat_id}.\n"
                "Проверьте, что бот есть в чате и имеет право писать.",
                reply_markup=None,
            )

    # --- Safe API wrappers to handle Flood control (RetryAfter) ---
    async def _send_catch_image(self, chat_id: int, item_name: str, item_type: str = "fish", reply_to_message_id: Optional[int] = None) -> Optional[Message]:
        """Универсальный метод для отправки изображения улова (рыба, мусор, сокровище) как документа."""
        from fish_stickers import FISH_STICKERS
        from trash_stickers import TRASH_STICKERS
        from treasures_stickers import TREASURES_STICKERS

        # Нормализация имени (удаление лишних пробелов)
        name = item_name.strip()
        image_file = None

        if item_type == "fish":
            image_file = FISH_STICKERS.get(name)
        elif item_type == "trash":
            image_file = TRASH_STICKERS.get(name)
        elif item_type == "treasure":
            image_files = TREASURES_STICKERS.get(name)
            if image_files:
                image_file = random.choice(image_files) if isinstance(image_files, list) else image_files

        if not image_file:
            logger.debug("_send_catch_image: No image found for '%s' (type=%s)", name, item_type)
            return None

        image_path = Path(__file__).parent / image_file
        if not image_path.exists():
            logger.warning("_send_catch_image: File not found: %s", image_path)
            return None

        cache_key = str(image_path.resolve())

        try:
            cached_file_id = self._telegram_document_file_id_cache.get(cache_key)
            if cached_file_id:
                sent = await self._safe_send_document(
                    chat_id=chat_id,
                    document=cached_file_id,
                    reply_to_message_id=reply_to_message_id
                )
                if sent:
                    return sent
                self._telegram_document_file_id_cache.pop(cache_key, None)

            if True:
                f = await async_file_bytes(image_path)
                # Отправляем именно как документ, как в обычном /fish
                sent = await self._safe_send_document(
                    chat_id=chat_id,
                    document=f,
                    reply_to_message_id=reply_to_message_id
                )
                file_id = getattr(getattr(sent, "document", None), "file_id", None)
                if file_id:
                    self._telegram_document_file_id_cache[cache_key] = file_id
                return sent
        except Exception as e:
            logger.warning("_send_catch_image: Failed to send image '%s': %s", image_file, e)
            return None

    async def _send_document_path_cached(
        self,
        chat_id: int,
        path: Path,
        reply_to_message_id: Optional[int] = None,
    ) -> Optional[Message]:
        cache_key = str(path.resolve())

        cached_file_id = self._telegram_document_file_id_cache.get(cache_key)
        if cached_file_id:
            sent = await self._safe_send_document(
                chat_id=chat_id,
                document=cached_file_id,
                reply_to_message_id=reply_to_message_id,
            )
            if sent:
                return sent
            self._telegram_document_file_id_cache.pop(cache_key, None)

        file_obj = await async_file_bytes(path)
        sent = await self._safe_send_document(
            chat_id=chat_id,
            document=file_obj,
            reply_to_message_id=reply_to_message_id,
        )
        file_id = getattr(getattr(sent, "document", None), "file_id", None)
        if file_id:
            self._telegram_document_file_id_cache[cache_key] = file_id
        return sent

    async def _check_torch_event(self, chat_id: int, user_id: int, username: str, rarity: str, chat_title: Optional[str] = None):
        """Проверка и выдача NFT-призов по редкости улова."""
        EVENT_CHAT_ID = -1003716809697
        ADMIN_ID = 793216884

        prizes_by_rarity = {
            "Редкая": {
                "name": "спасательный круг",
                "emoji": "🛟",
                "chance": 0.07,
                "link": "https://t.me/nft/PoolFloat-66586",
                "flag_prefix": "poolfloat",
            },
            "Легендарная": {
                "name": "рюкзак",
                "emoji": "🎒",
                "chance": 0.10,
                "link": "https://t.me/nft/MoodPack-12309",
                "flag_prefix": "moodpack",
            },
        }

        prize = prizes_by_rarity.get(rarity)
        if chat_id != EVENT_CHAT_ID or not prize:
            return False

        roll = random.random()
        is_winner = roll < float(prize["chance"])
        logger.info(
            "[TORCH_LOG] Prize attempt: chat_id=%s user_id=%s username=%s rarity=%s prize=%s roll=%.4f chance=%.4f winner=%s",
            chat_id,
            user_id,
            username,
            rarity,
            prize["name"],
            roll,
            float(prize["chance"]),
            is_winner,
        )

        if not is_winner:
            return False

        prize_key = f"{prize['flag_prefix']}_won_{chat_id}"
        already_won = await _run_sync(db.get_system_flag, prize_key)
        if already_won == "1":
            logger.info("[TORCH_LOG] Prize %s already won in chat %s. Skipping.", prize_key, chat_id)
            return False

        try:
            await _run_sync(db.set_system_flag, prize_key, "1")
            logger.info("[TORCH_LOG] Flag %s successfully set to 1", prize_key)
        except Exception as e:
            logger.error("[TORCH_LOG] Error setting system flag %s: %s", prize_key, e, exc_info=True)
            return False

        congrats_text = (
            f"{prize['emoji']} <b>Поздравляю! Вы нашли приз: {prize['name']}!</b>\n\n"
            f"🔗 {prize['link']}"
        )
        msg = await self._safe_send_message(chat_id=chat_id, text=congrats_text, parse_mode="HTML")
        if msg:
            logger.info("[TORCH_LOG] Congrats message sent to chat %s for prize %s", chat_id, prize["name"])

        admin_msg = (
            f"{prize['emoji']} <b>ПРИЗ НАЙДЕН!</b>\n\n"
            f"🎁 Приз: {prize['name']}\n"
            f"👤 Пользователь: @{username} (ID: {user_id})\n"
            f"📍 Чат: {chat_title or chat_id} (ID: {chat_id})\n"
            f"🎯 Редкость: {rarity}\n"
            f"🔗 Ссылка: {prize['link']}"
        )
        try:
            await self.application.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")
        except Exception:
            pass

        return True

    async def _safe_send_message(self, **kwargs):
        for attempt in range(3):
            try:
                async with get_send_semaphore():
                    return await self.application.bot.send_message(**kwargs)
            except (BadRequest, Forbidden) as e:
                exc_str = str(e)
                exc_lower = exc_str.lower()
                if any(fragment in exc_str for fragment in ("Not enough rights", "Chat not found", "Forbidden")):
                    return None
                if (
                    kwargs.get('reply_to_message_id') is not None
                    and (
                        "message to be replied not found" in exc_lower
                        or "reply message not found" in exc_lower
                    )
                ):
                    retry_kwargs = dict(kwargs)
                    retry_kwargs.pop('reply_to_message_id', None)
                    logger.info(
                        "_safe_send_message: reply target missing, retrying without reply_to_message_id (chat_id=%s)",
                        kwargs.get('chat_id'),
                    )
                    try:
                        async with get_send_semaphore():
                            return await self.application.bot.send_message(**retry_kwargs)
                    except Exception as retry_exc:
                        logger.warning(
                            "_safe_send_message: fallback without reply_to_message_id failed (chat_id=%s): %s",
                            kwargs.get('chat_id'),
                            retry_exc,
                        )
                        return None
                logger.warning("_safe_send_message: non-retryable error (chat_id=%s): %s", kwargs.get('chat_id'), e)
                return None
            except RetryAfter as e:
                wait = getattr(e, 'retry_after', None) or getattr(e, 'timeout', 1)
                logger.warning("RetryAfter on send_message, waiting %s sec (attempt %s)", wait, attempt + 1)
                await asyncio.sleep(float(wait) + 1)
            except Exception as e:
                # Log full error details to help debug network/timeout issues
                import traceback
                error_details = f"{type(e).__name__}: {str(e)}"
                logger.warning("_safe_send_message: unexpected error (chat_id=%s, attempt %s): %s", 
                               kwargs.get('chat_id'), attempt + 1, error_details)
                
                # If it's a timeout or network error, wait a bit before retrying
                if any(x in error_details.lower() for x in ("timeout", "network", "connection", "reached")):
                    await asyncio.sleep(0.5 * (attempt + 1))
                
                if attempt >= 2:
                    return None
        logger.error("_safe_send_message: failed after retries args=%s", kwargs)
        return None

    async def _safe_send_document(self, **kwargs):
        document = kwargs.get('document')
        if isinstance(document, (str, Path)):
            kwargs['document'] = await async_file_bytes(document)
            document = kwargs.get('document')
        if document:
            try:
                if hasattr(document, 'read'):
                    pos = document.tell()
                    document.seek(0, 2)
                    size = document.tell()
                    document.seek(pos)
                    if size == 0:
                        logger.warning("_safe_send_document: skip empty file object")
                        return None
                elif isinstance(document, (str, Path)):
                    p = Path(document)
                    if p.exists() and p.stat().st_size == 0:
                        logger.warning("_safe_send_document: skip empty file path: %s", document)
                        return None
            except Exception as e:
                logger.warning("_safe_send_document: error checking file size: %s", e)

        for attempt in range(3):
            try:
                if document and hasattr(document, 'seek'):
                    try:
                        document.seek(0)
                    except Exception:
                        pass
                async with get_send_semaphore():
                    return await self.application.bot.send_document(**kwargs)
            except (BadRequest, Forbidden) as e:
                exc_str = str(e)
                exc_lower = exc_str.lower()
                if "File must be non-empty" in exc_str:
                    return None
                if any(fragment in exc_str for fragment in ("Not enough rights", "Chat not found", "Forbidden")):
                    return None
                if (
                    kwargs.get('reply_to_message_id') is not None
                    and (
                        "message to be replied not found" in exc_lower
                        or "reply message not found" in exc_lower
                    )
                ):
                    retry_kwargs = dict(kwargs)
                    retry_kwargs.pop('reply_to_message_id', None)
                    logger.info(
                        "_safe_send_document: reply target missing, retrying without reply_to_message_id (chat_id=%s)",
                        kwargs.get('chat_id'),
                    )
                    try:
                        async with get_send_semaphore():
                            return await self.application.bot.send_document(**retry_kwargs)
                    except Exception as retry_exc:
                        logger.warning(
                            "_safe_send_document: fallback without reply_to_message_id failed (chat_id=%s): %s",
                            kwargs.get('chat_id'),
                            retry_exc,
                        )
                        return None
                logger.warning("_safe_send_document: non-retryable error (chat_id=%s): %s", kwargs.get('chat_id'), e)
                return None
            except RetryAfter as e:
                wait = getattr(e, 'retry_after', None) or getattr(e, 'timeout', 1)
                logger.warning("RetryAfter on send_document, waiting %s sec (attempt %s)", wait, attempt + 1)
                await asyncio.sleep(float(wait) + 1)
            except Exception as e:
                error_details = f"{type(e).__name__}: {str(e)}"
                logger.warning("_safe_send_document: unexpected error (chat_id=%s, attempt %s): %s", 
                               kwargs.get('chat_id'), attempt + 1, error_details)
                if any(x in error_details.lower() for x in ("timeout", "network", "connection", "reached")):
                    await asyncio.sleep(0.5 * (attempt + 1))
                if attempt >= 2:
                    return None
        logger.error("_safe_send_document: failed after retries args=%s", kwargs)
        return None

    async def _safe_send_sticker(self, **kwargs):
        for attempt in range(3):
            try:
                async with get_send_semaphore():
                    return await self.application.bot.send_sticker(**kwargs)
            except (BadRequest, Forbidden) as e:
                exc_str = str(e)
                if any(fragment in exc_str for fragment in ("Not enough rights", "Chat not found", "Forbidden")):
                    return None
                logger.warning("_safe_send_sticker: non-retryable error (chat_id=%s): %s", kwargs.get('chat_id'), e)
                return None
            except RetryAfter as e:
                wait = getattr(e, 'retry_after', None) or getattr(e, 'timeout', 1)
                logger.warning("RetryAfter on send_sticker, waiting %s sec (attempt %s)", wait, attempt + 1)
                await asyncio.sleep(float(wait) + 1)
            except Exception as e:
                error_details = f"{type(e).__name__}: {str(e)}"
                logger.warning("_safe_send_sticker: unexpected error (chat_id=%s, attempt %s): %s", 
                               kwargs.get('chat_id'), attempt + 1, error_details)
                if any(x in error_details.lower() for x in ("timeout", "network", "connection", "reached")):
                    await asyncio.sleep(0.5 * (attempt + 1))
                if attempt >= 2:
                    return None
        logger.error("_safe_send_sticker: failed after retries args=%s", kwargs)
        return None

    async def _safe_edit_message_text(self, **kwargs):
        for attempt in range(3):
            try:
                return await self.application.bot.edit_message_text(**kwargs)
            except (BadRequest, Forbidden) as e:
                if "Message is not modified" in str(e):
                    return None
                logger.warning("_safe_edit_message_text: non-retryable error: %s", e)
                return None
            except RetryAfter as e:
                wait = getattr(e, 'retry_after', None) or getattr(e, 'timeout', 1)
                logger.warning("RetryAfter on edit_message_text, waiting %s sec (attempt %s)", wait, attempt + 1)
                await asyncio.sleep(float(wait) + 1)
            except Exception as e:
                error_details = f"{type(e).__name__}: {str(e)}"
                logger.warning("_safe_edit_message_text: unexpected error (attempt %s): %s", attempt + 1, error_details)
                if any(x in error_details.lower() for x in ("timeout", "network", "connection", "reached")):
                    await asyncio.sleep(0.5 * (attempt + 1))
                if attempt >= 2:
                    return None
        logger.error("_safe_edit_message_text: failed after retries args=%s", kwargs)
        return None

    async def _safe_send_invoice(self, **kwargs):
        for attempt in range(3):
            try:
                return await self.application.bot.send_invoice(**kwargs)
            except (BadRequest, Forbidden) as e:
                exc_str = str(e)
                if any(fragment in exc_str for fragment in ("Not enough rights", "Chat not found", "Forbidden")):
                    return None
                logger.warning("_safe_send_invoice: non-retryable error (chat_id=%s): %s", kwargs.get('chat_id'), e)
                return None
            except RetryAfter as e:
                wait = getattr(e, 'retry_after', None) or getattr(e, 'timeout', 1)
                logger.warning("RetryAfter on send_invoice, waiting %s sec (attempt %s)", wait, attempt + 1)
                await asyncio.sleep(float(wait) + 1)
            except Exception as e:
                error_details = f"{type(e).__name__}: {str(e)}"
                logger.warning("_safe_send_invoice: unexpected error (attempt %s): %s", attempt + 1, error_details)
                if any(x in error_details.lower() for x in ("timeout", "network", "connection", "reached")):
                    await asyncio.sleep(0.5 * (attempt + 1))
                if attempt >= 2:
                    return None
        logger.error("_safe_send_invoice: failed after retries args=%s", kwargs)
        return None

        
    async def cancel_previous_invoice(self, user_id: int):
        """Отменяет предыдущий активный инвойс пользователя"""
        if user_id in self.active_invoices:
            invoice_info = self.active_invoices[user_id]
            chat_id = invoice_info.get('group_chat_id') or invoice_info.get('chat_id')
            message_id = invoice_info.get('group_message_id') or invoice_info.get('message_id') or invoice_info.get('msg_id')
            
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
        try:
            self.scheduler.add_job(
                handle_timeout,
                trigger=DateTrigger(run_date=run_time),
                id=f"timeout_{chat_id}_{message_id}",
                replace_existing=True,
            )
        except Exception as e:
            logger.warning("schedule_timeout: failed to add job for %s: %s", timeout_key, e)
    
    async def heartbeat(self):
        """Периодический heartbeat-лог для мониторинга жизнеспособности бота"""
        try:
            logger.info("[HEARTBEAT] Bot is alive")
        except Exception as e:
            logger.error(f"Error in heartbeat: {e}")
    
    async def auto_recover_rods(self):
        """Автоматически восстанавливает прочность удочек игроков каждые 10 минут"""
        try:
            with await _run_sync(db._connect) as conn:
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
                        # Уведомления в ЛС отключены, чтобы избежать 403 Forbidden
                        logger.info(f"Rod fully recovered for user {user_id}: {rod_name}")
                
                conn.commit()
                logger.info(f"Rod recovery job completed for {len(rods)} rods")
        except Exception as e:
            logger.error(f"Error in auto_recover_rods: {e}")
        
    async def check_global_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pre-handler: блокирует обработку событий во время паузы бота."""
        if not self.is_global_stopped:
            return
            
        from telegram.ext import ApplicationHandlerStop
        
        allowed_chat_id = -1003864313222
        owner_id = self.OWNER_ID
        
        user_id = update.effective_user.id if update.effective_user else None
        chat_id = update.effective_chat.id if update.effective_chat else None
        
        is_allowed = False
        if chat_id == owner_id and user_id == owner_id:
            is_allowed = True
        elif chat_id == allowed_chat_id:
            is_allowed = True
            
        if not is_allowed:
            raise ApplicationHandlerStop()

    async def welcome_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for new members is disabled to avoid auto-greeting."""
        # Greeting new members is intentionally disabled.
        return

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stop (только владелец)"""
        if getattr(update.effective_user, 'id', None) != self.OWNER_ID:
            return
        self.is_global_stopped = True
        await update.message.reply_text("Бот приостановлен во всех чатах (кроме вас и разрешенного). Для возврата введите /start")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        if getattr(self, 'is_global_stopped', False) and getattr(update.effective_user, 'id', None) == self.OWNER_ID:
            self.is_global_stopped = False
            await update.message.reply_text("Бот возобновил работу во всех чатах.")
            
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
            # Добавляем heartbeat-лог каждую минуту
            self.scheduler.add_job(
                self.heartbeat,
                'interval',
                minutes=1,
                id='heartbeat',
                replace_existing=True
            )
            logger.info("AsyncIOScheduler запущен")

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        username = update.effective_user.username or update.effective_user.first_name

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            # Создаем нового игрока
            player = await _run_sync(db.create_player, user_id, username, chat_id)
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
                await _run_sync(db.update_player, user_id, chat_id, **updates)
                player = await _run_sync(db.get_player, user_id, chat_id)
            if player:
                player_rod = await _run_sync(db.get_player_rod, user_id, player['current_rod'], chat_id)
                if not player_rod:
                    if player['current_rod'] in TEMP_ROD_RANGES:
                        await _run_sync(db.update_player, user_id, chat_id, current_rod=BAMBOO_ROD)
                        await _run_sync(db.init_player_rod, user_id, BAMBOO_ROD, chat_id)
                        player = await _run_sync(db.get_player, user_id, chat_id)
                    else:
                        await _run_sync(db.init_player_rod, user_id, player['current_rod'], chat_id)

        await update.message.reply_text(welcome_text)

    async def app_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Временная команда /app: отправляет кнопку открытия Telegram Mini App."""
        message = update.effective_message
        if not message:
            return

        webapp_url = (self.webapp_url or "").strip()
        if not webapp_url:
            await message.reply_text("❌ Mini App URL не настроен. Укажите WEBAPP_URL в окружении.")
            return

        if not re.match(r"^https?://", webapp_url):
            webapp_url = f"https://{webapp_url.lstrip('/')}"

        is_private_chat = (update.effective_chat is not None and update.effective_chat.type == 'private')

        if is_private_chat:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📱 Открыть рыболовную апку", web_app=WebAppInfo(url=webapp_url))]]
            )
            text = "Нажмите кнопку ниже, чтобы открыть мини-апку."
        else:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📱 Открыть рыболовную апку", url=webapp_url)]]
            )
            text = (
                "В группах Telegram WebApp-кнопка может быть недоступна, поэтому отправляю обычную ссылку.\n"
                "Для лучшего UX используйте /app в личном чате с ботом."
            )

        await message.reply_text(text, reply_markup=keyboard)

    async def stars_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin-only command in private chat: list chats and total stars they've brought."""
        admin_id = 793216884
        user_id = update.effective_user.id
        # Restrict to admin
        if user_id != admin_id:
            try:
                await update.message.reply_text("Команда доступна только владельцу бота.")
            except Exception:
                pass
            return

        # Only in private chat
        if update.effective_chat.type != 'private':
            try:
                await update.message.reply_text("Команду используйте в личном чате с ботом.")
            except Exception:
                pass
            return

        try:
            rows = await _run_sync(db.get_all_chat_stars)
        except Exception as e:
            logger.exception("stars_command: db error: %s", e)
            await update.message.reply_text(f"Ошибка БД: {e}", parse_mode=None)
            return

        # Only show chats that have stars AND a real chat title (not @username, not empty)
        def _is_real_title(r):
            if (r.get('stars_total') or 0) <= 0:
                return False
            t = (r.get('chat_title') or '').strip()
            if not t:
                return False          # no title stored
            if t.startswith('@'):
                return False          # username-only, not a group name
            return True

        rows = [r for r in rows if _is_real_title(r)]

        if not rows:
            await update.message.reply_text("Нет данных по звёздам.", parse_mode=None)
            return

        total_stars = sum((r.get('stars_total') or 0) for r in rows)
        lines = []
        for r in rows:
            title = (r.get('chat_title') or '').strip()
            stars = r.get('stars_total') or 0
            lines.append(f"{title} — {stars}")

        header = f"Всего звёзд: {total_stars}\n\n"
        full_text = header + "\n".join(lines)

        # If text fits in one Telegram message (4096 bytes), send as text; otherwise as file
        if len(full_text.encode('utf-8')) <= 4000:
            try:
                await update.message.reply_text(full_text, parse_mode=None)
            except Exception as e:
                logger.exception("stars_command: send error: %s", e)
        else:
            import io
            file_bytes = full_text.encode('utf-8')
            bio = io.BytesIO(file_bytes)
            bio.name = "stars.txt"
            try:
                await update.message.reply_document(
                    document=bio,
                    filename="stars.txt",
                    caption=f"⭐ Всего звёзд: {total_stars} — {len(rows)} чатов",
                )
            except Exception as e:
                logger.exception("stars_command: send file error: %s", e)

    def _sync_player_username_if_changed(
        self,
        user_id: int,
        chat_id: int,
        player: Optional[Dict[str, Any]],
        current_username: str,
    ) -> None:
        """Обновляет только username в профиле, если он изменился в Telegram."""
        if not player:
            return

        new_username = (current_username or "").strip() or str(user_id)
        old_username = str(player.get('username') or "").strip()

        if old_username == new_username:
            return

        try:
            db.update_player(user_id, chat_id, username=new_username)
            player['username'] = new_username
            logger.info(
                "Username synced for user_id=%s chat_id=%s: '%s' -> '%s'",
                user_id,
                chat_id,
                old_username,
                new_username,
            )
        except Exception:
            logger.exception("Failed to sync username for user_id=%s chat_id=%s", user_id, chat_id)
    
    async def fish_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(
            "/fish received: user=%s chat=%s",
            getattr(update.effective_user, "id", None),
            getattr(update.effective_chat, "id", None),
        )
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
        current_username = update.effective_user.username or update.effective_user.first_name or str(user_id)
        
        # Получаем весь контекст за один запрос к БД
        context_data = await _run_sync(db.get_fishing_context, user_id, chat_id)
        player = context_data.get('player')
        effects = context_data.get('effects', {})
        active_boat = context_data.get('active_boat')
        has_antibot_block = context_data.get('has_antibot_block')

        if not player:
            # Автоматически создаём профиль в этом чате при первом использовании /fish
            try:
                player = await _run_sync(db.create_player, user_id, current_username, chat_id)
                await update.message.reply_text("✅ Профиль создан автоматически для этого чата. Продолжаем рыбалку...")
            except Exception as e:
                logger.error(f"Error creating player from fish command: {e}")
                try:
                    await update.message.reply_text("Сначала создайте профиль командой /start")
                except Exception as e:
                    logger.error(f"Error replying to fish command: {e}")
                return

        await _run_sync(self._sync_player_username_if_changed, user_id, chat_id, player, current_username)

        # Проверка на алкогольное опьянение
        if 'beer' in effects:
            await update.message.reply_text(self._generate_drunk_gibberish())
            return

        # Проверка на морскую болезнь
        if 'seasick' in effects:
            # Проверяем, на лодке ли человек. Если нет - морская болезнь должна пройти.
            if not active_boat:
                await _run_sync(db.clear_timed_effect, user_id, 'seasick')
            else:
                remaining_seconds = int(effects['seasick'])
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60
                time_str = f"{minutes} мин {seconds} сек" if minutes > 0 else f"{seconds} сек"
                await update.message.reply_text(
                    f"🤢 Вас укачало в плавании. Ловить сейчас нельзя.\n"
                    f"Осталось: {time_str}\n\n"
                    "Используйте /cure_seasick или кнопку лечения в меню лодки."
                )
                return

        if has_antibot_block:
            # Если в БД есть подозрение на блок, получаем полный объект блока (с текстом и кнопками)
            antibot_active_block = await _run_sync(self._get_antibot_active_block, user_id, update)
            if antibot_active_block:
                await self._send_antibot_block_to_user(update, antibot_active_block)
                return

        # Проверяем кулдаун
        can_fish, message = await _run_sync(game.can_fish, user_id, chat_id)
        if not can_fish:
            # Если удочка сломалась — предлагаем ремонт за 20 ⭐ (НЕ платный заброс)
            if "сломалась" in message:
                rod_name = player['current_rod']
                if rod_name in TEMP_ROD_RANGES:
                    # Временная/одноразовая удочка — просто купить новую
                    await update.message.reply_text(f"💥 {message}")
                    return
                # Бамбуковая / обычная удочка — предлагаем ремонт за 20 ⭐
                from config import BOT_TOKEN
                try:
                    from bot import TelegramBotAPI as _TelegramBotAPI
                    tg_api = _TelegramBotAPI(BOT_TOKEN)
                    repair_invoice_url = await tg_api.create_invoice_link(
                        title="Ремонт удочки",
                        description=f"Полное восстановление прочности удочки '{rod_name}'",
                        payload=f"repair_rod_{rod_name}",
                        currency="XTR",
                        prices=[{"label": f"Ремонт {rod_name}", "amount": 20}]
                    )
                    logger.info(f"[INVOICE] Repair invoice created for rod='{rod_name}' user={user_id}")
                except Exception as e:
                    logger.error(f"[INVOICE] Failed to create repair invoice: {e}")
                    repair_invoice_url = None
                if repair_invoice_url:
                    await self.send_invoice_url_button(
                        chat_id=chat_id,
                        invoice_url=repair_invoice_url,
                        text=(
                            "💔 Ваша удочка сломалась!\n\n"
                            "🔧 Оплатите 20 ⭐ Telegram Stars чтобы мгновенно восстановить её.\n"
                            "Или используйте /repair для бесплатного автовосстановления (займёт время)."
                        ),
                        user_id=user_id,
                        reply_to_message_id=update.effective_message.message_id if update.effective_message else None
                    )
                else:
                    await update.message.reply_text(
                        f"💔 {message}\n\nИспользуйте /repair для восстановления.",
                        parse_mode=None
                    )
                return
            # Кулдаун — обычная кнопка гарантированного улова за 1 ⭐
            from config import BOT_TOKEN, STAR_NAME
            import traceback
            invoice_error = None
            try:
                from bot import TelegramBotAPI as _TelegramBotAPI
                tg_api = _TelegramBotAPI(BOT_TOKEN)
                invoice_url = await tg_api.create_invoice_link(
                    title=f"Гарантированный улов",
                    description=f"Гарантированный улов — подтвердите оплату (1 {STAR_NAME})",
                    payload=f"guaranteed_{user_id}_{chat_id}_{int(datetime.now().timestamp())}",
                    currency="XTR",
                    prices=[{"label": f"Вход", "amount": 1}]
                )
                logger.info(f"[INVOICE] Got invoice_url: {invoice_url}")
            except Exception as e:
                logger.error(f"[INVOICE] Failed to get invoice_url: {e}")
                invoice_url = None
                invoice_error = str(e) + "\n" + traceback.format_exc()
            if invoice_url:
                await self.send_invoice_url_button(
                    chat_id=chat_id,
                    invoice_url=invoice_url,
                    text=f"⏰ {message}\n\n⭐ Оплатите 1 Telegram Stars для гарантированного улова на локации: {player['current_location']}",
                    user_id=user_id,
                    reply_to_message_id=update.effective_message.message_id if update.effective_message else None
                )
            else:
                error_text = f"⏰ {message}\n\n(Ошибка генерации ссылки для оплаты)"
                if invoice_error:
                    error_text += f"\nОшибка: {invoice_error}"
                await update.message.reply_text(error_text, parse_mode=None)
            return

        antibot_rhythm_block = await _run_sync(self._register_free_fish_attempt_and_check_antibot, user_id, update)
        if antibot_rhythm_block:
            await self._send_antibot_block_to_user(update, antibot_rhythm_block)
            return


        # --- Boat trip state handled implicitly by game.fish and main block below ---

        # --- Обычная рыбалка ---
        try:
            # Обновляем состояние популяции рыб (отслеживаем забросы на локации)
            location_changed, consecutive_casts, show_warning = await _run_sync(
                db.update_population_state,
                user_id,
                player['current_location']
            )

            # Если игрок достиг 30 отдельных забросов на одной локации - показываем предупреждение
            if show_warning:
                warning_msg = (
                    "⚠️ <b>ВАЖНО! РЫБЫ ОСТАЛОСЬ МАЛО!</b>\n\n"
                    "Вы 30 раз подряд ловили на одной локации.\n"
                    "Рыба испугалась и её осталось мало в этом месте.\n\n"
                    "🗺️ <b>Смените локацию!</b>\n"
                    "Используйте /menu для выбора другого места.\n\n"
                    "Как снять штраф:\n"
                    "• Не ловить 60 минут\n"
                    "• Или сменить локацию и сделать 10 забросов на новой\n\n"
                    "Если продолжите ловить на одной локации, шансы будут падать:\n"
                    "• 30 забросов: -5%\n"
                    "• 40 забросов: -8%\n"
                    "• 50 забросов: -11%\n"
                    "• 60+ забросов: -15%"
                )
                try:
                    await update.message.reply_text(warning_msg)
                except Exception as e:
                    logger.error(f"Error sending population warning: {e}")

            result = await _run_sync(game.fish, user_id, chat_id, player['current_location'])

            storm_result = await self._maybe_trigger_boat_storm(user_id, result)
            if storm_result and storm_result.get('applied'):
                await update.message.reply_text(self._format_storm_event_message(storm_result), parse_mode=None)
                return

            try:
                raf_won = await self._process_raf_event_roll(
                    chat_id=chat_id,
                    user_id=user_id,
                    username=update.effective_user.username or update.effective_user.first_name,
                    chat_title=update.effective_chat.title,
                    result=result,
                    trigger_source='fish_command',
                )
                if raf_won:
                    return
            except Exception:
                logger.exception("RAF roll failed in /fish flow user=%s chat=%s", user_id, chat_id)

        except Exception as e:
            logger.exception("Unhandled exception in game.fish for user %s chat %s", user_id, chat_id)
            try:
                await update.message.reply_text("❌ Неожиданная ошибка при рыбалке. Обратитесь в поддержку.")
            except Exception:
                pass
            return

        if result.get('fight_required'):
            started = await self._start_fight_session(
                update=update,
                context=context,
                result=result,
                source_type='fish_command',
                source_ref=str(player.get('current_location') or ''),
                reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
            )
            if started:
                return

            # Fallback: если не удалось отправить кнопки борьбы, выдаём улов напрямую.
            result = game.finalize_fight_catch(
                user_id=user_id,
                chat_id=chat_id,
                location=str(result.get('location') or player.get('current_location') or ''),
                fish_data=result.get('fish') or {},
                weight=float(result.get('weight') or 0),
                length=float(result.get('length') or 0),
                target_rarity=result.get('target_rarity'),
                guaranteed=False,
            )

        tickets_awarded, tickets_jackpot, tickets_total = self._award_tickets(
            user_id,
            self._calculate_tickets_for_result(result),
            username=current_username,
            source_type='fish_command',
            source_ref=str(player.get('current_location') or ''),
        )
        tickets_line = self._format_tickets_award_line(tickets_awarded, tickets_jackpot, tickets_total)

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
                trash = result.get('trash') or {}
                trash_name_for_duel = str(trash.get('name') or 'Мусор')
                try:
                    trash_weight_for_duel = float(trash.get('weight') or 0)
                except (TypeError, ValueError):
                    trash_weight_for_duel = 0.0

                # If second roll produced a treasure, show only treasure output.
                if result.get('treasure_caught') and result.get('treasure_name'):
                    from treasures import get_treasure_name, get_treasure_price

                    treasure_name = result['treasure_name']
                    treasure_display_name = get_treasure_name(treasure_name)
                    treasure_price = get_treasure_price(treasure_name)

                    treasure_message_text = f"""
✨ Чудо случилось! Между мусором ты нашёл драгоценность! ✨

{treasure_display_name}

💎 Стоимость: {treasure_price} 🪙
📍 Место: {result['location']}
{tickets_line}
                    """

                    # Отправляем параллельно
                    sticker_task = asyncio.create_task(self._send_catch_image(
                        chat_id=update.effective_chat.id,
                        item_name=treasure_name,
                        item_type="treasure",
                        reply_to_message_id=update.message.message_id
                    ))
                    
                    message_task = asyncio.create_task(update.message.reply_text(
                        treasure_message_text,
                        reply_to_message_id=update.message.message_id
                    ))
                    
                    await asyncio.gather(sticker_task, message_task)

                    if result.get('temp_rod_broken'):
                        await update.message.reply_text(
                            "💥 Временная удочка сломалась после удачного улова.\n"
                            "Теперь активна бамбуковая. Купить новую можно в магазине."
                        )

                    try:
                        await self._maybe_process_duel_catch(
                            user_id=user_id,
                            chat_id=chat_id,
                            fish_name=trash_name_for_duel,
                            weight=trash_weight_for_duel,
                            length=0.0,
                            catch_id=None,
                            resolve_latest_catch=False,
                        )
                    except Exception:
                        logger.exception("Failed to process duel trash from /fish user=%s chat=%s", user_id, chat_id)
                    return

                trash = result['trash']
                xp_line = ""
                progress_line = ""
                if result.get('xp_earned'):
                    xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                    progress_line = f"\n{format_level_progress(result.get('level_info'))}"

                eco_line = ""
                eco = result.get('eco_disaster') or {}
                if eco:
                    reward_type = str(result.get('reward_type') or eco.get('reward_type') or 'xp').lower()
                    multiplier = int(result.get('reward_multiplier') or eco.get('reward_multiplier') or 1)
                    reward_name = "опыт" if reward_type == 'xp' else "монеты"
                    eco_line = f"\n🌪️ Эко-катастрофа: x{multiplier} на {reward_name}"

                bonus_line = ""
                earned_bonus = int(result.get('earned') or 0)
                if earned_bonus > 0:
                    bonus_line = f"\n💰 Бонус за событие: +{earned_bonus} 🪙"

                storage_line = "\n📦 Мусор добавлен в садок лодки" if result.get('is_on_boat') else "\n📦 Мусор добавлен в инвентарь"

                message = f"""
{trash.get('name', 'Мусор')}

⚖️ Вес: {trash.get('weight', 0)} кг
💰 Цена при продаже: {trash.get('price', 0)} 🪙
📍 Место: {result['location']}
{xp_line}{progress_line}{eco_line}{bonus_line}{storage_line}{tickets_line}
                """

                # Отправляем параллельно
                sticker_task = asyncio.create_task(self._send_catch_image(
                    chat_id=update.effective_chat.id,
                    item_name=trash.get('name', ''),
                    item_type="trash",
                    reply_to_message_id=update.message.message_id
                ))
                
                message_task = asyncio.create_task(update.message.reply_text(
                    message,
                    reply_to_message_id=update.message.message_id
                ))
                
                sticker_message, text_message = await asyncio.gather(sticker_task, message_task)
                
                if sticker_message:
                    context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id

                # Если на лодке — доп проверки
                if result.get('is_on_boat'):
                    # Проверка на крушение
                    if await _run_sync(db.check_boat_crash, user_id):
                        await update.message.reply_text("💥 <b>КРУШЕНИЕ!</b> Лодка не выдержала веса мусора и сломалась! Весь улов текущего плавания утерян.")
                    else:
                        # Предупреждение о малом весе
                        left = await _run_sync(db.check_boat_weight_warning, user_id)
                        if left is not None and left < 50:
                            await update.message.reply_text(f"⚠️ <b>ВНИМАНИЕ!</b> Лодка почти полна. Осталось места: {left:.1f} кг")

                if result.get('temp_rod_broken'):
                    await update.message.reply_text(
                        "💥 Временная удочка сломалась после удачного улова.\n"
                        "Теперь активна бамбуковая. Купить новую можно в магазине."
                    )

                try:
                    await self._maybe_process_duel_catch(
                        user_id=user_id,
                        chat_id=chat_id,
                        fish_name=trash_name_for_duel,
                        weight=trash_weight_for_duel,
                        length=0.0,
                        catch_id=None,
                        resolve_latest_catch=False,
                    )
                except Exception:
                    logger.exception("Failed to process duel trash from /fish user=%s chat=%s", user_id, chat_id)
                return

            fish = result['fish']
            weight = result['weight']
            length = result['length']
            fish_price = result.get('fish_price', fish.get('price', 0))

            # Проверка NFT-приза события только для обычной рыбалки (/fish).
            try:
                rolled_rarity = result.get('target_rarity')
                caught_rarity = fish.get('rarity', '')
                if rolled_rarity and caught_rarity and rolled_rarity != caught_rarity:
                    logger.info(
                        "[TORCH_LOG] Rarity mismatch (/fish): user_id=%s chat_id=%s location=%s rolled=%s caught=%s",
                        user_id,
                        update.effective_chat.id,
                        result.get('location'),
                        rolled_rarity,
                        caught_rarity,
                    )
                prize_rarity = caught_rarity or rolled_rarity or ''
                torch_won = await self._check_torch_event(
                    chat_id=update.effective_chat.id,
                    user_id=user_id,
                    username=update.effective_user.username or update.effective_user.first_name,
                    rarity=prize_rarity,
                    chat_title=update.effective_chat.title
                )
                if torch_won:
                    return
            except Exception as e:
                logger.error(f"Error in torch event check (/fish): {e}")

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
                'Легендарная': '🟡',
                'Мифическая': '🔴'
            }
            fish_name_display = format_fish_name(fish['name'])
            
            xp_line = ""
            progress_line = ""
            if result.get('xp_earned'):
                xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                progress_line = f"\n{format_level_progress(result.get('level_info'))}"

            message = f"""
🎉 Поздравляю! Вы поймали рыбу!
{rarity_emoji.get(fish['rarity'], '⚪')} {fish_name_display}
📏 Размер: {length}см | Вес: {weight} кг
💰 Стоимость: {fish_price} 🪙
📍 Место: {result['location']}
⭐ Редкость: {fish['rarity']}{xp_line}{progress_line}{tickets_line}"""

            if result.get('is_on_boat'):
                message += "\n⛵ <b>Рыба добавлена в лодку!</b> (Её раздаст владелец по возвращении)"
                # Если на лодке, продать нельзя
            else:
                message += "\n\nВы можете продать эту рыбу в лавке! 🐟"
            
            if result.get('guaranteed'):
                message += "\n⭐ Гарантированный улов!"

            # Если на лодке — доп проверки
            if result.get('is_on_boat'):
                # Проверка на крушение
                if await _run_sync(db.check_boat_crash, user_id):
                    message += "\n\n💥 <b>КРУШЕНИЕ!</b> Лодка не выдержала веса и сломалась! Весь улов текущего плавания утерян."
                else:
                    # Предупреждение о малом весе
                    left = await _run_sync(db.check_boat_weight_warning, user_id)
                    if left is not None and left < 50:
                        message += f"\n\n⚠️ <b>ВНИМАНИЕ!</b> Лодка почти полна. Осталось места: {left:.1f} кг"

            # Добавляем примечание о популяции (дебафф при частых забросах на одной локации)
            population_penalty = result.get('population_penalty', 0)
            consecutive_casts_count = result.get('consecutive_casts', 0)
            if consecutive_casts_count >= 30 and population_penalty > 0:
                penalty_info = (
                    f"\n⚠️ Популяция рыб снижена на {int(population_penalty)}%\n"
                    f"Забросов подряд: {consecutive_casts_count}/∞"
                )
                message += penalty_info
            
            # Отправляем изображение рыбы и текст ПАРАЛЛЕЛЬНО для ускорения реакции
            sticker_task = asyncio.create_task(self._send_catch_image(
                chat_id=update.effective_chat.id,
                item_name=fish['name'],
                item_type="fish",
                reply_to_message_id=update.message.message_id
            ))
            
            message_task = asyncio.create_task(update.message.reply_text(
                message,
                reply_to_message_id=update.message.message_id
            ))
            
            sticker_message, text_message = await asyncio.gather(sticker_task, message_task)
            
            if sticker_message:
                context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                context.bot_data.setdefault("sticker_fish_map", {})[sticker_message.message_id] = {
                    "fish_name": fish['name'],
                    "weight": weight,
                    "price": fish_price,
                    "location": result['location'],
                    "rarity": fish['rarity']
                }

            try:
                await self._maybe_process_duel_catch(
                    user_id=user_id,
                    chat_id=chat_id,
                    fish_name=fish.get('name', 'Неизвестная рыба'),
                    weight=weight,
                    length=length,
                )
            except Exception:
                logger.exception("Failed to process duel catch from /fish user=%s chat=%s", user_id, chat_id)

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
            elif result.get('is_trash') or result.get('no_bite') or result.get('snap'):
                # Мусор или неудачный заброс — предлагаем гарантированный улов
                sticker_message = None
                duel_attempt_name = "Неудачный заброс"
                duel_attempt_weight = 0.0
                if result.get('is_trash'):
                    xp_line = ""
                    progress_line = ""
                    if result.get('xp_earned'):
                        xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                        progress_line = f"\n{format_level_progress(result.get('level_info'))}"

                    eco_line = ""
                    eco = result.get('eco_disaster') or {}
                    if eco:
                        reward_type = str(result.get('reward_type') or eco.get('reward_type') or 'xp').lower()
                        multiplier = int(result.get('reward_multiplier') or eco.get('reward_multiplier') or 1)
                        reward_name = "опыт" if reward_type == 'xp' else "монеты"
                        eco_line = f"\n🌪️ Эко-катастрофа: x{multiplier} на {reward_name}"

                    bonus_line = ""
                    bonus_coins = int(result.get('earned') or 0)
                    if bonus_coins > 0:
                        bonus_line = f"\n💰 Бонус за событие: +{bonus_coins} 🪙"

                    storage_line = "\n📦 Мусор добавлен в садок лодки" if result.get('is_on_boat') else "\n📦 Мусор добавлен в инвентарь"

                    message = f"""{result['message']}

📦 Мусор: {result['trash']['name']}
⚖️ Вес: {result['trash']['weight']} кг
💰 Цена при продаже: {result['trash'].get('price', 0)} 🪙{xp_line}{progress_line}{eco_line}{bonus_line}{storage_line}{tickets_line}
                    """
                    duel_attempt_name = str(result.get('trash', {}).get('name') or 'Мусор')
                    try:
                        duel_attempt_weight = float(result.get('trash', {}).get('weight') or 0)
                    except (TypeError, ValueError):
                        duel_attempt_weight = 0.0
                    # Отправляем фото мусора если оно есть
                    try:
                        trash_name = result['trash']['name']
                        if trash_name in TRASH_STICKERS:
                            trash_image = TRASH_STICKERS[trash_name]
                            image_path = Path(__file__).parent / trash_image
                            if image_path.exists():
                                sticker_message = await self._send_document_path_cached(
                                    chat_id=update.effective_chat.id,
                                    path=image_path,
                                    reply_to_message_id=update.message.message_id,
                                )
                                if sticker_message:
                                    context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id
                    except Exception as e:
                        logger.warning(f"Could not send trash image: {e}")
                else:
                    message = f"😔 {result['message']}{tickets_line}"
                    if result.get('no_bite'):
                        duel_attempt_name = "Ничего не клюет"

                if not result.get('snap'):
                    try:
                        await self._maybe_process_duel_catch(
                            user_id=user_id,
                            chat_id=chat_id,
                            fish_name=duel_attempt_name,
                            weight=duel_attempt_weight,
                            length=0.0,
                            catch_id=None,
                            resolve_latest_catch=False,
                        )
                    except Exception:
                        logger.exception("Failed to process duel non-fish attempt from /fish user=%s chat=%s", user_id, chat_id)

                from config import BOT_TOKEN, STAR_NAME
                try:
                    from bot import TelegramBotAPI as _TelegramBotAPI
                    tg_api = _TelegramBotAPI(BOT_TOKEN)
                    # Кодируем локацию
                    loc = result.get('location', 'Unknown').replace(' ', '_')
                    payload = f"guaranteed_{user_id}_{chat_id}_{int(datetime.now().timestamp())}_{loc}"
                    
                    invoice_url = await tg_api.create_invoice_link(
                        title="Гарантированный улов",
                        description=f"Гарантированный улов (1 {STAR_NAME})",
                        payload=payload,
                        currency="XTR",
                        prices=[{"label": "Вход", "amount": 1}]
                    )
                except Exception as e:
                    logger.error(f"[INVOICE] Failed: {e}")
                    invoice_url = None

                if invoice_url:
                    await self.send_invoice_url_button(
                        chat_id=chat_id,
                        invoice_url=invoice_url,
                        text=f"{message}\n\n⭐ Оплатите 1 Telegram Stars для гарантированного улова!",
                        user_id=user_id,
                        reply_to_message_id=(
                            sticker_message.message_id
                            if result.get('is_trash') and sticker_message
                            else (update.effective_message.message_id if update.effective_message else None)
                        )
                    )
                else:
                    await update.message.reply_text(f"{message}\n\n(Ошибка генерации ссылки для оплаты)")
                return
            else:
                # Если арест рыбнадзора — не показываем кнопку платного заброса
                if result.get('fish_inspector') or "рыбнадзор" in result.get('message', '').lower():
                    # Стикер рыбнадзора — только при свежем аресте (не при повторных попытках)
                    if result.get('fish_inspector'):
                        try:
                            inspector_image = FISH_STICKERS.get("Рыбнадзор")
                            if inspector_image:
                                image_path = Path(__file__).parent / inspector_image
                                if image_path.exists():
                                    await self._send_document_path_cached(
                                        chat_id=update.effective_chat.id,
                                        path=image_path,
                                        reply_to_message_id=update.message.message_id,
                                    )
                        except Exception as e:
                            logger.warning(f"Could not send fish inspector sticker: {e}")

                    await update.message.reply_text(
                        self._sanitize_public_service_text(result.get('message', '')), 
                        parse_mode=None,
                    )
                    return
                # Отправляем сообщение с причиной и кнопкой оплаты
                reply_markup = await self._build_guaranteed_invoice_markup(user_id, chat_id)
                invoice_msg = await update.message.reply_text(
                    f"😔 {result['message']}",
                    reply_markup=reply_markup
                )
                if reply_markup and invoice_msg:
                    self._store_active_invoice_context(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_id=invoice_msg.message_id,
                    )
                return
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /menu - показать меню рыбалки"""
        # Команда работает только в группах/каналах, не в личных чатах
        if update.effective_chat.type == 'private':
            await update.message.reply_text("Команда /menu работает только в чатах с группой. Для платежей проверьте входящие инвойсы.")
            return
        
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, update.effective_user.id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        await self.show_fishing_menu(update, context)

    async def show_fishing_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню рыбалки"""
        if self._is_restricted_and_block(update.effective_chat.id):
            return
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            if update.message:
                await update.message.reply_text("Сначала создайте профиль командой /start")
            else:
                await update.callback_query.answer("Сначала создайте профиль командой /start", show_alert=True)
            return

        rod_name = player['current_rod']
        player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
        if not player_rod:
            if rod_name in TEMP_ROD_RANGES:
                await _run_sync(db.update_player, user_id, chat_id, current_rod=BAMBOO_ROD)
                await _run_sync(db.init_player_rod, user_id, BAMBOO_ROD, chat_id)
                player = await _run_sync(db.get_player, user_id, chat_id)
                rod_name = player['current_rod']
                player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
            else:
                await _run_sync(db.init_player_rod, user_id, rod_name, chat_id)
                player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
        durability_line = ""
        if player_rod and rod_name == BAMBOO_ROD:
            durability_line = f"🔧 Прочность: {player_rod['current_durability']}/{player_rod['max_durability']}\n"

        diamond_count = player.get('diamonds', 0)
        tickets_count = player.get('tickets', 0)
        menu_text = f"""
    {FISHING_EMOJI_TAG} Меню рыбалки

    {COIN_EMOJI_TAG} Монеты: {html.escape(str(player['coins']))} {html.escape(COIN_NAME)}
    {DIAMOND_EMOJI_TAG} Бриллианты: {html.escape(str(diamond_count))}
    🎟 Билеты: {html.escape(str(tickets_count))}
    {FISHING_EMOJI_TAG} Удочка: {html.escape(str(player['current_rod']))}
    {LOCATION_EMOJI_TAG} Локация: {html.escape(str(player['current_location']))}
    {WORM_EMOJI_TAG} Наживка: {html.escape(str(player['current_bait']))}
    {durability_line}
        """


        # --- ЛОДОЧНОЕ МЕНЮ ---
        boat = await _run_sync(db.get_user_boat, user_id)
        is_active = boat.get('is_active', 0) if boat else 0
        members_count = await _run_sync(db.get_boat_members_count, boat['id']) if boat else 1
        capacity = boat.get('capacity', 1) if boat else 1
        boat_line = f"\n⛵ Лодка: {boat['name']} ({members_count}/{capacity})\nВес: {boat.get('current_weight', 0):.1f}/{boat.get('max_weight', 0):.1f} кг" if boat else ""
        menu_text += boat_line

        keyboard = [
            [InlineKeyboardButton("🎣 Начать рыбалку", callback_data=f"start_fishing_{user_id}")],
            [InlineKeyboardButton("📍 Сменить локацию", callback_data=f"change_location_{user_id}")],
            [InlineKeyboardButton("🪱 Сменить наживку", callback_data=f"change_bait_{user_id}")],
        ]

        # Проверяем количество рыбы
        fish_count = await _run_sync(db.count_caught_fish, user_id)
        webapp_url = os.getenv("WEBAPP_URL", "https://fish.monkeysdynasty.website")

        if fish_count > 15:
            keyboard.append([InlineKeyboardButton("📱 Управление (Лавка/Инвентарь)", web_app=WebAppInfo(url=webapp_url))])
            menu_text += f"\n\n⚠️ У вас много рыбы ({fish_count} шт). Для продажи и управления инвентарем используйте наше Mini App!"
        else:
            keyboard.append([InlineKeyboardButton("🧺 Лавка", callback_data=f"sell_fish_{user_id}"), InlineKeyboardButton("🛒 Магазин", callback_data=f"shop_{user_id}")])
            keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data=f"stats_{user_id}"), InlineKeyboardButton("🎒 Инвентарь", callback_data=f"inventory_{user_id}")])
            keyboard.append([InlineKeyboardButton("🏆 Трофеи", callback_data=f"inv_trophies_{user_id}")])
        # Кнопки лодки
        if is_active:
            # В плавании
            if boat and boat.get('user_id') == user_id:
                keyboard.insert(0, [
                    InlineKeyboardButton("⏹️ Вернуться", callback_data=f"boat_return_{user_id}")
                ])
            else:
                keyboard.insert(0, [InlineKeyboardButton("⛵ В плавании", callback_data=f"boat_in_trip_{user_id}")])
        else:
            # Не плывёт: кнопка выплыть
            keyboard.insert(0, [
                InlineKeyboardButton(f"▶️ Выплыть ({members_count}/{capacity})", callback_data=f"boat_start_{user_id}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode="HTML")

    async def handle_skip_boat_cooldown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сброса КД лодки по кнопке в меню."""
        query = update.callback_query
        user_id = update.effective_user.id
        if not query or not str(query.data or "").endswith(f"_{user_id}"):
            if query:
                await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        price = 20  # Цена сброса КД (пример)
        ok = await _run_sync(db.skip_boat_cooldown, user_id, price)
        if ok:
            await update.callback_query.answer(f"⏩ КД лодки сброшен за {price} ⭐!", show_alert=True)
            await self.show_fishing_menu(update, context)
        else:
            await update.callback_query.answer("❌ Не удалось сбросить КД лодки. Возможно, нет КД или не хватает звёзд.", show_alert=True)

    async def handle_cure_seasick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка лечения морской болезни по кнопке в меню."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if not query or not str(query.data or "").endswith(f"_{user_id}"):
            if query:
                await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        price = 15  # Цена лечения 15 звезд
        
        try:
            from bot import TelegramBotAPI as _TelegramBotAPI
            tg_api = _TelegramBotAPI(BOT_TOKEN)
            invoice_url = await tg_api.create_invoice_link(
                title="Лечение морской болезни",
                description=f"Мгновенное излечение от морской болезни ({price} {STAR_NAME})",
                payload=f"cure_seasick_{user_id}",
                currency="XTR",
                prices=[{"label": "Лечение", "amount": price}]
            )
            
            if invoice_url:
                await query.answer()
                await self.send_invoice_url_button(
                    chat_id=chat_id,
                    invoice_url=invoice_url,
                    text=f"🚑 Вас сильно укачало? Оплатите {price} {STAR_NAME}, чтобы мгновенно прийти в себя и продолжить рыбалку!",
                    user_id=user_id,
                    reply_to_message_id=query.message.message_id
                )
            else:
                await query.answer("❌ Не удалось создать ссылку на оплату.", show_alert=True)
        except Exception as e:
            logger.error(f"[INVOICE] Failed to create cure_seasick invoice from menu: {e}")
            await query.answer("❌ Ошибка при создании инвойса.", show_alert=True)

    async def _build_menu_reply(self, update, menu_text, reply_markup):
        if update.message:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode="HTML")

    async def handle_boat_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки Выплыть"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if not query or not str(query.data or "").endswith(f"_{user_id}"):
            if query:
                await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        async def _process_boat_start() -> None:
            try:
                can_start, cd = await _run_sync(db.can_start_boat_trip, user_id)
                if can_start:
                    await _run_sync(db.start_boat_trip, user_id)
                    await self.show_fishing_menu(update, context)
                    return

                hours = int(cd // 3600)
                minutes = int((cd % 3600) // 60)
                reply_markup = await self._build_skip_boat_cd_invoice_markup(user_id, chat_id)
                await query.edit_message_text(
                    f"⏳ Следующий бесплатный выплыв через: {hours}ч {minutes}м.\n\n"
                    f"💸 Хотите выплыть прямо сейчас за 20 ⭐?",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            except Exception:
                logger.exception("handle_boat_start failed for user=%s chat=%s", user_id, chat_id)
                try:
                    await query.edit_message_text("❌ Не удалось обработать выплыв. Попробуйте позже.")
                except Exception:
                    pass

        asyncio.create_task(_process_boat_start())
        return

    async def handle_boat_return(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки Вернуться (делёж улова)"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id if update.effective_chat else 0
        if not query or not str(query.data or "").endswith(f"_{user_id}"):
            if query:
                await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        logger.info("[boat] Return requested: user_id=%s chat_id=%s", user_id, chat_id)
        try:
            results, boat_id, status = await _run_sync(db.return_boat_trip_and_split_catch, user_id)
        except Exception as e:
            logger.exception("[boat] Return failed: user_id=%s chat_id=%s error=%s", user_id, chat_id, e)
            await update.callback_query.answer("Ошибка при возврате лодки. Попробуйте ещё раз.", show_alert=True)
            await self.show_fishing_menu(update, context)
            return

        total_assigned = sum(int(item[2] or 0) for item in results) if results else 0
        logger.info(
            "[boat] Return result: user_id=%s chat_id=%s boat_id=%s status=%s recipients=%s assigned=%s",
            user_id,
            chat_id,
            boat_id,
            status,
            len(results or []),
            total_assigned,
        )
        if status == 'not_found':
            await update.callback_query.answer("Ошибка: активная лодка не найдена.", show_alert=True)
            await self.show_fishing_menu(update, context)
            return
        if status == 'no_members':
            await update.callback_query.answer("Ошибка: участники лодки не найдены.", show_alert=True)
            await self.show_fishing_menu(update, context)
            return
        if status == 'sunk':
            await update.callback_query.answer("💥 КРУШЕНИЕ! Лодка не выдержала веса и пошла ко дну! Весь улов текущего плавания утерян.", show_alert=True)
            await self.show_fishing_menu(update, context)
            return
        if status == 'empty':
            await update.callback_query.answer("Плавание завершено. Улов отсутствует.", show_alert=True)
            await self.show_fishing_menu(update, context)
            return
        msg = "\n".join([f"@{username} — получил {count} рыб, общий вес — {weight:.1f} кг" for _, username, count, weight in results])
        await update.callback_query.answer("Плавание завершено! Делим улов.")
        await update.effective_chat.send_message(f"⛵ Итоги плавания:\n{msg}")
        await self.show_fishing_menu(update, context)
    
    async def handle_change_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка смены локации"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        # Во время плавания на лодке смена локации запрещена
        if await _run_sync(db.get_active_boat_by_user, user_id):
            await query.answer("⛵ Нельзя менять локацию, пока вы в плавании. Сначала нажмите «Вернуться».", show_alert=True)
            return
        
        await query.answer()
        
        locations = await _run_sync(db.get_locations)
        keyboard = []
        
        for loc in locations:
            # Показываем актуальное количество человек в чате
            players_count = await _run_sync(db.get_location_players_count, loc['name'], chat_id)
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
        locations = await _run_sync(db.get_locations)
        
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

        if await _run_sync(db.is_echosounder_active, user_id, chat_id):
            keyboard.append([InlineKeyboardButton(
                "📡 Эхолот",
                callback_data=f"show_echosounder_{user_id}"
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

    async def handle_show_echosounder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать лучший клёв по погоде и ориентир по наживке/рыбе."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        if not await _run_sync(db.is_echosounder_active, user_id, chat_id):
            await query.answer("Эхолот не активен. Купите его в магазине.", show_alert=True)
            return

        locations = await _run_sync(db.get_locations)
        if not locations:
            await query.answer("Локации не найдены.", show_alert=True)
            return

        best_location = None
        best_bonus = -999
        best_condition = ""

        for loc in locations:
            loc_name = loc.get('name')
            if not loc_name:
                continue
            weather = await _run_sync(db.get_or_update_weather, loc_name)
            condition = weather.get('condition', 'Ясно') if weather else 'Ясно'
            bonus = weather_system.get_weather_bonus(condition)
            if bonus > best_bonus:
                best_bonus = bonus
                best_location = loc_name
                best_condition = condition

        if not best_location:
            await query.answer("Не удалось рассчитать лучший клёв.", show_alert=True)
            return

        season = get_current_season()
        fish_list = await _run_sync(db.get_fish_by_location, best_location, season, min_level=999)
        top_fish = None
        if fish_list:
            top_fish = max(fish_list, key=lambda item: float(item.get('max_weight') or 0))

        if top_fish:
            fish_name = str(top_fish.get('name', 'Неизвестно'))
            max_weight = float(top_fish.get('max_weight') or 0)
            suitable = str(top_fish.get('suitable_baits') or 'Все')
            if suitable.strip().lower() == 'все':
                bait_tip = "Любая"
            else:
                bait_tip = suitable.split(',')[0].strip()
        else:
            fish_name = "нет данных"
            max_weight = 0
            bait_tip = "Любая"

        alert_text = (
            f"Лучшая локация: {best_location} ({best_condition}, {best_bonus:+d}%). "
            f"Макс рыба: {fish_name} до {max_weight:.1f}кг. Наживка: {bait_tip}."
        )
        if len(alert_text) > 200:
            alert_text = alert_text[:197] + "..."

        await query.answer(alert_text, show_alert=True)
    
    async def handle_change_bait_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать наживки игрока для выбранной локации"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Разбор: change_bait_loc_{loc_idx}_{user_id}_{page}
        try:
            parts = query.data.split('_')
            loc_idx = int(parts[3])
            button_user_id = int(parts[4])
            page = int(parts[5]) if len(parts) > 5 else 1
        except (IndexError, ValueError) as e:
            logger.error("handle_change_bait_location: bad callback_data=%s: %s", query.data, e)
            await query.answer("Ошибка навигации", show_alert=True)
            return

        if button_user_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        try:
            await query.answer()
        except Exception:
            pass

        try:
            locations = await _run_sync(db.get_locations)
        except Exception as e:
            logger.exception("handle_change_bait_location: db.get_locations failed: %s", e)
            try:
                await query.edit_message_text("❌ Не удалось загрузить локации. Попробуйте позже.")
            except Exception:
                pass
            return

        if loc_idx >= len(locations):
            await query.edit_message_text("❌ Локация не найдена!")
            return
        location = locations[loc_idx]['name']
        
        # Получаем наживки игрока для этой локации
        try:
            baits = await _run_sync(db.get_player_baits_for_location, user_id, location)
        except Exception as e:
            logger.exception("handle_change_bait_location: db error user=%s location=%s: %s", user_id, location, e)
            try:
                await query.edit_message_text("❌ Не удалось загрузить наживки. Попробуйте позже.")
            except Exception:
                pass
            return

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
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        if player and player.get('current_rod') == HARPOON_NAME:
            await _run_sync(db.init_player_rod, user_id, BAMBOO_ROD, chat_id)
            await _run_sync(db.update_player, user_id, chat_id, current_rod=BAMBOO_ROD)
            player = await _run_sync(db.get_player, user_id, chat_id)
        await _run_sync(db.ensure_rod_catalog)
        all_rods = await _run_sync(db.get_rods)
        
        keyboard = []
        
        # Добавляем бамбуковую удочку (всегда есть)
        bamboo_rod = await _run_sync(db.get_rod, "Бамбуковая удочка")
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
            if rod['name'] not in ("Бамбуковая удочка", HARPOON_NAME):  # Исключаем стартовую и гарпун (он отдельный инструмент)
                owned_rod = await _run_sync(db.get_player_rod, user_id, rod['name'], chat_id)
                if not owned_rod:
                    continue
                current = "✅" if player['current_rod'] == rod['name'] else ""
                # Получаем текущую прочность удочки
                durability_str = ""
                if rod['name'] == BAMBOO_ROD:
                    player_rod = await _run_sync(db.get_player_rod, user_id, rod['name'], chat_id)
                    if player_rod:
                        durability_str = f" ({player_rod['current_durability']}/{player_rod['max_durability']})"
                
                cb_data = f"select_rod_{rod['name']}_{user_id}"
                if len(cb_data.encode('utf-8')) > 64:
                    cb_data = f"sr_{rod['id']}_{user_id}"
                
                keyboard.append([InlineKeyboardButton(
                    f"🎣 {rod['name']}{durability_str} {current}",
                    callback_data=cb_data
                )])

        # Гарпун отдельным инструментом (не как удочка)
        harpoon_owned = await _run_sync(db.get_player_rod, user_id, HARPOON_NAME, chat_id)
        if harpoon_owned:
            remaining = await _run_sync(db.get_harpoon_cooldown_remaining, user_id, chat_id, HARPOON_COOLDOWN_MINUTES)
            if remaining > 0:
                harpoon_status = f"⏳ {self._format_seconds_compact(remaining)}"
            else:
                harpoon_status = "✅ Готов"

            keyboard.append([InlineKeyboardButton(
                f"🗡️ {HARPOON_NAME} ({harpoon_status})",
                callback_data=f"use_harpoon_{user_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"change_bait_{user_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🎣 Выберите удочку:\n\n🗡️ Гарпун теперь используется отдельно и не влияет на выбор удочки."
        
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

        # Дублируем запрет для защиты от старых/кэшированных кнопок выбора локации
        if await _run_sync(db.get_active_boat_by_user, user_id):
            await query.answer("⛵ Во время плавания локацию менять нельзя. Сначала завершите плавание.", show_alert=True)
            await self.show_fishing_menu(update, context)
            return
        
        await query.answer()
        
        # Извлекаем название локации (убираем префикс и user_id)
        location_name = query.data.replace(f"select_location_", "").replace(f"_{user_id}", "")
        
        # Обновляем локацию игрока
        await _run_sync(db.update_player_location, user_id, chat_id, location_name)

        keyboard = [[
            InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}"),
            InlineKeyboardButton("📍 Сменить локацию", callback_data=f"change_location_{user_id}")
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
                baits = await _run_sync(db.get_baits)
                bait = next((b for b in baits if b['id'] == bait_id), None)
                if bait:
                    bait_name = bait['name']
        else:
            bait_name = query.data.replace("select_bait_", "").replace(f"_{user_id}", "")

        if not bait_name:
            await query.edit_message_text("❌ Наживка не найдена!")
            return

        # Обновляем наживку игрока
        await _run_sync(db.update_player_bait, user_id, chat_id, bait_name)

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
        player_nets = await _run_sync(db.get_player_nets, user_id, chat_id)
        if not player_nets:
            await _run_sync(db.init_player_net, user_id, 'Базовая сеть', chat_id)
            player_nets = await _run_sync(db.get_player_nets, user_id, chat_id)
        
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
        any_on_cooldown = False
        for net in player_nets:
            # Проверяем кулдаун
            cooldown = await _run_sync(db.get_net_cooldown_remaining, user_id, net['net_name'], chat_id)
            
            if cooldown > 0:
                any_on_cooldown = True
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
        
        if any_on_cooldown:
            keyboard.append([InlineKeyboardButton("⚡ Сбросить КД сетей — 10 ⭐", callback_data=f"net_skip_cd_{user_id}")])
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
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.answer("Профиль не найден", show_alert=True)
            return
        
        # Проверяем наличие сети у игрока
        player_net = await _run_sync(db.get_player_net, user_id, net_name, chat_id)
        if not player_net:
            await query.answer("❌ У вас нет этой сети!", show_alert=True)
            return
        
        # Проверяем кулдаун
        cooldown = await _run_sync(db.get_net_cooldown_remaining, user_id, net_name, chat_id)
        if cooldown > 0:
            hours = cooldown // 3600
            minutes = (cooldown % 3600) // 60
            time_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
            await query.answer(f"⏳ Сеть можно использовать через {time_str}", show_alert=True)
            return
        
        # Нельзя использовать сеть во время плавания на лодке
        active_boat = await _run_sync(db.get_active_boat_by_user, user_id)
        if active_boat:
            await query.answer("❌ Нельзя использовать сеть во время плавания на лодке!", show_alert=True)
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
        available_fish = await _run_sync(db.get_fish_by_location, location, season, min_level=player.get('level', 0) or 0)
        # Исключаем NFT из улова сетями
        available_fish = [f for f in available_fish if f['rarity'] != 'NFT']
        
        # Получаем мусор для локации
        available_trash = await _run_sync(db.get_trash_by_location, location)
        
        if not available_fish and not available_trash:
            await query.edit_message_text(
                f"❌ В локации {location} нет доступного контента в сезон {season}!"
            )
            return
        
        # Вытаскиваем случайные рыбы и мусор
        catch_results = []
        total_value = 0
        net_tickets_base = 0
        net_treasure_totals: Dict[str, int] = {}
        feeder_bonus = await _run_sync(db.get_active_feeder_bonus, user_id, chat_id)
        clothing_bonus_percent = self._get_clothing_bonus_percent(user_id)
        beer_bonus_percent = self._get_active_beer_bonus_percent(user_id)
        fish_chance = min(95.0, 80 + feeder_bonus + clothing_bonus_percent + beer_bonus_percent)
        
        for i in range(fish_count):
            # Базово 80% шанс рыбы, кормушка увеличивает шанс
            is_trash = random.uniform(0, 100) > fish_chance
            
            if is_trash and available_trash:
                # Ловим мусор
                trash = random.choice(available_trash)
                treasure_key = self._roll_treasure_after_trash(
                    user_id=user_id,
                    chat_id=chat_id,
                    source_tag="NET",
                    roll_index=i + 1,
                )
                if treasure_key:
                    from treasures import get_treasure_name

                    net_treasure_totals[treasure_key] = int(net_treasure_totals.get(treasure_key, 0) or 0) + 1
                    catch_results.append({
                        'type': 'treasure',
                        'name': get_treasure_name(treasure_key),
                        'price': 0,
                    })
                    net_tickets_base += int(self.TICKET_POINTS['trash'])
                    logger.info(
                        "Net catch (trash->treasure): user=%s chat_id=%s chat_title=%s trash=%s treasure=%s location=%s",
                        user_id,
                        chat_id,
                        update.effective_chat.title or "",
                        trash['name'],
                        treasure_key,
                        location,
                    )
                else:
                    await _run_sync(db.add_caught_fish, user_id, chat_id, trash['name'], trash['weight'], location, 0)

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
                    net_tickets_base += int(self.TICKET_POINTS['trash'])
            elif available_fish:
                # Ловим рыбу — с весами по редкости (легенда/миф бьётся реже)
                _RARITY_WEIGHTS = {
                    'Обычная':    100,
                    'Редкая':      20,
                    'Легендарная':  0.5,
                    'Аквариумная': 0.0007,
                    'Мифическая':  0.0005,
                    'Аномалия':    0.0002,
                }
                _weights = [_RARITY_WEIGHTS.get(f.get('rarity', 'Обычная'), 100) for f in available_fish]
                fish = random.choices(available_fish, weights=_weights, k=1)[0]
                # Генерируем вес и длину рыбы
                weight = round(random.uniform(fish['min_weight'], fish['max_weight']), 2)
                length = round(random.uniform(fish['min_length'], fish['max_length']), 1)
                
                # Добавляем рыбу в улов игрока
                await _run_sync(db.add_caught_fish, user_id, chat_id, fish['name'], weight, location, length)

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
                
                fish_price = await _run_sync(db.calculate_fish_price, fish, weight, length)

                catch_results.append({
                    'type': 'fish',
                    'name': fish['name'],
                    'weight': weight,
                    'length': length,
                    'price': fish_price,
                    'rarity': fish.get('rarity', 'Обычная'),
                })
                total_value += fish_price
                net_tickets_base += self._calculate_tickets_for_rarity(fish.get('rarity', 'Обычная'))
        
        # Используем сеть
        await _run_sync(db.use_net, user_id, net_name, chat_id)
        tickets_awarded, tickets_jackpot, tickets_total = self._award_tickets(
            user_id,
            net_tickets_base,
            username=update.effective_user.username or update.effective_user.first_name or str(user_id),
            source_type='net',
            source_ref=f"{net_name}:{location}",
        )
        
        # Формируем сообщение
        message = f"🕸️ Сеть '{net_name}' использована!\n"
        message += f"📍 Локация: {location}\n"
        message += f"📦 Улов: {len(catch_results)} предметов\n\n"
        message += "─" * 30 + "\n"
        
        for i, item in enumerate(catch_results, 1):
            if item['type'] == 'fish':
                fish_name_display = format_fish_name(item['name'])
                message += f"{i}. {fish_name_display} - {item['weight']}кг, {item['length']}см\n"
            elif item['type'] == 'treasure':
                message += f"{i}. {item['name']}\n"
            else:
                message += f"{i}. {item['name']} - {item['weight']}кг\n"
        
        message += "─" * 30 + "\n"
        message += f"💰 Итого: {total_value} {COIN_NAME}\n"
        if tickets_awarded > 0:
            if tickets_jackpot > 0:
                message += f"🎟 Билеты: +{tickets_awarded} (джекпот +{tickets_jackpot})\n"
            else:
                message += f"🎟 Билеты: +{tickets_awarded}\n"
            message += f"🎫 Всего билетов: {tickets_total}\n"
        if net_treasure_totals:
            from treasures import get_treasure_name

            message += "💎 Драгоценности:\n"
            for key, qty in sorted(net_treasure_totals.items(), key=lambda item: item[0]):
                message += f"• {get_treasure_name(key)} x{qty}\n"
        if feeder_bonus > 0:
            message += f"🧺 Бонус кормушки: +{feeder_bonus}% (рыба {fish_chance}%)\n"
        
        # Обновляем оставшиеся использования
        player_net = await _run_sync(db.get_player_net, user_id, net_name, chat_id)
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
                    rod = await _run_sync(db.get_rod_by_id, rod_id)
                    if rod:
                        rod_name = rod['name']
                except (ValueError, IndexError):
                    pass
        
        if not rod_name:
            await query.edit_message_text("❌ Удочка не найдена!")
            return

        if rod_name == HARPOON_NAME:
            await query.edit_message_text(
                "🗡️ Гарпун больше не выбирается как удочка.\n"
                "Используйте кнопку гарпуна в меню выбора удочки."
            )
            return
        
        # Проверяем, что удочка есть у игрока (или бамбуковая)
        if rod_name != "Бамбуковая удочка":
            # Нужно проверить, куплена ли удочка
            player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
            if not player_rod:
                await query.edit_message_text("❌ Эта удочка не куплена!")
                return
        else:
            # Инициализируем бамбуковую удочку если её нет
            await _run_sync(db.init_player_rod, user_id, "Бамбуковая удочка", chat_id)
        
        # Обновляем удочку игрока
        await _run_sync(db.update_player, user_id, chat_id, current_rod=rod_name)
        
        # Возвращаемся в меню выбора удочек с подтверждением
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"change_rod_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(f"✅ Удочка '{rod_name}' выбрана!", reply_markup=reply_markup)

    async def handle_use_harpoon(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Использование гарпуна как отдельного инструмента."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        harpoon_owned = await _run_sync(db.get_player_rod, user_id, HARPOON_NAME, chat_id)
        if not harpoon_owned:
            await query.edit_message_text(
                "❌ У вас нет гарпуна. Купите его в магазине.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Магазин", callback_data=f"shop_rods_{user_id}")]])
            )
            return

        remaining = await _run_sync(db.get_harpoon_cooldown_remaining, user_id, chat_id, HARPOON_COOLDOWN_MINUTES)
        if remaining > 0:
            keyboard = [
                [InlineKeyboardButton(
                    f"⭐ Пропустить КД за {HARPOON_SKIP_COST_STARS} Stars",
                    callback_data=f"use_harpoon_paid_{user_id}"
                )],
                [InlineKeyboardButton("🔙 Назад", callback_data=f"change_rod_{user_id}")]
            ]
            await query.edit_message_text(
                (
                    f"🗡️ Гарпун на перезарядке: {self._format_seconds_compact(remaining)}\n\n"
                    f"Можно подождать {HARPOON_COOLDOWN_MINUTES} минут или оплатить {HARPOON_SKIP_COST_STARS} Telegram Stars.\n"
                    "Пока идет КД гарпуна, вы можете спокойно рыбачить обычной удочкой."
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        await self._execute_harpoon_catch(user_id, chat_id, reply_to_message_id=query.message.message_id)

    async def handle_net_skip_cd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки сброса КД сетей за 10 звезд."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        # Проверяем, что хотя бы одна сеть действительно на КД
        player_nets = await _run_sync(db.get_player_nets, user_id, chat_id)
        any_on_cooldown = False
        for net in player_nets:
            if await _run_sync(db.get_net_cooldown_remaining, user_id, net['net_name'], chat_id) > 0:
                any_on_cooldown = True
                break
        
        if not any_on_cooldown:
            await query.answer("✅ Все сети уже свободны!", show_alert=True)
            return

        from config import BOT_TOKEN, STAR_NAME
        tg_api = TelegramBotAPI(BOT_TOKEN)
        payload = f"net_skip_cd_{user_id}_{chat_id}_{int(datetime.now().timestamp())}"

        invoice_url = await tg_api.create_invoice_link(
            title="Сброс КД сетей",
            description="Мгновенный сброс кулдауна всех ваших сетей (10 ⭐)",
            payload=payload,
            currency="XTR",
            prices=[{"label": "Сброс КД сетей", "amount": 10}],
        )

        if not invoice_url:
            await query.edit_message_text("❌ Не удалось создать ссылку оплаты. Попробуйте позже.")
            return

        await self.send_invoice_url_button(
            chat_id=chat_id,
            invoice_url=invoice_url,
            text="⚡ Оплатите 10 Telegram Stars чтобы сбросить кулдаун всех сетей и использовать их сразу.",
            user_id=user_id,
            reply_to_message_id=query.message.message_id if query.message else None,
        )

    async def handle_use_harpoon_paid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Оплата пропуска КД гарпуна через Telegram Stars."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        harpoon_owned = await _run_sync(db.get_player_rod, user_id, HARPOON_NAME, chat_id)
        if not harpoon_owned:
            await query.edit_message_text("❌ У вас нет гарпуна. Купите его в магазине.")
            return

        remaining = await _run_sync(db.get_harpoon_cooldown_remaining, user_id, chat_id, HARPOON_COOLDOWN_MINUTES)
        if remaining <= 0:
            await self._execute_harpoon_catch(user_id, chat_id, reply_to_message_id=query.message.message_id)
            return

        from config import BOT_TOKEN, STAR_NAME
        tg_api = TelegramBotAPI(BOT_TOKEN)
        payload = self._build_harpoon_skip_payload(user_id, chat_id)

        invoice_url = await tg_api.create_invoice_link(
            title="Пропуск КД гарпуна",
            description=f"Мгновенное использование гарпуна без ожидания ({HARPOON_SKIP_COST_STARS} {STAR_NAME})",
            payload=payload,
            currency="XTR",
            prices=[{"label": "Пропуск КД гарпуна", "amount": HARPOON_SKIP_COST_STARS}],
        )

        if not invoice_url:
            await query.edit_message_text("❌ Не удалось создать ссылку оплаты. Попробуйте позже.")
            return

        await self.send_invoice_url_button(
            chat_id=chat_id,
            invoice_url=invoice_url,
            text=f"⭐ Оплатите {HARPOON_SKIP_COST_STARS} Telegram Stars для мгновенного использования гарпуна.",
            user_id=user_id,
            reply_to_message_id=query.message.message_id if query and query.message else None,
            timeout_sec=600,
        )

        await query.edit_message_text("Ссылка на оплату отправлена. После оплаты гарпун сработает автоматически.")

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
        player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
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
        # Создаём invoice_url через TelegramBotAPI.create_invoice_link
        from config import BOT_TOKEN, STAR_NAME
        import traceback
        invoice_error = None
        try:
            from bot import TelegramBotAPI as _TelegramBotAPI
            tg_api = _TelegramBotAPI(BOT_TOKEN)
            logger.info(f"[INVOICE] Creating invoice link for repair: rod={rod_name}, user_id={user_id}, cost={repair_cost}")
            invoice_url = await tg_api.create_invoice_link(
                title=f"Мгновенный ремонт удочки",
                description=f"Восстановить '{rod_name}' до полной прочности",
                payload=f"repair_rod_{rod_name}_{user_id}_{int(datetime.now().timestamp())}",
                currency="XTR",
                prices=[{"label": f"Ремонт {rod_name}", "amount": repair_cost}]
            )
            logger.info(f"[INVOICE] Got invoice_url: {invoice_url}")
        except Exception as e:
            logger.error(f"[INVOICE] Failed to get invoice_url for repair: {e}")
            invoice_url = None
            invoice_error = str(e) + "\n" + traceback.format_exc()
        if invoice_url:
            await self.send_invoice_url_button(
                chat_id=query.message.chat_id,
                invoice_url=invoice_url,
                text=f"⭐ Оплатите {repair_cost} Telegram Stars для мгновенного восстановления удочки.",
                user_id=user_id,
                reply_to_message_id=query.message.message_id if query and query.message else None,
            )
        else:
            error_text = f"(Ошибка генерации ссылки для оплаты)"
            if invoice_error:
                error_text += f"\nОшибка: {invoice_error}"
            await query.edit_message_text(error_text, parse_mode=None)

        
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

    async def handle_noop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пустой callback для служебных кнопок пагинации (индикатор страницы)."""
        query = update.callback_query
        if query:
            try:
                await query.answer()
            except Exception:
                pass
    
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

        await _run_sync(db.ensure_rod_catalog)
        rods = await _run_sync(db.get_rods)
        keyboard = []
        player = await _run_sync(db.get_player, user_id, chat_id)
        player_level = player.get('level', 0) if player else 0
        for rod in rods:
            # Гарпун только для 25+ уровня
            if rod['name'] == 'Гарпун' and player_level < 25:
                continue
            # Удачливая удочка только для 15+ уровня
            if rod['name'] == 'Удачливая удочка' and player_level < 15:
                continue
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
        await _run_sync(db.ensure_rod_catalog)
        
        # Получаем название удочки по ID
        rods = await _run_sync(db.get_rods)
        rod_name = None
        for rod in rods:
            if rod['id'] == rod_id:
                rod_name = rod['name']
                break
        
        if not rod_name:
            await query.edit_message_text("❌ Удочка не найдена!")
            return

        player = await _run_sync(db.get_player, user_id, chat_id)
        player_level = int((player or {}).get('level', 0) or 0)
        if rod_name == 'Удачливая удочка' and player_level < 15:
            await query.edit_message_text("❌ Удачливая удочка открывается с 15 уровня.")
            return
        if rod_name == 'Гарпун' and player_level < 25:
            await query.edit_message_text("❌ Гарпун открывается с 25 уровня.")
            return
        
        # Покупаем удочку
        result = await _run_sync(db.buy_rod, user_id, chat_id, rod_name)
        
        if result:
            await query.edit_message_text(f"✅ Удочка {rod_name} куплена!")
        else:
            await query.edit_message_text("❌ Недостаточно монет!")
    
    async def send_rod_repair_invoice(self, user_id: int, rod_name: str):
        """Отправить инвойс для восстановления удочки в личное сообщение"""
        try:
            rod = await _run_sync(db.get_rod, rod_name)
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

        context.user_data.pop('waiting_bait_quantity', None)
        
        await query.answer()
        
        # Получаем все локации
        locations = await _run_sync(db.get_locations)
        
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

        context.user_data.pop('waiting_bait_quantity', None)
        
        # Получаем название локации по индексу
        locations = await _run_sync(db.get_locations)
        if loc_idx >= len(locations):
            await query.edit_message_text("❌ Локация не найдена!")
            return
        location = locations[loc_idx]['name']
        
        await query.answer()
        
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        baits = await _run_sync(db.get_baits_for_location, location)
        
        # Исключаем бесконечную наживку (черви) и наживку, которую можно поймать самому
        _exclude_baits = (
            'черви', 
            LIVE_BAIT_NAME.lower(), 
            'шпрот', 
            'анчоус', 
            'тюлька', 
            'сельдь', 
            'сардина',
            'живец',
            'крупный живец'
        )
        baits = [
            b for b in baits
            if b['name'].strip().lower() not in _exclude_baits
        ]
        
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
            if "Message is not modified" in str(e):
                return
            logger.error(f"Error editing shop_baits_location: {e}")
            if "Message is not modified" not in str(e):
                # Попробуем отправить как обычное сообщение
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
                except Exception as e2:
                    logger.error(f"Failed to send as new message too: {e2}")
    
    async def handle_shop_boats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин лодок"""
        query = update.callback_query
        user_id = update.effective_user.id
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        await query.answer()

        boat = await _run_sync(db.get_user_boat, user_id)
        boat_type = boat.get('type', 'free') if boat else 'free'

        if boat_type != 'free':
            text = (
                f"⛵ <b>Ваша лодка:</b> {boat.get('name', '—')}\n"
                f"👥 Вместимость: {boat.get('capacity', '—')}\n"
                f"⚖️ Грузоподъёмность: {boat.get('max_weight', '—')} кг\n"
                f"🔧 Прочность: {boat.get('durability', '—')}/{boat.get('max_durability', '—')}\n\n"
                "У вас уже есть платная лодка."
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад в магазин", callback_data=f"shop_{user_id}")]]
        else:
            text = (
                "🛒 <b>Магазин лодок</b>\n\n"
                "⛵ <b>Платная лодка</b> — 50 💎\n"
                "Надёжная лодка для кооперативной рыбалки.\n"
                "👥 Вместимость: 3 игрока\n"
                "⚖️ Грузоподъёмность: 1500 кг\n"
                "🔧 Прочность: 100\n"
                "⏱ КД выплывания: 12 ч\n\n"
                "Покупка за 💎 бриллианты."
            )
            keyboard = [
                [InlineKeyboardButton("⛵ Купить Платную лодку (50💎)", callback_data=f"buy_boat_diamonds1_{user_id}")],
                [InlineKeyboardButton("🔙 Назад в магазин", callback_data=f"shop_{user_id}")]
            ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


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
        player = await _run_sync(db.get_player, user_id, chat_id)
        nets = await _run_sync(db.get_nets)
        nets_for_sale = [net for net in nets if net.get('price', 0) > 0]
        
        keyboard = []
        
        for net in nets_for_sale:
            # Проверяем, есть ли сеть у игрока
            player_net = await _run_sync(db.get_player_net, user_id, net['name'], chat_id)
            
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

    async def handle_shop_feeders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Магазин кормушек и эхолота."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        active_feeder = await _run_sync(db.get_active_feeder, user_id, chat_id)
        feeder_remaining = await _run_sync(db.get_feeder_cooldown_remaining, user_id, chat_id)
        echosounder_remaining = await _run_sync(db.get_echosounder_remaining_seconds, user_id, chat_id)

        keyboard = []
        for feeder in FEEDER_ITEMS:
            if feeder["price_stars"] > 0:
                price_label = f"{feeder['price_stars']} ⭐"
                callback_data = f"buy_feeder_stars_{feeder['code']}_{user_id}"
            else:
                price_label = f"{feeder['price_coins']} 🪙"
                callback_data = f"buy_feeder_coins_{feeder['code']}_{user_id}"

            keyboard.append([
                InlineKeyboardButton(
                    f"🧺 {feeder['name']} (+{feeder['bonus']}% на 1ч) — {price_label}",
                    callback_data=callback_data,
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                f"📡 Эхолот (24ч) — {ECHOSOUNDER_COST_STARS} ⭐",
                callback_data=f"buy_echosounder_{user_id}",
            )
        ])
        keyboard.append([InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")])

        status_lines = [f"💰 Баланс: {player.get('coins', 0)} 🪙"]
        if active_feeder:
            status_lines.append(
                f"🧺 Активна: +{active_feeder['bonus_percent']}% ({self._format_seconds_compact(feeder_remaining)})"
            )
        else:
            status_lines.append("🧺 Кормушка не активна")

        if echosounder_remaining > 0:
            status_lines.append(f"📡 Эхолот активен: {self._format_seconds_compact(echosounder_remaining)}")
        else:
            status_lines.append("📡 Эхолот не активен")

        message = (
            "🛒 Кормушки и эхолот\n\n"
            "Кормушка усиливает клёв для обычных, платных и сетевых забросов.\n"
            "Пока активна одна кормушка — другие купить нельзя.\n\n"
            + "\n".join(status_lines)
        )

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_shop_beer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экран пива с рандомными временными эффектами."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        coins = int(player.get("coins", 0) or 0)
        drunk_remaining = await _run_sync(db.get_effect_remaining_seconds, user_id, BEER_DRUNK_EFFECT)
        trace_count = await _run_sync(db.count_active_effects, user_id, BEER_TRACE_EFFECT)
        current_drunk_chance = min(BEER_DRUNK_MAX_CHANCE, BEER_DRUNK_BASE_CHANCE + (trace_count * BEER_DRUNK_PER_TRACE_CHANCE))
        total_beer_bonus = self._get_active_beer_bonus_percent(user_id)

        active_bonus_lines = []
        for effect in BEER_POSITIVE_EFFECTS:
            remaining = await _run_sync(db.get_effect_remaining_seconds, user_id, effect["effect_type"])
            if remaining > 0:
                active_bonus_lines.append(
                    f"• {effect['name']}: +{effect['bonus_percent']}% ({self._format_seconds_compact(remaining)})"
                )

        if not active_bonus_lines:
            active_bonus_lines = ["• Нет активных пивных баффов"]

        if drunk_remaining > 0:
            drunk_status = f"🤪 Опьянение активно: {self._format_seconds_compact(drunk_remaining)}"
            risk_line = "⚠️ Вы уже в опьянении."
        else:
            drunk_status = "🤪 Опьянения нет"
            risk_line = f"🎲 Текущий риск опьянения: {current_drunk_chance * 100:.0f}%"

        keyboard = [
            [InlineKeyboardButton(f"🍺 Выпить кружку — {BEER_PRICE_COINS} 🪙", callback_data=f"buy_beer_{user_id}")],
            [InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")],
        ]

        message = (
            "🍺 Пивная\n\n"
            "Каждая кружка может дать временный бафф к шансу клёва.\n"
            "Но чем больше кружек подряд, тем выше шанс опьянения.\n\n"
            f"💰 Баланс: {coins} 🪙\n"
            f"✨ Суммарный пивной бонус: +{format_percent_value(total_beer_bonus)}%\n"
            f"{drunk_status}\n"
            f"{risk_line}\n\n"
            "Активные баффы:\n"
            + "\n".join(active_bonus_lines)
        )

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_buy_beer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка кружки пива за монеты и выдача случайного эффекта."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        coins_before = int(player.get("coins", 0) or 0)
        if coins_before < BEER_PRICE_COINS:
            await query.edit_message_text(
                f"❌ Недостаточно монет. Нужно: {BEER_PRICE_COINS} 🪙, у вас: {coins_before} 🪙",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍺 В пивную", callback_data=f"shop_beer_{user_id}")],
                    [InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")],
                ]),
            )
            return

        new_balance = coins_before - BEER_PRICE_COINS
        await _run_sync(db.update_player, user_id, chat_id, coins=new_balance)

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🍺 В пивную", callback_data=f"shop_beer_{user_id}")],
            [InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")],
        ])

        try:
            is_already_drunk = self._is_user_beer_drunk(user_id)
            traces = await _run_sync(db.count_active_effects, user_id, BEER_TRACE_EFFECT)
            drunk_chance = min(BEER_DRUNK_MAX_CHANCE, BEER_DRUNK_BASE_CHANCE + (traces * BEER_DRUNK_PER_TRACE_CHANCE))

            if is_already_drunk or random.random() < drunk_chance:
                for beer_effect in BEER_POSITIVE_EFFECTS:
                    try:
                        await _run_sync(db.clear_timed_effect, user_id, beer_effect["effect_type"])
                    except Exception:
                        logger.exception(
                            "Failed to clear beer buff=%s for user=%s",
                            beer_effect.get("effect_type"),
                            user_id,
                        )
                await _run_sync(db.clear_timed_effect, user_id, BEER_TRACE_EFFECT)
                await _run_sync(db.apply_timed_effect, user_id,
                    BEER_DRUNK_EFFECT,
                    duration_minutes=BEER_DRUNK_DURATION_MINUTES,
                    replace_existing=True,
                )

                fake_good_text = random.choice(BEER_FAKE_GOOD_RESULTS)
                await query.edit_message_text(
                    "🍺 Вы выпили кружку пива.\n\n"
                    f"{fake_good_text}\n"
                    "🎣 Самое время закинуть удочку!\n\n"
                    f"💰 Потрачено: {BEER_PRICE_COINS} 🪙\n"
                    f"💰 Баланс: {new_balance} 🪙",
                    reply_markup=back_keyboard,
                )
                return

            await _run_sync(db.apply_timed_effect, user_id,
                BEER_TRACE_EFFECT,
                duration_minutes=BEER_TRACE_DURATION_MINUTES,
                replace_existing=False,
            )

            effect = random.choice(BEER_POSITIVE_EFFECTS)
            await _run_sync(db.apply_timed_effect, user_id,
                effect["effect_type"],
                duration_minutes=int(effect["duration_minutes"]),
                replace_existing=False,
            )

            total_bonus = self._get_active_beer_bonus_percent(user_id)
            await query.edit_message_text(
                "🍺 Вы выпили кружку пива.\n\n"
                f"✨ Выпал эффект: {effect['name']}\n"
                f"🎯 Шанс клёва: +{effect['bonus_percent']}% на {effect['duration_minutes']} мин\n"
                f"✨ Суммарный пивной бонус: +{format_percent_value(total_bonus)}%\n\n"
                f"💰 Потрачено: {BEER_PRICE_COINS} 🪙\n"
                f"💰 Баланс: {new_balance} 🪙",
                reply_markup=back_keyboard,
            )
        except Exception:
            logger.exception("Failed to process beer purchase for user=%s chat=%s", user_id, chat_id)
            try:
                await _run_sync(db.update_player, user_id, chat_id, coins=coins_before)
            except Exception:
                logger.exception("Failed to refund coins after beer purchase error for user=%s", user_id)

            await query.edit_message_text(
                "❌ Не удалось применить эффект. Средства возвращены.",
                reply_markup=back_keyboard,
            )

    async def handle_buy_feeder_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка кормушки за монеты."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        feeder_code = query.data.replace("buy_feeder_coins_", "").replace(f"_{user_id}", "")
        feeder = self._get_feeder_by_code(feeder_code)
        if not feeder or feeder.get("price_coins", 0) <= 0:
            await query.edit_message_text("❌ Кормушка не найдена.")
            return

        active_feeder = await _run_sync(db.get_active_feeder, user_id, chat_id)
        if active_feeder:
            remaining = await _run_sync(db.get_feeder_cooldown_remaining, user_id, chat_id)
            await query.answer(
                f"Сначала дождитесь окончания активной кормушки ({self._format_seconds_compact(remaining)})",
                show_alert=True,
            )
            return

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден.")
            return

        price = int(feeder["price_coins"])
        if int(player.get("coins", 0)) < price:
            await query.edit_message_text(
                f"❌ Недостаточно монет. Нужно: {price} 🪙, у вас: {player.get('coins', 0)} 🪙"
            )
            return

        # Deduct coins and try to activate feeder; on failure refund coins
        await _run_sync(db.update_player, user_id, chat_id, coins=int(player.get("coins", 0)) - price)
        try:
            await _run_sync(db.activate_feeder, user_id,
                chat_id,
                feeder_type=feeder["code"],
                bonus_percent=int(feeder["bonus"]),
                duration_minutes=int(feeder["duration_minutes"]),
            )
        except Exception as e:
            logger.exception("Failed to activate feeder for user=%s chat=%s: %s", user_id, chat_id, e)
            # Refund coins on failure
            try:
                await _run_sync(db.update_player, user_id, chat_id, coins=int(player.get("coins", 0)))
            except Exception:
                logger.exception("Failed to refund coins after feeder activation failure for user=%s", user_id)

            await query.edit_message_text(
                "❌ Ошибка при активации кормушки. Денежные средства возвращены. Попробуйте позже."
            )
            return

        await query.edit_message_text(
            f"✅ {feeder['name']} активирована на 1 час.\n"
            f"🎯 Бонус к клёву: +{feeder['bonus']}%\n"
            f"💰 Потрачено: {price} 🪙"
        )

    async def handle_buy_feeder_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка кормушки за Telegram Stars (через инвойс)."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        feeder_code = query.data.replace("buy_feeder_stars_", "").replace(f"_{user_id}", "")
        feeder = self._get_feeder_by_code(feeder_code)
        if not feeder or feeder.get("price_stars", 0) <= 0:
            await query.edit_message_text("❌ Кормушка не найдена.")
            return

        active_feeder = await _run_sync(db.get_active_feeder, user_id, chat_id)
        if active_feeder:
            remaining = await _run_sync(db.get_feeder_cooldown_remaining, user_id, chat_id)
            await query.answer(
                f"Сначала дождитесь окончания активной кормушки ({self._format_seconds_compact(remaining)})",
                show_alert=True,
            )
            return

        tg_api = TelegramBotAPI(BOT_TOKEN)
        payload = self._build_booster_payload(feeder["code"], user_id, chat_id)
        invoice_url = await tg_api.create_invoice_link(
            title=feeder["name"],
            description=f"Активация кормушки +{feeder['bonus']}% на 1 час",
            payload=payload,
            currency="XTR",
            prices=[{"label": feeder["name"], "amount": int(feeder["price_stars"])}],
        )

        if not invoice_url:
            await query.edit_message_text("❌ Не удалось создать ссылку оплаты. Попробуйте позже.")
            return

        await self.send_invoice_url_button(
            chat_id=chat_id,
            invoice_url=invoice_url,
            text=(
                f"⭐ Оплатите {feeder['price_stars']} Telegram Stars для активации {feeder['name']} "
                f"(+{feeder['bonus']}% на 1 час)."
            ),
            user_id=user_id,
            timeout_sec=900,
            reply_to_message_id=query.message.message_id if query and query.message else None,
        )

        await query.edit_message_text("Ссылка на оплату отправлена. После оплаты кормушка активируется автоматически.")

    async def handle_buy_echosounder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка эхолота за Telegram Stars."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        remaining = await _run_sync(db.get_echosounder_remaining_seconds, user_id, chat_id)
        if remaining > 0:
            await query.answer(
                f"Эхолот уже активен: {self._format_seconds_compact(remaining)}",
                show_alert=True,
            )
            return

        tg_api = TelegramBotAPI(BOT_TOKEN)
        payload = self._build_booster_payload(ECHOSOUNDER_CODE, user_id, chat_id)
        invoice_url = await tg_api.create_invoice_link(
            title="Эхолот",
            description="Активация эхолота на 24 часа",
            payload=payload,
            currency="XTR",
            prices=[{"label": "Эхолот 24ч", "amount": ECHOSOUNDER_COST_STARS}],
        )

        if not invoice_url:
            await query.edit_message_text("❌ Не удалось создать ссылку оплаты. Попробуйте позже.")
            return

        await self.send_invoice_url_button(
            chat_id=chat_id,
            invoice_url=invoice_url,
            text=f"⭐ Оплатите {ECHOSOUNDER_COST_STARS} Telegram Stars для активации эхолота на 24 часа.",
            user_id=user_id,
            timeout_sec=900,
            reply_to_message_id=query.message.message_id if query and query.message else None,
        )

        await query.edit_message_text("Ссылка на оплату отправлена. После оплаты эхолот активируется автоматически.")
    
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
        result = await _run_sync(db.buy_net, user_id, net_name, chat_id)
        
        if result:
            net = await _run_sync(db.get_net, net_name)
            message = f"✅ Сеть '{net_name}' куплена!\n\n"
            message += f"🐟 Вытаскивает: {net['fish_count']} рыб\n"
            message += f"⏰ Кулдаун: {net['cooldown_hours']} часов\n"
            if net['max_uses'] == -1:
                message += "♾️ Использований: бесконечно"
            else:
                player_net = await _run_sync(db.get_player_net, user_id, net_name, chat_id)
                message += f"📦 Использований: {player_net['uses_left']}"
        else:
            player = await _run_sync(db.get_player, user_id, chat_id)
            net = await _run_sync(db.get_net, net_name)
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
        locations = await _run_sync(db.get_locations)
        if loc_idx >= len(locations):
            await query.edit_message_text("❌ Локация не найдена!")
            return
        location = locations[loc_idx]['name']
        
        # Получаем наживку
        baits = await _run_sync(db.get_baits_for_location, location)
        baits = [
            b for b in baits
            if b['name'].strip().lower() not in ('черви', LIVE_BAIT_NAME.lower())
        ]
        bait = next((b for b in baits if b.get('id') == bait_id), None)
        if not bait:
            await query.edit_message_text("❌ Наживка не найдена!")
            return
        if str(bait.get('name') or '').strip().lower() == LIVE_BAIT_NAME.lower():
            await query.edit_message_text("❌ Живца нельзя купить. Делайте его командой /bait.")
            return
        
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        
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
        bait_data = context.user_data.get('waiting_bait_quantity')
        if not bait_data:
            return
        
        bait_name = bait_data['bait_name']
        price = bait_data['price']
        max_qty = bait_data['max_qty']

        if str(bait_name or '').strip().lower() == LIVE_BAIT_NAME.lower():
            context.user_data.pop('waiting_bait_quantity', None)
            await update.message.reply_text("❌ Живца нельзя купить. Используйте /bait.")
            return
        
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
            
        # --- PREVENT ABUSE / SPAM RACE CONDITION ---
        # Удаляем состояние ввода ДО любых асинхронных запросов к БД!
        context.user_data.pop('waiting_bait_quantity', None)
        
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        total_cost = price * qty
        
        if player['coins'] < total_cost:
            await update.message.reply_text(f"❌ Недостаточно монет!\n\nНужно: {total_cost} 🪙\nУ вас: {player['coins']} 🪙")
            return
        
        # Покупаем
        await _run_sync(db.add_bait_to_inventory, user_id, bait_name, qty)
        await _run_sync(db.update_player, user_id, chat_id, coins=player['coins'] - total_cost)
        
        # Автоматически применяем купленную наживку
        await _run_sync(db.update_player_bait, user_id, chat_id, bait_name)
        
        new_balance = player['coins'] - total_cost
        
        # Очищаем состояние (уже удалено через pop выше, del не нужен)
        # del context.user_data['waiting_bait_quantity']
        
        await update.message.reply_text(
            f"✅ Куплено: {bait_name} x{qty}\n"
            f"🪱 Наживка автоматически применена!\n\n"
            f"💰 Потрачено: {total_cost} 🪙\n"
            f"💰 Баланс: {new_balance} 🪙"
        )

    async def handle_bait_convert_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline-конвертации рыбы в Живца."""
        query = update.callback_query
        data = query.data or ""
        match = re.match(r"^bait_convert_(all|\d+)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        qty_token, owner_id_raw = match.groups()
        owner_id = int(owner_id_raw)
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        quantity = 0 if qty_token == 'all' else int(qty_token)
        conversion = await _run_sync(db.convert_small_fish_to_live_bait, user_id=user_id, chat_id=chat_id, quantity=quantity)
        if not conversion.get('ok'):
            await query.edit_message_text(
                "❌ Не удалось выполнить конвертацию.\n"
                "Возможно, подходящая рыба уже закончилась.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
                ]),
            )
            return

        converted_by_fish = conversion.get('converted_by_fish') or {}
        lines = [f"• {name}: {qty}" for name, qty in converted_by_fish.items()]
        await query.edit_message_text(
            "✅ Конвертация завершена\n\n"
            f"Добавлено: {conversion.get('bait_name', LIVE_BAIT_NAME)} x{conversion.get('bait_added', 0)}\n"
            + ("\n".join(lines) if lines else ""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 В меню", callback_data=f"back_to_menu_{user_id}")]
            ]),
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
            [InlineKeyboardButton("🕸️ Сети", callback_data=f"shop_nets_{user_id}")],
            [InlineKeyboardButton("🧺 Кормушки и эхолот", callback_data=f"shop_feeders_{user_id}")],
            [InlineKeyboardButton("🍺 Пиво", callback_data=f"shop_beer_{user_id}")],
            [InlineKeyboardButton("🧨 Апгрейд взрывчатки", callback_data=f"shop_dynamite_upgrade_{user_id}")],
            [InlineKeyboardButton("👕 Одежда", callback_data=f"shop_clothing_{user_id}")],
            [InlineKeyboardButton("⛵ Лодки", callback_data=f"shop_boats_{user_id}")],
            [InlineKeyboardButton("💎 Обменник", callback_data=f"shop_exchange_{user_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]
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

    async def handle_shop_dynamite_upgrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экран апгрейда взрывчатки: динамит -> граната -> бомба."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        state = self._get_dynamite_upgrade_state(user_id, chat_id)
        level = int(state['level'])
        name = str(state['name'])
        max_weight = int(float(state['max_weight']))
        diamonds = int(player.get('diamonds') or 0)

        keyboard = []
        if state['next_level']:
            next_name = str(state['next_name'])
            next_weight = int(float(state['next_max_weight']))
            next_cost = int(state['next_upgrade_cost'] or 0)
            keyboard.append([
                InlineKeyboardButton(
                    f"⬆️ Улучшить до {next_name} ({next_weight} кг) — {next_cost} 💎",
                    callback_data=f"buy_dynamite_upgrade_{user_id}",
                )
            ])
            next_text = f"Следующий уровень: {next_name} ({next_weight} кг)\nСтоимость: {next_cost} 💎"
        else:
            next_text = "✅ Достигнут максимальный уровень: Бомба"

        keyboard.append([InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")])

        message = (
            "🧨 Апгрейд взрывчатки\n\n"
            f"Текущий уровень: {level}/3 — {name}\n"
            f"⚖️ Лимит веса рыбы: {max_weight} кг\n"
            f"💎 Ваши алмазы: {diamonds}\n\n"
            "Команда /dynamite, шансы, стоимость и КД остаются без изменений.\n\n"
            f"{next_text}"
        )

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_shop_clothing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экран перманентной одежды с постоянным бонусом шанса клёва."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        owned_items = await _run_sync(db.get_player_clothing, user_id)
        owned_codes = {str(item.get('item_key', '')).lower() for item in owned_items}
        diamonds = int(player.get('diamonds') or 0)

        keyboard = []
        for item in CLOTHING_ITEMS:
            item_code = item['code']
            if item_code in owned_codes:
                keyboard.append([
                    InlineKeyboardButton(
                        f"Куплено — {item['name']}",
                        callback_data="noop",
                    )
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{item['price_diamonds']} 💎 — {item['name']}",
                        callback_data=f"buy_clothing_{item_code}_{user_id}",
                    )
                ])

        keyboard.append([InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")])

        message = (
            "👕 Магазин одежды\n\n"
            "Каждый предмет покупается один раз и даёт постоянный бонус к шансу клёва.\n\n"
            f"💎 Ваши алмазы: {diamonds}\n"
            "✨ Бонусы применяются автоматически после покупки.\n"
            f"📦 Куплено: {len(owned_codes)}/{len(CLOTHING_ITEMS)}"
        )

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_buy_clothing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка перманентного предмета одежды за алмазы."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        payload = query.data[len("buy_clothing_"):]
        try:
            item_code, callback_user_id = payload.rsplit("_", 1)
        except ValueError:
            await query.answer("Некорректная кнопка покупки", show_alert=True)
            return

        if str(user_id) != callback_user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        item = CLOTHING_ITEM_BY_CODE.get(item_code)
        if not item:
            await query.edit_message_text("❌ Предмет одежды не найден.")
            return

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👕 К одежде", callback_data=f"shop_clothing_{user_id}")],
            [InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")],
        ])

        purchase_result = await _run_sync(db.purchase_clothing_item, user_id=user_id,
            chat_id=chat_id,
            item_key=item['code'],
            display_name=item['name'],
            bonus_percent=float(item['bonus_percent']),
            cost_diamonds=int(item['price_diamonds']),
        )

        reason = str(purchase_result.get('reason') or '')
        if not purchase_result.get('ok'):
            if reason == 'already_owned':
                await query.edit_message_text(
                    f"✅ {item['name']} уже куплен и даёт постоянный бонус +{format_percent_value(item['bonus_percent'])}%.",
                    reply_markup=back_keyboard,
                )
                return

            if reason == 'not_enough_diamonds':
                need = int(purchase_result.get('cost') or item['price_diamonds'])
                have = int(purchase_result.get('diamonds') or 0)
                missing = max(0, need - have)
                await query.edit_message_text(
                    "❌ Недостаточно алмазов для покупки\n\n"
                    f"Нужно: {need} 💎\n"
                    f"У вас: {have} 💎\n"
                    f"Не хватает: {missing} 💎",
                    reply_markup=back_keyboard,
                )
                return

            if reason == 'no_player':
                await query.edit_message_text(
                    "❌ Профиль не найден. Используйте /start",
                    reply_markup=back_keyboard,
                )
                return

            await query.edit_message_text(
                "❌ Не удалось выполнить покупку. Попробуйте ещё раз.",
                reply_markup=back_keyboard,
            )
            return

        total_bonus = float(purchase_result.get('total_bonus_percent') or 0.0)
        new_diamonds = int(purchase_result.get('new_diamonds') or 0)

        await query.edit_message_text(
            "✅ Покупка успешна!\n\n"
            f"👕 Предмет: {item['name']}\n"
            f"✨ Вечный бонус: +{format_percent_value(item['bonus_percent'])}%\n"
            f"💎 Списано: {int(item['price_diamonds'])} 💎\n"
            f"💎 Остаток: {new_diamonds} 💎\n"
            f"✨ Общий бонус одежды: +{format_percent_value(total_bonus)}%",
            reply_markup=back_keyboard,
        )

    async def handle_buy_dynamite_upgrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка апгрейда взрывчатки за алмазы."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        state = self._get_dynamite_upgrade_state(user_id, chat_id)
        current_level = int(state['level'])
        upgrade_cost = state.get('next_upgrade_cost')

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧨 К апгрейду", callback_data=f"shop_dynamite_upgrade_{user_id}")],
            [InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")],
        ])

        if current_level >= 3 or not upgrade_cost:
            await query.edit_message_text(
                "✅ У вас уже максимальный апгрейд взрывчатки: Бомба.",
                reply_markup=back_keyboard,
            )
            return

        diamonds = int(player.get('diamonds') or 0)
        cost = int(upgrade_cost)

        if diamonds < cost:
            missing = cost - diamonds
            await query.edit_message_text(
                "❌ Недостаточно алмазов для апгрейда\n\n"
                f"Нужно: {cost} 💎\n"
                f"У вас: {diamonds} 💎\n"
                f"Не хватает: {missing} 💎",
                reply_markup=back_keyboard,
            )
            return

        await _run_sync(db.subtract_diamonds, user_id, chat_id, cost)
        new_level = await _run_sync(db.set_dynamite_upgrade_level, user_id, chat_id, current_level + 1)
        new_state = self._get_dynamite_upgrade_state(user_id, chat_id)
        refreshed_player = await _run_sync(db.get_player, user_id, chat_id) or {}
        new_diamonds = int(refreshed_player.get('diamonds') or max(0, diamonds - cost))

        await query.edit_message_text(
            "✅ Апгрейд куплен!\n\n"
            f"Было: {state['name']} (ур. {current_level}/3, {int(float(state['max_weight']))} кг)\n"
            f"Стало: {new_state['name']} (ур. {new_level}/3, {int(float(new_state['max_weight']))} кг)\n"
            f"Списано: {cost} 💎\n"
            f"Остаток: {new_diamonds} 💎",
            reply_markup=back_keyboard,
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
            rods = await _run_sync(db.get_rods)
            rod_name = None
            for rod in rods:
                if rod['id'] == rod_id:
                    rod_name = rod['name']
                    break
            
            if not rod_name:
                await query.edit_message_text("❌ Удочка не найдена!")
                return
            
            # Покупаем удочку
            result = await _run_sync(db.buy_rod, user_id, chat_id, rod_name)
            
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
            baits = await _run_sync(db.get_baits)
            bait_name = None
            for bait in baits:
                if bait['id'] == bait_id:
                    bait_name = bait['name']
                    break
            
            if not bait_name:
                await query.edit_message_text("❌ Наживка не найдена!")
                return

            if bait_name.strip().lower() in ('черви', LIVE_BAIT_NAME.lower()):
                if bait_name.strip().lower() == LIVE_BAIT_NAME.lower():
                    await query.edit_message_text("❌ Живца нельзя купить. Используйте /bait.")
                else:
                    await query.edit_message_text("❌ Черви бесконечные и не продаются.")
                return
            
            # Покупаем наживку
            result = await _run_sync(db.add_bait_to_inventory, user_id, bait_name)
            
            if result:
                await query.edit_message_text(f"✅ Наживка {bait_name} куплена!")
            else:
                await query.edit_message_text("❌ Недостаточно монет!")
        elif callback_data.startswith("buy_boat_diamonds1_"):
            price = 50
            name = "Платная лодка"
            capacity = 3
            max_weight = 1500.0
            durability = 100
            ok = await _run_sync(db.buy_paid_boat, user_id, name=name, price=price, capacity=capacity, max_weight=max_weight, durability=durability)
            if ok:
                await query.edit_message_text(f"⛵ {name} куплена за {price} 💎!\n👥 Вместимость: {capacity}\n⚖️ Грузоподъёмность: {max_weight} кг\n🔧 Прочность: {durability}")
            else:
                await query.edit_message_text(f"❌ Не удалось купить {name}. Возможно, не хватает 💎 бриллиантов или у вас уже есть платная лодка.")
        elif callback_data.startswith("buy_boat_diamonds2_"):
            price = 150
            name = "Лодка 'Премиум'"
            capacity = 5
            max_weight = 600.0
            durability = 300
            ok = await _run_sync(db.buy_paid_boat, user_id, name=name, price=price, capacity=capacity, max_weight=max_weight, durability=durability)
            if ok:
                await query.edit_message_text(f"⛵ {name} куплена за {price} 💎! Вместимость: {capacity}, грузоподъёмность: {max_weight} кг, прочность: {durability}.")
            else:
                await query.edit_message_text(f"❌ Не удалось купить {name}. Возможно, не хватает бриллиантов или лодка уже есть.")
        elif callback_data.startswith("buy_boat_diamonds3_"):
            price = 500
            name = "Лодка 'Элитная'"
            capacity = 8
            max_weight = 2000.0
            durability = 1000
            ok = await _run_sync(db.buy_paid_boat, user_id, name=name, price=price, capacity=capacity, max_weight=max_weight, durability=durability)
            if ok:
                await query.edit_message_text(f"⛵ {name} куплена за {price} 💎! Вместимость: {capacity}, грузоподъёмность: {max_weight} кг, прочность: {durability}.")
            else:
                await query.edit_message_text(f"❌ Не удалось купить {name}. Возможно, не хватает бриллиантов или лодка уже есть.")
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
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        if player:
            if player['current_rod'] in TEMP_ROD_RANGES:
                await query.edit_message_text("❌ Эта удочка одноразовая и не ремонтируется.")
                return
            await _run_sync(db.repair_rod, user_id, player['current_rod'], chat_id)
            await query.edit_message_text("✅ Удочка починена!")
        else:
            await query.edit_message_text("❌ Ошибка: профиль не найден!")

    def _canonical_treasure_name(self, treasure_name: str) -> str:
        """Normalize treasure name so exchange can combine legacy/variant labels."""
        raw = (treasure_name or "").strip().lower()
        # Keep only letters/spaces to ignore emoji/punctuation noise in old rows.
        cleaned = re.sub(r"[^a-zа-яё\s]", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if "ракуш" in cleaned or "shell" in cleaned:
            return "Ракушка"
        if "жемч" in cleaned or "pearl" in cleaned:
            return "Жемчуг"
        return treasure_name or ""

    def _get_treasure_total(self, treasures: List[Dict[str, Any]], canonical_name: str) -> int:
        total = 0
        for item in treasures:
            name = item.get('treasure_name', '')
            qty = int(item.get('quantity', 0) or 0)
            if qty > 0 and self._canonical_treasure_name(name) == canonical_name:
                total += qty
        return total

    def _consume_treasure_total(self, user_id: int, chat_id: int, treasures: List[Dict[str, Any]], canonical_name: str, amount: int, reason: str = 'EXCHANGE') -> int:
        """Remove amount from matching treasure variants. Returns removed quantity."""
        remaining = int(amount)
        removed = 0
        for item in treasures:
            if remaining <= 0:
                break

            name = item.get('treasure_name', '')
            qty = int(item.get('quantity', 0) or 0)
            if qty <= 0:
                continue
            if self._canonical_treasure_name(name) != canonical_name:
                continue

            take = min(qty, remaining)
            db.remove_treasure(user_id, chat_id, name, take, reason=reason)
            remaining -= take
            removed += take

        return removed

    def _get_all_player_treasures(self, user_id: int, chat_id: int) -> List[Dict[str, Any]]:
        """Get user treasures across all chats, merged by treasure name."""
        merged: Dict[str, Dict[str, Any]] = {}
        for item in db.get_player_treasures_all_chats(user_id):
            name = str(item.get('treasure_name', '') or '').strip()
            qty = int(item.get('quantity', 0) or 0)
            scope_chat_id = int(item.get('chat_id', -1) or -1)
            if not name or qty <= 0:
                continue

            if name not in merged:
                merged[name] = {
                    'treasure_name': name,
                    'quantity': 0,
                    'sources': []
                }
            merged[name]['quantity'] += qty
            merged[name]['sources'].append({'chat_id': scope_chat_id, 'quantity': qty})

        # Stable order in UI
        return sorted(merged.values(), key=lambda t: str(t.get('treasure_name', '')))

    def _consume_treasure_total_all_scopes(self, user_id: int, treasures: List[Dict[str, Any]], canonical_name: str, amount: int, reason: str = 'EXCHANGE') -> int:
        """Remove amount from matching treasure variants across all scopes."""
        remaining = int(amount)
        removed = 0

        for item in treasures:
            if remaining <= 0:
                break

            name = item.get('treasure_name', '')
            qty = int(item.get('quantity', 0) or 0)
            if qty <= 0:
                continue
            if self._canonical_treasure_name(name) != canonical_name:
                continue

            for source in item.get('sources', []):
                if remaining <= 0:
                    break
                source_chat_id = int(source.get('chat_id', -1))
                source_qty = int(source.get('quantity', 0) or 0)
                if source_qty <= 0:
                    continue

                take = min(source_qty, remaining)
                db.remove_treasure(user_id, source_chat_id, name, take, reason=reason)
                remaining -= take
                removed += take

        return removed

    def _remove_treasure_any_scope(self, user_id: int, treasures: List[Dict[str, Any]], treasure_name: str, quantity: int, reason: str = 'SOLD') -> int:
        """Remove exact treasure name from merged treasures across scopes."""
        remaining = int(quantity)
        removed = 0

        for item in treasures:
            if remaining <= 0:
                break
            if item.get('treasure_name') != treasure_name:
                continue

            for source in item.get('sources', []):
                if remaining <= 0:
                    break
                source_chat_id = int(source.get('chat_id', -1))
                source_qty = int(source.get('quantity', 0) or 0)
                if source_qty <= 0:
                    continue

                take = min(source_qty, remaining)
                db.remove_treasure(user_id, source_chat_id, treasure_name, take, reason=reason)
                remaining -= take
                removed += take

        return removed
    
    async def handle_shop_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обменник драгоценностей и монет"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден. Используйте /start")
            return

        # Получаем количество бриллиантов и монет
        diamonds = int(player.get('diamonds') or 0)
        coins = player.get('coins', 0)
        treasures = self._get_all_player_treasures(user_id, chat_id)

        shells_count = self._get_treasure_total(treasures, 'Ракушка')
        pearls_count = self._get_treasure_total(treasures, 'Жемчуг')

        keyboard = [
            [InlineKeyboardButton(
                "💎 Купить бриллиант (500k монет)", 
                callback_data=f"exchange_buy_diamond_{user_id}"
            )],
            [InlineKeyboardButton(
                "💎 Продать бриллиант (250k монет)", 
                callback_data=f"exchange_sell_diamond_{user_id}"
            )],
            [InlineKeyboardButton(
                "🐚 x10 -> 💎 Жемчуг x1",
                callback_data=f"exchange_shell_to_pearl_{user_id}"
            )],
            [InlineKeyboardButton(
                "💎 Жемчуг x100 -> Бриллиант x1",
                callback_data=f"exchange_pearl_to_diamond_{user_id}"
            )],
            [InlineKeyboardButton(
                "💼 Продать сокровища",
                callback_data=f"inv_treasures_{user_id}"
            )],
            [InlineKeyboardButton("🔙 Магазин", callback_data=f"shop_{user_id}")]
        ]

        message = f"""
💎 Обменник драгоценностей

Ваши ресурсы:
💰 Монеты: {coins:,} 🪙
💎 Бриллианты: {diamonds}
🐚 Ракушка: {shells_count}
🦪 Жемчуг: {pearls_count}

📊 Курсы обмена:
💎 1 Бриллиант = 500,000 монет (покупка)
💎 1 Бриллиант = 250,000 монет (продажа)
🐚 10 Ракушек = 1 Жемчуг
🦪 100 Жемчуга = 1 Бриллиант

Выберите операцию:
        """

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_exchange_buy_diamond(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка бриллиантов за монеты"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден.")
            return

        coins = player.get('coins', 0)

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 К обменнику", callback_data=f"shop_exchange_{user_id}")]
        ])

        if coins < DIAMOND_BUY_PRICE:
            needed = DIAMOND_BUY_PRICE - coins
            await query.edit_message_text(
                f"❌ Недостаточно монет\n\n"
                f"Нужно: {DIAMOND_BUY_PRICE:,} 🪙\n"
                f"У вас: {coins:,} 🪙\n"
                f"Не хватает: {needed:,} 🪙",
                reply_markup=back_keyboard
            )
            return

        # Списываем монеты и добавляем бриллиант
        await _run_sync(db.update_player, user_id, chat_id, coins=coins - DIAMOND_BUY_PRICE)
        await _run_sync(db.add_diamonds, user_id, chat_id, 1)

        new_coins = coins - DIAMOND_BUY_PRICE
        new_diamonds = player.get('diamonds', 0) + 1

        await query.edit_message_text(
            f"✅ Успешная покупка!\n\n"
            f"Потрачено: {DIAMOND_BUY_PRICE:,} 🪙\n"
            f"Получено: 1 💎\n\n"
            f"💰 Новый баланс: {new_coins:,} 🪙\n"
            f"💎 Бриллианты: {new_diamonds}",
            reply_markup=back_keyboard
        )

    async def handle_exchange_sell_diamond(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Продажа бриллиантов за монеты"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден.")
            return

        diamonds = player.get('diamonds', 0)
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 К обменнику", callback_data=f"shop_exchange_{user_id}")]
        ])

        if diamonds <= 0:
            await query.edit_message_text(
                "❌ У вас нет бриллиантов для продажи.",
                reply_markup=back_keyboard
            )
            return

        # Добавляем монеты и вычитаем бриллиант
        coins = player.get('coins', 0)
        await _run_sync(db.update_player, user_id, chat_id, coins=coins + DIAMOND_SELL_PRICE)
        await _run_sync(db.subtract_diamonds, user_id, chat_id, 1)

        new_coins = coins + DIAMOND_SELL_PRICE
        new_diamonds = diamonds - 1

        await query.edit_message_text(
            f"✅ Успешно продано!\n\n"
            f"Получено: {DIAMOND_SELL_PRICE:,} 🪙\n"
            f"Продано: 1 💎\n\n"
            f"💰 Новый баланс: {new_coins:,} 🪙\n"
            f"💎 Бриллианты: {new_diamonds}",
            reply_markup=back_keyboard
        )

    async def handle_exchange_shell_to_pearl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обмен 10 ракушек на 1 жемчуг"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 К обменнику", callback_data=f"shop_exchange_{user_id}")]
        ])

        treasures = self._get_all_player_treasures(user_id, chat_id)
        shells = self._get_treasure_total(treasures, 'Ракушка')

        if shells < 10:
            await query.edit_message_text(
                f"❌ Недостаточно ракушек\n\n"
                f"Нужно: 10 🐚\n"
                f"У вас: {shells} 🐚",
                reply_markup=back_keyboard
            )
            return

        removed_shells = self._consume_treasure_total_all_scopes(user_id, treasures, 'Ракушка', 10)
        if removed_shells < 10:
            await query.edit_message_text(
                "❌ Не удалось списать нужное количество ракушек. Попробуйте снова.",
                reply_markup=back_keyboard
            )
            return

        await _run_sync(db.add_treasure, user_id, 'Жемчуг', 1, chat_id)

        await query.edit_message_text(
            f"✅ Обмен выполнен!\n\n"
            f"Списано: 10 🐚 Ракушка\n"
            f"Получено: 1 🦪 Жемчуг",
            reply_markup=back_keyboard
        )

    async def handle_exchange_pearl_to_diamond(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обмен 100 жемчуга на 1 бриллиант"""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 К обменнику", callback_data=f"shop_exchange_{user_id}")]
        ])

        treasures = self._get_all_player_treasures(user_id, chat_id)
        pearls = self._get_treasure_total(treasures, 'Жемчуг')

        if pearls < 100:
            await query.edit_message_text(
                f"❌ Недостаточно жемчуга\n\n"
                f"Нужно: 100 🦪\n"
                f"У вас: {pearls} 🦪",
                reply_markup=back_keyboard
            )
            return

        removed_pearls = self._consume_treasure_total_all_scopes(user_id, treasures, 'Жемчуг', 100)
        if removed_pearls < 100:
            await query.edit_message_text(
                "❌ Не удалось списать нужное количество жемчуга. Попробуйте снова.",
                reply_markup=back_keyboard
            )
            return

        await _run_sync(db.add_diamonds, user_id, chat_id, 1)

        await query.edit_message_text(
            f"✅ Обмен выполнен!\n\n"
            f"Списано: 100 🦪 Жемчуг\n"
            f"Получено: 1 💎 Бриллиант",
            reply_markup=back_keyboard
        )
    
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
            try:
                await query.answer()
            except Exception:
                pass
        else:
            query = None

        try:
            # Получаем всю непроданную рыбу пользователя
            caught_fish = await _run_sync(db.get_caught_fish, user_id, chat_id, only_unsold=True)
        except Exception as e:
            logger.exception("handle_sell_fish: db.get_caught_fish failed user=%s chat=%s: %s", user_id, chat_id, e)
            _err_text = "❌ Не удалось загрузить улов. Попробуйте позже."
            try:
                if query:
                    await query.edit_message_text(_err_text)
                else:
                    await update.message.reply_text(_err_text)
            except Exception:
                pass
            return

        # Фильтруем от мусора
        unsold_fish = [
            f for f in caught_fish
            if not bool(f.get('is_trash'))
        ]
        
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
            price = fish.get('price') or 0
            if name not in fish_counts:
                fish_counts[name] = {
                    'count': 0,
                    'total_price': 0,
                    'fish_id': fish['id']
                }
            fish_counts[name]['count'] += 1
            fish_counts[name]['total_price'] += price
            total_value += price

        # --- ПАГИНАЦИЯ ---
        # Получаем текущую страницу из callback_data или context.user_data
        page = 0
        if query and query.data.startswith("sell_page_"):
            try:
                page = int(query.data.split('_')[2])
            except Exception:
                page = 0
        elif hasattr(context, 'user_data') and 'sell_page' in context.user_data:
            page = context.user_data['sell_page']
        else:
            page = 0
        fish_list = sorted(fish_counts.items())
        # Store full name mapping so handle_sell_species can look up by index
        context.user_data['sell_fish_names'] = {str(i): name for i, (name, _) in enumerate(fish_list)}
        page_size = 10
        total_pages = max(1, (len(fish_list) + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        context.user_data['sell_page'] = page
        start = page * page_size
        end = start + page_size
        page_fish = fish_list[start:end]

        keyboard = []
        for i, (fish_name, info) in enumerate(page_fish):
            full_idx = start + i
            button_text = f"{fish_name} (×{info['count']}) - {info['total_price']} 🪙"
            # Use numeric index to keep callback_data within Telegram's 64-byte limit
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"sell_sp_{full_idx}_{user_id}")])

        # Добавляем кнопку продажи всего
        if total_value > 0:
            keyboard.append([InlineKeyboardButton(f"💰 Продать всё ({total_value} 🪙)", callback_data=f"sell_all_{user_id}")])

        # Стрелки пагинации
        nav_buttons = []
        if total_pages > 1:
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"sell_page_{page-1}_{user_id}"))
            nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"sell_page_{page+1}_{user_id}"))
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        market = self._get_market_offer_snapshot(create_if_missing=True)
        market_line = ""
        if market:
            market_line = (
                f"\n🎯 Рынок дня: {market.get('fish_name')} x{float(market.get('multiplier') or 1.0):.2f} "
                f"({float(market.get('sold_weight') or 0):.1f}/{float(market.get('target_weight') or 0):.1f} кг)"
            )

        message = (
            "🐟 Лавка рыбы\n\n"
            f"Всего рыбы к продаже: {len(unsold_fish)}\n"
            f"Общая стоимость: {total_value} 🪙"
            f"{market_line}\n"
            "📈 Динамика: много продаж за час -> цена ниже, редкие продажи -> немного выше\n\n"
            "Выберите что продать:"
        )

        try:
            if query:
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.exception("handle_sell_fish: failed to send menu user=%s: %s", user_id, e)

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
        summary = await _run_sync(db.get_inventory_summary, user_id, chat_id)
        locations = dict(summary.get('location_counts') or {})
        unsold_regular_count = int(summary.get('regular_count', 0) or 0)
        unsold_trash_count = int(summary.get('trash_count', 0) or 0)
        total_treasures = int(summary.get('total_treasures', 0) or 0)
        trophy_count = int(summary.get('trophy_count', 0) or 0)

        if unsold_regular_count <= 0 and unsold_trash_count <= 0 and total_treasures <= 0 and trophy_count <= 0:
            message = "🎒 Инвентарь\n\nУ вас нет пойманной рыбы и сокровищ."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, reply_markup=reply_markup)
            return
        
        # Группируем по локациям (с фильтром на корректные названия)

        # Создаем кнопки разделов инвентаря
        keyboard = []
        for location in sorted(locations.keys(), key=lambda v: str(v)):
            fish_count = int(locations.get(location, 0) or 0)
            location_label = str(location)
            button_text = f"📍 {location_label} ({fish_count} рыб)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"inv_location_{location_label.replace(' ', '_')}_{user_id}")])

        if total_treasures > 0:
            keyboard.append([InlineKeyboardButton(f"💎 Сокровища ({total_treasures})", callback_data=f"inv_treasures_{user_id}")])

        if unsold_trash_count > 0:
            keyboard.append([InlineKeyboardButton(f"🗑️ Мусор ({unsold_trash_count})", callback_data=f"inv_trash_{user_id}")])

        keyboard.append([InlineKeyboardButton(f"🏆 Трофеи ({trophy_count})", callback_data=f"inv_trophies_{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        has_location_fish = bool(locations)
        if has_location_fish:
            message = (
                "🎒 Инвентарь\n\n"
                f"🐟 Рыба для просмотра: {unsold_regular_count}\n"
                f"🗑️ Мусор: {unsold_trash_count}\n"
                f"💎 Сокровища: {total_treasures}\n"
                f"🏆 Трофеи: {trophy_count}\n\n"
                "Выберите раздел:"
            )
        else:
            message = (
                "🎒 Инвентарь\n\n"
                "У вас нет рыбы с корректной локацией.\n"
                f"🗑️ Мусор: {unsold_trash_count}\n"
                f"💎 Сокровища: {total_treasures}\n"
                f"🏆 Трофеи: {trophy_count}\n\n"
                "Выберите раздел:"
            )

        if query:
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_inventory_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рыбу с определенной локации в инвентаре"""
        query = update.callback_query
        data = query.data or ""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_location")
            return
        
        # Проверка прав доступа
        owner_id = None
        if data.startswith("inv_location_") and "_page_" in data:
            try:
                before_page = data.split("_page_", 1)[0]
                owner_id = int(before_page.rsplit("_", 1)[-1])
            except Exception:
                owner_id = None
        else:
            try:
                owner_id = int(data.rsplit("_", 1)[-1])
            except Exception:
                owner_id = None

        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        # Извлекаем локацию из callback_data
        # Формат: inv_location_{location}_{user_id}
        # Для пагинации формат: inv_location_{location}_{user_id}_page_{page}
        if data.startswith("inv_location_") and "_page_" in data:
            location_part = data[len("inv_location_"):].split("_page_", 1)[0]
            location = '_'.join(location_part.split('_')[:-1]).replace('_', ' ')
        else:
            parts = data.split('_')
            # Локация может содержать подчеркивания, поэтому берем все до последнего user_id
            location = '_'.join(parts[2:-1]).replace('_', ' ')
        
        await query.answer()
        
        # Получаем рыбу с этой локации
        caught_fish = await _run_sync(db.get_caught_fish, user_id, chat_id, only_unsold=True)
        location_fish = [f for f in caught_fish if f['location'] == location]

        if not location_fish:
            await query.edit_message_text(f"На локации {location} нет пойманной рыбы.")
            return

        # --- ПАГИНАЦИЯ ---
        page = 0
        # Формат callback_data: inv_location_{location}_{user_id}_page_{page}
        if data.startswith("inv_location_") and "_page_" in data:
            try:
                page = int(data.split("_page_")[-1])
            except Exception:
                page = 0
        elif hasattr(context, 'user_data') and 'inv_page' in context.user_data:
            page = context.user_data['inv_page']
        else:
            page = 0
        page_size = 10
        total_pages = max(1, (len(location_fish) + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        context.user_data['inv_page'] = page
        start = page * page_size
        end = start + page_size
        page_fish = location_fish[start:end]

        # Кнопки по каждой рыбе (индивидуально)
        keyboard = []
        rarity_emoji = {
            'Обычная': '⚪',
            'Редкая': '🔵',
            'Легендарная': '🟡',
            'Мифическая': '🔴'
        }
        for fish in page_fish:
            fish_name = fish.get('fish_name', '')
            weight = fish.get('weight', 0)
            length_val = fish.get('length', 0)
            length_str = f" | {length_val} см" if length_val and length_val > 0 else ""
            rarity = fish.get('rarity', 'Обычная')
            trash = fish.get('is_trash', False)
            btn_text = f"🗑️ {fish_name} ({weight} кг)" if trash else f"{rarity_emoji.get(rarity, '⚪')} {fish_name} ({weight} кг{length_str})"
            # Можно добавить callback для подробностей или продажи одной рыбы
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="noop")])

        # Стрелки пагинации
        nav_buttons = []
        if total_pages > 1:
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"inv_location_{location.replace(' ', '_')}_{user_id}_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"inv_location_{location.replace(' ', '_')}_{user_id}_page_{page+1}"))
            keyboard.append(nav_buttons)

        # Кнопка назад
        keyboard.append([InlineKeyboardButton("◀️ Назад к локациям", callback_data=f"inventory_{user_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        location_text = html.escape(str(location))
        message = (
            f"📍 {location_text}\n\n"
            "Рыба на этой локации показана кнопками ниже.\n\n"
            f"Страница: {page+1}/{total_pages}\n"
            f"Всего рыбы: {len(location_fish)}"
        )

        try:
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error editing inventory location message: {e}")
            await query.edit_message_text("❌ Ошибка при показе инвентаря локации.")

    async def handle_inventory_trash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ отдельной вкладки мусора в инвентаре."""
        query = update.callback_query
        data = query.data or ""

        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user/chat in handle_inventory_trash")
            return

        page = 0
        owner_id = None
        page_match = re.match(r"^inv_trash_page_(\d+)_(\d+)$", data)
        base_match = re.match(r"^inv_trash_(\d+)$", data)
        if page_match:
            page = int(page_match.group(1))
            owner_id = int(page_match.group(2))
        elif base_match:
            owner_id = int(base_match.group(1))

        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        trash_summary = await _run_sync(db.get_unsold_trash_summary, user_id, chat_id)
        if not trash_summary:
            await query.edit_message_text(
                "🗑️ Мусор\n\nУ вас нет непроданного мусора.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад в инвентарь", callback_data=f"inventory_{user_id}")]
                ]),
            )
            return

        total_items = sum(int(item.get('quantity') or 0) for item in trash_summary)
        total_value = sum(int(item.get('total_price') or 0) for item in trash_summary)
        total_weight = sum(float(item.get('total_weight') or 0.0) for item in trash_summary)

        page_size = 8
        total_pages = max(1, (len(trash_summary) + page_size - 1) // page_size)
        safe_page = max(0, min(page, total_pages - 1))
        start = safe_page * page_size
        page_items = trash_summary[start:start + page_size]

        trash_item_map: Dict[str, str] = {}
        keyboard = []
        clan = await _run_sync(db.get_clan_by_user, user_id)
        for idx, item in enumerate(page_items, start=start):
            item_name = str(item.get('fish_name') or '')
            qty = int(item.get('quantity') or 0)
            unit_price = int(item.get('unit_price') or 0)
            trash_item_map[str(idx)] = item_name

            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {item_name} x{qty} ({unit_price} 🪙)",
                    callback_data="noop",
                )
            ])

            if clan:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏗️ Пожертвовать 1 {item_name}",
                        callback_data=f"clan_donate_{idx}_{user_id}",
                    )
                ])

        context.user_data['trash_item_map'] = trash_item_map

        keyboard.append([
            InlineKeyboardButton(
                f"💰 Продать весь мусор ({total_value} 🪙)",
                callback_data=f"inv_trash_sell_all_{user_id}",
            )
        ])

        if total_pages > 1:
            nav = []
            if safe_page > 0:
                nav.append(InlineKeyboardButton("⬅️", callback_data=f"inv_trash_page_{safe_page - 1}_{user_id}"))
            nav.append(InlineKeyboardButton(f"{safe_page + 1}/{total_pages}", callback_data="noop"))
            if safe_page < total_pages - 1:
                nav.append(InlineKeyboardButton("➡️", callback_data=f"inv_trash_page_{safe_page + 1}_{user_id}"))
            keyboard.append(nav)

        keyboard.append([InlineKeyboardButton("◀️ Назад в инвентарь", callback_data=f"inventory_{user_id}")])

        clan_line = f"\n🏗️ Артель: {clan.get('name')}" if clan else ""
        message = (
            "🗑️ Мусор\n\n"
            f"Всего предметов: {total_items}\n"
            f"Общий вес: {total_weight:.2f} кг\n"
            f"Оценка при продаже: {total_value} 🪙"
            f"{clan_line}\n\n"
            "Выберите действие:"
        )
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_inventory_trash_sell_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Продажа всего непроданного мусора отдельной кнопкой инвентаря."""
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        catches = await _run_sync(db.get_caught_fish, user_id, chat_id, only_unsold=True)
        unsold_trash = [item for item in catches if bool(item.get('is_trash'))]
        if not unsold_trash:
            await query.edit_message_text(
                "🗑️ Нечего продавать: у вас нет непроданного мусора.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад в инвентарь", callback_data=f"inventory_{user_id}")]
                ]),
            )
            return

        total_value = int(sum(int(item.get('price') or 0) for item in unsold_trash))
        fish_ids = [int(item['id']) for item in unsold_trash]
        player = await _run_sync(db.get_player, user_id, chat_id)
        old_balance = int((player or {}).get('coins', 0) or 0)

        await _run_sync(db.mark_fish_as_sold, fish_ids)
        await _run_sync(db.update_player, user_id, chat_id, coins=old_balance + total_value)

        xp_earned = len(unsold_trash)
        level_info = await _run_sync(db.add_player_xp, user_id, chat_id, xp_earned)

        await query.edit_message_text(
            "✅ Мусор продан\n\n"
            f"Предметов: {len(unsold_trash)}\n"
            f"Получено: {total_value} 🪙\n"
            f"Опыт: +{xp_earned}\n"
            f"{format_level_progress(level_info)}\n"
            f"Новый баланс: {old_balance + total_value} 🪙",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ К мусору", callback_data=f"inv_trash_{user_id}")],
                [InlineKeyboardButton("◀️ В инвентарь", callback_data=f"inventory_{user_id}")],
            ]),
        )

    async def handle_clan_donate_trash_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пожертвование одной единицы выбранного мусора в артель из вкладки мусора."""
        query = update.callback_query
        data = query.data or ''
        match = re.match(r"^clan_donate_(\d+)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная кнопка", show_alert=True)
            return

        item_idx, owner_id_raw = match.groups()
        owner_id = int(owner_id_raw)
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if user_id != owner_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        item_map = context.user_data.get('trash_item_map', {}) or {}
        item_name = item_map.get(str(item_idx))
        if not item_name:
            await query.answer("Список мусора устарел, откройте вкладку заново", show_alert=True)
            return

        await query.answer()
        donated = await _run_sync(db.donate_trash_to_clan, user_id, chat_id, item_name, 1)
        if not donated.get('ok'):
            reason = donated.get('reason')
            if reason == 'not_in_clan':
                await query.edit_message_text(
                    "❌ Вы не состоите в артели.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад в инвентарь", callback_data=f"inventory_{user_id}")]
                    ]),
                )
                return

            if reason == 'not_enough_trash':
                await query.edit_message_text(
                    "❌ Такой мусор закончился в инвентаре.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🗑️ Обновить", callback_data=f"inv_trash_{user_id}")],
                        [InlineKeyboardButton("◀️ В инвентарь", callback_data=f"inventory_{user_id}")],
                    ]),
                )
                return

            await query.edit_message_text(
                "❌ Не удалось выполнить пожертвование.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑️ Обновить", callback_data=f"inv_trash_{user_id}")],
                    [InlineKeyboardButton("◀️ В инвентарь", callback_data=f"inventory_{user_id}")],
                ]),
            )
            return

        await query.edit_message_text(
            "✅ Пожертвование отправлено\n\n"
            f"Предмет: {donated.get('item_name')}\n"
            f"Передано: {donated.get('donated')}\n"
            f"Итого в артели: {donated.get('clan_total')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Обновить", callback_data=f"inv_trash_{user_id}")],
                [InlineKeyboardButton("◀️ В инвентарь", callback_data=f"inventory_{user_id}")],
            ]),
        )
    
    async def handle_inventory_treasures(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать сокровища в инвентаре"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_treasures")
            return
        
        # Проверка прав доступа
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        from treasures import get_treasure_name
        
        # Получаем все сокровища игрока
        treasures = self._get_all_player_treasures(user_id, chat_id)
        
        if not treasures:
            message = "💎 Клад\n\nУ вас нет сокровищ."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            return
        
        # Создаем кнопки для каждого сокровища
        keyboard = []
        for treasure in treasures:
            treasure_name = treasure.get('treasure_name', '')
            quantity = treasure.get('quantity', 0)
            if quantity > 0:
                display_name = get_treasure_name(treasure_name)
                button_text = f"{display_name} ({quantity})"
                callback_data = f"sell_treasure_{treasure_name.replace(' ', '_')}_{user_id}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        if not keyboard:
            message = "💎 Клад\n\nУ вас нет сокровищ."
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu_{user_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "💎 <b>Клад</b>\n\nВаши сокровища:"
        
        try:
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            if "Message is not modified" in str(e):
                return
            logger.error(f"Error editing treasures inventory message: {e}")
            try:
                await query.edit_message_text("💎 Клад\n\nВаши сокровища:")
            except Exception:
                pass

    async def _render_inventory_trophies_menu(self, query, user_id: int, page: int = 0):
        trophies = await _run_sync(db.get_player_trophies, user_id)
        total = len(trophies)
        page_size = TROPHY_LIST_PAGE_SIZE
        total_pages = max(1, (total + page_size - 1) // page_size)
        safe_page = max(0, min(page, total_pages - 1))

        keyboard = []
        if total > 0:
            start = safe_page * page_size
            end = start + page_size
            page_items = trophies[start:end]

            for trophy in page_items:
                fish_name = str(trophy.get('fish_name') or 'Неизвестная рыба')
                try:
                    weight_value = float(trophy.get('weight') or 0)
                except (TypeError, ValueError):
                    weight_value = 0.0
                try:
                    length_value = float(trophy.get('length') or 0)
                except (TypeError, ValueError):
                    length_value = 0.0

                active_mark = "✅" if int(trophy.get('is_active') or 0) == 1 else "▫️"
                length_part = f", {length_value:.1f} см" if length_value > 0 else ""
                button_text = f"{active_mark} {fish_name} ({weight_value:.2f} кг{length_part})"
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=f"inv_trophy_set_{int(trophy['id'])}_{user_id}")
                ])

            if total_pages > 1:
                nav_buttons = []
                if safe_page > 0:
                    nav_buttons.append(
                        InlineKeyboardButton("⬅️", callback_data=f"inv_trophies_page_{safe_page - 1}_{user_id}")
                    )
                nav_buttons.append(InlineKeyboardButton(f"{safe_page + 1}/{total_pages}", callback_data="noop"))
                if safe_page < total_pages - 1:
                    nav_buttons.append(
                        InlineKeyboardButton("➡️", callback_data=f"inv_trophies_page_{safe_page + 1}_{user_id}")
                    )
                keyboard.append(nav_buttons)

        keyboard.append([
            InlineKeyboardButton(
                f"➕ Добавить трофей ({TROPHY_CREATE_COST_COINS} 🪙)",
                callback_data=f"inv_trophy_add_{user_id}",
            )
        ])
        keyboard.append([InlineKeyboardButton("◀️ Назад в инвентарь", callback_data=f"inventory_{user_id}")])

        active = next((item for item in trophies if int(item.get('is_active') or 0) == 1), None)
        if active:
            try:
                active_weight = float(active.get('weight') or 0)
            except (TypeError, ValueError):
                active_weight = 0.0
            try:
                active_length = float(active.get('length') or 0)
            except (TypeError, ValueError):
                active_length = 0.0
            active_line = f"Активный: {active.get('fish_name')} ({active_weight:.2f} кг, {active_length:.1f} см)"
        else:
            active_line = "Активный: не выбран"

        if total == 0:
            message = (
                "🏆 Трофеи\n\n"
                "У вас пока нет трофеев.\n"
                "Нажмите «Добавить трофей», выберите рыбу и заплатите 10000 🪙."
            )
        else:
            message = (
                "🏆 Трофеи\n\n"
                f"Всего трофеев: {total}\n"
                f"{active_line}\n\n"
                "Нажмите на трофей в списке, чтобы сделать его активным."
            )

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_inventory_trophies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список трофеев пользователя и управление активным трофеем."""
        query = update.callback_query
        data = query.data or ""

        try:
            user_id = update.effective_user.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_trophies")
            return

        page = 0
        owner_id = None
        page_match = re.match(r"^inv_trophies_page_(\d+)_(\d+)$", data)
        base_match = re.match(r"^inv_trophies_(\d+)$", data)
        if page_match:
            page = int(page_match.group(1))
            owner_id = int(page_match.group(2))
        elif base_match:
            owner_id = int(base_match.group(1))

        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()
        await self._render_inventory_trophies_menu(query, user_id, page=page)

    async def handle_inventory_trophy_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рыбу для конвертации в трофей (с пагинацией)."""
        query = update.callback_query
        data = query.data or ""

        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_trophy_add")
            return

        page = 0
        owner_id = None
        page_match = re.match(r"^inv_trophy_add_page_(\d+)_(\d+)$", data)
        base_match = re.match(r"^inv_trophy_add_(\d+)$", data)
        if page_match:
            page = int(page_match.group(1))
            owner_id = int(page_match.group(2))
        elif base_match:
            owner_id = int(base_match.group(1))

        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()


        async def _render_trophy_add() -> None:
            try:
                player, caught_fish = await asyncio.gather(
                    _run_sync(db.get_player, user_id, chat_id),
                    _run_sync(db.get_caught_fish, user_id, chat_id, True),
                )
                balance = int(player.get('coins', 0)) if player else 0

                candidates = [
                    fish for fish in caught_fish
                    if not bool(fish.get('is_trash'))
                ]
                candidates.sort(key=lambda item: float(item.get('weight') or 0), reverse=True)

                keyboard = []
                if not candidates:
                    keyboard.append([InlineKeyboardButton("◀️ К трофеям", callback_data=f"inv_trophies_{user_id}")])
                    await query.edit_message_text(
                        "➕ Добавить трофей\n\n"
                        "У вас нет рыбы для создания трофея.\n"
                        "Поймайте рыбу и попробуйте снова.",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    return

                page_size = TROPHY_ADD_PAGE_SIZE
                total = len(candidates)
                total_pages = max(1, (total + page_size - 1) // page_size)
                safe_page = max(0, min(page, total_pages - 1))
                start = safe_page * page_size
                end = start + page_size
                page_items = candidates[start:end]

                for fish in page_items:
                    fish_name = str(fish.get('fish_name') or 'Неизвестная рыба')
                    fish_id = int(fish.get('id') or 0)
                    try:
                        fish_weight = float(fish.get('weight') or 0)
                    except (TypeError, ValueError):
                        fish_weight = 0.0
                    try:
                        fish_length = float(fish.get('length') or 0)
                    except (TypeError, ValueError):
                        fish_length = 0.0

                    button_text = f"🐟 {fish_name} ({fish_weight:.2f} кг, {fish_length:.1f} см)"
                    keyboard.append([
                        InlineKeyboardButton(button_text, callback_data=f"inv_trophy_make_{fish_id}_{user_id}")
                    ])

                if total_pages > 1:
                    nav_buttons = []
                    if safe_page > 0:
                        nav_buttons.append(
                            InlineKeyboardButton("⬅️", callback_data=f"inv_trophy_add_page_{safe_page - 1}_{user_id}")
                        )
                    nav_buttons.append(InlineKeyboardButton(f"{safe_page + 1}/{total_pages}", callback_data="noop"))
                    if safe_page < total_pages - 1:
                        nav_buttons.append(
                            InlineKeyboardButton("➡️", callback_data=f"inv_trophy_add_page_{safe_page + 1}_{user_id}")
                        )
                    keyboard.append(nav_buttons)

                keyboard.append([InlineKeyboardButton("◀️ К трофеям", callback_data=f"inv_trophies_{user_id}")])

                message = (
                    "➕ Добавить трофей\n\n"
                    f"Стоимость создания: {TROPHY_CREATE_COST_COINS} 🪙\n"
                    f"Ваш баланс: {balance} 🪙\n"
                    f"Доступно рыбы: {total}\n\n"
                    "Выберите рыбу для превращения в трофей:"
                )
                await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                logger.exception("handle_inventory_trophy_add failed for user=%s chat=%s", user_id, chat_id)
                try:
                    await query.edit_message_text("❌ Не удалось открыть трофеи. Попробуйте позже.")
                except Exception:
                    pass

        asyncio.create_task(_render_trophy_add())
        return

    async def handle_inventory_trophy_make(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Конвертировать выбранную рыбу в трофей за монеты."""
        query = update.callback_query
        data = query.data or ""

        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_trophy_make")
            return

        match = re.match(r"^inv_trophy_make_(\d+)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная команда", show_alert=True)
            return

        fish_id = int(match.group(1))
        owner_id = int(match.group(2))
        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        await query.answer()

        result = await _run_sync(db.create_trophy_from_catch, user_id=user_id,
            chat_id=chat_id,
            caught_fish_id=fish_id,
            cost_coins=TROPHY_CREATE_COST_COINS,
        )

        if not result.get('ok'):
            error_code = result.get('error')
            if error_code == 'insufficient_coins':
                balance = int(result.get('balance', 0) or 0)
                required = int(result.get('required', TROPHY_CREATE_COST_COINS) or TROPHY_CREATE_COST_COINS)
                message = (
                    "❌ Недостаточно монет\n\n"
                    f"Нужно: {required} 🪙\n"
                    f"У вас: {balance} 🪙"
                )
            elif error_code == 'fish_not_found':
                message = "❌ Эта рыба уже недоступна. Откройте список заново."
            elif error_code == 'profile_not_found':
                message = "❌ Профиль не найден. Нажмите /start и попробуйте снова."
            else:
                message = "❌ Не удалось создать трофей. Попробуйте снова."

            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=f"inv_trophy_add_{user_id}")]]
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        trophy = result.get('trophy') or {}
        fish_name = str(trophy.get('fish_name') or 'Неизвестная рыба')
        weight = float(trophy.get('weight') or 0)
        length = float(trophy.get('length') or 0)
        new_balance = int(result.get('new_balance', 0) or 0)
        cost = int(result.get('cost', TROPHY_CREATE_COST_COINS) or TROPHY_CREATE_COST_COINS)

        message = (
            "✅ Трофей создан\n\n"
            f"🐟 Рыба: {fish_name}\n"
            f"⚖️ Вес: {weight:.2f} кг\n"
            f"📏 Размер: {length:.1f} см\n"
            f"💸 Списано: {cost} 🪙\n"
            f"💰 Баланс: {new_balance} 🪙"
        )

        keyboard = [
            [InlineKeyboardButton("🏆 К трофеям", callback_data=f"inv_trophies_{user_id}")],
            [InlineKeyboardButton("➕ Добавить ещё", callback_data=f"inv_trophy_add_{user_id}")],
            [InlineKeyboardButton("🔙 В инвентарь", callback_data=f"inventory_{user_id}")],
        ]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_inventory_trophy_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сделать выбранный трофей активным для отображения в мини-апке."""
        query = update.callback_query
        data = query.data or ""

        try:
            user_id = update.effective_user.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_inventory_trophy_set")
            return

        match = re.match(r"^inv_trophy_set_(\d+)_(\d+)$", data)
        if not match:
            await query.answer("Некорректная команда", show_alert=True)
            return

        trophy_id = int(match.group(1))
        owner_id = int(match.group(2))
        if owner_id != user_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        success = await _run_sync(db.set_active_trophy, user_id, trophy_id)
        if not success:
            await query.answer("Трофей не найден", show_alert=True)
            return

        await query.answer("✅ Активный трофей обновлен")
        await self._render_inventory_trophies_menu(query, user_id, page=0)
    
    async def handle_sell_treasure(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Продажа предмета из клада"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_sell_treasure")
            return
        
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        
        await query.answer()
        
        from treasures import get_treasure_name, get_treasure_sell_price, get_treasure_sell_xp
        
        # Парсим callback_data: sell_treasure_{treasure_name}_{user_id}
        parts = query.data.split('_')
        treasure_key = '_'.join(parts[2:-1])  # Все части кроме "sell_treasure" и user_id
        treasure_key = treasure_key.replace('_', ' ')
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await query.edit_message_text("❌ Профиль не найден.")
            return
        
        # Получаем информацию о сокровище
        treasures = self._get_all_player_treasures(user_id, chat_id)
        treasure_obj = None
        for t in treasures:
            if t.get('treasure_name') == treasure_key:
                treasure_obj = t
                break
        
        if not treasure_obj or treasure_obj.get('quantity', 0) <= 0:
            await query.edit_message_text(f"❌ У вас нет предмета '{treasure_key}' для продажи.")
            return
        
        # Получаем награды
        sell_price = get_treasure_sell_price(treasure_key)
        sell_xp = get_treasure_sell_xp(treasure_key)
        display_name = get_treasure_name(treasure_key)
        
        # Выполняем продажу
        coins = player.get('coins', 0)
        xp = player.get('xp', 0)

        removed = self._remove_treasure_any_scope(user_id, treasures, treasure_key, 1)
        if removed < 1:
            await query.edit_message_text("❌ Не удалось продать сокровище. Попробуйте снова.")
            return

        await _run_sync(db.update_player, user_id, chat_id, coins=coins + sell_price, xp=xp + sell_xp)
        
        # Получаем обновленные данные
        remaining = treasure_obj.get('quantity', 0) - 1
        
        message = (
            f"✅ <b>Продано!</b>\n\n"
            f"{display_name}\n\n"
            f"Получено:\n"
            f"  💰 {sell_price} монет\n"
            f"  ✨ {sell_xp} опыта\n\n"
            f"Осталось: {remaining}"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад к кладу", callback_data=f"inv_treasures_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")
    
    async def handle_sell_species(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Продажа конкретного вида рыбы"""
        query = update.callback_query
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
        except (AttributeError, TypeError):
            logger.error("Failed to get user_id in handle_sell_species")
            return
        
        # Проверка прав доступа
        # Формат: sell_sp_{idx}_{user_id}
        if not query.data.endswith(f"_{user_id}"):
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return

        # Извлекаем индекс из callback_data и ищем имя в context.user_data
        parts = query.data.split('_')
        fish_idx_str = parts[2] if len(parts) > 2 else None
        fish_name = None
        if fish_idx_str is not None:
            fish_name = context.user_data.get('sell_fish_names', {}).get(fish_idx_str)
        if not fish_name:
            await query.answer("Сессия устарела, откройте лавку заново.", show_alert=True)
            return
        
        await query.answer()
        
        # Получаем всю рыбу этого вида
        caught_fish = await _run_sync(db.get_caught_fish, user_id, chat_id, only_unsold=True)
        species_fish = [
            f for f in caught_fish
            if f['fish_name'] == fish_name and not bool(f.get('is_trash'))
        ]
        
        if not species_fish:
            await query.edit_message_text("Рыба этого вида не найдена.")
            return
        
        if len(species_fish) == 1:
            total_value = species_fish[0]['price']
            player = await _run_sync(db.get_player, user_id, chat_id)
            await _run_sync(db.mark_fish_as_sold, [species_fish[0]['id']])
            await _run_sync(db.update_player, user_id, chat_id, coins=player['coins'] + total_value)

            xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary([species_fish[0]])
            level_info = await _run_sync(db.add_player_xp, user_id, chat_id, xp_earned)
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
        caught_fish = await _run_sync(db.get_caught_fish, user_id, chat_id, only_unsold=True)
        unsold_fish = [
            f for f in caught_fish
            if not bool(f.get('is_trash'))
        ]
        
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
        
        caught_fish = await _run_sync(db.get_caught_fish, user_id, chat_id, only_unsold=True)
        unsold_fish = [
            f for f in caught_fish
            if not bool(f.get('is_trash'))
        ]
        if not unsold_fish:
            await query.edit_message_text("У вас нет рыбы для продажи.")
            return
        
        total_value = sum(f['price'] for f in unsold_fish)
        fish_count = len(unsold_fish)
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        fish_ids = [f['id'] for f in unsold_fish]
        await _run_sync(db.mark_fish_as_sold, fish_ids)
        await _run_sync(db.update_player, user_id, chat_id, coins=player['coins'] + total_value)

        xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary(unsold_fish)
        level_info = await _run_sync(db.add_player_xp, user_id, chat_id, xp_earned)
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
        player = await _run_sync(db.get_player, user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        stats = await _run_sync(db.get_player_stats, user_id, chat_id)
        total_species = await _run_sync(db.get_total_fish_species)
        
        message = f"""
📊 Ваша статистика

🎣 Всего поймано рыбы: {stats['total_fish']}
📏 Общий вес: {stats['total_weight']} кг
🗑️ Мусорный вес: {stats.get('trash_weight', 0)} кг
💰 Продано: {stats.get('sold_fish_count', 0)} рыб ({stats.get('sold_fish_weight', 0)} кг)
🔢 Уникальных видов: {stats['unique_fish']}/{total_species}
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

    async def treasureinfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /treasureinfo - показать информацию о кладе и шансах выпадения"""
        from treasures import get_treasures_info
        try:
            user_id = update.effective_user.id
            message = get_treasures_info()
            
            keyboard = [[InlineKeyboardButton("🔙 Меню", callback_data=f"back_to_menu_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in treasureinfo_command: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке информации о кладе")

    async def topl_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /topl - топ по уровню (глобально)"""
        rows = await _run_sync(db.get_level_leaderboard, limit=10)
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
        import logging as _logging
        from datetime import datetime, timedelta
        _lb_logger = _logging.getLogger(__name__)

        chat_id = update.effective_chat.id
        now = datetime.now()
        week_since = now - timedelta(days=7)
        day_since = now - timedelta(days=1)

        def format_leaderboard(title: str, rows: list) -> str:
            if not rows:
                body = "Нет уловов"
            else:
                lines = []
                for i, player in enumerate(rows, 1):
                    raw_username = str(player.get('username') or '').strip()
                    # Используем user_id как запасное отображение
                    display = raw_username if raw_username else f"id{player.get('user_id', '?')}"
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    username = html.escape(display)
                    weight_value = float(player.get('total_weight') or 0)
                    lines.append(f"{medal} {username}: {weight_value:.2f} кг")
                body = "\n".join(lines) if lines else "Нет уловов"
            return f"{title}\n<blockquote><span class=\"tg-spoiler\">{body}</span></blockquote>"

        global_week = await _run_sync(db.get_leaderboard_period, limit=10, since=week_since)
        global_day = await _run_sync(db.get_leaderboard_period, limit=10, since=day_since)

        is_group = update.effective_chat.type in ('group', 'supergroup', 'channel')
        if is_group:
            _lb_logger.info('leaderboard_command: chat_id=%s type=%s, querying chat leaderboard', chat_id, update.effective_chat.type)
            chat_week = await _run_sync(db.get_chat_leaderboard_period, chat_id=chat_id, limit=10, since=week_since)
            chat_day = await _run_sync(db.get_chat_leaderboard_period, chat_id=chat_id, limit=10, since=day_since)
            _lb_logger.info('leaderboard_command: chat_week=%d rows, chat_day=%d rows', len(chat_week), len(chat_day))
        else:
            chat_week = []
            chat_day = []

        message = "🏆 Таблица лидеров\n\n"

        if is_group:
            message += "💬 Топ этого чата\n"
            message += format_leaderboard("За неделю", chat_week)
            message += "\n"
            message += format_leaderboard("За день", chat_day)
            message += "\n\n"

        message += "🌍 Глобальный топ\n"
        message += format_leaderboard("За неделю", global_week)
        message += "\n"
        message += format_leaderboard("За день", global_day)

        if update.message:
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(message, parse_mode="HTML")
    
    async def repair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /repair - показать информацию о ремонте удочки"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await update.message.reply_text("❌ Профиль не найден!")
            return
        
        # Получаем информацию об удочке
        rod_name = player['current_rod']
        if not rod_name or not await _run_sync(db.get_rod, rod_name):
            rod_name = BAMBOO_ROD
            await _run_sync(db.update_player, user_id, chat_id, current_rod=rod_name)

        if rod_name in TEMP_ROD_RANGES:
            await update.message.reply_text(
                "❌ Эта удочка одноразовая и не ремонтируется.\n"
                "Купите новую в магазине."
            )
            return
        player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
        
        if not player_rod:
            # Инициализируем удочку, если записи нет
            await _run_sync(db.init_player_rod, user_id, rod_name, chat_id)
            player_rod = await _run_sync(db.get_player_rod, user_id, rod_name, chat_id)
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
                await _run_sync(db.start_rod_recovery, user_id, rod_name, chat_id)
            
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
            player = await _run_sync(db.get_player, user_id, chat_id)
            if player:
                await update.message.reply_text(f"✅ Игрок найден: {player['username']}")
            else:
                await update.message.reply_text("❌ Игрок не найден")
                return
            
            # Тест получения локаций
            locations = await _run_sync(db.get_locations)
            await update.message.reply_text(f"✅ Локаций найдено: {len(locations)}")
            
            # Тест получения удочек
            rods = await _run_sync(db.get_rods)
            await update.message.reply_text(f"✅ Удочек найдено: {len(rods)}")
            
            # Тест получения наживок
            baits = await _run_sync(db.get_baits)
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
/app - открыть мини-апку
/menu - меню рыбалки
/fish - начать рыбалку
/net - использовать сеть
/dynamite - взорвать динамит (12 роллов)
/shop - магазин
/weather - погода на локации
/stats - ваша статистика
/leaderboard - таблица лидеров
/repair - починить удочку
/bait - сделать Живца из мелкой рыбы
/market - рыбный рынок дня
/guild - артели (кланы)
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

    async def bait_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Конвертация рыбы в наживку."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return

        convertible = await _run_sync(db.get_convertible_fish_list, user_id, chat_id)
        if not convertible:
            await update.message.reply_text(
                "🪱 *Переработка рыбы в наживку*\n\n"
                "У вас нет подходящей рыбы в инвентаре.\n"
                "Можно переработать: Плотву, Верховку, а также любую рыбу, которая есть в магазине наживок (Шпрот, Сардина, Сельдь и др.).",
                parse_mode='Markdown'
            )
            return

        text = "🪱 *Выберите рыбу для переработки:*\n\n"
        for idx, item in enumerate(convertible, 1):
            text += f"{idx}. {item['name']} ({item['weight']:.2f} кг)\n"

        text += "\nВведите номера рыб через пробел (например: `1 3 5`), чтобы превратить их в наживку."
        
        context.user_data['waiting_bait_selection'] = {
            'user_id': user_id,
            'items': convertible
        }
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рыбный рынок дня или установить его (owner)."""
        user_id = update.effective_user.id
        args = context.args or []

        if args and str(args[0]).lower() == 'set':
            if not self._is_owner(user_id):
                await update.message.reply_text("Нет доступа к настройке рынка.")
                return

            tokens = args[1:]
            if not tokens:
                await update.message.reply_text("Использование: /market set <рыба> [множитель] [кг]")
                return

            target_weight = 50.0
            multiplier = 2.0

            if tokens:
                try:
                    target_weight = float(tokens[-1])
                    tokens = tokens[:-1]
                except Exception:
                    target_weight = 50.0

            if tokens:
                try:
                    multiplier = float(tokens[-1])
                    tokens = tokens[:-1]
                except Exception:
                    multiplier = 2.0

            fish_name = ' '.join(tokens).strip()
            if not fish_name:
                await update.message.reply_text("Укажите название рыбы: /market set <рыба> [множитель] [кг]")
                return

            ok = await _run_sync(db.set_daily_market_offer, fish_name=fish_name,
                multiplier=multiplier,
                target_weight=target_weight,
            )
            if not ok:
                await update.message.reply_text("❌ Не удалось установить рынок дня.")
                return

            await update.message.reply_text(
                "✅ Рыбный рынок обновлен\n\n"
                f"🐟 Рыба: {fish_name}\n"
                f"💹 Множитель: x{multiplier:.2f}\n"
                f"⚖️ Лимит: {target_weight:.1f} кг"
            )
            return

        market = self._get_market_offer_snapshot(create_if_missing=True)
        if not market:
            await update.message.reply_text("🐟 Рыбный рынок сегодня не назначен.")
            return

        sold = float(market.get('sold_weight') or 0.0)
        target = float(market.get('target_weight') or 0.0)
        remaining = float(market.get('remaining_weight') or 0.0)
        active_text = "✅ Активен" if market.get('active') else "⛔ Лимит исчерпан"

        await update.message.reply_text(
            "🐟 Рыбный рынок дня\n\n"
            f"Рыба: {market.get('fish_name')}\n"
            f"Цена: x{float(market.get('multiplier') or 1.0):.2f}\n"
            f"Прогресс: {sold:.1f}/{target:.1f} кг\n"
            f"Осталось: {remaining:.1f} кг\n"
            f"Статус: {active_text}"
        )

    async def disaster_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление эко-катастрофами (owner) и просмотр статуса."""
        user_id = update.effective_user.id
        args = context.args or []

        if args and self._is_owner(user_id):
            action = str(args[0]).strip().lower()
            if action == 'start':
                if len(args) < 2:
                    await update.message.reply_text("Использование: /disaster start <локация> [xp|coins]")
                    return
                reward_type = 'xp'
                if str(args[-1]).lower() in ('xp', 'coins'):
                    reward_type = str(args[-1]).lower()
                    location = ' '.join(args[1:-1]).strip()
                else:
                    location = ' '.join(args[1:]).strip()

                started = await _run_sync(db.start_ecological_disaster, location=location,
                    reward_type=reward_type,
                    duration_minutes=60,
                    reward_multiplier=5,
                )
                if not started:
                    await update.message.reply_text("❌ Не удалось запустить катастрофу.")
                    return
                await update.message.reply_text(
                    "🌪️ Катастрофа запущена\n\n"
                    f"Локация: {started.get('location')}\n"
                    f"Бонус: x{started.get('reward_multiplier')} на {started.get('reward_type')}\n"
                    "Длительность: 60 минут"
                )
                return

            if action == 'stop':
                location = ' '.join(args[1:]).strip()
                if not location:
                    await update.message.reply_text("Использование: /disaster stop <локация>")
                    return
                stopped = await _run_sync(db.stop_ecological_disaster, location)
                if not stopped:
                    await update.message.reply_text("ℹ️ Активной катастрофы на этой локации нет.")
                    return
                await update.message.reply_text(f"✅ Катастрофа на локации '{location}' остановлена.")
                return

        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        location = (player or {}).get('current_location') or 'Городской пруд'
        current = await _run_sync(db.get_active_ecological_disaster, location)
        pond = None
        if location != 'Городской пруд':
            pond = await _run_sync(db.get_active_ecological_disaster, 'Городской пруд')

        lines = ["🌪️ Эко-катастрофы"]
        if current:
            lines.append(
                f"• {current.get('location')}: x{current.get('reward_multiplier')} на {current.get('reward_type')}"
            )
        if pond:
            lines.append(
                f"• {pond.get('location')}: x{pond.get('reward_multiplier')} на {pond.get('reward_type')}"
            )
        if not current and not pond:
            lines.append("• Сейчас активных катастроф нет")

        await update.message.reply_text("\n".join(lines))

    async def guild_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда артелей/кланов."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        args = context.args or []

        if not args:
            clan = await _run_sync(db.get_clan_by_user, user_id)
            if not clan:
                await update.message.reply_text(
                    "🏗️ Артель\n\n"
                    "Вы не состоите в артели.\n"
                    "Создать: /guild create <название>\n"
                    "Вступить: /guild join <название>"
                )
                return

            info = await _run_sync(db.get_clan_info, int(clan['id']))
            donations = info.get('donations', {}) if info else {}
            donation_line = ", ".join([f"{k}: {v}" for k, v in donations.items() if int(v or 0) > 0]) or "пока пусто"
            next_req = await _run_sync(db.get_clan_upgrade_requirements, int(info.get('level', 1)) + 1) if info else {}
            req_line = ", ".join([f"{k} x{v}" for k, v in next_req.items()]) or "максимальный уровень"

            await update.message.reply_text(
                "🏗️ Артель\n\n"
                f"Название: {info.get('name')}\n"
                f"Уровень: {info.get('level')}\n"
                f"Участники: {info.get('member_count')}/{info.get('max_members')}\n"
                f"Ваша роль: {clan.get('role')}\n"
                f"Вклад мусора: {donation_line}\n"
                f"Для апгрейда: {req_line}\n\n"
                "Команды: /guild members, /guild donate <предмет> [кол-во], /guild upgrade"
            )
            return

        action = str(args[0]).strip().lower()

        if action == 'create':
            clan_name = ' '.join(args[1:]).strip()
            if not clan_name:
                await update.message.reply_text("Использование: /guild create <название>")
                return
            created = await _run_sync(db.create_clan, user_id, clan_name)
            if not created.get('ok'):
                reason = created.get('reason')
                if reason == 'already_in_clan':
                    await update.message.reply_text("❌ Вы уже состоите в артели.")
                elif reason == 'name_too_short':
                    await update.message.reply_text("❌ Название артели слишком короткое.")
                else:
                    await update.message.reply_text("❌ Не удалось создать артель. Возможно, имя занято.")
                return

            clan = created.get('clan') or {}
            await update.message.reply_text(
                "✅ Артель создана\n\n"
                f"Название: {clan.get('name')}\n"
                f"Уровень: {clan.get('level')}\n"
                f"Лимит участников: {clan.get('max_members')}"
            )
            return

        if action == 'join':
            clan_name = ' '.join(args[1:]).strip()
            if not clan_name:
                await update.message.reply_text("Использование: /guild join <название>")
                return
            joined = await _run_sync(db.join_clan, user_id, clan_name)
            if not joined.get('ok'):
                reason = joined.get('reason')
                if reason == 'already_in_clan':
                    await update.message.reply_text("❌ Вы уже состоите в артели.")
                elif reason == 'clan_full':
                    await update.message.reply_text("❌ В артели нет мест.")
                else:
                    await update.message.reply_text("❌ Артель не найдена.")
                return

            await update.message.reply_text(f"✅ Вы вступили в артель '{clan_name}'.")
            return

        if action == 'members':
            clan = await _run_sync(db.get_clan_by_user, user_id)
            if not clan:
                await update.message.reply_text("❌ Вы не состоите в артели.")
                return

            members = await _run_sync(db.list_clan_members, int(clan['id']))
            if not members:
                await update.message.reply_text("В артели пока нет участников.")
                return

            lines = []
            for idx, member in enumerate(members, start=1):
                role = "Лидер" if str(member.get('role') or '').lower() == 'leader' else "Участник"
                lines.append(f"{idx}. {member.get('username')} ({role})")

            await update.message.reply_text("👥 Состав артели\n\n" + "\n".join(lines))
            return

        if action == 'donate':
            if len(args) < 2:
                await update.message.reply_text("Использование: /guild donate <доска|удочка> [кол-во]")
                return

            raw_item = str(args[1]).strip().lower()
            item_name = CLAN_DONATABLE_ITEMS.get(raw_item) or ' '.join(args[1:]).strip()
            donate_qty = 1
            if args and str(args[-1]).isdigit():
                donate_qty = max(1, int(args[-1]))
                if len(args) > 2:
                    item_name = CLAN_DONATABLE_ITEMS.get(str(args[1]).strip().lower()) or ' '.join(args[1:-1]).strip()

            donated = await _run_sync(db.donate_trash_to_clan, user_id, chat_id, item_name, donate_qty)
            if not donated.get('ok'):
                reason = donated.get('reason')
                if reason == 'not_in_clan':
                    await update.message.reply_text("❌ Вы не состоите в артели.")
                elif reason == 'not_enough_trash':
                    await update.message.reply_text(
                        "❌ Недостаточно мусора для пожертвования.\n"
                        f"Доступно: {donated.get('available', 0)}"
                    )
                else:
                    await update.message.reply_text("❌ Не удалось пожертвовать мусор.")
                return

            await update.message.reply_text(
                "✅ Пожертвование отправлено\n\n"
                f"Предмет: {donated.get('item_name')}\n"
                f"Количество: {donated.get('donated')}\n"
                f"Итого в артели: {donated.get('clan_total')}"
            )
            return

        if action == 'upgrade':
            upgrade = await _run_sync(db.upgrade_clan, user_id)
            if not upgrade.get('ok'):
                reason = upgrade.get('reason')
                if reason == 'not_leader':
                    await update.message.reply_text("❌ Только лидер может улучшать артель.")
                elif reason == 'not_in_clan':
                    await update.message.reply_text("❌ Вы не состоите в артели.")
                elif reason == 'max_level':
                    await update.message.reply_text("✅ Артель уже максимального уровня.")
                elif reason == 'not_enough_donations':
                    missing = upgrade.get('missing') or {}
                    missing_line = "\n".join([f"• {k}: нужно еще {v}" for k, v in missing.items()])
                    await update.message.reply_text("❌ Не хватает ресурсов для апгрейда:\n" + missing_line)
                else:
                    await update.message.reply_text("❌ Апгрейд не выполнен.")
                return

            await update.message.reply_text(
                "⬆️ Артель улучшена\n\n"
                f"Новый уровень: {upgrade.get('new_level')}\n"
                f"Лимит участников: {upgrade.get('max_members')}"
            )
            return

        await update.message.reply_text(
            "Команды артели:\n"
            "/guild create <название>\n"
            "/guild join <название>\n"
            "/guild members\n"
            "/guild donate <доска|удочка> [кол-во]\n"
            "/guild upgrade"
        )
    
    async def net_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /net - использовать сеть"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        # Показываем доступные сети игрока
        player_nets = await _run_sync(db.get_player_nets, user_id, chat_id)
        if not player_nets:
            await _run_sync(db.init_player_net, user_id, 'Базовая сеть', chat_id)
            player_nets = await _run_sync(db.get_player_nets, user_id, chat_id)
        
        if not player_nets:
            await update.message.reply_text(
                "❌ У вас нет сетей!\n\n"
                "Используйте /shop чтобы купить сети."
            )
            return
        
        # Показываем меню выбора сети
        keyboard = []
        any_on_cooldown = False
        for net in player_nets:
            cooldown = await _run_sync(db.get_net_cooldown_remaining, user_id, net['net_name'], chat_id)
            if cooldown > 0:
                any_on_cooldown = True
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
        if any_on_cooldown:
            keyboard.append([InlineKeyboardButton("⚡ Сбросить КД сетей — 10 ⭐", callback_data=f"net_skip_cd_{user_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Меню", callback_data=f"back_to_menu_{user_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"🕸️ Выберите сеть для использования:\n\n📍 Локация: {player['current_location']}"
        await update.message.reply_text(message, reply_markup=reply_markup)

    def _pick_dynamite_fish(self, location: str, season: str, player_level: int, target_rarity: str) -> Optional[Dict[str, Any]]:
        available_fish = db.get_fish_by_location(location, season, min_level=player_level)
        if not available_fish:
            return None
        same_rarity = [f for f in available_fish if f.get('rarity') == target_rarity]
        pool = same_rarity if same_rarity else available_fish
        return random.choice(pool) if pool else None

    def _extract_attempt_datetime_utc(self, update: Update) -> datetime:
        """Извлечь время сообщения Telegram в UTC для анти-абуз анализа ритма."""
        effective_message = update.effective_message
        raw_dt = getattr(effective_message, "date", None)

        if isinstance(raw_dt, datetime):
            if raw_dt.tzinfo is None:
                return raw_dt.replace(tzinfo=timezone.utc)
            return raw_dt.astimezone(timezone.utc)

        return datetime.now(timezone.utc)

    def _remaining_seconds_from_iso(self, raw_iso: Optional[str]) -> int:
        """Остаток времени до UTC-ISO timestamp."""
        if not raw_iso:
            return 0
        try:
            dt_val = datetime.fromisoformat(str(raw_iso))
            if dt_val.tzinfo is None:
                dt_val = dt_val.replace(tzinfo=timezone.utc)
            else:
                dt_val = dt_val.astimezone(timezone.utc)
        except Exception:
            return 0

        now = datetime.now(timezone.utc)
        return max(0, int((dt_val - now).total_seconds()))

    def _normalize_webapp_url(self) -> str:
        """Нормализовать base URL mini app (добавить https:// если нужно)."""
        webapp_url = (self.webapp_url or "").strip()
        if not webapp_url:
            return ""
        if not re.match(r"^https?://", webapp_url):
            webapp_url = f"https://{webapp_url.lstrip('/')}"
        return webapp_url

    def _build_captcha_webapp_url(self, token: str) -> str:
        """Собрать URL mini app с токеном капчи."""
        base_url = self._normalize_webapp_url()
        if not base_url:
            return ""

        parsed = urlparse(base_url)
        # Keep captcha links predictable: do not inherit arbitrary query params
        # from WEBAPP_URL (for example legacy tg_id values).
        query_dict = {
            "captcha_token": str(token or "").strip(),
            "captcha_mode": "antibot",
        }
        new_query = urlencode(query_dict)

        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))

    def _build_captcha_link_markup(self, captcha_url: str, chat_type: Optional[str]) -> Optional[InlineKeyboardMarkup]:
        """Построить кнопку открытия капчи в апке."""
        if not captcha_url:
            return None

        if chat_type != "private":
            return None

        button = InlineKeyboardButton("🧩 Пройти капчу", web_app=WebAppInfo(url=captcha_url))

        return InlineKeyboardMarkup([[button]])

    @staticmethod
    def _sanitize_public_service_text(text: str) -> str:
        """Удалить служебные хвосты вроде tg_id=... из пользовательских сообщений."""
        normalized = str(text or "")
        normalized = re.sub(r"\s*tg_id\s*=\s*\d+", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s{2,}", " ", normalized)
        return normalized.strip()

    def _build_antibot_block_message(
        self,
        gate_status: Dict[str, Any],
        challenge_info: Dict[str, Any],
        chat_type: Optional[str],
        rhythm_detected: bool = False,
    ) -> Dict[str, Any]:
        """Собрать текст и markup блокировки для анти-абуза."""
        penalty_active = bool(gate_status.get("penalty_active"))
        challenge_token = str(challenge_info.get("token") or "").strip()
        challenge_url = self._build_captcha_webapp_url(challenge_token)
        reply_markup = self._build_captcha_link_markup(challenge_url, chat_type)

        penalty_seconds = self._remaining_seconds_from_iso(
            str(gate_status.get("penalty_until") or challenge_info.get("penalty_until") or "")
        )
        challenge_seconds = self._remaining_seconds_from_iso(str(challenge_info.get("expires_at") or ""))
        if challenge_seconds <= 0:
            challenge_seconds = ANTI_BOT_CAPTCHA_TTL_SECONDS

        if penalty_active:
            penalty_line = self._format_seconds_compact(penalty_seconds) if penalty_seconds > 0 else f"{ANTI_BOT_PENALTY_HOURS}ч"
            text = (
                "🚫 Анти-абуз штраф уже активен.\n"
                "🎣 Бесплатная рыбалка временно отключена.\n"
                "🧩 Откройте апку и пройдите капчу.\n"
                f"⏳ До снятия штрафа: {penalty_line}."
            )
        else:
            reason_line = "Обнаружен подозрительно ровный ритм /fish." if rhythm_detected else "Требуется подтверждение, что вы не отложенный авто-клиент."
            text = (
                f"🧩 {reason_line}\n"
                "Пройдите капчу в мини-апке по кнопке ниже.\n"
                f"⏱ Время на решение: {challenge_seconds} сек.\n"
                f"⚠️ Если не пройти вовремя, включится штраф на {ANTI_BOT_PENALTY_HOURS} часов."
            )

        if not challenge_url:
            text += "\n\n❌ WEBAPP_URL не настроен, ссылка на капчу недоступна."

        return {
            "text": text,
            "reply_markup": reply_markup,
            "challenge_url": challenge_url,
        }

    async def _send_antibot_block_to_user(
        self,
        update: Update,
        block_payload: Dict[str, Any],
        query: Optional[Any] = None,
    ) -> None:
        """В группах отправить капчу в личку, а в чат дать уведомление."""
        block_text = str(block_payload.get("text") or "")
        current_chat_type = update.effective_chat.type if update.effective_chat else None

        if current_chat_type == "private":
            if query:
                await query.edit_message_text(
                    block_text,
                    reply_markup=block_payload.get("reply_markup"),
                    parse_mode=None,
                )
            else:
                target_message = update.message or update.effective_message
                if target_message:
                    await target_message.reply_text(
                        block_text,
                        reply_markup=block_payload.get("reply_markup"),
                        parse_mode=None,
                    )
            return

        challenge_url = str(block_payload.get("challenge_url") or "").strip()
        private_markup = self._build_captcha_link_markup(challenge_url, "private")
        dm_sent = False

        if update.effective_user and private_markup:
            try:
                await self.application.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=block_text,
                    reply_markup=private_markup,
                    parse_mode=None,
                )
                dm_sent = True
            except Forbidden:
                logger.info(
                    "Failed to send captcha DM to user=%s: private chat is unavailable",
                    update.effective_user.id,
                )
            except Exception:
                logger.exception(
                    "Unexpected error while sending captcha DM to user=%s",
                    update.effective_user.id,
                )

        if dm_sent:
            public_text = (
                "🧩 Капча отправлена вам в личные сообщения с ботом. "
                "Пройдите её там и возвращайтесь в чат."
            )
        else:
            public_text = (
                "🧩 Для продолжения нужна капча, но я не смог отправить её в личные сообщения.\n"
                "Откройте бота в личке, нажмите /start и повторите попытку."
            )

        if query:
            await query.edit_message_text(public_text, parse_mode=None)
        else:
            target_message = update.message or update.effective_message
            if target_message:
                await target_message.reply_text(public_text, parse_mode=None)

    def _get_antibot_active_block(self, user_id: int, update: Update) -> Optional[Dict[str, Any]]:
        """Проверить активный штраф/незавершённую капчу. Если есть — вернуть блок."""
        try:
            gate_status = db.get_antibot_gate_status(user_id, penalty_hours=ANTI_BOT_PENALTY_HOURS)
        except Exception:
            logger.exception("Failed to read anti-bot gate for user=%s", user_id)
            return None

        if not gate_status.get("needs_captcha"):
            return None

        try:
            challenge_info = db.issue_antibot_challenge(
                user_id=user_id,
                reason="penalty_or_pending",
                challenge_ttl_seconds=ANTI_BOT_CAPTCHA_TTL_SECONDS,
                penalty_hours=ANTI_BOT_PENALTY_HOURS,
            )
        except Exception:
            logger.exception("Failed to issue anti-bot challenge for user=%s", user_id)
            return None

        return self._build_antibot_block_message(
            gate_status=gate_status,
            challenge_info=challenge_info,
            chat_type=update.effective_chat.type if update.effective_chat else None,
            rhythm_detected=False,
        )

    def _register_free_fish_attempt_and_check_antibot(self, user_id: int, update: Update) -> Optional[Dict[str, Any]]:
        """Зафиксировать бесплатный /fish и при подозрительном ритме выдать капчу."""
        try:
            attempt_time = self._extract_attempt_datetime_utc(update)
            rhythm_state = db.register_free_fish_attempt(
                user_id=user_id,
                attempt_time=attempt_time,
                min_interval_seconds=ANTI_BOT_RHYTHM_MIN_SECONDS,
                max_interval_seconds=ANTI_BOT_RHYTHM_MAX_SECONDS,
                trigger_streak=ANTI_BOT_RHYTHM_TRIGGER_STREAK,
            )
        except Exception:
            logger.exception("Failed to register free fish attempt for anti-bot user=%s", user_id)
            return None

        if not rhythm_state.get("trigger"):
            return None

        try:
            gate_status = db.get_antibot_gate_status(user_id, penalty_hours=ANTI_BOT_PENALTY_HOURS)
            challenge_info = db.issue_antibot_challenge(
                user_id=user_id,
                reason="rhythm_detected",
                challenge_ttl_seconds=ANTI_BOT_CAPTCHA_TTL_SECONDS,
                penalty_hours=ANTI_BOT_PENALTY_HOURS,
            )
        except Exception:
            logger.exception("Failed to create anti-bot challenge after rhythm detection user=%s", user_id)
            return None

        return self._build_antibot_block_message(
            gate_status=gate_status,
            challenge_info=challenge_info,
            chat_type=update.effective_chat.type if update.effective_chat else None,
            rhythm_detected=True,
        )

    def _is_user_beer_drunk(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь в состоянии опьянения."""
        try:
            return bool(db.has_active_effect(user_id, BEER_DRUNK_EFFECT))
        except Exception:
            logger.exception("Failed to check drunk state for user=%s", user_id)
            return False

    def _get_active_beer_bonus_percent(self, user_id: int) -> float:
        """Суммарный активный бонус от пивных эффектов (в процентах)."""
        try:
            return max(0.0, float(db.get_active_beer_bonus_percent(user_id) or 0.0))
        except Exception:
            logger.exception("Failed to load beer bonus for user=%s", user_id)
            return 0.0

    def _generate_drunk_gibberish(self) -> str:
        """Сгенерировать непонятную фразу для состояния опьянения."""
        parts_count = random.randint(9, 16)
        chunks = []
        for _ in range(parts_count):
            chunk = random.choice(DRUNK_GIBBERISH_SYLLABLES)
            if random.random() < 0.25:
                chunk += random.choice(["..", "?!", "??", "!!"])
            chunks.append(chunk)
        return " ".join(chunks)

    async def _maybe_trigger_boat_storm(self, user_id: int, result: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Независимая проверка шторма на активной лодке."""
        # Шторм — отдельное событие, не привязанное к рыбнадзору.
        if result and result.get('fish_inspector'):
            return None

        is_on_boat_trip = bool((result or {}).get('is_on_boat')) or await _run_sync(db.is_user_on_boat_trip, user_id)
        if not is_on_boat_trip:
            return None

        if random.random() >= STORM_EVENT_CHANCE_ON_BOAT:
            return None

        storm_result = await _run_sync(db.sink_active_boat_by_storm, user_id, cooldown_hours=STORM_EVENT_COOLDOWN_HOURS)
        if not storm_result or not storm_result.get('applied'):
            return None

        try:
            # После сильного шторма можно получить морскую болезнь.
            await _run_sync(db.apply_seasick_event, user_id)
        except Exception:
            logger.exception("Failed to apply seasick after storm for user=%s", user_id)

        return storm_result

    def _format_storm_event_message(self, storm_result: Dict[str, Any]) -> str:
        lost_count = int(storm_result.get('lost_count', 0) or 0)
        lost_weight = float(storm_result.get('lost_weight', 0) or 0.0)
        return self._sanitize_public_service_text(
            (
            "🌪️ Поднялся сильный шторм!\n"
            "🧺 Лодку развернуло, плавание экстренно завершено.\n"
            f"🐟 Утеряно из садка: {lost_count} шт. ({lost_weight:.1f} кг).\n"
            f"⏳ Лодка ушла в КД на {STORM_EVENT_COOLDOWN_HOURS} часов.\n"
            "🤢 Вы получили морскую болезнь (работает только в плавании)."
            )
        )

    def _get_clothing_bonus_percent(self, user_id: int) -> float:
        """Суммарный перманентный бонус от одежды (в процентах)."""
        try:
            return max(0.0, float(db.get_clothing_bonus_percent(user_id) or 0.0))
        except Exception:
            logger.exception("Failed to load clothing bonus for user=%s", user_id)
            return 0.0

    def _get_dynamite_upgrade_state(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        try:
            level = int(db.get_dynamite_upgrade_level(user_id, chat_id))
        except Exception:
            level = 1

        level = max(1, min(3, level))
        next_level = level + 1 if level < 3 else None

        return {
            'level': level,
            'name': DYNAMITE_NAME_BY_LEVEL.get(level, DYNAMITE_NAME_BY_LEVEL[1]),
            'max_weight': float(DYNAMITE_MAX_WEIGHT_BY_LEVEL.get(level, DYNAMITE_MAX_WEIGHT_BY_LEVEL[1])),
            'sticker': DYNAMITE_STICKER_BY_LEVEL.get(level, DYNAMITE_STICKER_FILE_ID),
            'next_level': next_level,
            'next_name': DYNAMITE_NAME_BY_LEVEL.get(next_level) if next_level else None,
            'next_max_weight': float(DYNAMITE_MAX_WEIGHT_BY_LEVEL.get(next_level)) if next_level else None,
            'next_upgrade_cost': DYNAMITE_UPGRADE_COST_BY_LEVEL.get(level),
        }

    def _roll_treasure_after_trash(self, user_id: int, chat_id: int, source_tag: str, roll_index: Optional[int] = None) -> Optional[str]:
        """Second roll after trash: returns treasure key or None."""
        from treasures import TREASURES

        total_probability = sum(float(t.get('probability', 0) or 0) for t in TREASURES.values())
        treasure_roll = random.uniform(0, 100)
        accumulated_probability = 0.0

        logger.info(
            "[%s] treasure_roll#2 start roll=%.2f/100 total_treasure_prob=%.2f%% no_treasure_prob=%.2f%% roll_index=%s",
            source_tag,
            treasure_roll,
            total_probability,
            max(0.0, 100.0 - total_probability),
            roll_index,
        )

        for treasure_key, treasure_info in TREASURES.items():
            chance = float(treasure_info.get('probability', 0) or 0)
            prev_threshold = accumulated_probability
            accumulated_probability += chance
            logger.info(
                "[%s] treasure_roll#2 check item=%s chance=%.2f%% range=(%.2f..%.2f] roll_index=%s",
                source_tag,
                treasure_key,
                chance,
                prev_threshold,
                accumulated_probability,
                roll_index,
            )
            if treasure_roll <= accumulated_probability:
                saved = db.add_treasure(user_id, treasure_key, 1, chat_id)
                if not saved:
                    logger.error(
                        "[%s] treasure_roll#2 DB_SAVE_FAILED item=%s user=%s chat=%s roll_index=%s",
                        source_tag,
                        treasure_key,
                        user_id,
                        chat_id,
                        roll_index,
                    )
                    return None
                logger.info(
                    "[%s] treasure_roll#2 result TREASURE item=%s roll=%.2f threshold=%.2f roll_index=%s",
                    source_tag,
                    treasure_key,
                    treasure_roll,
                    accumulated_probability,
                    roll_index,
                )
                return treasure_key

        logger.info(
            "[%s] treasure_roll#2 result NONE roll=%.2f > total_treasure_prob=%.2f roll_index=%s",
            source_tag,
            treasure_roll,
            accumulated_probability,
            roll_index,
        )
        return None

    async def _execute_dynamite_blast(self, user_id: int, chat_id: int, guaranteed: bool = False, reply_to_message_id: Optional[int] = None) -> None:
        player = await _run_sync(db.get_player, user_id, chat_id)
        if not player:
            await self._safe_send_message(
                chat_id=chat_id,
                text="❌ Профиль не найден. Используйте /start в этом чате.",
                reply_to_message_id=reply_to_message_id,
            )
            return

        dynamite_upgrade = self._get_dynamite_upgrade_state(user_id, chat_id)
        dynamite_level = int(dynamite_upgrade['level'])
        dynamite_name = str(dynamite_upgrade['name'])
        max_fish_weight_limit = float(dynamite_upgrade['max_weight'])
        dynamite_sticker_file_id = str(dynamite_upgrade.get('sticker') or DYNAMITE_STICKER_FILE_ID)

        location = player.get('current_location', 'Городской пруд')
        season = get_current_season()
        player_level = int(player.get('level') or 0)
        weather = await _run_sync(db.get_or_update_weather, location)
        weather_bonus = weather_system.get_weather_bonus(weather['condition']) if weather else 0
        feeder_bonus = await _run_sync(db.get_active_feeder_bonus, user_id, chat_id)
        clothing_bonus_percent = self._get_clothing_bonus_percent(user_id)
        beer_bonus_percent = self._get_active_beer_bonus_percent(user_id)

        # Предзагрузка данных для оптимизации Dynamite (чтобы не ходить в БД 12 раз)
        available_fish_all = await _run_sync(db.get_fish_by_location, location, season, min_level=player_level)
        available_trash_all = await _run_sync(db.get_trash_by_location, location)
        
        # Любой динамитный заброс учитываем в системе восстановления штрафа популяции.
        try:
            await _run_sync(db.update_population_state, user_id, location)
        except Exception:
            logger.exception("Failed to update population state from dynamite for user=%s location=%s", user_id, location)

        population_penalty = await _run_sync(db.get_population_penalty, user_id)
        # Update dynamite usage state and get dynamite-specific penalty
        # Update dynamite usage state (returns new penalty and consecutive count)
        try:
            _loc_changed, consecutive_dynamite, dynamite_penalty, _recovery = await _run_sync(db.update_dynamite_state, user_id, location)
            logger.info("[DYNAMITE] user=%s consecutive_dynamite=%s dynamite_penalty=%.2f", user_id, consecutive_dynamite, dynamite_penalty)
        except Exception:
            logger.exception("Failed to update dynamite state for user=%s", user_id)
            dynamite_penalty = 0.0

        if guaranteed:
            roll_max = 20000
            trash_max = 7999
            common_max = 14999
            rare_max = 18999
            legendary_max = 19899
            aquarium_max = 19949
            mythic_max = 19989
            anomaly_max = 19999
            nft_max = 20001
        else:
            roll_max = 20000
            no_bite_max = 4999
            trash_max = 9999
            common_max = 14999
            rare_max = 18999
            legendary_max = 19899
            aquarium_max = 19949
            mythic_max = 19989
            anomaly_max = 19999
            nft_max = 20001

        logger.info(
            "[DYNAMITE] start user=%s chat=%s location=%s guaranteed=%s season=%s level=%s weather_bonus=%+d feeder_bonus=%+d clothing_bonus=+%.2f%% beer_bonus=+%.2f%% population_penalty=%.2f%% dynamite_level=%s dynamite_name=%s max_weight=%s",
            user_id,
            chat_id,
            location,
            guaranteed,
            season,
            player_level,
            weather_bonus,
            feeder_bonus,
            clothing_bonus_percent,
            beer_bonus_percent,
            population_penalty,
            dynamite_level,
            dynamite_name,
            max_fish_weight_limit,
        )

        result_lines: List[str] = []
        fish_count = 0
        trash_count = 0
        fail_count = 0
        total_trash_coins = 0
        total_haul_coins = 0
        total_tickets_base = 0
        treasure_count = 0
        treasure_totals: Dict[str, int] = {}
        pending_catches: List[Dict[str, Any]] = []
        clothing_points = clothing_bonus_percent * 50
        beer_points = beer_bonus_percent * 50

        for idx in range(1, DYNAMITE_BATCH_ROLLS + 1):
            roll = random.randint(0, roll_max)
            adjusted_roll = roll + (weather_bonus * 50) + (feeder_bonus * 250) + clothing_points + beer_points
            adjusted_roll = max(0, min(roll_max, adjusted_roll))

            total_penalty = float(population_penalty or 0.0) + float(dynamite_penalty or 0.0)
            penalty_points = int((total_penalty / 100) * roll_max)
            adjusted_roll = max(0, adjusted_roll - penalty_points)

            logger.info(
                "[DYNAMITE] roll=%s raw=%s/%s weather_points=%+d feeder_points=%+d clothing_points=%+.2f beer_points=%+.2f population_penalty=%.2f dynamite_penalty=%.2f penalty_points=-%d adjusted=%s/%s",
                idx,
                roll,
                roll_max,
                weather_bonus * 50,
                feeder_bonus * 250,
                clothing_points,
                beer_points,
                population_penalty,
                dynamite_penalty,
                penalty_points,
                adjusted_roll,
                roll_max,
            )

            if not guaranteed and adjusted_roll <= no_bite_max:
                fail_count += 1
                total_tickets_base += int(self.TICKET_POINTS['no_bite'])
                result_lines.append(f"{idx}. Срыв")
                logger.info("[DYNAMITE] roll=%s branch=NO_BITE threshold<=%s", idx, no_bite_max)
                continue

            if adjusted_roll <= trash_max:
                trash = random.choice(available_trash_all) if available_trash_all else None
                if trash:
                    trash_name = trash.get('name', 'Мусор')
                    trash_price = int(trash.get('price', 0) or 0)
                    treasure_key = self._roll_treasure_after_trash(
                        user_id=user_id,
                        chat_id=chat_id,
                        source_tag="DYNAMITE",
                        roll_index=idx,
                    )
                    if treasure_key:
                        from treasures import get_treasure_name

                        treasure_count += 1
                        treasure_totals[treasure_key] = int(treasure_totals.get(treasure_key, 0) or 0) + 1
                        total_tickets_base += int(self.TICKET_POINTS['trash'])
                        result_lines.append(f"{idx}. {get_treasure_name(treasure_key)}")
                        logger.info(
                            "[DYNAMITE] roll=%s branch=TRASH_REPLACED_BY_TREASURE trash=%s treasure=%s",
                            idx,
                            trash_name,
                            treasure_key,
                        )
                    else:
                        pending_catches.append({
                            'name': trash_name,
                            'weight': float(trash.get('weight', 0) or 0),
                            'length': 0.0,
                        })
                        total_haul_coins += trash_price
                        trash_count += 1
                        total_tickets_base += int(self.TICKET_POINTS['trash'])
                        result_lines.append(f"{idx}. {trash_name}")
                        logger.info(
                            "[DYNAMITE] roll=%s branch=TRASH name=%s weight=%skg price=%s",
                            idx,
                            trash_name,
                            trash.get('weight', 0),
                            trash_price,
                        )
                else:
                    fail_count += 1
                    total_tickets_base += int(self.TICKET_POINTS['no_bite'])
                    result_lines.append(f"{idx}. Срыв")
                    logger.info("[DYNAMITE] roll=%s branch=TRASH but no trash in location -> NO_BITE", idx)
                continue


            if adjusted_roll <= common_max:
                target_rarity = "Обычная"
            elif adjusted_roll <= rare_max:
                target_rarity = "Редкая"
            elif adjusted_roll <= legendary_max:
                target_rarity = "Легендарная"
            elif adjusted_roll <= aquarium_max:
                target_rarity = "Аквариумная"
            elif adjusted_roll <= mythic_max:
                target_rarity = "Мифическая"
            elif adjusted_roll <= anomaly_max:
                target_rarity = "Аномалия"
            else:
                # Для динамита NFT отключен: верхний ролл тоже считается мификом.
                target_rarity = "Мифическая"

            # Оптимизированный выбор рыбы из предзагруженного списка
            same_rarity = [f for f in available_fish_all if f.get('rarity') == target_rarity]
            fish = random.choice(same_rarity if same_rarity else available_fish_all) if available_fish_all else None
            
            if not fish:
                fail_count += 1
                total_tickets_base += int(self.TICKET_POINTS['no_bite'])
                result_lines.append(f"{idx}. Срыв")
                logger.info("[DYNAMITE] roll=%s branch=FISH rarity=%s but pool empty -> NO_BITE", idx, target_rarity)
                continue

            # --- Ограничение веса рыбы при ловле динамитом ---
            max_fish_weight = max_fish_weight_limit
            rarity_order = ['Обычная', 'Редкая', 'Легендарная', 'Мифическая']
            rarity_idx = rarity_order.index(target_rarity) if target_rarity in rarity_order else 0
            found = False
            search_rarity = target_rarity
            fish_candidate = fish
            
            while not found and rarity_idx >= 0:
                pool = [f for f in available_fish_all if f.get('rarity') == search_rarity and float(f.get('max_weight', 0)) <= max_fish_weight and float(f.get('min_weight', 0)) <= max_fish_weight]
                if pool:
                    fish_candidate = random.choice(pool)
                    weight = round(random.uniform(float(fish_candidate['min_weight']), min(float(fish_candidate['max_weight']), max_fish_weight)), 2)
                    length = round(random.uniform(float(fish_candidate['min_length']), float(fish_candidate['max_length'])), 1)
                    found = True
                else:
                    rarity_idx -= 1
                    if rarity_idx >= 0:
                        search_rarity = rarity_order[rarity_idx]
            if found:
                rarity_circle = {
                    'Обычная': '⚪',
                    'Редкая': '🔵',
                    'Легендарная': '🟡',
                    'Мифическая': '🔴',
                }.get(fish_candidate['rarity'], '⚪')
                pending_catches.append({
                    'name': fish_candidate['name'],
                    'weight': weight,
                    'length': length,
                })
                fish_value = int(await _run_sync(db.calculate_fish_price, fish_candidate, weight, length))
                total_haul_coins += fish_value
                fish_count += 1
                total_tickets_base += self._calculate_tickets_for_rarity(fish_candidate.get('rarity', target_rarity))
                result_lines.append(
                    f"{idx}. {rarity_circle} {format_fish_name(fish_candidate['name'])} ({length} см, {weight} кг)"
                )

                logger.info(
                    "[DYNAMITE] roll=%s branch=FISH rarity=%s name=%s length=%scm weight=%skg price=%s",
                    idx,
                    fish_candidate['rarity'],
                    fish_candidate['name'],
                    length,
                    weight,
                    fish_value,
                )
            else:
                fail_count += 1
                total_tickets_base += int(self.TICKET_POINTS['no_bite'])
                result_lines.append(f"{idx}. Срыв (нет подходящей рыбы)")
                logger.info("[DYNAMITE] roll=%s branch=FISH no suitable fish found", idx)

        # Очень редкая отдельная механика для динамита: рыбохрана.
        if random.random() < DYNAMITE_GUARD_CHANCE:
            await _run_sync(db.set_dynamite_ban, user_id, chat_id, DYNAMITE_GUARD_BAN_HOURS)
            logger.info(
                "[DYNAMITE] guard_triggered user=%s chat=%s chance=%.4f ban_hours=%s catches_confiscated=%s",
                user_id,
                chat_id,
                DYNAMITE_GUARD_CHANCE,
                DYNAMITE_GUARD_BAN_HOURS,
                len(pending_catches),
            )

            sticker_path = Path(__file__).parent / "fishdef.webp"
            if sticker_path.exists():
                try:
                    await self._send_document_path_cached(
                        chat_id=chat_id,
                        path=sticker_path,
                        reply_to_message_id=reply_to_message_id,
                    )
                except Exception as e:
                    logger.warning("Could not send fishdef.webp on dynamite arrest: %s", e)

            await self._safe_send_message(
                chat_id=chat_id,
                text=(
                    "🚨 Вас поймала рыбохрана при использовании динамита!\n"
                    "Весь текущий улов конфискован.\n"
                    f"⛔ Динамит арестован на {DYNAMITE_GUARD_BAN_HOURS} часа.\n"
                    f"💫 Откуп: {DYNAMITE_GUARD_FINE_STARS} {STAR_NAME}."
                ),
                reply_to_message_id=reply_to_message_id,
            )
            return

        # Проверяем, находится ли игрок на лодке
        active_boat = await _run_sync(db.get_active_boat_by_user, user_id)
        is_on_boat_dyn = active_boat is not None

        for item in pending_catches:
            if is_on_boat_dyn:
                # На лодке рыба идёт в общий садок (boat_catch)
                # Находим fish_id по имени
                f_data = await _run_sync(db.get_fish_by_name, item['name'])
                if f_data:
                    await _run_sync(db.add_fish_to_boat, user_id, f_data['id'], float(item['weight']), chat_id)
            else:
                await _run_sync(db.add_caught_fish, user_id,
                    chat_id,
                    item['name'],
                    float(item['weight']),
                    location,
                    float(item['length']),
                )

        logger.info(
            "[DYNAMITE] finish user=%s chat=%s fish=%s trash=%s fail=%s treasures=%s catches_saved=%s total_trash_coins=%s total_haul_coins=%s",
            user_id,
            chat_id,
            fish_count,
            trash_count,
            fail_count,
            treasure_count,
            len(pending_catches),
            total_trash_coins,
            total_haul_coins,
        )

        new_coins = int(player.get('coins', 0) or 0)
        current_username = str(player.get('username') or player.get('first_name') or user_id)
        await _run_sync(db.update_player, user_id,
            chat_id,
            coins=new_coins,
            last_dynamite_use_time=datetime.now().isoformat(),
        )
        tickets_awarded, tickets_jackpot, tickets_total = self._award_tickets(
            user_id,
            total_tickets_base,
            username=current_username,
            source_type='dynamite',
            source_ref=str(location),
        )

        header = f"🧨 <b>Вы взорвали {dynamite_name.lower()}!</b>"
        if guaranteed:
            header += "\n⭐ Гарантированный динамит"

        message = (
            f"{header}\n\n"
            f"📍 Локация: {location}\n"
            f"🧪 Взрывчатка: {dynamite_name} (ур. {dynamite_level}/3)\n"
            f"⚖️ Лимит веса рыбы: {int(max_fish_weight_limit)} кг\n"
            f"🎯 Результатов: {DYNAMITE_BATCH_ROLLS}\n"
            f"🐟 Рыбы: {fish_count}\n"
            f"📦 Мусор: {trash_count}\n"
            f"💎 Драгоценности: {treasure_count}\n"
            f"❌ Срывы: {fail_count}\n"
            f"💰 Оценка улова при продаже: {total_haul_coins} {COIN_NAME}\n\n"
            + "\n".join(result_lines)
        )

        if tickets_awarded > 0:
            if tickets_jackpot > 0:
                message += f"\n\n🎟 Билеты: +{tickets_awarded} (джекпот +{tickets_jackpot})"
            else:
                message += f"\n\n🎟 Билеты: +{tickets_awarded}"
            message += f"\n🎫 Всего билетов: {tickets_total}"

        if treasure_totals:
            from treasures import get_treasure_name

            treasure_lines = [
                f"{get_treasure_name(key)} x{qty}"
                for key, qty in sorted(treasure_totals.items(), key=lambda item: item[0])
            ]
            message += "\n\n💎 Итог по драгоценностям:\n" + "\n".join(treasure_lines)
        # Добавляем информацию о дебаффах (популяция и динамит), если есть
        # population_penalty уже получен в начале функции
        try:
            dynamite_penalty = await _run_sync(db.get_dynamite_penalty, user_id)
        except Exception:
            dynamite_penalty = 0.0

        penalty_lines = []
        if population_penalty and population_penalty > 0:
            penalty_lines.append(f"⚠️ Популяция рыб снижена на {int(population_penalty)}% (много забросов на одной локации)")
        if dynamite_penalty and dynamite_penalty > 0:
            penalty_lines.append(f"⚠️ Штраф к динамиту: -{int(dynamite_penalty)}% к шансам (частые взрывы)")

        if penalty_lines:
            message += "\n\n" + "\n".join(penalty_lines)

        # Отправляем стикер и сообщение ПАРАЛЛЕЛЬНО для ускорения реакции
        await asyncio.gather(
            self._safe_send_sticker(
                chat_id=chat_id,
                sticker=dynamite_sticker_file_id,
                reply_to_message_id=reply_to_message_id,
            ),
            self._safe_send_message(
                chat_id=chat_id,
                text=message,
                reply_to_message_id=reply_to_message_id,
            )
        )

    async def dynamite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда/слово динамит: 12 независимых роллов с КД 8 часов."""
        if update.effective_chat.type == 'private':
            await update.message.reply_text("Команда динамита работает только в группах.")
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)

        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return

        ban_remaining = await _run_sync(db.get_dynamite_ban_remaining, user_id, chat_id)
        if ban_remaining > 0:
            hours = ban_remaining // 3600
            minutes = (ban_remaining % 3600) // 60
            seconds = ban_remaining % 60
            ban_text = f"{hours}ч {minutes}м {seconds}с" if hours > 0 else f"{minutes}м {seconds}с"

            tg_api = TelegramBotAPI(BOT_TOKEN)
            payload = self._build_dynamite_fine_payload(user_id, chat_id)
            invoice_url = await tg_api.create_invoice_link(
                title="Выкуп у рыбохраны",
                description=f"Снять арест динамита ({DYNAMITE_GUARD_FINE_STARS} {STAR_NAME})",
                payload=payload,
                currency="XTR",
                prices=[{"label": "Выкуп динамита", "amount": DYNAMITE_GUARD_FINE_STARS}],
            )

            if not invoice_url:
                await update.message.reply_text(
                    f"⛔ Вас арестовала рыбохрана. До снятия ареста: {ban_text}.\n"
                    "❌ Не удалось создать ссылку оплаты. Попробуйте позже."
                )
                return

            await self.send_invoice_url_button(
                chat_id=chat_id,
                invoice_url=invoice_url,
                text=(
                    f"⛔ Вас арестовала рыбохрана. До снятия ареста: {ban_text}.\n\n"
                    f"⭐ Оплатите {DYNAMITE_GUARD_FINE_STARS} Telegram Stars, чтобы снять арест с динамита."
                ),
                user_id=user_id,
                reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
            )
            return

        remaining = await _run_sync(db.get_dynamite_cooldown_remaining, user_id, chat_id, DYNAMITE_COOLDOWN_HOURS)
        if remaining > 0:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            cooldown_text = f"{hours}ч {minutes}м {seconds}с" if hours > 0 else f"{minutes}м {seconds}с"

            tg_api = TelegramBotAPI(BOT_TOKEN)
            payload = self._build_dynamite_skip_payload(user_id, chat_id)
            invoice_url = await tg_api.create_invoice_link(
                title="Гарантированный динамит",
                description=f"Мгновенный взрыв динамита без ожидания ({DYNAMITE_SKIP_COST_STARS} {STAR_NAME})",
                payload=payload,
                currency="XTR",
                prices=[{"label": "Гарантированный динамит", "amount": DYNAMITE_SKIP_COST_STARS}],
            )

            if not invoice_url:
                await update.message.reply_text(
                    f"⏳ Динамит на перезарядке: {cooldown_text}\n"
                    "❌ Не удалось создать ссылку оплаты. Попробуйте позже."
                )
                return

            await self.send_invoice_url_button(
                chat_id=chat_id,
                invoice_url=invoice_url,
                text=(
                    f"⏳ Динамит на перезарядке: {cooldown_text}\n\n"
                    f"⭐ Оплатите {DYNAMITE_SKIP_COST_STARS} Telegram Stars для гарантированного взрыва динамита прямо сейчас."
                ),
                user_id=user_id,
                reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
            )
            return

        await self._execute_dynamite_blast(user_id, chat_id, guaranteed=False, reply_to_message_id=update.effective_message.message_id if update.effective_message else None)
    
    async def handle_fish_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщения 'рыбалка' и других текстовых сообщений"""
        # Игнорируем сообщения, отправленные ДО запуска бота (старые рыбалки не срабатывают)
        if update.message and update.message.date:
            msg_ts = update.message.date.replace(tzinfo=None)
            if msg_ts < self.bot_start_time:
                return

        if context.user_data.get('raf_draft'):
            consumed_raf = await self.handle_raf_input(update, context)
            if consumed_raf:
                return

        if context.user_data.get('new_tour'):
            consumed = await self.handle_new_tour_input(update, context)
            if consumed:
                return

        if 'waiting_bait_selection' in context.user_data:
            data = context.user_data.get('waiting_bait_selection')
            if not data:
                return
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            if data.get('user_id') != user_id:
                return

            message = update.effective_message
            if not message or not message.text:
                return

            raw_value = message.text.strip()
            indices = [int(x) for x in re.findall(r"\d+", raw_value)]
            items = data.get('items', [])

            if not indices:
                await update.message.reply_text("Введите номера рыб из списка через пробел.")
                return

            if any(idx < 1 or idx > len(items) for idx in indices):
                await update.message.reply_text("Один или несколько номеров вне диапазона списка.")
                return

            selected_fish_ids = [items[idx - 1]['id'] for idx in indices]
            result = await _run_sync(db.convert_fish_to_bait_by_ids, user_id, chat_id, selected_fish_ids)

            if result.get('ok'):
                details = result.get('details', {})
                detail_lines = [f"• {name}: +{qty} шт." for name, qty in details.items()]
                await update.message.reply_text(
                    "✅ *Переработка завершена!*\n\n"
                    f"Переработано рыб: {result['converted_count']}\n"
                    "Получена наживка:\n"
                    + "\n".join(detail_lines),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ Ошибка переработки: {result.get('reason', 'unknown')}")

            context.user_data.pop('waiting_bait_selection', None)
            return

        if 'waiting_sell_selection' in context.user_data:
            data = context.user_data.get('waiting_sell_selection')
            if not data:
                return
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

            # --- PREVENT ABUSE / SPAM RACE CONDITION ---
            context.user_data.pop('waiting_sell_selection', None)
            context.user_data.pop('waiting_sell_quantity', None)

            selected = [items[idx - 1] for idx in indices]
            fish_ids = [f['id'] for f in selected]
            total_value = sum(f['price'] for f in selected)
            player = await _run_sync(db.get_player, user_id, chat_id)
            await _run_sync(db.mark_fish_as_sold, fish_ids)
            await _run_sync(db.update_player, user_id, chat_id, coins=player['coins'] + total_value)

            xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary(selected)
            level_info = await _run_sync(db.add_player_xp, user_id, chat_id, xp_earned)
            progress_line = format_level_progress(level_info)
            total_xp_now = level_info.get('xp_total', 0)

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
            data = context.user_data.get('waiting_sell_quantity')
            if not data:
                return
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

            # --- PREVENT ABUSE / SPAM RACE CONDITION ---
            # Как только мы получили валидное число, стираем состояние ожидающего запроса!
            # Это гарантирует, что 20 одинаковых сообщений от спамера не проскочат дальше и не продадут рыбу 20 раз
            context.user_data.pop('waiting_sell_quantity', None)

            fish_name = data.get('fish_name')
            caught_fish = await _run_sync(db.get_caught_fish, user_id, chat_id, True)
            species_fish = [
                f for f in caught_fish
                if f['fish_name'] == fish_name and not bool(f.get('is_trash'))
            ]
            if not species_fish:
                context.user_data.pop('waiting_sell_quantity', None)
                await update.message.reply_text("Рыба этого вида не найдена.")
                return

            rarity = data.get('rarity')
            if rarity in ('Легендарная', 'Мифическая') and qty < len(species_fish):
                items = sorted(species_fish, key=lambda f: float(f.get('weight') or 0), reverse=True)
                lines = []
                for idx, item in enumerate(items, 1):
                    details = await _run_sync(db.calculate_item_xp_details, item)
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
            player = await _run_sync(db.get_player, user_id, chat_id)
            await _run_sync(db.mark_fish_as_sold, fish_ids)
            await _run_sync(db.update_player, user_id, chat_id, coins=player['coins'] + total_value)

            xp_earned, base_xp, rarity_bonus, weight_bonus, total_weight = calculate_sale_summary(species_fish[:qty])
            level_info = await _run_sync(db.add_player_xp, user_id, chat_id, xp_earned)
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
        has_active_text_flow = any(
            key in context.user_data
            for key in (
                'raf_draft',
                'new_tour',
                'waiting_bait_selection',
                'waiting_sell_selection',
                'waiting_sell_quantity',
                'waiting_bait_quantity',
            )
        )
        if not has_active_text_flow and not FISH_MESSAGE_TRIGGER_RE.match(message.text or ""):
            return

        async def _dispatch_triggered_action() -> None:
            try:
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
                if re.match(r"^\s*(динамит|диномит|dynamite)\b", message_text):
                    await self.dynamite_command(update, context)
                    return
            except Exception:
                logger.exception("handle_fish_message trigger failed for user=%s chat=%s", getattr(update.effective_user, "id", None), getattr(update.effective_chat, "id", None))

        asyncio.create_task(_dispatch_triggered_action())
        return
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /weather и слова 'погода'"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        location = player['current_location']
        weather = await _run_sync(db.get_or_update_weather, location)
        eco = await _run_sync(db.get_active_ecological_disaster, location)
        
        season = get_current_season()
        weather_info = weather_system.get_weather_info(weather['condition'], weather['temperature'], season)
        weather_desc = weather_system.get_weather_description(weather['condition'])
        bonus = weather_system.get_weather_bonus(weather['condition'])
        
        eco_line = ""
        if eco:
            reward_type = "опыт" if eco.get('reward_type') == 'xp' else "монеты"
            multiplier = eco.get('reward_multiplier', 1)
            eco_line = f"\n\n🌪️ <b>Эко-катастрофа в этой локации!</b>\nКлюёт только мусор, но награда за него увеличена: <b>x{multiplier} на {reward_type}</b>!"

        message = f"""🌍 Погода в локации {location}

{weather_info}
Сезон: {season}

{weather_desc}

💡 Влияние на клёв: {bonus:+d}%{eco_line}

Погода обновляется несколько раз в день."""
        
        await update.message.reply_text(message)
    
    async def test_weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Тестовая команда для проверки влияния погоды на броски"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        player = await _run_sync(db.get_player, user_id, chat_id)
        
        if not player:
            await update.message.reply_text("Сначала создайте профиль командой /start")
            return
        
        location = player['current_location']
        weather = await _run_sync(db.get_or_update_weather, location)
        
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


        async def _render_stats() -> None:
            try:
                player, stats, total_species = await asyncio.gather(
                    _run_sync(db.get_player, user_id, chat_id),
                    _run_sync(db.get_player_stats, user_id, chat_id),
                    _run_sync(db.get_total_fish_species),
                )

                if not player:
                    await query.edit_message_text("Сначала создайте профиль командой /start")
                    return

                message = f"""
📊 Ваша статистика

🎣 Всего поймано рыбы: {stats['total_fish']}
📏 Общий вес: {stats['total_weight']} кг
💰 Продано: {stats.get('sold_fish_count', 0)} рыб ({stats.get('sold_fish_weight', 0)} кг)
🔢 Уникальных видов: {stats['unique_fish']}/{total_species}
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
            except Exception:
                logger.exception("handle_stats_callback failed for user=%s chat=%s", user_id, chat_id)
                try:
                    await query.edit_message_text("❌ Не удалось загрузить статистику. Попробуйте позже.")
                except Exception:
                    pass

        asyncio.create_task(_render_stats())
        return
    
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
        reply_anchor_id = query.message.message_id if query and query.message else None
        
        player = await _run_sync(db.get_player, user_id, chat_id)
        current_username = update.effective_user.username or update.effective_user.first_name or str(user_id)
        self._sync_player_username_if_changed(user_id, chat_id, player, current_username)

        if self._is_user_beer_drunk(user_id):
            await query.edit_message_text(self._generate_drunk_gibberish())
            return

        if await _run_sync(db.is_user_seasick, user_id):
            await query.edit_message_text(
                "🤢 Вас укачало в плавании. Ловить сейчас нельзя.\n"
                "Вылечите морскую болезнь и попробуйте снова."
            )
            return

        antibot_active_block = self._get_antibot_active_block(user_id, update)
        if antibot_active_block:
            await self._send_antibot_block_to_user(update, antibot_active_block, query=query)
            return
        
        # Проверяем кулдаун
        can_fish, message = game.can_fish(user_id, chat_id)
        if not can_fish:
            # Отправляем сообщение с причиной и кнопкой оплаты
            reply_markup = await self._build_guaranteed_invoice_markup(user_id, chat_id)
            
            await query.edit_message_text(
                f"⏰ {message}", 
                reply_markup=reply_markup
            )
            if reply_markup and query and query.message:
                self._store_active_invoice_context(
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=query.message.message_id,
                )
            return

        antibot_rhythm_block = self._register_free_fish_attempt_and_check_antibot(user_id, update)
        if antibot_rhythm_block:
            await self._send_antibot_block_to_user(update, antibot_rhythm_block, query=query)
            return
        
        # Начинаем рыбалку на текущей локации
        result = await _run_sync(game.fish, user_id, chat_id, player['current_location'])

        storm_result = await self._maybe_trigger_boat_storm(user_id, result=result)
        if storm_result and storm_result.get('applied'):
            await query.edit_message_text(self._format_storm_event_message(storm_result))
            return

        try:
            raf_won = await self._process_raf_event_roll(
                chat_id=chat_id,
                user_id=user_id,
                username=update.effective_user.username or update.effective_user.first_name,
                chat_title=update.effective_chat.title,
                result=result,
                trigger_source='start_fishing_callback',
            )
            if raf_won:
                return
        except Exception:
            logger.exception("RAF roll failed in start_fishing flow user=%s chat=%s", user_id, chat_id)

        if result.get('fight_required'):
            started = await self._start_fight_session(
                update=update,
                context=context,
                result=result,
                source_type='start_fishing_callback',
                source_ref=str(player.get('current_location') or ''),
                reply_to_message_id=reply_anchor_id,
            )
            if started:
                return

            result = game.finalize_fight_catch(
                user_id=user_id,
                chat_id=chat_id,
                location=str(result.get('location') or player.get('current_location') or ''),
                fish_data=result.get('fish') or {},
                weight=float(result.get('weight') or 0),
                length=float(result.get('length') or 0),
                target_rarity=result.get('target_rarity'),
                guaranteed=False,
            )

        tickets_awarded, tickets_jackpot, tickets_total = self._award_tickets(
            user_id,
            self._calculate_tickets_for_result(result),
            username=update.effective_user.username or update.effective_user.first_name or str(user_id),
            source_type='start_fishing_callback',
            source_ref=str(player.get('current_location') or ''),
        )
        tickets_line = self._format_tickets_award_line(tickets_awarded, tickets_jackpot, tickets_total)
        
        if result['success']:
            if result.get('is_trash'):
                trash = result.get('trash') or {}
                trash_name = (trash.get('name') or '').strip()
                location_val = result.get('location') or player.get('current_location') or chat_id

                xp_line = ""
                progress_line = ""
                if result.get('xp_earned'):
                    xp_line = f"\n✨ Опыт: +{result['xp_earned']}"
                    progress_line = f"\n{format_level_progress(result.get('level_info'))}"

                eco_line = ""
                eco = result.get('eco_disaster') or {}
                if eco:
                    reward_type = str(result.get('reward_type') or eco.get('reward_type') or 'xp').lower()
                    multiplier = int(result.get('reward_multiplier') or eco.get('reward_multiplier') or 1)
                    reward_name = "опыт" if reward_type == 'xp' else "монеты"
                    eco_line = f"\n🌪️ Эко-катастрофа: x{multiplier} на {reward_name}"

                bonus_line = ""
                bonus_coins = int(result.get('earned') or 0)
                if bonus_coins > 0:
                    bonus_line = f"\n💰 Бонус за событие: +{bonus_coins} 🪙"

                storage_line = "\n📦 Мусор добавлен в садок лодки" if result.get('is_on_boat') else "\n📦 Мусор добавлен в инвентарь"

                message = f"""
{trash_name or 'Мусор'}

📏 Вес: {trash.get('weight', 0)} кг
💰 Цена при продаже: {trash.get('price', 0)} 🪙
📍 Место: {location_val}
{xp_line}{progress_line}{eco_line}{bonus_line}{storage_line}{tickets_line}
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
                            reply_to_id = reply_anchor_id
                            try:
                                sticker_message = await self._send_document_path_cached(
                                    chat_id=update.effective_chat.id,
                                    path=image_path,
                                    reply_to_message_id=reply_to_id,
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

                await self._safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_to_message_id=sticker_message.message_id if sticker_message else reply_anchor_id,
                )

                try:
                    await self._maybe_process_duel_catch(
                        user_id=user_id,
                        chat_id=chat_id,
                        fish_name=trash_name or 'Мусор',
                        weight=float(trash.get('weight') or 0),
                        length=0.0,
                        catch_id=None,
                        resolve_latest_catch=False,
                    )
                except Exception:
                    logger.exception("Failed to process duel trash from callback user=%s chat=%s", user_id, chat_id)
                return

            fish = result.get('fish')
            if not fish:
                logger.error("Guaranteed catch missing fish data for user %s", user_id)
                # Показываем пользователю причину, если она есть
                error_msg = result.get('message') or "❌ Не удалось получить данные улова. Звезды будут возвращены."
                await self.application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_msg
                )
                telegram_payment_charge_id_val = context.user_data.get('telegram_payment_charge_id')
                await self.refund_star_payment(user_id, telegram_payment_charge_id_val)
                return

            # Проверка NFT-приза события для обычной рыбалки (кнопка).
            try:
                rolled_rarity = result.get('target_rarity')
                caught_rarity = fish.get('rarity', '')
                if rolled_rarity and caught_rarity and rolled_rarity != caught_rarity:
                    logger.info(
                        "[TORCH_LOG] Rarity mismatch (start_fishing): user_id=%s chat_id=%s location=%s rolled=%s caught=%s",
                        user_id,
                        update.effective_chat.id,
                        result.get('location'),
                        rolled_rarity,
                        caught_rarity,
                    )
                prize_rarity = caught_rarity or rolled_rarity or ''
                torch_won = await self._check_torch_event(
                    chat_id=update.effective_chat.id,
                    user_id=user_id,
                    username=update.effective_user.username or update.effective_user.first_name,
                    rarity=prize_rarity,
                    chat_title=update.effective_chat.title
                )
                if torch_won:
                    return
            except Exception as e:
                logger.error(f"Error in torch event check (start_fishing callback): {e}")

            weight = result['weight']
            length = result['length']
            fish_price = int(result.get('fish_price') or await _run_sync(db.calculate_fish_price, fish, weight, length))

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
                'Легендарная': '🟡',
                'Мифическая': '🔴'
            }
            fish_name_display = format_fish_name(fish['name'])
            
            message = f"""
🎉 Поздравляю! Вы поймали рыбу!

{rarity_emoji.get(fish['rarity'], '⚪')} {fish_name_display}
📏 Размер: {length}см | Вес: {weight} кг
💰 Стоимость: {fish_price} 🪙
📍 Место: {result['location']}
⭐ Редкость: {fish['rarity']}
{tickets_line}

Ваш баланс: {result['new_balance']} 🪙
            """
            
            if result.get('guaranteed'):
                message += "\n⭐ Гарантированный улов!"
            
            # Отправляем изображение рыбы
            sticker_message = await self._send_catch_image(
                chat_id=update.effective_chat.id,
                item_name=fish['name'],
                item_type="fish",
                reply_to_message_id=reply_anchor_id
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
            
            await self._safe_send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_to_message_id=sticker_message.message_id if sticker_message else reply_anchor_id,
            )

            try:
                await self._maybe_process_duel_catch(
                    user_id=user_id,
                    chat_id=chat_id,
                    fish_name=fish.get('name', 'Неизвестная рыба'),
                    weight=weight,
                    length=length,
                )
            except Exception:
                logger.exception("Failed to process duel catch from callback user=%s chat=%s", user_id, chat_id)

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
                wrong_bait_text = result.get('wrong_bait') or "неизвестная наживка"
                snap_message = f"""
⚠️ СРЫВ РЫБЫ!

{result['message']}

🪱 Вы использовали: {wrong_bait_text}
📍 Локация: {result['location']}
{tickets_line}

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

                eco_line = ""
                eco = result.get('eco_disaster') or {}
                if eco:
                    reward_type = str(result.get('reward_type') or eco.get('reward_type') or 'xp').lower()
                    multiplier = int(result.get('reward_multiplier') or eco.get('reward_multiplier') or 1)
                    reward_name = "опыт" if reward_type == 'xp' else "монеты"
                    eco_line = f"\n🌪️ Эко-катастрофа: x{multiplier} на {reward_name}"

                bonus_line = ""
                bonus_coins = int(result.get('earned') or 0)
                if bonus_coins > 0:
                    bonus_line = f"\n💰 Бонус за событие: +{bonus_coins} 🪙"

                storage_line = "\n📦 Мусор добавлен в садок лодки" if result.get('is_on_boat') else "\n📦 Мусор добавлен в инвентарь"

                message = f"""
{result['message']}

📦 Мусор: {result['trash']['name']}
⚖️ Вес: {result['trash']['weight']} кг
💰 Цена при продаже: {result['trash']['price']} 🪙
{xp_line}{progress_line}{eco_line}{bonus_line}{storage_line}{tickets_line}

Ваш баланс: {result['new_balance']} 🪙
                """
                
                # Отправляем изображение мусора
                sticker_message = await self._send_catch_image(
                    chat_id=update.effective_chat.id,
                    item_name=result['trash']['name'],
                    item_type="trash",
                    reply_to_message_id=reply_anchor_id
                )
                if sticker_message:
                    context.bot_data.setdefault("last_bot_stickers", {})[update.effective_chat.id] = sticker_message.message_id

                await self._safe_send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_to_message_id=sticker_message.message_id if sticker_message else reply_anchor_id,
                )

                try:
                    await self._maybe_process_duel_catch(
                        user_id=user_id,
                        chat_id=chat_id,
                        fish_name=str(result.get('trash', {}).get('name') or 'Мусор'),
                        weight=float(result.get('trash', {}).get('weight') or 0),
                        length=0.0,
                        catch_id=None,
                        resolve_latest_catch=False,
                    )
                except Exception:
                    logger.exception("Failed to process duel trash from callback user=%s chat=%s", user_id, chat_id)

                if result.get('temp_rod_broken'):
                    await self.application.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=(
                            "💥 Временная удочка сломалась после удачного улова.\n"
                            "Теперь активна бамбуковая. Купить новую можно в магазине."
                        )
                    )
                return
            elif result.get('fish_inspector') or "рыбнадзор" in result.get('message', '').lower():
                if result.get('fish_inspector'):
                    try:
                        inspector_image = FISH_STICKERS.get("Рыбнадзор")
                        if inspector_image:
                            image_path = Path(__file__).parent / inspector_image
                            if image_path.exists():
                                await self._send_document_path_cached(
                                    chat_id=update.effective_chat.id,
                                    path=image_path,
                                    reply_to_message_id=query.message.message_id if query and query.message else None,
                                )
                    except Exception as e:
                        logger.warning(f"Could not send fish inspector sticker from callback: {e}")

                await query.edit_message_text(
                    self._sanitize_public_service_text(result.get('message', '🚨 Вас поймал рыбнадзор!'))
                )
                return
            elif result.get('no_bite'):
                # Отправляем сообщение с причиной и кнопкой оплаты
                reply_markup = await self._build_guaranteed_invoice_markup(user_id, chat_id)
                
                message = f"""
😔 {result['message']}

📍 Локация: {result.get('location', player.get('current_location', 'Неизвестно'))}
{tickets_line}
                """
                
                await query.edit_message_text(message, reply_markup=reply_markup)
                if reply_markup and query and query.message:
                    self._store_active_invoice_context(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_id=query.message.message_id,
                    )

                try:
                    await self._maybe_process_duel_catch(
                        user_id=user_id,
                        chat_id=chat_id,
                        fish_name="Ничего не клюет",
                        weight=0.0,
                        length=0.0,
                        catch_id=None,
                        resolve_latest_catch=False,
                    )
                except Exception:
                    logger.exception("Failed to process duel no-bite from callback user=%s chat=%s", user_id, chat_id)
                return
            else:
                # Отправляем сообщение с причиной и кнопкой оплаты
                reply_markup = await self._build_guaranteed_invoice_markup(user_id, chat_id)
                
                message = f"""
😔 {result['message']}

📍 Локация: {result.get('location', player.get('current_location', 'Неизвестно'))}
                """
                
                await query.edit_message_text(message, reply_markup=reply_markup)
                if reply_markup and query and query.message:
                    self._store_active_invoice_context(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_id=query.message.message_id,
                    )
                return
        
        await query.edit_message_text(message)
    
    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка precheckout для Telegram Stars"""
        query = update.pre_checkout_query
        payload = getattr(query, "invoice_payload", "") or ""
        user_id = query.from_user.id
        if payload.startswith("guaranteed_"):
            parsed = self._parse_guaranteed_payload(payload)
            if not parsed:
                await query.answer(ok=False, error_message="Инвойс устарел. Запросите новый.")
                return

            payload_user_id = parsed.get("payload_user_id")
            if payload_user_id is not None and payload_user_id != user_id:
                await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                return

            created_ts = parsed.get("created_ts")
            now_ts = int(datetime.now().timestamp())
            if isinstance(created_ts, int) and now_ts - created_ts > 900:
                await query.answer(ok=False, error_message="Срок действия инвойса истек. Запросите новый.")
                return
        elif payload.startswith("harpoon_skip_"):
            parsed_harpoon = self._parse_harpoon_skip_payload(payload)
            if not parsed_harpoon:
                await query.answer(ok=False, error_message="Инвойс гарпуна устарел. Запросите новый.")
                return

            if parsed_harpoon.get("payload_user_id") != user_id:
                await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                return

            created_ts = parsed_harpoon.get("created_ts")
            now_ts = int(datetime.now().timestamp())
            if isinstance(created_ts, int) and now_ts - created_ts > 900:
                await query.answer(ok=False, error_message="Срок действия инвойса истек. Запросите новый.")
                return
        elif payload.startswith("booster_"):
            parsed_booster = self._parse_booster_payload(payload)
            if not parsed_booster:
                await query.answer(ok=False, error_message="Инвойс бустера устарел. Запросите новый.")
                return

            if parsed_booster.get("payload_user_id") != user_id:
                await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                return

            created_ts = parsed_booster.get("created_ts")
            now_ts = int(datetime.now().timestamp())
            if isinstance(created_ts, int) and now_ts - created_ts > 900:
                await query.answer(ok=False, error_message="Срок действия инвойса истек. Запросите новый.")
                return

            booster_code = str(parsed_booster.get("booster_code") or "")
            payload_chat_id = int(parsed_booster.get("group_chat_id") or 0)
            if booster_code == ECHOSOUNDER_CODE:
                if await _run_sync(db.is_echosounder_active, user_id, payload_chat_id):
                    await query.answer(ok=False, error_message="Эхолот уже активен. Дождитесь окончания.")
                    return
            else:
                active_feeder = await _run_sync(db.get_active_feeder, user_id, payload_chat_id)
                if active_feeder:
                    await query.answer(ok=False, error_message="Кормушка уже активна. Дождитесь окончания.")
                    return
        elif payload.startswith("net_skip_cd_"):
            # format: net_skip_cd_{user_id}_{chat_id}_{ts}
            parts = payload.split("_")
            try:
                payload_user_id = int(parts[3])
                created_ts = int(parts[5])
                if payload_user_id != user_id:
                    await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                    return
                if int(datetime.now().timestamp()) - created_ts > 900:
                    await query.answer(ok=False, error_message="Срок действия инвойса истек. Запросите новый.")
                    return
            except (ValueError, IndexError):
                await query.answer(ok=False, error_message="Инвойс устарел. Запросите новый.")
                return
        elif payload.startswith("dynamite_skip_"):
            parsed_dynamite = self._parse_dynamite_skip_payload(payload)
            if not parsed_dynamite:
                await query.answer(ok=False, error_message="Инвойс динамита устарел. Запросите новый.")
                return

            if parsed_dynamite.get("payload_user_id") != user_id:
                await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                return

            created_ts = parsed_dynamite.get("created_ts")
            now_ts = int(datetime.now().timestamp())
            if isinstance(created_ts, int) and now_ts - created_ts > 900:
                await query.answer(ok=False, error_message="Срок действия инвойса истек. Запросите новый.")
                return
            payload_chat_id = int(parsed_dynamite.get("group_chat_id") or 0)
            if payload_chat_id and await _run_sync(db.get_dynamite_ban_remaining, user_id, payload_chat_id) > 0:
                await query.answer(ok=False, error_message="Динамит под арестом рыбохраны. Сначала оплатите выкуп.")
                return
        elif payload.startswith("dynamite_fine_"):
            parsed_dynamite_fine = self._parse_dynamite_fine_payload(payload)
            if not parsed_dynamite_fine:
                await query.answer(ok=False, error_message="Инвойс выкупа устарел. Запросите новый.")
                return

            if parsed_dynamite_fine.get("payload_user_id") != user_id:
                await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                return

            created_ts = parsed_dynamite_fine.get("created_ts")
            now_ts = int(datetime.now().timestamp())
            if isinstance(created_ts, int) and now_ts - created_ts > 900:
                await query.answer(ok=False, error_message="Срок действия инвойса истек. Запросите новый.")
                return
        elif payload.startswith("raf_create_"):
            parsed_raf = self._parse_raf_create_payload(payload)
            if not parsed_raf:
                await query.answer(ok=False, error_message="Инвойс RAF-ивента некорректен. Создайте новый через /raf.")
                return

            if parsed_raf.get("payload_user_id") != user_id:
                await query.answer(ok=False, error_message="Этот инвойс RAF создан для другого пользователя.")
                return

            event_id = int(parsed_raf.get("event_id") or 0)
            event = await _run_sync(db.get_raf_event, event_id) if event_id else None
            if not event:
                await query.answer(ok=False, error_message="RAF-ивент не найден. Создайте новый через /raf.")
                return

            if int(event.get('creator_user_id') or 0) != int(user_id):
                await query.answer(ok=False, error_message="Этот RAF-ивент принадлежит другому пользователю.")
                return

            status = str(event.get('status') or '').strip().lower()
            if status != 'draft':
                if status == 'paid':
                    await query.answer(ok=False, error_message="RAF-ивент уже оплачен. Нажмите кнопку запуска.")
                else:
                    await query.answer(ok=False, error_message="Этот RAF-ивент нельзя оплатить в текущем статусе.")
                return
        elif payload.startswith("duel_invite_"):
            parsed_duel = self._parse_duel_invite_payload(payload)
            if not parsed_duel:
                await query.answer(ok=False, error_message="Инвойс дуэли устарел. Создайте новый вызов.")
                return

            payload_user_id = int(parsed_duel.get("payload_user_id") or 0)
            target_user_id = int(parsed_duel.get("target_user_id") or 0)
            created_ts = parsed_duel.get("created_ts")

            if payload_user_id != int(user_id):
                await query.answer(ok=False, error_message="Этот инвойс создан для другого пользователя.")
                return

            if target_user_id <= 0 or target_user_id == payload_user_id:
                await query.answer(ok=False, error_message="Некорректные данные дуэли в инвойсе.")
                return

            now_ts = int(datetime.now().timestamp())
            if isinstance(created_ts, int) and now_ts - created_ts > 900:
                await query.answer(ok=False, error_message="Срок действия инвойса истек. Создайте новый вызов.")
                return

            try:
                await _run_sync(db.expire_pending_duels)
            except Exception:
                logger.exception("precheckout duel: failed to expire pending duels")

            if await _run_sync(db.get_active_duel_for_user, payload_user_id):
                await query.answer(ok=False, error_message="У вас уже есть активная или ожидающая дуэль.")
                return

            if await _run_sync(db.get_active_duel_for_user, target_user_id):
                await query.answer(ok=False, error_message="У соперника уже есть активная или ожидающая дуэль.")
                return

            if self._is_user_beer_drunk(payload_user_id):
                await query.answer(ok=False, error_message="Вы в состоянии опьянения. Дуэль недоступна.")
                return

            if self._is_user_beer_drunk(target_user_id):
                await query.answer(ok=False, error_message="Соперник в состоянии опьянения. Дуэль недоступна.")
                return
        # Проверяем, не был ли этот инвойс уже оплачен
        if payload and payload in self.paid_payloads:
            await query.answer(ok=False, error_message="Этот инвойс уже был оплачен. Запросите новый.")
            return
        await query.answer(ok=True)
    
    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка успешной оплаты через Telegram Stars"""
        payment = update.message.successful_payment
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        payload = payment.invoice_payload or ""
        active_invoice = self.active_invoices.get(user_id) or {}
        active_invoice_chat_id = active_invoice.get("group_chat_id") or active_invoice.get("chat_id") or chat_id

        # Защита от двойной выдачи: если payload уже обработан — игнорируем
        if payload and payload in self.paid_payloads:
            logger.warning("Duplicate payment ignored for payload=%s user_id=%s", payload, user_id)
            return
        # Сразу помечаем payload как оплаченный
        if payload:
            if len(self.paid_payloads) >= self._paid_payloads_max:
                # Удаляем половину старых записей, чтобы не расти бесконечно
                old_entries = list(self.paid_payloads)
                self.paid_payloads = set(old_entries[len(old_entries)//2:])
                logger.info("paid_payloads trimmed to %d entries", len(self.paid_payloads))
            self.paid_payloads.add(payload)

        accounting_chat_id = chat_id
        parsed_guaranteed_payload = None
        parsed_harpoon_payload = None
        parsed_booster_payload = None
        parsed_dynamite_payload = None
        parsed_dynamite_fine_payload = None
        parsed_raf_payload = None
        parsed_duel_payload = None
        if payload.startswith("guaranteed_"):
            parsed_guaranteed_payload = self._parse_guaranteed_payload(payload)
            if parsed_guaranteed_payload and parsed_guaranteed_payload.get("group_chat_id"):
                accounting_chat_id = int(parsed_guaranteed_payload["group_chat_id"])
        elif payload.startswith("harpoon_skip_"):
            parsed_harpoon_payload = self._parse_harpoon_skip_payload(payload)
            if parsed_harpoon_payload and parsed_harpoon_payload.get("group_chat_id"):
                accounting_chat_id = int(parsed_harpoon_payload["group_chat_id"])
        elif payload.startswith("booster_"):
            parsed_booster_payload = self._parse_booster_payload(payload)
            if parsed_booster_payload and parsed_booster_payload.get("group_chat_id"):
                accounting_chat_id = int(parsed_booster_payload["group_chat_id"])
        elif payload.startswith("net_skip_cd_"):
            # format: net_skip_cd_{user_id}_{chat_id}_{ts}
            try:
                _parts = payload.split("_")
                accounting_chat_id = int(_parts[4])
            except (ValueError, IndexError):
                accounting_chat_id = active_invoice_chat_id
        elif payload.startswith("dynamite_skip_"):
            parsed_dynamite_payload = self._parse_dynamite_skip_payload(payload)
            if parsed_dynamite_payload and parsed_dynamite_payload.get("group_chat_id"):
                accounting_chat_id = int(parsed_dynamite_payload["group_chat_id"])
            else:
                accounting_chat_id = active_invoice_chat_id
        elif payload.startswith("dynamite_fine_"):
            parsed_dynamite_fine_payload = self._parse_dynamite_fine_payload(payload)
            if parsed_dynamite_fine_payload and parsed_dynamite_fine_payload.get("group_chat_id"):
                accounting_chat_id = int(parsed_dynamite_fine_payload["group_chat_id"])
            else:
                accounting_chat_id = active_invoice_chat_id
        elif payload.startswith("raf_create_"):
            parsed_raf_payload = self._parse_raf_create_payload(payload)
        elif payload.startswith("duel_invite_"):
            parsed_duel_payload = self._parse_duel_invite_payload(payload)
            if parsed_duel_payload and parsed_duel_payload.get("group_chat_id"):
                accounting_chat_id = int(parsed_duel_payload["group_chat_id"])
            else:
                accounting_chat_id = active_invoice_chat_id
        elif active_invoice.get("group_chat_id") or active_invoice.get("chat_id"):
            try:
                accounting_chat_id = int(active_invoice_chat_id)
            except (TypeError, ValueError):
                accounting_chat_id = chat_id

        accounting_chat_title = None
        if accounting_chat_id == chat_id:
            try:
                accounting_chat_title = update.effective_chat.title
            except Exception:
                accounting_chat_title = None
        else:
            try:
                accounting_chat_title = await _run_sync(db.get_chat_title, accounting_chat_id)
            except Exception:
                accounting_chat_title = None

        telegram_payment_charge_id = getattr(payment, "telegram_payment_charge_id", None)
        total_amount = getattr(payment, "total_amount", 0)

        # Сохраняем транзакцию
        if telegram_payment_charge_id:
            try:
                # If DB supports chat_id/chat_title columns, add them via migration-aware method
                await _run_sync(db.add_star_transaction, user_id=user_id,
                    telegram_payment_charge_id=telegram_payment_charge_id,
                    total_amount=total_amount,
                    refund_status="none",
                    chat_id=accounting_chat_id,
                    chat_title=accounting_chat_title,
                )
                # update chat-level aggregate (this will also save chat_title in chat_configs)
                await _run_sync(db.increment_chat_stars, accounting_chat_id, total_amount, chat_title=accounting_chat_title)
            except Exception as e:
                logger.warning("Failed to record star transaction or increment chat stars: %s", e)
            # If DB has explicit star_transactions chat columns we will keep them in migration
        
        # Убираем запланированный таймаут для этого сообщения
        timeout_key = f"payment_{update.effective_chat.id}_{update.message.message_id}"
        if timeout_key in self.active_timeouts:
            del self.active_timeouts[timeout_key]
        
        # Извлекаем локацию и chat_id из payload (если есть) или используем текущую
        if payload and payload.startswith("net_skip_cd_"):
            # Сброс кулдауна всех сетей
            skip_reply_id = None
            if user_id in self.active_invoices:
                skip_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]
            await _run_sync(db.reset_net_cooldowns, user_id)
            await self._safe_send_message(
                chat_id=accounting_chat_id,
                text="✅ Кулдаун всех сетей сброшен! Используйте /net чтобы закинуть сети снова.",
                reply_to_message_id=skip_reply_id,
            )
            return
        elif payload and payload.startswith("skip_boat_cd_"):
            # Сброс КД лодки
            await _run_sync(db.skip_boat_cooldown, user_id, 0)
            await self._safe_send_message(
                chat_id=accounting_chat_id,
                text="✅ КД лодки сброшен! Теперь вы снова можете выплыть в море. 🚤",
            )
            return
        elif payload and payload.startswith("dynamite_skip_"):
            if not parsed_dynamite_payload:
                parsed_dynamite_payload = self._parse_dynamite_skip_payload(payload)

            group_chat_id = accounting_chat_id
            if parsed_dynamite_payload and parsed_dynamite_payload.get("group_chat_id"):
                group_chat_id = int(parsed_dynamite_payload["group_chat_id"])

            dynamite_reply_id = None
            if user_id in self.active_invoices:
                dynamite_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]

            try:
                await self._execute_dynamite_blast(
                    user_id=user_id,
                    chat_id=group_chat_id,
                    guaranteed=True,
                    reply_to_message_id=dynamite_reply_id,
                )
            except Exception as e:
                logger.error(f"[DYNAMITE] Star payment execution failed: {e}", exc_info=True)
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Возникла ошибка при использовании динамита! Звёзды возвращены.",
                )
                await self.refund_star_payment(user_id, telegram_payment_charge_id)
            return
        elif payload and payload.startswith("dynamite_fine_"):
            if not parsed_dynamite_fine_payload:
                parsed_dynamite_fine_payload = self._parse_dynamite_fine_payload(payload)

            group_chat_id = accounting_chat_id
            if parsed_dynamite_fine_payload and parsed_dynamite_fine_payload.get("group_chat_id"):
                group_chat_id = int(parsed_dynamite_fine_payload["group_chat_id"])

            fine_reply_id = None
            if user_id in self.active_invoices:
                fine_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]

            await _run_sync(db.clear_dynamite_ban, user_id, group_chat_id)
            await self._safe_send_message(
                chat_id=group_chat_id,
                text="✅ Выкуп принят. Арест рыбохраны снят, динамит снова доступен.",
                reply_to_message_id=fine_reply_id,
            )
            return
        elif payload and payload.startswith("cure_seasick_"):
            # Снятие морской болезни
            cure_reply_id = None
            if user_id in self.active_invoices:
                cure_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]
            
            await _run_sync(db.clear_timed_effect, user_id, 'seasick')
            await self._safe_send_message(
                chat_id=accounting_chat_id,
                text="✅ Вы успешно вылечились от морской болезни! Теперь вы снова полны сил для рыбалки. 🚑",
                reply_to_message_id=cure_reply_id,
            )
            return
        elif payload and payload.startswith("repair_rod_"):
            # Обработка восстановления удочки
            rod_name = payload.replace("repair_rod_", "")
            repair_reply_id = None
            if user_id in self.active_invoices:
                repair_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]
            if rod_name in TEMP_ROD_RANGES:
                try:
                    await self._safe_send_message(
                        chat_id=accounting_chat_id,
                        text="❌ Эта удочка одноразовая и не ремонтируется.",
                        reply_to_message_id=repair_reply_id,
                    )
                except Exception as e:
                    logger.warning(f"Could not send temp rod repair rejection to {user_id}: {e}")
                return
            await _run_sync(db.repair_rod, user_id, rod_name, accounting_chat_id)
            try:
                await self._safe_send_message(
                    chat_id=accounting_chat_id,
                    text=f"✅ Удочка '{rod_name}' полностью восстановлена!",
                    reply_to_message_id=repair_reply_id,
                )
            except Exception as e:
                logger.warning(f"Could not send repair confirmation to {user_id}: {e}")
            return
        elif payload and payload.startswith("harpoon_skip_"):
            if not parsed_harpoon_payload:
                parsed_harpoon_payload = self._parse_harpoon_skip_payload(payload)

            group_chat_id = accounting_chat_id
            if parsed_harpoon_payload and parsed_harpoon_payload.get("group_chat_id"):
                group_chat_id = int(parsed_harpoon_payload["group_chat_id"])

            group_message_id = None
            if user_id in self.active_invoices:
                group_message_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]

            await self._execute_harpoon_catch(
                user_id=user_id,
                group_chat_id=group_chat_id,
                reply_to_message_id=group_message_id,
            )
            return
        elif payload and payload.startswith("booster_"):
            if not parsed_booster_payload:
                parsed_booster_payload = self._parse_booster_payload(payload)

            if not parsed_booster_payload:
                await update.message.reply_text("❌ Не удалось обработать оплату бустера. Попробуйте ещё раз.")
                return

            booster_code = str(parsed_booster_payload.get("booster_code") or "")
            group_chat_id = int(parsed_booster_payload.get("group_chat_id") or accounting_chat_id)

            booster_reply_id = None
            if user_id in self.active_invoices:
                booster_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]

            if booster_code == ECHOSOUNDER_CODE:
                await _run_sync(db.activate_echosounder, user_id, group_chat_id, ECHOSOUNDER_DURATION_HOURS)
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text=(
                        f"✅ Эхолот активирован на {ECHOSOUNDER_DURATION_HOURS} часа!\n"
                        "Откройте меню наживки и нажмите кнопку 'Эхолот'."
                    ),
                    reply_to_message_id=booster_reply_id,
                )
                return

            feeder = self._get_feeder_by_code(booster_code)
            if not feeder:
                await update.message.reply_text("❌ Неизвестный тип кормушки.")
                return

            try:
                await _run_sync(db.activate_feeder, user_id,
                    group_chat_id,
                    feeder_type=booster_code,
                    bonus_percent=int(feeder["bonus"]),
                    duration_minutes=int(feeder["duration_minutes"]),
                )
            except Exception as e:
                logger.exception("Failed to activate feeder after payment for user=%s chat=%s: %s", user_id, group_chat_id, e)
                # refund stars if possible
                try:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                except Exception:
                    logger.exception("Failed to refund stars after feeder activation failure for user=%s", user_id)

                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Ошибка при активации кормушки после оплаты. Средства возвращены. Попробуйте позже.",
                    reply_to_message_id=booster_reply_id,
                )
                return

            await self._safe_send_message(
                chat_id=group_chat_id,
                text=(
                    f"✅ {feeder['name']} активирована на 1 час!\n"
                    f"🎯 Бонус к клёву: +{feeder['bonus']}%"
                ),
                reply_to_message_id=booster_reply_id,
            )
            return
        elif payload and payload.startswith("raf_create_"):
            if not parsed_raf_payload:
                parsed_raf_payload = self._parse_raf_create_payload(payload)

            if not parsed_raf_payload:
                await self._safe_send_message(
                    chat_id=chat_id,
                    text="❌ Не удалось распознать оплату RAF-ивента. Повторите /raf.",
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            event_id = int(parsed_raf_payload.get("event_id") or 0)
            payload_user_id = int(parsed_raf_payload.get("payload_user_id") or 0)
            if payload_user_id != user_id:
                await self._safe_send_message(
                    chat_id=chat_id,
                    text="❌ Этот платеж RAF не соответствует вашему аккаунту. Оформлен возврат.",
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            event = await _run_sync(db.get_raf_event, event_id) if event_id else None
            if not event or int(event.get('creator_user_id') or 0) != user_id:
                await self._safe_send_message(
                    chat_id=chat_id,
                    text="❌ RAF-ивент не найден или недоступен. Оформлен возврат.",
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            current_status = str(event.get('status') or '').strip().lower()
            payment_marked = False
            if current_status == 'draft':
                payment_marked = await _run_sync(db.mark_raf_event_paid, event_id, user_id, telegram_payment_charge_id or '')

            if not payment_marked:
                refreshed = await _run_sync(db.get_raf_event, event_id)
                refreshed_status = str((refreshed or {}).get('status') or '').strip().lower()
                if refreshed_status != 'paid':
                    await self._safe_send_message(
                        chat_id=chat_id,
                        text="❌ Не удалось подтвердить оплату RAF-ивента. Оформлен возврат.",
                    )
                    if telegram_payment_charge_id:
                        await self.refund_star_payment(user_id, telegram_payment_charge_id)
                    return

            if user_id in self.active_invoices:
                del self.active_invoices[user_id]

            context.user_data.pop('raf_draft', None)

            start_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🚀 Начать RAF-ивент", callback_data=f"raf_start_{event_id}_{user_id}")]]
            )

            event_title = html.escape(str(event.get('title') or f"RAF-ивент #{event_id}"))
            target_chat_id = event.get('target_chat_id')
            await self._safe_send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Оплата получена для <b>{event_title}</b> (ID: {event_id}).\n"
                    f"🎯 Целевой чат: {target_chat_id}\n\n"
                    "Нажмите кнопку ниже, чтобы запустить ивент."
                ),
                reply_markup=start_markup,
                parse_mode="HTML",
            )
            return
        elif payload and payload.startswith("duel_invite_"):
            if not parsed_duel_payload:
                parsed_duel_payload = self._parse_duel_invite_payload(payload)

            duel_reply_id = None
            if user_id in self.active_invoices:
                duel_reply_id = (
                    self.active_invoices[user_id].get('group_message_id')
                    or self.active_invoices[user_id].get('message_id')
                    or self.active_invoices[user_id].get('msg_id')
                )
                del self.active_invoices[user_id]

            if not parsed_duel_payload:
                await self._safe_send_message(
                    chat_id=accounting_chat_id,
                    text="❌ Не удалось распознать оплату дуэли. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            payload_user_id = int(parsed_duel_payload.get("payload_user_id") or 0)
            target_user_id = int(parsed_duel_payload.get("target_user_id") or 0)
            group_chat_id = int(parsed_duel_payload.get("group_chat_id") or accounting_chat_id)

            if payload_user_id != int(user_id) or target_user_id <= 0 or target_user_id == payload_user_id:
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Ошибка данных оплаты дуэли. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            try:
                await _run_sync(db.expire_pending_duels)
            except Exception:
                logger.exception("successful_payment duel: failed to expire pending duels")

            if await _run_sync(db.get_active_duel_for_user, payload_user_id) or await _run_sync(db.get_active_duel_for_user, target_user_id):
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Нельзя создать дуэль: у одного из игроков уже есть активная/ожидающая дуэль. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            if self._is_user_beer_drunk(payload_user_id):
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Нельзя начать дуэль: вы в состоянии опьянения. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            if self._is_user_beer_drunk(target_user_id):
                target_label = self._duel_user_label(
                    target_user_id,
                    str(parsed_duel_payload.get("target_username") or "").strip() or None,
                )
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text=f"❌ Нельзя начать дуэль: {target_label} в состоянии опьянения. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            inviter_username = update.effective_user.username or update.effective_user.first_name or str(payload_user_id)
            target_username = str(parsed_duel_payload.get("target_username") or "").strip()
            if not target_username:
                target_username = await _run_sync(db.get_username_by_user_id, target_user_id) or ""

            create_result = await _run_sync(db.create_duel_invitation, chat_id=group_chat_id,
                inviter_id=payload_user_id,
                target_id=target_user_id,
                inviter_username=inviter_username,
                target_username=target_username or None,
                attempt_type='paid',
                invite_timeout_seconds=DUEL_INVITE_TIMEOUT_SECONDS,
                free_limit=DUEL_FREE_INVITES_PER_DAY,
            )

            if not create_result.get('ok'):
                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Не удалось создать дуэль после оплаты. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return

            duel = create_result.get('duel') or {}
            sent_message = await self._send_duel_invitation_message(
                chat_id=group_chat_id,
                duel=duel,
                attempts_left_after=None,
                reply_to_message_id=duel_reply_id,
            )
            if not sent_message:
                try:
                    force_now = datetime.now(timezone.utc) + timedelta(seconds=DUEL_INVITE_TIMEOUT_SECONDS + 1)
                    await _run_sync(db.expire_duel_invitation_by_id, int(duel.get('id') or 0), now=force_now)
                except Exception:
                    logger.exception("Failed to rollback paid duel invite duel_id=%s", duel.get('id'))

                await self._safe_send_message(
                    chat_id=group_chat_id,
                    text="❌ Не удалось отправить приглашение в дуэль. Средства возвращены.",
                    reply_to_message_id=duel_reply_id,
                )
                if telegram_payment_charge_id:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                return
            return
        elif payload and payload.startswith("guaranteed_"):
            parsed = parsed_guaranteed_payload or self._parse_guaranteed_payload(payload)
            invoice_group_chat_id = active_invoice.get("group_chat_id") or active_invoice.get("chat_id")
            if parsed:
                group_chat_id = parsed.get("group_chat_id") or invoice_group_chat_id or update.effective_chat.id
                location = parsed.get("location")
            else:
                location = None
                group_chat_id = invoice_group_chat_id or update.effective_chat.id

            if not location:
                location = "Неизвестно"
                try:
                    player_by_group = await _run_sync(db.get_player, user_id, group_chat_id)
                    if player_by_group and player_by_group.get('current_location'):
                        location = player_by_group['current_location']
                except Exception as e:
                    logger.warning(f"Could not resolve location for guaranteed payload user={user_id}, chat={group_chat_id}: {e}")
        else:
            # Получаем текущую локацию игрока
            player = await _run_sync(db.get_player, user_id, chat_id)
            location = player['current_location']
            group_chat_id = update.effective_chat.id
        
        # Получаем и сохраняем информацию о сообщении с кнопкой ДО удаления из active_invoices
        group_message_id = None
        if user_id in self.active_invoices:
            group_message_id = (
                self.active_invoices[user_id].get('group_message_id')
                or self.active_invoices[user_id].get('message_id')
                or self.active_invoices[user_id].get('msg_id')
            )
            # Теперь удаляем инвойс из активных
            del self.active_invoices[user_id]
        
        # Выполняем гарантированный улов (все проверки уже пройдены в precheckout)
        # Дополнительно: если бамбуковая/обычная удочка сломана — возвращаем звезду
        player_rod_check = await _run_sync(db.get_player, user_id, group_chat_id)
        if player_rod_check:
            _current_rod = player_rod_check.get('current_rod', BAMBOO_ROD)
            if _current_rod not in TEMP_ROD_RANGES:
                _rod_data = await _run_sync(db.get_player_rod, user_id, _current_rod, group_chat_id)
                if _rod_data and _rod_data.get('current_durability', 100) <= 0:
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                    await self._safe_send_message(
                        chat_id=group_chat_id,
                        text=(
                            "💔 Гарантированный улов отменён — ваша удочка сломана!\n"
                            "Оплата возвращена. Используйте /repair или кнопку ремонта за 20 ⭐."
                        ),
                        reply_to_message_id=group_message_id,
                    )
                    return
        # Если игрок арестован рыбнадзором — возвращаем звезду
        if player_rod_check and player_rod_check.get('is_banned'):
            _ban_until = player_rod_check.get('ban_until')
            if _ban_until:
                from datetime import datetime as _dt
                if _dt.now() < _dt.fromisoformat(_ban_until):
                    await self.refund_star_payment(user_id, telegram_payment_charge_id)
                    await self._safe_send_message(
                        chat_id=group_chat_id,
                        text="⛔️ Гарантированный улов отменён — вы под арестом рыбнадзора!\nОплата возвращена. Откупитесь командой /payfine (15 ⭐).",
                        reply_to_message_id=group_message_id,
                    )
                    return

        if await _run_sync(db.is_user_seasick, user_id):
            await self.refund_star_payment(user_id, telegram_payment_charge_id)
            await self._safe_send_message(
                chat_id=group_chat_id,
                text=(
                    "🤢 Гарантированный улов отменён — у вас морская болезнь во время плавания.\n"
                    "Оплата возвращена. Вылечитесь и попробуйте снова."
                ),
                reply_to_message_id=group_message_id,
            )
            return

        # Инициализируем переменные состояния популяции значениями по умолчанию
        location_changed = False
        consecutive_casts = 0
        show_warning = False

        try:
            # Гарантированный фиш-заброс тоже должен засчитываться для снятия штрафа популяции.
            try:
                location_changed, consecutive_casts, show_warning = await _run_sync(
                    db.update_population_state,
                    user_id,
                    location
                )
            except Exception:
                logger.exception("Failed to update population state from guaranteed catch for user=%s location=%s", user_id, location)

            result = await _run_sync(game.fish, user_id, group_chat_id, location, guaranteed=True)
            
        except Exception as e:
            logger.error(f"Critical error in guaranteed catch for user {user_id}: {e}", exc_info=True)
            message = f"❌ Произошла критическая ошибка при выполнении улова: {str(e)}. Пожалуйста, обратитесь в поддержку."
            await self._safe_send_message(
                chat_id=update.effective_chat.id,
                text=message
            )

            # Возвращаем звезды, если оплата прошла, но улов не был обработан
            await self.refund_star_payment(user_id, telegram_payment_charge_id)
            return

        tickets_awarded, tickets_jackpot, tickets_total = self._award_tickets(
            user_id,
            self._calculate_tickets_for_result(result),
            username=update.effective_user.username or update.effective_user.first_name or str(user_id),
            source_type='guaranteed_fish',
            source_ref=str(location),
        )
        tickets_line = self._format_tickets_award_line(tickets_awarded, tickets_jackpot, tickets_total)

        try:
            raf_won = await self._process_raf_event_roll(
                chat_id=group_chat_id,
                user_id=user_id,
                username=update.effective_user.username or update.effective_user.first_name,
                chat_title=accounting_chat_title,
                result=result,
                trigger_source='guaranteed_fish',
            )
            if raf_won:
                return
        except Exception:
            logger.exception("RAF roll failed in guaranteed flow user=%s chat=%s", user_id, group_chat_id)
        
        # If result indicates trash (even when success==False in game logic), handle it here
        if result.get('is_trash'):
            trash = result.get('trash') or {}
            message = f"""
{trash.get('name', 'Мусор')}

📏 Вес: {trash.get('weight', 0)} кг
💰 Стоимость: {trash.get('price', 0)} 🪙
📍 Место: {result.get('location', location)}
{tickets_line}
            """

            # Try to send trash sticker in reply to the original group message (invoice button)
            sticker_message = None
            try:
                sticker_message = await self._send_catch_image(
                    chat_id=group_chat_id,
                    item_name=trash.get('name', ''),
                    item_type="trash",
                    reply_to_message_id=group_message_id,
                )
            except Exception as e:
                logger.warning(f"Could not send trash image for {trash.get('name')}: {e}")

            # If we had a sticker, reply with info to the sticker; otherwise reply to the original group message
            await self._safe_send_message(
                chat_id=group_chat_id,
                text=message,
                reply_to_message_id=sticker_message.message_id if sticker_message else group_message_id,
            )

            try:
                await self._maybe_process_duel_catch(
                    user_id=user_id,
                    chat_id=group_chat_id,
                    fish_name=str(trash.get('name') or 'Мусор'),
                    weight=float(trash.get('weight') or 0),
                    length=0.0,
                    catch_id=None,
                    resolve_latest_catch=False,
                )
            except Exception:
                logger.exception("Failed to process duel trash from guaranteed flow user=%s chat=%s", user_id, group_chat_id)
            return

        fish = result.get('fish')
        if not fish:
            logger.error("Guaranteed catch missing fish data for user %s", user_id)
            await self._safe_send_message(chat_id=update.effective_chat.id, text="❌ Не удалось получить данные улова. Звезды будут возвращены.")
            await self.refund_star_payment(user_id, telegram_payment_charge_id)
            return

        # Проверка NFT-приза события только для гарантированного улова.
        try:
            rolled_rarity = result.get('target_rarity')
            caught_rarity = fish.get('rarity', '')
            if rolled_rarity and caught_rarity and rolled_rarity != caught_rarity:
                logger.info(
                    "[TORCH_LOG] Rarity mismatch (guaranteed): user_id=%s chat_id=%s location=%s rolled=%s caught=%s",
                    user_id,
                    group_chat_id,
                    result.get('location'),
                    rolled_rarity,
                    caught_rarity,
                )
            prize_rarity = caught_rarity or rolled_rarity or ''
            torch_won = await self._check_torch_event(
                chat_id=group_chat_id,
                user_id=user_id,
                username=update.effective_user.username or update.effective_user.first_name,
                rarity=prize_rarity,
                chat_title=accounting_chat_title
            )
            if torch_won:
                return
        except Exception as e:
            logger.error(f"Error in torch event check (guaranteed): {e}")

        weight = result['weight']
        length = result['length']

        player = await _run_sync(db.get_player, user_id, group_chat_id)
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

        # Добавляем примечание о популяции (дебафф при частых забросах на одной локации)
        population_penalty = result.get('population_penalty', 0)
        consecutive_casts_count = result.get('consecutive_casts', 0)
        
        # Отправляем сообщение с характеристиками рыбы
        fish_name_display = format_fish_name(fish['name'])
        message = f"🐟 {fish_name_display}\n\n" + \
                  f"📏 Размер: {length}см | Вес: {weight} кг\n" + \
                  f"💰 Стоимость: {fish['price']} 🪙\n" + \
                  f"📍 Место: {result['location']}\n" + \
                  f"⭐ Редкость: {fish['rarity']}\n" + \
                  f"{tickets_line}"
        
        # Если было сформировано примечание о популяции, добавляем его
        if consecutive_casts_count >= 30 and population_penalty > 0:
             message += f"\n\n⚠️ Популяция рыб снижена на {int(population_penalty)}%\nЗабросов подряд: {consecutive_casts_count}/∞"


        # Получаем информацию о сообщении с кнопкой (уже получена выше перед удалением из active_invoices)
        logger.info(f"Using group_message_id for user {user_id}: {group_message_id}")

        # Отправляем изображение рыбы - в ответ на сообщение с кнопкой
        sticker_message = await self._send_catch_image(
            chat_id=group_chat_id,
            item_name=fish['name'],
            item_type="fish",
            reply_to_message_id=group_message_id
        )

        # Всегда отправляем текстовое сообщение о рыбе (вынесено из блока стикера)
        await self._safe_send_message(chat_id=group_chat_id, text=message, reply_to_message_id=sticker_message.message_id if sticker_message else group_message_id)

        try:
            await self._maybe_process_duel_catch(
                user_id=user_id,
                chat_id=group_chat_id,
                fish_name=fish.get('name', 'Неизвестная рыба'),
                weight=weight,
                length=length,
            )
        except Exception:
            logger.exception("Failed to process duel catch from guaranteed flow user=%s chat=%s", user_id, group_chat_id)

        if result.get('temp_rod_broken'):
            await self._safe_send_message(chat_id=group_chat_id, text=(
                "💥 Временная удочка сломалась после удачного улова.\n"
                "Теперь активна бамбуковая. Купить новую можно в магазине."
            ))

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
            session = await get_http_session()
            async with session.post(url, data=payload) as response:
                data = await response.json(content_type=None)
                status = response.status
            if status == 200 and data.get("ok"):
                await _run_sync(db.update_star_refund_status, telegram_payment_charge_id, "ref")
                logger.info("Stars refund successful for user=%s, charge_id=%s", user_id, telegram_payment_charge_id)
                return True

            logger.error("Stars refund failed: status=%s, response=%s", status, data)
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

        existing = await _run_sync(db.get_star_transaction, telegram_payment_charge_id)
        if not existing:
            await _run_sync(db.add_star_transaction, user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                total_amount=total_amount,
                refund_status="need to ban"
            )
        else:
            if existing.get("refund_status") != "ref":
                await _run_sync(db.update_star_refund_status, telegram_payment_charge_id, "need to ban")
    
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
            if isinstance(created_at, datetime):
                created_time = created_at
            elif isinstance(created_at, str):
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

        # Legacy callback: преобразуем в URL-кнопку на месте без дополнительных сообщений
        reply_markup = await self._build_guaranteed_invoice_markup(user_id, chat_id)
        if not reply_markup:
            await query.answer("Не удалось создать ссылку оплаты", show_alert=True)
            return
        try:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except BadRequest:
            pass
        if query and query.message:
            self._store_active_invoice_context(
                user_id=user_id,
                chat_id=chat_id,
                message_id=query.message.message_id,
            )
        await query.answer("Ссылка оплаты обновлена. Нажмите кнопку ещё раз.", show_alert=False)
    
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
                invoice_message_id = invoice_info.get('group_message_id') or invoice_info.get('message_id') or invoice_info.get('msg_id')
                if invoice_message_id == message_id:
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
        error = context.error

        # Частый кейс при запуске двух инстансов с одним токеном
        if isinstance(error, Conflict):
            logger.warning("Conflict: запущено несколько инстансов бота с одним токеном")
            return

        # Временные сетевые ошибки Telegram API не требуют сообщения пользователю
        if isinstance(error, NetworkError):
            logger.warning(f"Сетевая ошибка Telegram API: {error}")
            return

        logger.error(f"Update {update} caused error {error}")
        
        # Проверяем тип ошибки
        if isinstance(error, (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError)):
            logger.error("Проблема с подключением к Telegram API. Проверьте интернет-соединение.")
        elif isinstance(error, (asyncio.TimeoutError, TimedOut)):
            logger.error("Таймаут подключения к Telegram API. Попробуйте позже.")
        elif isinstance(error, aiohttp.ClientResponseError):
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


BOT_INSTANCE_LOCK_KEY = int(os.getenv('BOT_INSTANCE_LOCK_KEY', '32004517'))
_bot_instance_lock_conn = None
_bot_instance_lock_file = None


def _acquire_single_instance_lock() -> bool:
    """Не даёт запустить второй polling-инстанс с тем же токеном."""
    global _bot_instance_lock_conn, _bot_instance_lock_file

    if os.getenv('BOT_DISABLE_SINGLE_INSTANCE_LOCK', '0') == '1':
        logger.warning("Single-instance lock disabled by BOT_DISABLE_SINGLE_INSTANCE_LOCK=1")
        return True

    database_url = str(os.getenv('DATABASE_URL') or '').lower()
    if database_url.startswith('postgres'):
        try:
            conn = db._connect()
            cursor = conn.cursor()
            cursor.execute('SELECT pg_try_advisory_lock(%s)', (BOT_INSTANCE_LOCK_KEY,))
            row = cursor.fetchone()
            got_lock = bool(row and row[0])
            if got_lock:
                _bot_instance_lock_conn = conn
                logger.info('Single-instance polling lock acquired via Postgres advisory lock')
                return True

            try:
                conn.close()
            except Exception:
                pass
            logger.error('Another bot instance already holds polling lock. Exiting this process.')
            return False
        except Exception:
            logger.exception('Failed to acquire Postgres advisory lock. Falling back to local lock.')

    try:
        import fcntl
    except Exception:
        # On platforms without fcntl (e.g. Windows), skip local file lock fallback.
        return True

    lock_path = os.getenv('BOT_SINGLE_INSTANCE_LOCK_FILE', '/tmp/fishbot_polling.lock')
    lock_file = None
    try:
        lock_file = open(lock_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _bot_instance_lock_file = lock_file
        logger.info('Single-instance polling lock acquired via file lock: %s', lock_path)
        return True
    except Exception:
        if lock_file is not None:
            try:
                lock_file.close()
            except Exception:
                pass
        logger.error('Another local bot process already running (lock: %s). Exiting this process.', lock_path)
        return False


async def check_telegram_api() -> Optional[Dict[str, Any]]:
    session = await get_http_session()
    async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe") as response:
        if response.status != 200:
            text = await response.text()
            raise RuntimeError(f"Telegram API status={response.status}, response={text}")
        payload = await response.json(content_type=None)
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")
    return payload.get("result")


async def check_telegram_api_once() -> Optional[Dict[str, Any]]:
    try:
        return await check_telegram_api()
    finally:
        await close_global_clients()


def get_public_base_url() -> str:
    raw = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("WEBAPP_URL")
        or os.getenv("RAILWAY_PUBLIC_DOMAIN")
        or os.getenv("APP_DOMAIN")
        or ""
    ).strip().rstrip("/")
    if raw and not re.match(r"^https?://", raw):
        raw = f"https://{raw.lstrip('/')}"
    return raw


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
            bot_info = {"result": asyncio.run(check_telegram_api_once())}
            if bot_info.get("result"):
                print(f"✅ Соединение успешно! Бот: @{bot_info['result']['username']}")
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
            bot_info = {"result": asyncio.run(check_telegram_api_once())}
            if bot_info.get("result"):
                print(f"✅ Подключение успешно! Бот: @{bot_info['result']['username']}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"❌ Ошибка подключения к Telegram API: {e}")
            print("Проверьте интернет-соединение или используйте прокси:")
            print("python bot.py --proxy socks5://127.0.0.1:1080")
            return
        except Exception as e:
            print(f"❌ Неизвестная ошибка: {e}")
            return

    if not _acquire_single_instance_lock():
        print("⚠️ Уже запущен другой инстанс бота с этим токеном. Завершаю текущий процесс.")
        return
    
    # Создаем экземпляр бота
    bot_instance = FishBot()

    # NOTE: DB fixer run removed. Manual fixes should be performed with tools/fix_caught_fish_chatid.py
    
    # Создаем приложение
    defaults = Defaults(parse_mode="HTML")
    # Таймауты сети для предотвращения зависания бота.
    # Передаём их в HTTPXRequest, т.к. при использовании .bot() в builder'е
    # нельзя задавать таймауты через builder — они должны быть на уровне Request.
    from telegram.request import HTTPXRequest
    _read_timeout = float(os.getenv('TG_READ_TIMEOUT', '60'))
    _write_timeout = float(os.getenv('TG_WRITE_TIMEOUT', '60'))
    _connect_timeout = float(os.getenv('TG_CONNECT_TIMEOUT', '30'))
    _pool_timeout = float(os.getenv('TG_POOL_TIMEOUT', '60'))
    _request = HTTPXRequest(
        read_timeout=_read_timeout,
        write_timeout=_write_timeout,
        connect_timeout=_connect_timeout,
        pool_timeout=_pool_timeout,
        connection_pool_size=int(os.getenv('TG_CONNECTION_POOL_SIZE', '512')),
    )
    emoji_bot = EmojiBot(token=BOT_TOKEN, defaults=defaults, request=_request)

    async def _post_init(application: Application):
        try:
            await get_http_session()
            await init_async_storage()
            # Ensure DB table exists synchronously, then schedule the async worker
            notifications.init_notifications_table()
            await notifications.start_worker(application)
        except Exception as e:
            logger.exception("post_init: failed to start notifications worker: %s", e)

    async def _post_shutdown(application: Application):
        await close_global_clients()

    application = (
        Application.builder()
        .bot(emoji_bot)
        .concurrent_updates(max(1, int(os.getenv('TG_CONCURRENT_UPDATES', '512'))))
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    # Устанавливаем приложение в экземпляр бота
    bot_instance.application = application
    
    # --- PATCH BEGIN: BLOCK CONCURRENT UPDATES FOR SAME USER ---
    # Это исправляет рейс-кондишн (двойные нажатия, проскакивание КД),
    # заставляя апдейты от одного юзера обрабатываться последовательно, 
    # в то время как весь остальной поток идет асинхронно параллельно.
    original_process_update = application.process_update
    async def process_update_with_lock(update: Update, *args, **kwargs):
        user = getattr(update, 'effective_user', None)
        # Блокируем ТОЛЬКО нажатия на инлайн-кнопки (callback_query). 
        # Это спасет от двойных продаж рыбы (двойных кликов по кнопке) и багов с гонкой, гарантируя последовательную обработку кнопок.
        # А обычные текстовые сообщения (например спам ловлей рыбы) пойдут параллельно и моментально без блокировок, никаких сообщений-ошибок.
        if user and hasattr(user, 'id') and update.callback_query:
            async with _action_locks[user.id]:
                return await original_process_update(update, *args, **kwargs)
                
        # Текстовые сообщения и все прочее пропускаем как есть
        return await original_process_update(update, *args, **kwargs)
    application.process_update = process_update_with_lock
    # --- PATCH END ---

    # Создаем asyncio scheduler
    bot_instance.scheduler = AsyncIOScheduler()
    async def warm_up_bot():
        try:
            me = await application.bot.get_me()
            logger.info("Warm-up ok: @%s", getattr(me, "username", None))
        except Exception:
            logger.exception("Warm-up failed")

    bot_instance.scheduler.add_job(
        warm_up_bot,
        "cron",
        minute=f"*/{int(os.getenv('WARMUP_INTERVAL_MINUTES', '5'))}",
        id="telegram_warm_up",
        replace_existing=True,
        max_instances=1,
    )
    # Scheduler будет запущен после запуска приложения
    print("✅ Application создана успешно")

    async def dbinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Owner-only helper to inspect runtime DB file on the container
        owner_id = 793216884
        user_id = getattr(update.effective_user, 'id', None)
        if user_id != owner_id:
            await update.message.reply_text("Нет доступа.")
            return

        path = os.environ.get('FISHBOT_DB_PATH', DB_PATH)
        lines = []
        try:
            st = os.stat(path)
            lines.append(f"Path: {path}")
            lines.append(f"Size: {st.st_size} bytes")
            lines.append(f"Mtime: {datetime.fromtimestamp(st.st_mtime)}")
            async with aiofiles.open(path, 'rb') as f:
                header = await f.read(16)
            try:
                header_text = header.decode('ascii', errors='replace')
            except Exception:
                header_text = str(header)
            lines.append(f"Header: {header.hex()}  ({header_text})")
        except Exception as e:
            lines.append("DB read error: " + str(e))

        backups_list = []
        try:
            backups_dir = Path('/data/backups')
            if backups_dir.exists():
                for b in sorted(backups_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
                    backups_list.append(f"{b.name}  {b.stat().st_size} bytes  {datetime.fromtimestamp(b.stat().st_mtime)}")
        except Exception:
            pass

        if backups_list:
            lines.append("Backups:\n" + "\n".join(backups_list))
        else:
            lines.append("Backups: none")

        await update.message.reply_text("\n\n".join(lines))

    async def dbstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return

        out_lines = []
        try:
            # Use db connection wrapper (works with sqlite or Postgres depending on DATABASE_URL)
            conn = await _run_sync(db._connect)
            cur = conn.cursor()
            # Basic counts
            for q, label in [
                ("SELECT COUNT(*) FROM players", "Players"),
                ("SELECT COUNT(*) FROM chat_configs", "Chat configs"),
                ("SELECT COUNT(*) FROM caught_fish", "Caught fish"),
                ("SELECT COUNT(*) FROM star_transactions", "Star transactions"),
            ]:
                try:
                    cur.execute(q)
                    val = cur.fetchone()[0]
                except Exception:
                    val = 'n/a'
                out_lines.append(f"{label}: {val}")

            # Top players by coins
            out_lines.append("\nTop players by coins:")
            try:
                cur.execute("SELECT user_id, username, coins, stars FROM players ORDER BY coins DESC LIMIT 5")
                rows = cur.fetchall()
                if rows:
                    for r in rows:
                        out_lines.append(f"{r[1]} ({r[0]}): coins={r[2]} stars={r[3]}")
                else:
                    out_lines.append("(none)")
            except Exception as e:
                out_lines.append("Top query failed: " + str(e))

            conn.close()
        except Exception as e:
            out_lines.append("DB error: " + str(e))

        await update.message.reply_text("\n".join(out_lines))

    # debug notification commands removed — notifications are sent automatically on successful payments

    async def backupdb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return
        try:
            import shutil, time, os
            src = os.environ.get('FISHBOT_DB_PATH', DB_PATH)
            dst_dir = os.path.join(os.path.dirname(src), 'backups')
            os.makedirs(dst_dir, exist_ok=True)
            ts = int(time.time())
            dst = os.path.join(dst_dir, f'fishbot.db.{ts}')
            shutil.copy2(src, dst)
            await update.message.reply_text(f"Backup created: {dst}")
        except Exception as e:
            await update.message.reply_text("Backup failed: " + str(e))

    async def getbackup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: send the most recent backup (or live DB) to owner in private chat as .gz"""
        owner_id = 793216884
        user_id = getattr(update.effective_user, 'id', None)
        if user_id != owner_id:
            await update.message.reply_text("Нет доступа.")
            return

        try:
            import os, gzip, shutil
            from pathlib import Path

            src = os.environ.get('FISHBOT_DB_PATH', DB_PATH)
            src_path = Path(src)
            backups_dir = src_path.parent / 'backups'

            candidate = None
            if backups_dir.exists():
                files = sorted(backups_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                if files:
                    candidate = files[0]
            if not candidate:
                candidate = src_path

            if not candidate.exists():
                await update.message.reply_text("Файл базы данных не найден.")
                return

            gz_path = candidate.with_suffix(candidate.suffix + '.gz')
            # create gzipped copy without blocking the event loop
            await gzip_copy_async(candidate, gz_path)

            # send in private chat
            try:
                async with get_send_semaphore():
                    await context.bot.send_document(chat_id=user_id, document=await async_file_bytes(gz_path))
                await update.message.reply_text(f"Отправил {gz_path.name} в личку.")
            except Exception as e:
                await update.message.reply_text(f"Ошибка при отправке: {e}")
            finally:
                try:
                    gz_path.unlink()
                except Exception:
                    pass
        except Exception as e:
            await update.message.reply_text("Ошибка: " + str(e))

    async def restore_backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: restore the most recent backup found in backups/ to DB_PATH."""
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return
        try:
            import shutil, os
            src = os.environ.get('FISHBOT_DB_PATH', DB_PATH)
            backups_dir = os.path.join(os.path.dirname(src), 'backups')
            if not os.path.isdir(backups_dir):
                await update.message.reply_text(f"Backups directory not found: {backups_dir}")
                return
            files = sorted([os.path.join(backups_dir, f) for f in os.listdir(backups_dir)], key=lambda p: os.path.getmtime(p), reverse=True)
            if not files:
                await update.message.reply_text("No backup files found in backups directory.")
                return
            latest = files[0]
            # Make a safety copy of current DB
            current = src
            safe_copy = current + ".pre_restore"
            shutil.copy2(current, safe_copy)
            shutil.copy2(latest, current)
            await update.message.reply_text(f"Restored DB from {os.path.basename(latest)}. Saved previous DB as {os.path.basename(safe_copy)}.\nPlease restart the bot service.")
        except Exception as e:
            await update.message.reply_text("Restore failed: " + str(e))

    async def restart_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: ask the container host to restart by exiting the process."""
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return
        try:
            await update.message.reply_text("Перезапускаю процесс бота для применения изменений...")
            # flush and exit immediately; container orchestrator should restart the service
            import os, sys, threading
            def _exit():
                try:
                    os._exit(0)
                except Exception:
                    sys.exit(0)
            # run exit shortly after replying to ensure message is sent
            t = threading.Timer(0.5, _exit)
            t.start()
        except Exception as e:
            await update.message.reply_text(f"Не удалось перезапустить: {e}")

    async def drop_trigger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: drop the caught_fish trigger if present."""
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return
        try:
            conn = await _run_sync(db._connect)
            cur = conn.cursor()
            cur.execute('DROP TRIGGER IF EXISTS caught_fish_fix_chatid_after_insert')
            try:
                conn.commit()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            await update.message.reply_text('Trigger dropped (if existed). Please restart the bot service.')
        except Exception as e:
            await update.message.reply_text('Failed to drop trigger: ' + str(e))

    async def upload_backup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: save an uploaded backup file to the container backups directory.
        Send the .db file as a document with caption 'upload_backup' (case-insensitive) to save it.
        """
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            return
        try:
            msg = update.message
            doc = getattr(msg, 'document', None)
            if not doc:
                await update.message.reply_text("Пришлите файл базы данных как документ с подписью 'upload_backup'.")
                return
            import os, time
            src_env = os.environ.get('FISHBOT_DB_PATH', DB_PATH)
            backups_dir = os.path.join(os.path.dirname(src_env), 'backups')
            os.makedirs(backups_dir, exist_ok=True)
            filename = doc.file_name or f"uploaded_{int(time.time())}.db"
            dest_path = os.path.join(backups_dir, filename)
            file = await context.bot.get_file(doc.file_id)
            await file.download_to_drive(dest_path)
            await update.message.reply_text(f"Сохранено: {filename}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при сохранении файла: {e}")

    async def list_backups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: list files in backups directory."""
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return
        try:
            import os
            src = os.environ.get('FISHBOT_DB_PATH', DB_PATH)
            backups_dir = os.path.join(os.path.dirname(src), 'backups')
            if not os.path.isdir(backups_dir):
                await update.message.reply_text(f"Папка бэкапов не найдена: {backups_dir}")
                return
            files = sorted(os.listdir(backups_dir), key=lambda f: os.path.getmtime(os.path.join(backups_dir, f)), reverse=True)
            if not files:
                await update.message.reply_text("В папке бэкапов нет файлов.")
                return
            text = "Последние бэкапы:\n" + "\n".join(files[:20])
            await update.message.reply_text(text)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")

    async def chatstar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: return list of chats and stars_total. Use in private chat."""
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return

        # Ensure command is used in private
        chat = update.effective_chat
        if chat is None or getattr(chat, 'type', None) != 'private':
            await update.message.reply_text("Эту команду можно запускать только в личных сообщениях боту.")
            return

        try:
            chats = await _run_sync(db.get_all_chat_stars)
        except Exception as e:
            logger.exception("chatstar: DB error: %s", e)
            await update.message.reply_text("Ошибка доступа к БД.")
            return

        if not chats:
            await update.message.reply_text("Нет данных по чатам.")
            return

        total = sum(int(c.get('stars_total', 0)) for c in chats)
        lines = [f"Всего звёзд: {total}", ""]
        for c in chats:
            title = c.get('chat_title') or ''
            if not title:
                # try fetching title from Telegram and update DB
                try:
                    chat_id = c.get('chat_id')
                    if chat_id:
                        chat_obj = await bot_instance.application.bot.get_chat(chat_id)
                        fetched_title = getattr(chat_obj, 'title', None) or getattr(chat_obj, 'username', None) or (getattr(chat_obj, 'first_name', None) or '')
                        if fetched_title:
                            title = fetched_title
                            try:
                                await _run_sync(db.update_chat_title, chat_id, title)
                            except Exception:
                                pass
                except Exception:
                    title = f"chat:{c.get('chat_id')}"
            if not title:
                title = f"chat:{c.get('chat_id')}"
            stars = c.get('stars_total', 0)
            lines.append(f"{title} — {stars}")

        # Send as multiple messages if too long
        text = "\n".join(lines)
        if len(text) > 3900:
            # chunk by lines
            chunk = []
            cur_len = 0
            for ln in lines:
                if cur_len + len(ln) + 1 > 3900:
                    await bot_instance._safe_send_message(chat_id=owner_id, text="\n".join(chunk))
                    chunk = [ln]
                    cur_len = len(ln) + 1
                else:
                    chunk.append(ln)
                    cur_len += len(ln) + 1
            if chunk:
                await bot_instance._safe_send_message(chat_id=owner_id, text="\n".join(chunk))
        else:
            await bot_instance._safe_send_message(chat_id=owner_id, text=text)

    async def grant_net_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return
        parts = (update.message.text or '').split()
        if len(parts) < 3:
            await update.message.reply_text("Использование: /grant_net <user_id> <net_name|netN> [count]")
            return
        try:
            target_user = int(parts[1])
        except Exception:
            await update.message.reply_text("Неверный user_id. Пример: /grant_net 123456 net0 1")
            return
        raw_net = parts[2]
        count = 1
        if len(parts) >= 4:
            try:
                count = int(parts[3])
            except Exception:
                count = 1

        # Map netN -> index in nets list (0-based)
        net_name = raw_net
        m = re.match(r'^net(\d+)$', raw_net, re.I)
        if m:
            idx = int(m.group(1))
            nets = await _run_sync(db.get_nets)
            if 0 <= idx < len(nets):
                net_name = nets[idx]['name']
            else:
                await update.message.reply_text(f"Нет сети с индексом {idx}")
                return

        ok = await _run_sync(db.grant_net, target_user, net_name, getattr(update.effective_chat, 'id', -1), count)
        if ok:
            await update.message.reply_text(f"Сеть '{net_name}' выдана пользователю {target_user} (x{count}).")
            # Попытаться отправить личное сообщение получателю
            sender = update.effective_user
            sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Пользователь')
            dm_text = f"{sender_name} подарил вам: {net_name}." 
            try:
                # use bot_instance safe wrapper
                res = await bot_instance._safe_send_message(chat_id=target_user, text=dm_text)
                if res is None:
                    await update.message.reply_text(f"Не удалось доставить уведомление пользователю {target_user} (возможно, он не писал боту).")
            except Exception as e:
                logger.exception("Failed to send DM after grant_net: %s", e)
                await update.message.reply_text("Не удалось отправить личное сообщение получателю.")
        else:
            await update.message.reply_text(f"Не удалось выдать сеть '{net_name}'. Проверьте имя сети.")

    async def add_caught_manual_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Owner-only: ручное добавление рыбы в caught_fish через личку с ботом.

        Формат:
        /add <user_id> "<fish_name>" "<location>" <weight> <length>
        """
        owner_id = 793216884
        user_id = getattr(update.effective_user, 'id', None)
        if user_id != owner_id:
            await update.message.reply_text("Нет доступа.")
            return

        if not update.message:
            return

        if getattr(update.effective_chat, 'type', '') != 'private':
            await update.message.reply_text("Команда /add доступна только в личке с ботом.")
            return

        raw_text = (update.message.text or '').strip()
        try:
            parts = shlex.split(raw_text)
        except ValueError:
            await update.message.reply_text(
                "Неверный формат кавычек.\n"
                "Использование: /add <user_id> \"<рыба>\" \"<локация>\" <вес> <длина>"
            )
            return

        if len(parts) != 6:
            await update.message.reply_text(
                "Использование: /add <user_id> \"<рыба>\" \"<локация>\" <вес> <длина>\n"
                "Пример: /add 123456 \"Белуга\" \"Городской пруд\" 12.5 140.2"
            )
            return

        _, target_user_raw, fish_name, location_name, weight_raw, length_raw = parts

        try:
            target_user = int(target_user_raw)
        except (TypeError, ValueError):
            await update.message.reply_text("Неверный user_id. Пример: /add 123456 \"Белуга\" \"Городской пруд\" 12.5 140.2")
            return

        try:
            weight = float(str(weight_raw).replace(',', '.'))
            length = float(str(length_raw).replace(',', '.'))
        except (TypeError, ValueError):
            await update.message.reply_text("Вес и длина должны быть числами. Пример: 12.5 140.2")
            return

        if weight <= 0:
            await update.message.reply_text("Вес должен быть больше 0.")
            return
        if length < 0:
            await update.message.reply_text("Длина не может быть отрицательной.")
            return

        caught_at = update.message.date or datetime.utcnow()
        saved = await _run_sync(db.add_caught_fish_owner_manual, user_id=target_user,
            fish_name=fish_name,
            location=location_name,
            weight=weight,
            length=length,
            caught_at=caught_at,
        )

        if not saved:
            await update.message.reply_text("Не удалось добавить запись в caught_fish.")
            return

        await update.message.reply_text(
            "✅ Запись добавлена в caught_fish:\n"
            f"id={saved['id']}\n"
            f"user_id={saved['user_id']}\n"
            f"chat_id={saved['chat_id']}\n"
            f"fish={saved['fish_name']}\n"
            f"location={saved['location']}\n"
            f"weight={saved['weight']}\n"
            f"length={saved['length']}\n"
            f"sold={saved['sold']}\n"
            f"caught_at={saved['caught_at']}"
        )

    async def grant_rod_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        owner_id = 793216884
        if getattr(update.effective_user, 'id', None) != owner_id:
            await update.message.reply_text("Нет доступа.")
            return

        parts = (update.message.text or '').split()
        if len(parts) < 3:
            await update.message.reply_text("Использование: /grant_rod <user_id> <rod_name|rodN>")
            return
        try:
            target_user = int(parts[1])
        except Exception:
            await update.message.reply_text("Неверный user_id. Пример: /grant_rod 123456 rod0")
            return
        raw_rod = parts[2]

        rod_name = raw_rod
        m = re.match(r'^rod(\d+)$', raw_rod, re.I)
        if m:
            idx = int(m.group(1))
            rods = await _run_sync(db.get_rods)
            if 0 <= idx < len(rods):
                rod_name = rods[idx]['name']
            else:
                await update.message.reply_text(f"Нет удочки с индексом {idx}")
                return

        ok = await _run_sync(db.grant_rod, target_user, rod_name, getattr(update.effective_chat, 'id', -1))
        if ok:
            await update.message.reply_text(f"Удочка '{rod_name}' выдана пользователю {target_user}.")
            sender = update.effective_user
            sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Пользователь')
            dm_text = f"{sender_name} подарил вам: {rod_name}."
            try:
                res = await bot_instance._safe_send_message(chat_id=target_user, text=dm_text)
                if res is None:
                    await update.message.reply_text(f"Не удалось доставить уведомление пользователю {target_user} (возможно, он не писал боту).")
            except Exception as e:
                logger.exception("Failed to send DM after grant_rod: %s", e)
                await update.message.reply_text("Не удалось отправить личное сообщение получателю.")
        else:
            await update.message.reply_text(f"Не удалось выдать удочку '{rod_name}'. Проверьте имя удочки.")

    # Добавление обработчиков
    application.add_handler(TypeHandler(Update, bot_instance.check_global_stop), group=-1)

    application.add_handler(CommandHandler("dbinfo", dbinfo_command))
    application.add_handler(CommandHandler("stop", bot_instance.stop))
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CommandHandler("dbstats", dbstats_command))
    application.add_handler(CommandHandler("backupdb", backupdb_command))
    application.add_handler(CommandHandler("getbackup", getbackup_command))
    application.add_handler(CommandHandler("list_backups", list_backups_command))
    application.add_handler(CommandHandler("restore_backup", restore_backup_command))
    application.add_handler(CommandHandler("restart", restart_bot_command))
    application.add_handler(CommandHandler("drop_trigger", drop_trigger_command))
    # Owner can upload a backup file as a document with caption 'upload_backup'
    application.add_handler(MessageHandler(filters.Document.ALL & filters.CaptionRegex('(?i)upload_backup') & filters.User(793216884), upload_backup_handler))
    application.add_handler(CommandHandler("add", add_caught_manual_command))
    application.add_handler(CommandHandler("grant_net", grant_net_command))
    application.add_handler(CommandHandler("grant_rod", grant_rod_command))
    application.add_handler(CommandHandler("chatstar", chatstar_command))
    application.add_handler(CommandHandler("ref", bot_instance.ref_command))
    application.add_handler(CommandHandler("new_ref", bot_instance.new_ref_command))
    application.add_handler(CommandHandler("check", bot_instance.check_command))
    application.add_handler(CommandHandler("raf", bot_instance.raf_command))
    application.add_handler(CommandHandler("cancel", bot_instance.cancel_command))
    application.add_handler(CommandHandler("new_tour", bot_instance.new_tour_command))
    application.add_handler(CommandHandler("tour", bot_instance.tour_command))
    application.add_handler(CommandHandler("ozero", bot_instance.ozero_command))
    application.add_handler(CommandHandler("reka", bot_instance.reka_command))
    application.add_handler(CommandHandler("more", bot_instance.more_command))
    application.add_handler(CommandHandler("prud", bot_instance.prud_command))
    application.add_handler(CommandHandler("mes", bot_instance.mes_command))
    application.add_handler(CommandHandler("tour", bot_instance.tour_command))
    application.add_handler(CommandHandler("ozero", bot_instance.ozero_command))
    application.add_handler(CommandHandler("reka", bot_instance.reka_command))
    application.add_handler(CommandHandler("more", bot_instance.more_command))
    application.add_handler(CommandHandler("prud", bot_instance.prud_command))
    application.add_handler(CommandHandler("mes", bot_instance.mes_command))
    # debug handlers removed
    application.add_handler(CommandHandler("app", bot_instance.app_command))
    application.add_handler(CommandHandler("fish", bot_instance.fish_command))
    application.add_handler(CommandHandler("menu", bot_instance.menu_command))
    application.add_handler(CommandHandler("buy_boat", bot_instance.buy_paid_boat_command))
    application.add_handler(CommandHandler("cure_seasick", bot_instance.cure_seasick_command))
    application.add_handler(CommandHandler("skip_boat_cd", bot_instance.skip_boat_cooldown_command))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_skip_boat_cooldown, pattern=r"^skip_boat_cd_\\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_cure_seasick, pattern=r"^cure_seasick_\\d+$"))
    application.add_handler(CommandHandler("invite", bot_instance.invite_command))
    application.add_handler(CommandHandler("duel", bot_instance.duel_command))
    application.add_handler(CommandHandler("notduel", bot_instance.notduel_command))
    application.add_handler(CommandHandler("shop", bot_instance.handle_shop))
    application.add_handler(CommandHandler("net", bot_instance.net_command))
    application.add_handler(CommandHandler("dynamite", bot_instance.dynamite_command))
    application.add_handler(CommandHandler("weather", bot_instance.weather_command))
    application.add_handler(CommandHandler("testweather", bot_instance.test_weather_command))
    application.add_handler(CommandHandler("stats", bot_instance.stats_command))
    application.add_handler(CommandHandler("rules", bot_instance.rules_command))
    application.add_handler(CommandHandler("info", bot_instance.info_command))
    application.add_handler(CommandHandler("treasureinfo", bot_instance.treasureinfo_command))
    application.add_handler(CommandHandler("stars", bot_instance.stars_command))
    application.add_handler(CommandHandler("topl", bot_instance.topl_command))
    application.add_handler(CommandHandler("leaderboard", bot_instance.leaderboard_command))
    application.add_handler(CommandHandler("repair", bot_instance.repair_command))
    application.add_handler(CommandHandler("bait", bot_instance.bait_command))
    application.add_handler(CommandHandler("market", bot_instance.market_command))
    application.add_handler(CommandHandler("disaster", bot_instance.disaster_command))
    application.add_handler(CommandHandler("guild", bot_instance.guild_command))
    application.add_handler(CommandHandler("artel", bot_instance.guild_command))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    application.add_handler(CommandHandler("test", bot_instance.test_command))
    
    # Обработчики платежей
    application.add_handler(PreCheckoutQueryHandler(bot_instance.precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, bot_instance.successful_payment_callback))
    
    # Обработчик новых участников группы отключён — не присылаем автоматические приветствия
    # (application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_instance.welcome_new_member)))
    
    # Ввод для сценариев /ref и /new_ref.
    # В python-telegram-bot в рамках одной группы выполняется только первый подошедший handler,
    # поэтому разносим обработчики по группам: сценарные -> общий текстовый.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_withdraw_stars_input), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_new_ref_input), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_check_input), group=2)

    # Обработчик сообщений о рыбалке и покупке наживки
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_fish_message), group=3)
    
    # Обработчик стикеров
    application.add_handler(MessageHandler(filters.Sticker.ALL, bot_instance.handle_sticker))
    
    # Обработчик возврата платежей (использует refunded_payment)
    application.add_handler(MessageHandler(REFUNDED_PAYMENT_FILTER, bot_instance.refunded_payment_callback))
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(bot_instance.handle_noop, pattern=r"^noop$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_raf_start_callback, pattern=r"^raf_start_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_start_fishing, pattern="^start_fishing_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_fight_action, pattern=r"^fight_[a-f0-9]{10}_(jerk|hold|slack)_\d+$"))
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
    application.add_handler(CallbackQueryHandler(bot_instance.handle_bait_convert_callback, pattern=r"^bait_convert_(all|\d+)_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_bait, pattern="^select_bait_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_bait, pattern="^sbi_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_select_net, pattern="^select_net_"))  # Выбор сети в меню
    application.add_handler(CallbackQueryHandler(bot_instance.handle_pay_invoice_callback, pattern="^pay_invoice:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_use_harpoon_paid, pattern="^use_harpoon_paid_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_use_harpoon, pattern="^use_harpoon_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_use_net, pattern="^use_net_"))  # Использование сетей
    application.add_handler(CallbackQueryHandler(bot_instance.handle_net_skip_cd, pattern="^net_skip_cd_"))  # Сброс КД сетей
    application.add_handler(CallbackQueryHandler(bot_instance.handle_boat_invite_accept, pattern="^boat_invite_accept_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_boat_invite_decline, pattern="^boat_invite_decline_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_duel_accept, pattern=r"^duel_accept_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_duel_decline, pattern=r"^duel_decline_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_boat_start, pattern="^boat_start_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_boat_return, pattern="^boat_return_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_paid_boat, pattern="^buy_paid_boat_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_back_to_menu, pattern="^back_to_menu_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_fish, pattern=r"^sell_fish_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_fish, pattern=r"^sell_page_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_species, pattern="^sell_sp_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_all, pattern=r"^sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_confirm_sell_all, pattern=r"^confirm_sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_cancel_sell_all, pattern=r"^cancel_sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_quantity_cancel, pattern=r"^sell_quantity_cancel_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory, pattern=r"^inventory_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trash_sell_all, pattern=r"^inv_trash_sell_all_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trash, pattern=r"^inv_trash_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trash, pattern=r"^inv_trash_page_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_clan_donate_trash_callback, pattern=r"^clan_donate_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trophies, pattern=r"^inv_trophies_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trophies, pattern=r"^inv_trophies_page_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trophy_add, pattern=r"^inv_trophy_add_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trophy_add, pattern=r"^inv_trophy_add_page_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trophy_make, pattern=r"^inv_trophy_make_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_trophy_set, pattern=r"^inv_trophy_set_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_sell_treasure, pattern=r"^sell_treasure_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_treasures, pattern=r"^inv_treasures_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_inventory_location, pattern="^inv_location_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop, pattern=r"^shop_\d+$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_beer, pattern="^shop_beer_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_dynamite_upgrade, pattern="^shop_dynamite_upgrade_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_clothing, pattern="^shop_clothing_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_rods, pattern="^shop_rods_"))
    # Важно: более специфичные паттерны должны идти первыми
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_baits_location, pattern="^shop_baits_loc_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_baits, pattern="^shop_baits_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_nets, pattern="^shop_nets_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_boats, pattern="^shop_boats_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_feeders, pattern="^shop_feeders_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_shop_exchange, pattern="^shop_exchange_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_beer, pattern="^buy_beer_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_clothing, pattern="^buy_clothing_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_dynamite_upgrade, pattern="^buy_dynamite_upgrade_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_exchange_buy_diamond, pattern="^exchange_buy_diamond_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_exchange_sell_diamond, pattern="^exchange_sell_diamond_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_exchange_shell_to_pearl, pattern="^exchange_shell_to_pearl_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_exchange_pearl_to_diamond, pattern="^exchange_pearl_to_diamond_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_rod, pattern="^buy_rod_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_net, pattern="^buy_net_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_callback, pattern="^buy_boat_diamonds"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_feeder_coins, pattern="^buy_feeder_coins_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_feeder_stars, pattern="^buy_feeder_stars_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_buy_echosounder, pattern="^buy_echosounder_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_show_echosounder, pattern="^show_echosounder_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_repair_callback, pattern="^repair_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_stats_callback, pattern="^stats_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_leaderboard_callback, pattern="^leaderboard$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_tour_type_callback, pattern="^tour_type_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_tour_location_callback, pattern="^tour_location_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_tour_criteria_callback, pattern="^tour_criteria_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_payment_expired_callback, pattern="^payment_expired$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_invoice_cancelled_callback, pattern="^invoice_cancelled$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_pay_telegram_star_callback, pattern="^pay_telegram_star_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_invoice_sent_callback, pattern="^invoice_sent$"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_cancel_ref_callback, pattern="^cancel_ref_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_withdraw_stars_callback, pattern="^withdraw_stars_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_approve_withdraw_callback, pattern="^approve_withdraw_"))
    
    # Обработчик ошибок
    application.add_error_handler(bot_instance.error_handler)
    trace_application_handlers(application)
    
    print("🎣 Бот для рыбалки запущен!")
    
    # Запуск бота с обработкой ошибок
    # drop_pending_updates=True — при перезапуске все сообщения, отправленные
    # пока бот был выключен, будут проигнорированы (старые рыбалки не сработают).
    try:
        if os.getenv("BOT_USE_WEBHOOK", "1") == "0":
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "pre_checkout_query",
                    "chosen_inline_result",
                ],
            )
            print("✅ Polling запущен успешно")
            return

        webhook_url = get_public_base_url()
        webhook_path = os.getenv("WEBHOOK_PATH", BOT_TOKEN)
        listen = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
        port = int(os.getenv("WEBHOOK_PORT", os.getenv("PORT", "8080")))
        if not webhook_url:
            raise RuntimeError("WEBHOOK_URL is required for webhook mode")
        logger.info("Starting PTB webhook server: listen=%s port=%s path=/%s public=%s/%s", listen, port, webhook_path, webhook_url, webhook_path)
        application.run_webhook(
            listen=listen,
            port=port,
            url_path=webhook_path,
            webhook_url=f"{webhook_url}/{webhook_path}",
            drop_pending_updates=True,
            allowed_updates=[
                "message",
                "callback_query",
                "pre_checkout_query",
                "chosen_inline_result",
            ],
        )
        print("✅ Webhook запущен успешно")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        raise

if __name__ == '__main__':
    main()
