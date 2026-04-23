// ─────────────────────────────────────────────────────────────────────────────
// Book screen data — fish encyclopedia entries
// ─────────────────────────────────────────────────────────────────────────────

import { fetchApi } from './api';

export interface EncyclopediaEntry {
  id: string;
  emoji: string;
  name: string;
  latinName: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  glowColor: string;
  depth: string;
  habitat: string;
  length: string;
  description: string;
  funFact: string;
  chapter: string;
  isCaught?: boolean;
}

export let ENCYCLOPEDIA: EncyclopediaEntry[] = [];

export async function loadEncyclopedia(): Promise<void> {
  try {
    const data = await fetchApi<any>('/api/book');
    if (data && data.ok) {
      ENCYCLOPEDIA = data.items.map((f: any) => ({
        id: f.image_file || 'fishdef',
        emoji: '🐟',
        name: f.name,
        latinName: f.name,
        rarity: mapRarity(f.rarity),
        glowColor: getGlowColor(f.rarity),
        depth: '1-100 м',
        habitat: f.locations,
        length: `${f.min_length}-${f.max_length} см`,
        description: f.lore || `Рыба вида ${f.name}.`,
        funFact: 'Информации пока нет.',
        chapter: 'Общий атлас',
        isCaught: f.is_caught
      }));
    }
  } catch (e) {
    console.error('Failed to load encyclopedia:', e);
  }
}

function mapRarity(r: string): any {
  const map: any = {
    'Обычная': 'common',
    'Редкая': 'rare',
    'Легендарная': 'legendary',
    'Мифическая': 'epic'
  };
  return map[r] || 'common';
}

function getGlowColor(r: string): string {
  const map: any = {
    'Обычная': '#90e0ef',
    'Редкая': '#00b4d8',
    'Легендарная': '#f4a82e',
    'Мифическая': '#9b5de5'
  };
  return map[r] || '#90e0ef';
}
