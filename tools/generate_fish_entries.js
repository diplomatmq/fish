const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const stickersPath = path.join(root, 'fish_stickers.py');
const databasePath = path.join(root, 'database.py');

const stickersContent = fs.readFileSync(stickersPath, 'utf8');
const databaseContent = fs.readFileSync(databasePath, 'utf8');

const NEW_LOCATION_PREFIXES = [
  'Коралловый риф',
  'Глубоководный желоб',
  'Мангровые заросли',
];

const RARITY_TITLE_MAP = {
  обычная: 'Обычная',
  редкая: 'Редкая',
  легендарная: 'Легендарная',
  мифическая: 'Мифическая',
};

const BAIT_NAME_MAP = {
  хлеб: 'Хлеб',
  манка: 'Манка',
  черви: 'Черви',
  опарыш: 'Опарыш',
  тесто: 'Тесто',
  кукуруза: 'Кукуруза',
  мотыль: 'Мотыль',
  горох: 'Горох',
  каша: 'Каша',
  сало: 'Сало',
  'кусочки рыбы': 'Кусочки рыбы',
  личинка: 'Личинка',
  мышь: 'Мышь',
  икра: 'Икра',
  мормыш: 'Мормыш',
  спрут: 'Спрут',
  'туша рыбы': 'Туша рыбы',
  'крупный кусок мяса': 'Крупный кусок мяса',
  печень: 'Печень',
  'кусок мяса': 'Кусок мяса',
  живец: 'Живец',
  блесна: 'Блесна',
  воблер: 'Воблер',
  мушка: 'Мушка',
  бойлы: 'Бойлы',
  картофель: 'Картофель',
  'пучок червей': 'Пучок червей',
  моллюск: 'Моллюск',
  камыш: 'Камыш',
  зелень: 'Зелень',
  паста: 'Паста',
  лягушонок: 'Лягушонок',
  'крупный живец': 'Крупный живец',
  сельдь: 'Сельдь',
  выползок: 'Выползок',
  'личинка короеда': 'Личинка короеда',
  кузнечик: 'Кузнечик',
  'майский жук': 'Майский жук',
  'маленькая блесна': 'Маленькая блесна',
  'узкая блесна': 'Узкая блесна',
  'творожное тесто': 'Творожное тесто',
  огурец: 'Огурец',
  'технопланктон': 'Технопланктон',
  креветка: 'Креветка',
  'морской червь': 'Морской червь',
  пилькер: 'Пилькер',
  кальмар: 'Кальмар',
  сардина: 'Сардина',
  'мякиш хлеба': 'Мякиш хлеба',
  медуза: 'Медуза',
  салат: 'Салат',
  ракушка: 'Ракушка',
  краб: 'Краб',
  рыба: 'Кусочки рыбы',
  'мелкая рыба': 'Кусочки рыбы',
  планктон: 'Мотыль',
  зоопланктон: 'Мотыль',
  рачки: 'Мотыль',
  'мелкие рачки': 'Мотыль',
  насекомые: 'Муха',
  муха: 'Муха',
  детрит: 'Мотыль',
  водоросли: 'Зелень',
  губки: 'Мотыль',
  мшанки: 'Мотыль',
  'коралловые полипы': 'Мотыль',
  полипы: 'Мотыль',
  'коралловый песок': 'Мотыль',
  'мелкие беспозвоночные': 'Мотыль',
  'крупный планктон': 'Кусочки рыбы',
  'беспозвоночные': 'Мотыль',
};

function parseFishInfo(content) {
  const fishInfoStart = content.indexOf('FISH_INFO = {');
  if (fishInfoStart === -1) throw new Error('FISH_INFO not found');
  const section = content.slice(fishInfoStart);

  const entries = {};
  const blockRegex = /"([^"]+)":\s*\{([\s\S]*?)\n    \},/g;
  let match;
  while ((match = blockRegex.exec(section)) !== null) {
    const name = match[1];
    const body = match[2];
    const getField = (field) => {
      const m = body.match(new RegExp(`"${field}":\\s*"([^"]*)"`));
      return m ? m[1] : '';
    };
    entries[name] = {
      habitat: getField('habitat'),
      nutrition: getField('nutrition'),
      seasons: getField('seasons'),
      rarity: getField('rarity'),
      weight_range: getField('weight_range'),
      size_range: getField('size_range'),
    };
  }
  return entries;
}

function getExistingFishNames(content) {
  const names = new Set();
  const regex = /\("([^"]+)",\s*"(?:Обычная|Редкая|Легендарная|Мифическая|Аквариумная|Аномалия)"/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    names.add(match[1]);
  }
  return names;
}

function parseMetricRange(rangeValue, fallback = [0.01, 0.1]) {
  if (!rangeValue || /неприменимо/i.test(rangeValue)) return fallback;
  const m = rangeValue.match(/([\d.]+)\s*-\s*([\d.]+)/);
  if (!m) return fallback;
  return [parseFloat(m[1]), parseFloat(m[2])];
}

function normalizeSeasons(seasonsValue) {
  if (!seasonsValue) return 'Все';
  if (seasonsValue.includes('Круглый год')) return 'Все';
  const parts = seasonsValue.split(',').map((s) => s.trim()).filter(Boolean);
  return parts.length ? parts.join(',') : 'Все';
}

function normalizeBaits(nutritionValue) {
  if (!nutritionValue || /неизвестно/i.test(nutritionValue)) return 'Все';
  const rawParts = nutritionValue.split(',').map((p) => p.trim()).filter(Boolean);
  const normalized = [];
  const seen = new Set();
  for (const part of rawParts) {
    const lower = part.toLowerCase();
    let bait = BAIT_NAME_MAP[lower];
    if (!bait) {
      bait = part.charAt(0).toUpperCase() + part.slice(1);
    }
    if (!seen.has(bait)) {
      seen.add(bait);
      normalized.push(bait);
    }
  }
  return normalized.length ? normalized.join(',') : 'Все';
}

function estimateFishBasePrice(rarity, maxWeight) {
  const rarityBase = {
    Обычная: 12,
    Редкая: 55,
    Легендарная: 280,
    Мифическая: 700,
  };
  const base = rarityBase[rarity] || 12;
  let multiplier;
  if (maxWeight <= 0.05) multiplier = 0.85;
  else if (maxWeight <= 0.5) multiplier = 1.0;
  else if (maxWeight <= 5) multiplier = 1.2 + maxWeight * 0.12;
  else if (maxWeight <= 30) multiplier = 1.4 + maxWeight * 0.06;
  else if (maxWeight <= 100) multiplier = 1.6 + maxWeight * 0.025;
  else multiplier = 2.0 + maxWeight * 0.004;
  return Math.max(3, Math.round(base * multiplier));
}

function estimateMaxRodWeight(maxWeight) {
  if (maxWeight <= 0.02) return 2;
  if (maxWeight <= 0.1) return 4;
  if (maxWeight <= 0.5) return 6;
  if (maxWeight <= 2) return 10;
  if (maxWeight <= 8) return 18;
  if (maxWeight <= 25) return 30;
  if (maxWeight <= 80) return 50;
  if (maxWeight <= 200) return 65;
  return 80;
}

function buildFishEntry(name, info) {
  const habitat = (info.habitat || '').trim();
  const location = NEW_LOCATION_PREFIXES.find((prefix) => habitat.startsWith(prefix));
  if (!location) return null;
  const rarity = RARITY_TITLE_MAP[(info.rarity || 'обычная').trim().toLowerCase()] || 'Обычная';
  const [minWeight, maxWeight] = parseMetricRange(info.weight_range);
  const [minLength, maxLength] = parseMetricRange(info.size_range, [5, 15]);
  const seasons = normalizeSeasons(info.seasons);
  const baits = normalizeBaits(info.nutrition);
  const price = estimateFishBasePrice(rarity, maxWeight);
  const rodWeight = estimateMaxRodWeight(maxWeight);
  return [name, rarity, minWeight, maxWeight, minLength, maxLength, price, location, seasons, baits, rodWeight, null];
}

function formatEntry(entry) {
  const [name, rarity, minW, maxW, minL, maxL, price, location, seasons, baits, rodWeight] = entry;
  const fmtNum = (n) => (Number.isInteger(n) ? String(n) : String(n));
  return `                ("${name}", "${rarity}", ${fmtNum(minW)}, ${fmtNum(maxW)}, ${fmtNum(minL)}, ${fmtNum(maxL)}, ${price}, "${location}", "${seasons}", "${baits}", ${rodWeight}, None),`;
}

const fishInfo = parseFishInfo(stickersContent);
const existing = getExistingFishNames(databaseContent);

const coral = [];
const deep = [];
const mangrove = [];

for (const [name, info] of Object.entries(fishInfo)) {
  if (existing.has(name)) continue;
  const entry = buildFishEntry(name, info);
  if (!entry) continue;
  const loc = entry[7];
  if (loc === 'Коралловый риф') coral.push(entry);
  else if (loc === 'Глубоководный желоб') deep.push(entry);
  else if (loc === 'Мангровые заросли') mangrove.push(entry);
}

console.log('Coral new:', coral.length);
console.log('Deep new:', deep.length);
console.log('Mangrove new:', mangrove.length);
console.log('Total new:', coral.length + deep.length + mangrove.length);

const output = [];
output.push('                # ===== КОРАЛЛОВЫЙ РИФ (новые виды) =====');
coral.forEach((e) => output.push(formatEntry(e)));
output.push('');
output.push('                # ===== ГЛУБОКОВОДНЫЙ ЖЕЛОБ (новые виды) =====');
deep.forEach((e) => output.push(formatEntry(e)));
output.push('');
output.push('                # ===== МАНГРОВЫЕ ЗАРОСЛИ (новые виды) =====');
mangrove.forEach((e) => output.push(formatEntry(e)));

const outPath = path.join(__dirname, 'generated_fish_entries.txt');
fs.writeFileSync(outPath, output.join('\n'), 'utf8');
console.log('Written to', outPath);
