# Конфигурация бота
import os
from pathlib import Path
from datetime import datetime, timedelta

# Load .env file (if present) so os.getenv() can read values from it during dev
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv not installed — it's optional in production where env vars are set
    pass

# Токен бота Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')  # set via environment variable or CI secrets

# Путь к базе данных SQLite — можно переопределить через окружение FISHBOT_DB_PATH
DB_PATH = Path(os.getenv('FISHBOT_DB_PATH', Path(__file__).parent / 'fishbot.db'))

# Названия валют
COIN_NAME = "монеты"
STAR_NAME = "звезды"

# Ссылки и тексты для команд /rules и /info
RULES_TEXT = "Правила: уважайте участников, без спама и оскорблений."
RULES_LINK = "https://t.me/monkeys_giveaways/66"
INFO_LINK = "https://t.me/monkeys_giveaways/66"

# Настройки механики
CATCH_CHANCE = 50  # Шанс поймать рыбу в процентах (для реки)
TRASH_CHANCE = 20  # Шанс поймать мусор в процентах (для реки)
NO_BITE_CHANCE = 30  # Шанс что рыба не клюнет
GUARANTEED_CATCH_COST = 1  # Стоимость гарантированного улова в звездах
COOLDOWN_MINUTES = 10  # Кулдаун между попытками рыбалки в минутах

# Стоимость починки удочки
ROD_REPAIR_COST = 20  # Стоимость в звездах

# Времена года меняются еженедельно, начиная с 01.02.2026 (Зима)
# 1 февраля 2026 -> Зима
# 8 февраля 2026 -> Весна
# 15 февраля 2026 -> Лето
# 22 февраля 2026 -> Осень
# 1 марта 2026 -> Зима (цикл повторяется)
SEASONS_CYCLE = ["Зима", "Весна", "Лето", "Осень"]  # Цикл из 4 недель
SEASON_START_DATE = datetime(2026, 2, 1)  # Дата начала (1 февраля 2026)
SEASON_CHANGE_INTERVAL = 7  # Дни (каждую неделю)

def get_current_season() -> str:
    """Получить текущий сезон на основе даты"""
    days_passed = (datetime.now() - SEASON_START_DATE).days
    week_number = days_passed // SEASON_CHANGE_INTERVAL
    season_index = week_number % len(SEASONS_CYCLE)
    return SEASONS_CYCLE[season_index]

# Динамическое получение текущего сезона
CURRENT_SEASON = get_current_season()
