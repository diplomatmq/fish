import { UserProfile } from '../types';
import { fetchApi } from './api';

export interface GuildMember {
  userId: string;
  name: string;
  level: number;
  role: 'owner' | 'member' | 'officer';
}

export interface GuildRequest {
  requestId: string;
  userId: string;
  name: string;
  level: number;
  userAvatar: string;
}

export interface GuildUpgradeRequirement {
  item: string;
  required: number;
  current: number;
}

export interface Guild {
  id: string;
  name: string;
  avatar: string;
  borderColor: string;
  type: 'open' | 'invite';
  level: number;
  members: GuildMember[];
  requests: GuildRequest[];
  upgradeProgress: GuildUpgradeRequirement[];
  capacity: number;
  minLevel: number;
}

export const GUILD_AVATARS = [
  'guild_beer',    // Пивной рыбак
  'guild_rich',    // Богатый рыбак
  'guild_cthulhu', // Ктулху / Кракен
  'guild_king'     // Морской царь / Королевская
];
export const GUILD_COLORS  = ['#00b4d8', '#f4a82e', '#9b5de5', '#ff6b6b', '#a5a5a5', '#4d908e'];

export let guilds: Guild[] = [];
export let currentUserGuildId: string | null = null;
export let currentUserIsOwner = false;

export async function loadClans(): Promise<void> {
  try {
    const data = await fetchApi<any>('/api/guilds');
    if (data && data.ok) {
      const myClanData = data.my_clan;
      if (myClanData && myClanData.id) {
        const requests = Array.isArray(myClanData.requests) ? myClanData.requests : [];
        const guild: Guild = {
          id: String(myClanData.id),
          name: myClanData.name,
          avatar: myClanData.avatar_emoji || '🔱',
          borderColor: myClanData.color_hex || '#00b4d8',
          type: myClanData.access_type || 'open',
          level: myClanData.level || 1,
          members: [], // В снимке нет списка участников, его можно догрузить отдельно если нужно
          requests: requests.map((request: any) => ({
            requestId: String(request.request_id ?? request.id ?? ''),
            userId: String(request.user_id ?? request.requester_user_id ?? ''),
            name: String(request.username || 'user'),
            level: Number(request.level || 0),
            userAvatar: String(request.user_avatar || '👤')
          })),
          upgradeProgress: [],
          capacity: 20,
          minLevel: myClanData.min_level || 0
        };
        guilds = [guild];
        currentUserGuildId = guild.id;
        currentUserIsOwner = myClanData.role === 'leader';
      } else {
        guilds = (data.items || []).map((g: any) => ({
          id: String(g.id),
          name: g.name,
          avatar: g.avatar_emoji || '🔱',
          borderColor: g.color_hex || '#00b4d8',
          type: g.access_type || 'open',
          level: g.level || 1,
          members: [],
          requests: [],
          upgradeProgress: [],
          capacity: 20,
          minLevel: g.min_level || 0
        }));
        currentUserGuildId = null;
      }
    }
  } catch (e) {
    console.error('Failed to load clans:', e);
  }
}

export async function createGuild(data: Partial<Guild>): Promise<Guild | null> {
  try {
    const response = await fetchApi<any>('/api/guilds/create', {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        avatar: data.avatar,
        color: data.borderColor,
        type: data.type,
        min_level: data.minLevel
      })
    });
    
    if (response && response.ok) {
      await loadClans(); // Перезагружаем список
      return guilds.find(g => g.id === String(response.clan_id)) || null;
    }
    if (response && !response.ok) {
       if (response.reason === 'not_enough_coins') {
         alert(`Недостаточно монет для создания артели! Нужно ${response.cost.toLocaleString()} 🪙`);
       } else {
         alert(`Ошибка создания: ${response.reason || 'неизвестная ошибка'}`);
       }
    }
  } catch (e) {
    console.error('Failed to create guild:', e);
  }
  return null;
}

export async function joinGuild(guildId: string): Promise<boolean> {
  const guild = guilds.find(g => g.id === guildId);
  if (!guild) return false;

  try {
    const endpoint = guild.type === 'open' ? '/api/guilds/join' : '/api/guilds/apply';
    const data = await fetchApi<any>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ guild_id: guildId })
    });
    
    if (data && data.ok) {
      if (guild.type === 'open') {
        currentUserGuildId = guild.id;
      }
      return true;
    }
    if (data && !data.ok) {
      if (data.reason === 'level_too_low') {
        alert(`Ваш уровень слишком низок! Требуется уровень ${data.required}`);
      } else if (data.reason === 'not_enough_coins') {
        alert(`Недостаточно монет! Требуется ${data.cost} 🪙`);
      } else {
        alert(`Ошибка: ${data.reason || data.error || 'неизвестная ошибка'}`);
      }
    }
  } catch (e) {
    console.error('Failed to join guild:', e);
  }
  return false;
}

export async function respondClanRequest(requestId: string, action: 'accept' | 'decline'): Promise<boolean> {
  try {
    const data = await fetchApi<any>('/api/guilds/request/respond', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, action })
    });

    if (data && data.ok) {
      await loadClans();
      return true;
    }

    if (data && !data.ok) {
      alert(`Ошибка обработки заявки: ${data.error || 'неизвестная ошибка'}`);
    }
  } catch (e) {
    console.error('Failed to respond to clan request:', e);
  }
  return false;
}

export async function leaveGuild(): Promise<void> {
  if (!currentUserGuildId) return;
  try {
    const data = await fetchApi<any>('/api/guilds/leave', { method: 'POST' });
    if (data && data.ok) {
      currentUserGuildId = null;
      currentUserIsOwner = false;
      await loadClans();
    }
  } catch (e) {
    console.error('Failed to leave guild:', e);
  }
}

export function setMockUserGuild(id: string | null, isOwner = false) {
  currentUserGuildId = id;
  currentUserIsOwner = isOwner;
}
