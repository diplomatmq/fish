import { UserProfile } from '../types';
import { fetchApi } from './api';

export interface GuildMember {
  userId: string;
  name: string;
  level: number;
  role: 'leader' | 'member' | 'officer' | 'owner';
  totalWeight: number;
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
  memberCount: number;
  capacity: number;
  minLevel: number;
  totalWeight: number;
  totalFish: number;
  canUpgrade: boolean;
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
export let currentUserIsAdmin = false;

export interface ClanTournament {
  id: string;
  title: string;
  startsAt: string;
  endsAt: string;
  createdBy: string;
  createdAt: string;
  isActive: boolean;
}

export interface ClanTournamentEntry {
  clanId: string;
  name: string;
  totalWeight: number;
  totalFish: number;
}

const CLAN_CAPACITY_BY_LEVEL: Record<number, number> = { 1: 5, 2: 10, 3: 20 };

const mapMember = (member: any): GuildMember => ({
  userId: String(member.user_id ?? member.userId ?? ''),
  name: String(member.username || member.name || 'user'),
  level: Number(member.level || 0),
  role: (member.role || 'member') as GuildMember['role'],
  totalWeight: Number(member.total_weight || member.totalWeight || 0),
});

export async function loadClans(): Promise<void> {
  try {
    const data = await fetchApi<any>('/api/guilds');
    if (data && data.ok) {
      currentUserIsAdmin = Boolean(data.is_admin);
      const myClanData = data.my_clan;
      if (myClanData && myClanData.id) {
        const members = Array.isArray(myClanData.members) ? myClanData.members.map(mapMember) : [];
        const requests = Array.isArray(myClanData.requests) ? myClanData.requests : [];
        const upgradeProgress = Array.isArray(myClanData.upgrade_progress)
          ? myClanData.upgrade_progress.map((p: any) => ({
            item: String(p.item || ''),
            required: Number(p.required || 0),
            current: Number(p.current || 0)
          }))
          : [];

        const guild: Guild = {
          id: String(myClanData.id),
          name: myClanData.name,
          avatar: myClanData.avatar_emoji || '🔱',
          borderColor: myClanData.color_hex || '#00b4d8',
          type: myClanData.access_type || 'open',
          level: myClanData.level || 1,
          members,
          requests: requests.map((request: any) => ({
            requestId: String(request.request_id ?? request.id ?? ''),
            userId: String(request.user_id ?? request.requester_user_id ?? ''),
            name: String(request.username || 'user'),
            level: Number(request.level || 0),
            userAvatar: String(request.user_avatar || '👤')
          })),
          upgradeProgress,
          memberCount: members.length || Number(myClanData.members_count ?? myClanData.member_count ?? 0),
          capacity: Number(myClanData.max_members) || CLAN_CAPACITY_BY_LEVEL[myClanData.level || 1] || 5,
          minLevel: myClanData.min_level || 0,
          totalWeight: Number(myClanData.total_catch_weight || 0),
          totalFish: Number(myClanData.total_catch_count || 0),
          canUpgrade: Boolean(myClanData.can_upgrade)
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
          memberCount: Number(g.members_count ?? g.member_count ?? 0),
          capacity: Number(g.max_members) || CLAN_CAPACITY_BY_LEVEL[g.level || 1] || 5,
          minLevel: g.min_level || 0,
          totalWeight: Number(g.total_catch_weight || 0),
          totalFish: Number(g.total_catch_count || 0),
          canUpgrade: false
        }));
        currentUserGuildId = null;
        currentUserIsOwner = false;
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
       } else if (response.reason === 'tournament_active') {
         const endsAt = response.tournament?.ends_at || response.tournament?.endsAt;
         const suffix = endsAt ? ` до ${String(endsAt).replace('T', ' ').slice(0, 16)}` : '';
         alert(`Во время турнира нельзя создавать артели${suffix}.`);
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
      currentUserIsAdmin = Boolean(data.is_admin || currentUserIsAdmin);
      await loadClans();
      return;
    }
    if (data && !data.ok) {
      alert(`Не удалось покинуть артель: ${data.reason || data.error || 'неизвестная ошибка'}`);
    }
  } catch (e) {
    console.error('Failed to leave guild:', e);
  }
}

export async function loadClanMembers(guildId: string): Promise<GuildMember[]> {
  try {
    const data = await fetchApi<any>(`/api/guilds/members?guild_id=${encodeURIComponent(guildId)}`);
    if (data && data.ok) {
      const members = Array.isArray(data.members) ? data.members.map(mapMember) : [];
      const guild = guilds.find(g => g.id === guildId);
      if (guild) {
        guild.members = members;
        guild.memberCount = Number(data.members_count || members.length || guild.memberCount);
      }
      return members;
    }
  } catch (e) {
    console.error('Failed to load clan members:', e);
  }
  return [];
}

export async function donateToGuild(itemName: string, quantity = 1): Promise<boolean> {
  try {
    const data = await fetchApi<any>('/api/guilds/donate', {
      method: 'POST',
      body: JSON.stringify({ item_name: itemName, quantity })
    });
    if (data && data.ok) {
      await loadClans();
      return true;
    }
    if (data && !data.ok) {
      if (data.reason === 'not_enough_trash') {
        alert(`Недостаточно предметов. Есть ${data.available || 0} из ${data.required || quantity}.`);
      } else {
        alert(`Ошибка пожертвования: ${data.reason || data.error || 'неизвестная ошибка'}`);
      }
    }
  } catch (e) {
    console.error('Failed to donate to guild:', e);
  }
  return false;
}

export async function upgradeGuild(): Promise<boolean> {
  try {
    const data = await fetchApi<any>('/api/guilds/upgrade', { method: 'POST' });
    if (data && data.ok) {
      await loadClans();
      return true;
    }
    if (data && !data.ok) {
      alert(`Не удалось улучшить артель: ${data.reason || data.error || 'неизвестная ошибка'}`);
    }
  } catch (e) {
    console.error('Failed to upgrade guild:', e);
  }
  return false;
}

export async function removeGuildMember(memberId: string): Promise<boolean> {
  try {
    const data = await fetchApi<any>('/api/guilds/members/remove', {
      method: 'POST',
      body: JSON.stringify({ member_id: memberId })
    });
    if (data && data.ok) {
      await loadClans();
      return true;
    }
    if (data && !data.ok) {
      alert(`Не удалось удалить участника: ${data.reason || data.error || 'неизвестная ошибка'}`);
    }
  } catch (e) {
    console.error('Failed to remove guild member:', e);
  }
  return false;
}

export async function loadClanTournaments(): Promise<{ items: ClanTournament[]; activeId: string | null; active?: ClanTournament | null }> {
  try {
    const data = await fetchApi<any>('/api/guilds/tournaments');
    if (data && data.ok) {
      const activeId = data.active_id ? String(data.active_id) : null;
      const items = (data.items || []).map((t: any) => ({
        id: String(t.id),
        title: String(t.title || ''),
        startsAt: String(t.starts_at || ''),
        endsAt: String(t.ends_at || ''),
        createdBy: String(t.created_by || ''),
        createdAt: String(t.created_at || ''),
        isActive: activeId === String(t.id)
      }));
      const active = data.active ? {
        id: String(data.active.id),
        title: String(data.active.title || ''),
        startsAt: String(data.active.starts_at || ''),
        endsAt: String(data.active.ends_at || ''),
        createdBy: String(data.active.created_by || ''),
        createdAt: String(data.active.created_at || ''),
        isActive: true
      } : null;
      return { items, activeId, active };
    }
  } catch (e) {
    console.error('Failed to load clan tournaments:', e);
  }
  return { items: [], activeId: null, active: null };
}

export async function createClanTournament(title: string, startsAt: string, endsAt: string): Promise<ClanTournament | null> {
  try {
    const data = await fetchApi<any>('/api/guilds/tournaments/create', {
      method: 'POST',
      body: JSON.stringify({ title, starts_at: startsAt, ends_at: endsAt })
    });
    if (data && data.ok && data.tournament) {
      const t = data.tournament;
      return {
        id: String(t.id),
        title: String(t.title || ''),
        startsAt: String(t.starts_at || ''),
        endsAt: String(t.ends_at || ''),
        createdBy: String(t.created_by || ''),
        createdAt: String(t.created_at || ''),
        isActive: false
      };
    }
  } catch (e) {
    console.error('Failed to create clan tournament:', e);
  }
  return null;
}

export async function loadClanTournamentLeaderboard(tournamentId: string): Promise<ClanTournamentEntry[]> {
  try {
    const data = await fetchApi<any>(`/api/guilds/tournaments/leaderboard?tournament_id=${encodeURIComponent(tournamentId)}`);
    if (data && data.ok) {
      return (data.items || []).map((row: any) => ({
        clanId: String(row.clan_id ?? row.clanId ?? ''),
        name: String(row.name || ''),
        totalWeight: Number(row.total_weight || 0),
        totalFish: Number(row.total_fish || 0)
      }));
    }
  } catch (e) {
    console.error('Failed to load clan tournament leaderboard:', e);
  }
  return [];
}

export function setMockUserGuild(id: string | null, isOwner = false) {
  currentUserGuildId = id;
  currentUserIsOwner = isOwner;
}
