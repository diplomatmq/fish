// ─────────────────────────────────────────────────────────────────────────────
// Book screen data — fish encyclopedia entries
// ─────────────────────────────────────────────────────────────────────────────

import { fetchApi } from './api';
import { normalizeRarity, rarityColor } from './rarity';

export interface EncyclopediaEntry {
  id: string;
  emoji: string;
  name: string;
  latinName: string;
  rarity: 'common' | 'rare' | 'legendary' | 'aquarium' | 'mythical' | 'anomaly';
  glowColor: string;
  depth: string;
  habitat: string;
  length: string;
  description: string;
  funFact: string;
  chapter: string;
  isCaught?: boolean;
  imageUrl?: string;
}

export let ENCYCLOPEDIA: EncyclopediaEntry[] = [];
export let ENCYCLOPEDIA_TOTAL_ALL = 0;

export async function loadEncyclopedia(): Promise<void> {
  try {
    const data = await fetchApi<any>('/api/book?limit=500');
    if (data && data.ok) {
      ENCYCLOPEDIA_TOTAL_ALL = Number(data.total_all || 0);
      ENCYCLOPEDIA = data.items.map((f: any) => ({
        id: f.image_file || 'fishdef',
        emoji: '🐟',
        name: f.name,
        latinName: f.name,
        rarity: mapRarity(f.rarity),
        glowColor: getGlowColor(f.rarity),
        depth: `${f.min_weight}-${f.max_weight} кг`,
        habitat: f.locations,
        length: `${f.min_length}-${f.max_length} см`,
        description: f.lore || `Рыба вида ${f.name}.`,
        funFact: f.baits ? `Лучше ловится на: ${f.baits}.` : 'Информации пока нет.',
        chapter: 'Общий атлас',
        isCaught: f.is_caught,
        imageUrl: f.image_url || undefined
      }));
    }
  } catch (e) {
    console.error('Failed to load encyclopedia:', e);
  }
}

function mapRarity(r: string): EncyclopediaEntry['rarity'] {
  return normalizeRarity(r);
}

function getGlowColor(r: string): string {
  return rarityColor(r);
}
