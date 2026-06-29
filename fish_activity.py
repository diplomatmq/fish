"""Дневная/ночная активность рыб (UTC сервера)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

ACTIVITY_DAY = "day"
ACTIVITY_NIGHT = "night"
ACTIVITY_ALL = "all"

ACTIVITY_LABELS_RU = {
    ACTIVITY_DAY: "дневная",
    ACTIVITY_NIGHT: "ночная",
    ACTIVITY_ALL: "круглосуточная",
}

NIGHT_START_HOUR = 21
NIGHT_END_HOUR = 4

EXPLICIT_NIGHT = frozenset({
    "Налим", "Сом", "Голубой сом", "Канальный сомик", "Американский сомик",
    "Судак", "Угорь", "Змееголов", "Минога", "Речная минога", "Корюшка",
    "Рыба-удильщик", "Глубоководный удильщик (самка)", "Вампировый кальмар",
    "Стеклянный кальмар", "Гигантский изопод", "Осьминог Дамбо", "Баррелей",
    "Черный живоглот", "Рыба-капля", "Морской чёрт", "Морской черт",
    "Медуза-корнерот", "Конгер", "Мурена", "Мурена-зебра", "Камбала",
    "Камбала речная", "Палтус синекорый", "Скат-хвостокол", "Морская лисица",
    "Кальмар-стрела", "Осьминог рифовый", "Луна-рыба", "Белая акула",
    "Лисья акула", "Акула Мако", "Скорпена", "Каменный окунь", "Морской дракон",
    "Личинка угря (лептоцефал)", "Подкаменщик", "Бычок-кругляк", "Бычок-песочник",
    "Бычок", "Вьюн", "Палия", "Муксун", "Чир", "Пелядь", "Валаамка", "Омуль",
    "Байкальский омуль", "Голец арктический", "Арктический голец", "Ёрш",
})

EXPLICIT_ALL = frozenset({
    "Щука", "Таймень", "Белуга", "Калуга", "Осетр", "Осетр русский",
    "Сибирский осетр", "Стерлядь", "Нельма", "Севрюга", "Шип", "Жерех",
    "Черный амур", "Карп Кои", "Веслонос", "Бестер", "Аллигаторовый панцирник",
    "Тигровая акула", "Акула-молот", "Пилорыл", "Рыба-луна", "Групер гигантский",
    "Морской петух", "Рыба-трамп", "Сакабамбаспис", "Плащеносная акула",
})

_NIGHT_KEYWORDS = (
    "налим", "сом", "судак", "угор", "миног", "корюш", "удильщ", "кальмар",
    "осьмин", "мурен", "конгер", "камбал", "палтус", "скат", "акул", "изопод",
    "бarrел", "живоглот", "рыба-капля", "морской черт", "скорпен", "морской дракон",
    "морская лис", "бычок", "подкамен", "личинка угря", "глубоковод", "вампир",
    "медуза-корнер", "каменный окун", "луна-рыб", "муксун", "палия", "пеляд",
    "омуль", "валаам", "голец", "змееголов", "вьюн", "ерш", "чир",
)

_DAY_KEYWORDS = (
    "карась", "плотв", "лещ", "густер", "pескар", "елец", "краснопер", "уклей",
    "верхов", "горчак", "чebak", "карп", "толстолоб", "форел", "голавл", "язь",
    "линь", "подлещ", "синец", "чехон", "подуст", "ряпуш", "gольян", "шиповк",
    "колюшк", "сиг", "хариус", "guppi", "guppi", "скаляр", "данio", "данио",
    "моллин", "пetush", "петуш", "neon", "неон", "тернец", "барбус", "gurami",
    "gurami", "гурами", "pecil", "пецил", "kloon", "kloун", "kloун", "анchous",
)

def _normalize_name(name: str) -> str:
    return (name or "").strip().lower().replace("ё", "е")


def is_night_time_utc(dt: Optional[datetime] = None) -> bool:
    hour = (dt or datetime.now(timezone.utc)).hour
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def allowed_periods_for_hour(hour: int) -> frozenset:
    if hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR:
        return frozenset({ACTIVITY_NIGHT, ACTIVITY_ALL})
    return frozenset({ACTIVITY_DAY, ACTIVITY_ALL})


def filter_fish_by_time(
    fish_list: Iterable[Dict[str, Any]],
    hour: Optional[int] = None,
) -> List[Dict[str, Any]]:
    h = hour if hour is not None else datetime.now(timezone.utc).hour
    allowed = allowed_periods_for_hour(h)
    result: List[Dict[str, Any]] = []
    for fish in fish_list:
        period = fish.get("activity_period") or ACTIVITY_ALL
        if period in allowed:
            result.append(fish)
    return result


def get_activity_for_fish_name(name: str, rarity: str = "") -> str:
    clean = (name or "").strip()
    if not clean:
        return ACTIVITY_ALL

    rarity_clean = (rarity or "").strip()
    if rarity_clean in ("Мифическая", "Аномалия"):
        return ACTIVITY_ALL
    if clean in EXPLICIT_ALL:
        return ACTIVITY_ALL
    if clean in EXPLICIT_NIGHT:
        return ACTIVITY_NIGHT
    if rarity_clean == "Аквариумная":
        return ACTIVITY_DAY
    if rarity_clean == "Легендарная":
        return ACTIVITY_ALL

    lowered = _normalize_name(clean)
    for keyword in _NIGHT_KEYWORDS:
        if keyword in lowered:
            return ACTIVITY_NIGHT
    for keyword in _DAY_KEYWORDS:
        if keyword in lowered:
            return ACTIVITY_DAY

    bucket = sum(ord(ch) for ch in clean) % 3
    if bucket == 0:
        return ACTIVITY_DAY
    if bucket == 1:
        return ACTIVITY_NIGHT
    return ACTIVITY_ALL


def time_hint_message_ru(hour: Optional[int] = None) -> str:
    h = hour if hour is not None else datetime.now(timezone.utc).hour
    if h >= NIGHT_START_HOUR or h < NIGHT_END_HOUR:
        return (
            "🌙 Сейчас ночь (UTC 21:00–04:00): активны только ночные "
            "и круглосуточные рыбы. Дневные виды проснутся после рассвета."
        )
    return (
        "☀️ Сейчас день (UTC 04:00–21:00): активны только дневные "
        "и круглосуточные рыбы. Ночные виды клюют с 21:00 до 04:00 UTC."
    )
