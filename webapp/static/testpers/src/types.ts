// ─────────────────────────────────────────────────────────────────────────────
// Types & Interfaces
// ─────────────────────────────────────────────────────────────────────────────

export interface FishData {
  id: string;
  emoji: string;
  name: string;
  latinName: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  rarityLabel: string;
  rarityStars: string;
  weight: string;
  depth: string;
}

export type ScreenId = 'home' | 'adventures' | 'friends' | 'guilds' | 'book';

export type HapticStyle = 'light' | 'medium' | 'heavy' | 'selection' | 'impact' | 'error' | 'success';

export interface TabConfig {
  id: ScreenId;
  icon: string;
  label: string;
}

export interface UserProfile {
  name: string;
  tag: string;
  level: number;
  xp: number;
  maxXp: number;
  avatar: string;
}
