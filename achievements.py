"""Определения достижений и вспомогательные функции."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

AchievementTier = Dict[str, Any]
AchievementDef = Dict[str, Any]

ACHIEVEMENTS: List[AchievementDef] = [
    {
        "id": "great_collector",
        "title": "Великий коллекционер",
        "icon": "📚",
        "stat": "unique_fish",
        "stat_label": "уникальных видов",
        "tiers": [
            {"tier": 1, "threshold": 50, "description": "50 уникальных видов рыб", "reward": {"coins": 5000}},
            {"tier": 2, "threshold": 75, "description": "75 уникальных видов рыб", "reward": {"coins": 10000, "nets": 3}},
            {"tier": 3, "threshold": 100, "description": "100 уникальных видов рыб", "reward": {"coins": 20000, "rod": "Золотая удочка"}},
            {"tier": 4, "threshold": 125, "description": "125 уникальных видов рыб", "reward": {"coins": 35000, "nets": 5}},
            {"tier": 5, "threshold": 150, "description": "150 уникальных видов рыб", "reward": {"coins": 50000, "rod": "Удачливая удочка"}},
            {"tier": 6, "threshold": 175, "description": "175 уникальных видов рыб", "reward": {"coins": 75000, "nets": 10}},
            {"tier": 7, "threshold": 190, "description": "190 уникальных видов рыб", "reward": {"coins": 100000, "rod": "Гарпун"}},
        ],
    },
    {
        "id": "fisherman",
        "title": "Рыбачок",
        "icon": "🎣",
        "stat": "total_fish",
        "stat_label": "рыб поймано",
        "tiers": [
            {"tier": 1, "threshold": 500, "description": "500 рыб поймано", "reward": {"coins": 3000}},
            {"tier": 2, "threshold": 1000, "description": "1000 рыб поймано", "reward": {"coins": 7000, "nets": 2}},
            {"tier": 3, "threshold": 2000, "description": "2000 рыб поймано", "reward": {"coins": 15000, "nets": 5}},
            {"tier": 4, "threshold": 5000, "description": "5000 рыб поймано", "reward": {"coins": 40000, "rod": "Золотая удочка"}},
            {"tier": 5, "threshold": 15000, "description": "15000 рыб поймано", "reward": {"coins": 100000, "rod": "Гарпун"}},
        ],
    },
    {
        "id": "heavy_catch",
        "title": "Тяжеловес",
        "icon": "⚖️",
        "stat": "total_weight",
        "stat_label": "кг поймано",
        "tiers": [
            {"tier": 1, "threshold": 100, "description": "100 кг рыбы поймано", "reward": {"coins": 2000}},
            {"tier": 2, "threshold": 500, "description": "500 кг рыбы поймано", "reward": {"coins": 5000, "nets": 2}},
            {"tier": 3, "threshold": 1000, "description": "1000 кг рыбы поймано", "reward": {"coins": 12000, "nets": 3}},
            {"tier": 4, "threshold": 5000, "description": "5000 кг рыбы поймано", "reward": {"coins": 30000, "rod": "Золотая удочка"}},
            {"tier": 5, "threshold": 10000, "description": "10000 кг рыбы поймано", "reward": {"coins": 60000, "nets": 10}},
            {"tier": 6, "threshold": 25000, "description": "25000 кг рыбы поймано", "reward": {"coins": 150000, "rod": "Гарпун"}},
        ],
    },
    {
        "id": "merchant",
        "title": "Торговец",
        "icon": "💰",
        "stat": "sold_fish_count",
        "stat_label": "рыб продано",
        "tiers": [
            {"tier": 1, "threshold": 100, "description": "100 рыб продано", "reward": {"coins": 3000}},
            {"tier": 2, "threshold": 500, "description": "500 рыб продано", "reward": {"coins": 8000}},
            {"tier": 3, "threshold": 1000, "description": "1000 рыб продано", "reward": {"coins": 18000, "nets": 3}},
            {"tier": 4, "threshold": 5000, "description": "5000 рыб продано", "reward": {"coins": 50000, "rod": "Золотая удочка"}},
            {"tier": 5, "threshold": 10000, "description": "10000 рыб продано", "reward": {"coins": 100000, "nets": 10}},
        ],
    },
    {
        "id": "treasure_hunter",
        "title": "Золотые руки",
        "icon": "🪙",
        "stat": "total_coins_earned",
        "stat_label": "монет заработано",
        "tiers": [
            {"tier": 1, "threshold": 10000, "description": "10000 монет заработано", "reward": {"coins": 5000}},
            {"tier": 2, "threshold": 50000, "description": "50000 монет заработано", "reward": {"coins": 15000, "nets": 3}},
            {"tier": 3, "threshold": 100000, "description": "100000 монет заработано", "reward": {"coins": 30000, "nets": 5}},
            {"tier": 4, "threshold": 500000, "description": "500000 монет заработано", "reward": {"coins": 80000, "rod": "Золотая удочка"}},
            {"tier": 5, "threshold": 1000000, "description": "1000000 монет заработано", "reward": {"coins": 200000, "rod": "Удачливая удочка"}},
        ],
    },
    {
        "id": "trash_collector",
        "title": "Мусорщик",
        "icon": "🗑️",
        "stat": "total_trash_caught",
        "stat_label": "мусора поймано",
        "tiers": [
            {"tier": 1, "threshold": 250, "description": "250 предметов мусора поймано", "reward": {"coins": 2000}},
            {"tier": 2, "threshold": 1000, "description": "1000 предметов мусора поймано", "reward": {"coins": 6000, "nets": 2}},
            {"tier": 3, "threshold": 2500, "description": "2500 предметов мусора поймано", "reward": {"coins": 15000, "nets": 5}},
            {"tier": 4, "threshold": 5000, "description": "5000 предметов мусора поймано", "reward": {"coins": 35000, "rod": "Золотая удочка"}},
            {"tier": 5, "threshold": 10000, "description": "10000 предметов мусора поймано", "reward": {"coins": 80000, "nets": 15}},
        ],
    },
    {
        "id": "record_breaker",
        "title": "Рекордсмен",
        "icon": "🏅",
        "stat": "biggest_weight",
        "stat_label": "кг — личный рекорд",
        "tiers": [
            {"tier": 1, "threshold": 5, "description": "Поймать рыбу от 5 кг", "reward": {"coins": 1000}},
            {"tier": 2, "threshold": 15, "description": "Поймать рыбу от 15 кг", "reward": {"coins": 3000, "nets": 1}},
            {"tier": 3, "threshold": 30, "description": "Поймать рыбу от 30 кг", "reward": {"coins": 7000, "nets": 2}},
            {"tier": 4, "threshold": 100, "description": "Поймать рыбу от 100 кг", "reward": {"coins": 20000, "rod": "Золотая удочка"}},
            {"tier": 5, "threshold": 400, "description": "Поймать рыбу от 400 кг", "reward": {"coins": 50000, "rod": "Удачливая удочка"}},
            {"tier": 6, "threshold": 700, "description": "Поймать рыбу от 700 кг", "reward": {"coins": 100000, "rod": "Гарпун"}},
        ],
    },
    {
        "id": "angler_level",
        "title": "Мастер удилища",
        "icon": "⭐",
        "stat": "level",
        "stat_label": "уровень",
        "tiers": [
            {"tier": 1, "threshold": 5, "description": "Достигнуть 5 уровня", "reward": {"coins": 2000, "nets": 1}},
            {"tier": 2, "threshold": 10, "description": "Достигнуть 10 уровня", "reward": {"coins": 5000, "nets": 3}},
            {"tier": 3, "threshold": 20, "description": "Достигнуть 20 уровня", "reward": {"coins": 15000, "rod": "Золотая удочка"}},
            {"tier": 4, "threshold": 30, "description": "Достигнуть 30 уровня", "reward": {"coins": 35000, "nets": 8}},
            {"tier": 5, "threshold": 50, "description": "Достигнуть 50 уровня", "reward": {"coins": 80000, "rod": "Удачливая удочка"}},
        ],
    },
]

ACHIEVEMENT_BY_ID: Dict[str, AchievementDef] = {a["id"]: a for a in ACHIEVEMENTS}


def tier_title(achievement_id: str, tier: int) -> str:
    ach = ACHIEVEMENT_BY_ID[achievement_id]
    return f"{ach['title']} {tier}"


def tier_description(achievement_id: str, tier: int) -> str:
    ach = ACHIEVEMENT_BY_ID[achievement_id]
    for t in ach["tiers"]:
        if int(t["tier"]) == int(tier):
            return str(t["description"])
    return ""


def highest_reachable_tier(achievement_id: str, stat_value: float) -> int:
    ach = ACHIEVEMENT_BY_ID[achievement_id]
    reached = 0
    for t in ach["tiers"]:
        if stat_value >= float(t["threshold"]):
            reached = int(t["tier"])
    return reached


def format_unlock_message(username: Optional[str], achievement_id: str, tier: int) -> str:
    label = f"@{username.lstrip('@')}" if username else "Рыбак"
    title = tier_title(achievement_id, tier)
    desc = tier_description(achievement_id, tier)
    return f"🏆 {label} получил достижение «{title}» — {desc}!"


def get_tier_reward(achievement_id: str, tier: int) -> Dict[str, Any]:
    """Получить награду за тир достижения."""
    ach = ACHIEVEMENT_BY_ID.get(achievement_id)
    if not ach:
        return {}
    
    for t in ach["tiers"]:
        if int(t["tier"]) == int(tier):
            return t.get("reward", {})
    return {}


def format_reward_message(reward: Dict[str, Any]) -> str:
    """Форматировать сообщение о награде."""
    parts = []
    
    if "coins" in reward:
        parts.append(f"💰 {reward['coins']:,} монет")
    
    if "nets" in reward:
        parts.append(f"🕸️ {reward['nets']} сетей")
    
    if "rod" in reward:
        parts.append(f"🎣 {reward['rod']}")
    
    if not parts:
        return ""
    
    return "Награда: " + ", ".join(parts)

