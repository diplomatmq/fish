export type RarityKey = 'common' | 'rare' | 'legendary' | 'aquarium' | 'mythical' | 'anomaly';

const RARITY_NORMALIZE_MAP: Record<string, RarityKey> = {
  'обычная': 'common',
  'редкая': 'rare',
  'легендарная': 'legendary',
  'аквариумная': 'aquarium',
  'мифическая': 'mythical',
  'аномалия': 'anomaly'
};

const RARITY_LABELS: Record<RarityKey, string> = {
  common: 'Обычная',
  rare: 'Редкая',
  legendary: 'Легендарная',
  aquarium: 'Аквариумная',
  mythical: 'Мифическая',
  anomaly: 'Аномалия'
};

const RARITY_STARS: Record<RarityKey, string> = {
  common: '★★',
  rare: '★★★',
  legendary: '★★★★★',
  aquarium: '★★★★',
  mythical: '★★★★★',
  anomaly: '★★★★★★'
};

const RARITY_COLORS: Record<RarityKey, string> = {
  common: '#90e0ef',
  rare: '#00b4d8',
  legendary: '#f4a82e',
  aquarium: '#4cc9f0',
  mythical: '#ef476f',
  anomaly: '#7b2cbf'
};

export function normalizeRarity(value: string | null | undefined): RarityKey {
  const key = String(value || '').trim().toLowerCase();
  return RARITY_NORMALIZE_MAP[key] || 'common';
}

export function rarityLabel(value: string | null | undefined): string {
  return RARITY_LABELS[normalizeRarity(value)];
}

export function rarityStars(value: string | null | undefined): string {
  return RARITY_STARS[normalizeRarity(value)];
}

export function rarityColor(value: string | null | undefined): string {
  return RARITY_COLORS[normalizeRarity(value)];
}

export function rarityDisplay(value: string | null | undefined): string {
  const key = normalizeRarity(value);
  return `${RARITY_STARS[key]} ${RARITY_LABELS[key]}`;
}
