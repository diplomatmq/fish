import type { FishData } from '../types';
import { fetchApi } from './api';
import { normalizeRarity, rarityLabel, rarityStars } from './rarity';

interface TrophyApiItem {
  id: string;
  name: string;
  fish_name?: string;
  weight: number;
  length: number;
  rarity?: string;
  image_url?: string | null;
  is_active?: boolean;
}

export let TROPHY_FISH: FishData[] = [];
export let ACTIVE_TROPHY_ID = '';

function formatWeight(value: number): string {
  const normalized = Number.isFinite(value) ? Math.max(0, value) : 0;
  return `${normalized.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} кг`;
}

function formatLength(value: number): string {
  const normalized = Number.isFinite(value) ? Math.max(0, value) : 0;
  return `${normalized.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} см`;
}

function mapTrophyToFish(item: TrophyApiItem): FishData {
  const raritySource = item.rarity || 'Обычная';
  return {
    id: item.id,
    emoji: '🐟',
    name: item.fish_name || item.name || 'Неизвестная рыба',
    latinName: '',
    rarity: normalizeRarity(raritySource),
    rarityLabel: rarityLabel(raritySource),
    rarityStars: rarityStars(raritySource),
    weight: formatWeight(Number(item.weight || 0)),
    depth: formatLength(Number(item.length || 0)),
    imageUrl: item.image_url || undefined,
    trophyId: item.id
  };
}

export async function loadTrophies(): Promise<FishData[]> {
  try {
    const data = await fetchApi<{ items?: TrophyApiItem[] }>('/api/trophies');
    const items = Array.isArray(data?.items) ? data.items : [];
    ACTIVE_TROPHY_ID = (items.find((item) => Boolean(item.is_active))?.id || '');

    TROPHY_FISH = items
      .filter((item) => item.id !== 'none')
      .map(mapTrophyToFish);

    return TROPHY_FISH;
  } catch (error) {
    console.error('Failed to load trophies:', error);
    TROPHY_FISH = [];
    ACTIVE_TROPHY_ID = '';
    return TROPHY_FISH;
  }
}

export async function selectTrophy(trophyId: string): Promise<boolean> {
  if (!trophyId) {
    return false;
  }

  try {
    const data = await fetchApi<{ ok?: boolean }>('/api/trophy/select', {
      method: 'POST',
      body: JSON.stringify({ trophy_id: trophyId })
    });
    return Boolean(data?.ok);
  } catch (error) {
    console.error('Failed to select trophy:', error);
    return false;
  }
}
