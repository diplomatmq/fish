import type { FishData, TabConfig, UserProfile } from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Fish catalogue
// ─────────────────────────────────────────────────────────────────────────────
export const FISH_DATA: FishData[] = [
  {
    id: 'lionfish',
    emoji: '🦁',
    name: 'Рыба-лев',
    latinName: 'Pterois volitans',
    rarity: 'rare',
    rarityLabel: 'Редкая',
    rarityStars: '★★★',
    weight: '1.2 кг',
    depth: '50–80 м',
  },
  {
    id: 'clownfish',
    emoji: '🐠',
    name: 'Рыба-клоун',
    latinName: 'Amphiprioninae',
    rarity: 'common',
    rarityLabel: 'Обычная',
    rarityStars: '★★',
    weight: '0.18 кг',
    depth: '1–15 м',
  },
  {
    id: 'anglerfish',
    emoji: '👾',
    name: 'Чёрный удильщик',
    latinName: 'Melanocetus johnsonii',
    rarity: 'legendary',
    rarityLabel: 'Легендарная',
    rarityStars: '★★★★★',
    weight: '5.4 кг',
    depth: '200–2000 м',
  },
  {
    id: 'barracuda',
    emoji: '🐟',
    name: 'Барракуда',
    latinName: 'Sphyraena barracuda',
    rarity: 'common',
    rarityLabel: 'Обычная',
    rarityStars: '★★',
    weight: '0.9 кг',
    depth: '0–30 м',
  },
  {
    id: 'seahorse',
    emoji: '🦑',
    name: 'Морской конёк',
    latinName: 'Hippocampus',
    rarity: 'rare',
    rarityLabel: 'Редкая',
    rarityStars: '★★★',
    weight: '0.08 кг',
    depth: '1–30 м',
  },
  {
    id: 'pufferfish',
    emoji: '🐡',
    name: 'Рыба-шар',
    latinName: 'Tetraodontidae',
    rarity: 'rare',
    rarityLabel: 'Редкая',
    rarityStars: '★★★',
    weight: '0.7 кг',
    depth: '5–25 м',
  },
  {
    id: 'shark',
    emoji: '🦈',
    name: 'Белая акула',
    latinName: 'Carcharodon carcharias',
    rarity: 'epic',
    rarityLabel: 'Эпическая',
    rarityStars: '★★★★',
    weight: '120 кг',
    depth: '0–250 м',
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Tab bar config
// ─────────────────────────────────────────────────────────────────────────────
export const TABS: TabConfig[] = [
  { id: 'home',       icon: '🧭', label: 'Главная'   },
  { id: 'shop',       icon: '🧺', label: 'Лавка'     },
  { id: 'friends',    icon: '👤', label: 'Друзья'    },
  { id: 'guilds',     icon: '🔱', label: 'Артели'    },
  { id: 'book',       icon: '📖', label: 'Книга'     },
];

// ─────────────────────────────────────────────────────────────────────────────
// User data (would come from Telegram / API in production)
// ─────────────────────────────────────────────────────────────────────────────
export const USER_PROFILE: UserProfile = {
  name: 'АКВАМАН_01',
  tag: '@aquaman01',
  level: 15,
  xp: 7200,
  maxXp: 10000,
  avatar: '🤿',
};

export const RARITY_COLORS: Record<FishData['rarity'], string> = {
  common:    '#90e0ef',
  rare:      '#00b4d8',
  epic:      '#9b5de5',
  legendary: '#f4a82e',
};
