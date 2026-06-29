"""Молитва Морскому Повелителю — исходы и тексты."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Загрузите этот файл в корень проекта (рядом с bot.py)
SEA_GOD_IMAGE_FILE = "poseidon_sea_god.webp"

PRAY_COOLDOWN_HOURS = 24
DIVINE_EFFECT_HOURS = 6

WRATH_EFFECT = "sea_god_wrath"
BLESSING_EFFECT = "sea_god_blessing"

WRATH_CATCH_PENALTY = -40.0
BLESSING_CATCH_BONUS = 35.0


@dataclass(frozen=True)
class PrayOutcome:
    outcome_id: str
    title: str
    weight: int
    emoji: str


PRAY_OUTCOMES: Tuple[PrayOutcome, ...] = (
    PrayOutcome("wrath", "Гнев Посейдона", 12, "🌊"),
    PrayOutcome("blessing", "Благословение Амфитриты", 12, "✨"),
    PrayOutcome("gift_fish", "Дар Левиафана", 10, "🐉"),
    PrayOutcome("coins_pearl", "Жемчужный дождь", 14, "🦪"),
    PrayOutcome("coins_atlantis", "Сокровище Атлантиды", 8, "👑"),
    PrayOutcome("rod_break", "Сломанный трезубец", 10, "⚡"),
    PrayOutcome("gift_net", "Сеть нереид", 12, "🕸️"),
    PrayOutcome("gift_rod", "Удилище Нереиды", 10, "🔱"),
    PrayOutcome("paid_boat", "Корабль Аргонавтов", 2, "⛵"),
    PrayOutcome("silence", "Молчание бездны", 10, "🌫️"),
)

PRAY_INTRO_CAPTION = (
    "🌊 *Молитва вознесена…*\n\n"
    "Волны стихают. Из глубин поднимается _Повелитель Морей_ — "
    "он присматривает за каждым, кто смело забрасывает удочку в его царство."
)

OUTCOME_MESSAGES: Dict[str, str] = {
    "wrath": (
        "🌊 *Гнев Посейдона*\n\n"
        "Трезубец вспыхнул багровым светом. Бог недоволен вашей настойчивостью — "
        "шанс клёва снижен на *40%* на *6 часов*.\n\n"
        "_«Не зови меня понапрасну, смертный…»_"
    ),
    "blessing": (
        "✨ *Благословение Амфитриты*\n\n"
        "Морская королева коснулась вод вашей души. "
        "Шанс клёва повышен на *+35%* на *6 часов*.\n\n"
        "_«Иди, и пусть волны будут милостивы к тебе.»_"
    ),
    "gift_fish": (
        "🐉 *Дар Левиафана*\n\n"
        "Из пучины всплывает трофей — редчайшее создание, "
        "подаренное самим океаном!"
    ),
    "coins_pearl": (
        "🦪 *Жемчужный дождь*\n\n"
        "С небес (или с поверхности?) сыплется жемчуг — "
        "океан одаривает вас монетами!"
    ),
    "coins_atlantis": (
        "👑 *Сокровище Атлантиды*\n\n"
        "Перед вами всплывает сундук затонувшей империи — "
        "боги щедры сегодня!"
    ),
    "rod_break": (
        "⚡ *Сломанный трезубец*\n\n"
        "Молния раскалывает небо! Божественная сила обрушилась на вашу удочку — "
        "снаряжение повреждено до предела."
    ),
    "gift_net": (
        "🕸️ *Сеть нереид*\n\n"
        "Нереиды сплетают для вас морскую сеть — "
        "пусть она принесёт богатые уловы!"
    ),
    "gift_rod": (
        "🔱 *Удилище Нереиды*\n\n"
        "Из пены волн возникает удилище, выточенное руками морских богинь."
    ),
    "paid_boat": (
        "⛵ *Корабль Аргонавтов*\n\n"
        "Легендарное судно материализуется на волнах! "
        "Платная лодка теперь ваша — дар, о котором мечтают все рыбаки."
    ),
    "silence": (
        "🌫️ *Молчание бездны*\n\n"
        "Боги услышали молитву… и отвернулись. "
        "Только туман и шёпот прибоя. Ничего не изменилось.\n\n"
        "_«Ещё рано. Вернись, когда сердце будет чище.»_"
    ),
}

GIFT_ROD_POOL: Tuple[str, ...] = (
    "Углепластиковая удочка",
    "Карбоновая удочка",
    "Золотая удочка",
)

GIFT_NET_POOL: Tuple[str, ...] = (
    "Прочная сеть",
    "Быстрая сеть",
)

GIFT_FISH_RARITIES: Tuple[Tuple[str, int], ...] = (
    ("Легендарная", 55),
    ("Мифическая", 30),
    ("Аномалия", 15),
)


def roll_pray_outcome() -> PrayOutcome:
    total = sum(o.weight for o in PRAY_OUTCOMES)
    roll = random.randint(1, total)
    acc = 0
    for outcome in PRAY_OUTCOMES:
        acc += outcome.weight
        if roll <= acc:
            return outcome
    return PRAY_OUTCOMES[-1]


def pick_gift_rod_name() -> str:
    weights = [40, 35, 25]
    return random.choices(list(GIFT_ROD_POOL), weights=weights, k=1)[0]


def pick_gift_net_name() -> str:
    return random.choice(GIFT_NET_POOL)


def pick_coin_reward(outcome_id: str) -> int:
    if outcome_id == "coins_atlantis":
        return random.randint(2500, 9000)
    return random.randint(350, 1200)


def pick_gift_fish(
    fish_rows: List[Dict[str, Any]],
    location: str,
) -> Optional[Dict[str, Any]]:
    if not fish_rows:
        return None
    rarity = random.choices(
        [r for r, _ in GIFT_FISH_RARITIES],
        weights=[w for _, w in GIFT_FISH_RARITIES],
        k=1,
    )[0]
    candidates = [f for f in fish_rows if f.get("rarity") == rarity]
    if not candidates:
        candidates = [
            f for f in fish_rows
            if f.get("rarity") in ("Легендарная", "Мифическая", "Аномалия")
        ]
    if not candidates:
        return None
    return random.choice(candidates)


def generate_fish_stats(fish: Dict[str, Any]) -> Tuple[float, float]:
    min_w = float(fish.get("min_weight") or 0.1)
    max_w = float(fish.get("max_weight") or min_w)
    min_l = float(fish.get("min_length") or 1)
    max_l = float(fish.get("max_length") or min_l)
    if max_w <= min_w:
        weight = min_w
    else:
        weight = round(random.uniform(min_w, max_w * 0.85 + min_w * 0.15), 2)
    if max_l <= min_l:
        length = min_l
    else:
        length = round(random.uniform(min_l, max_l), 1)
    return weight, length
