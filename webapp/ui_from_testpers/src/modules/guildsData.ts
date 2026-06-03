import { UserProfile } from '../types';
import { fetchApi } from './api';

export interface GuildMember {
  userId: string;
  name: string;
  level: number;
  role: 'leader' | 'member' | 'officer' | 'owner';
  totalWeight: number;
  joinedAt?: string;
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
export let myGuild: Guild | null = null;
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
  phase?: 'active' | 'grace';
}

export interface ClanTournamentEntry {
  clanId: string;
  name: string;
  totalWeight: number;
  totalFish: number;
}

const CLAN_CAPACITY_BY_LEVEL: Record<number, number> = { 1: 5, 2: 10, 3: 20, 4: 25, 5: 30 };

export function guildCapacityForLevel(level: number, maxMembers?: number): number {
  const fromApi = Number(maxMembers);
  if (fromApi > 0) return fromApi;
  return CLAN_CAPACITY_BY_LEVEL[level] ?? CLAN_CAPACITY_BY_LEVEL[3] ?? 20;
}

export function guildMemberCount(members: GuildMember[], fallback = 0): number {
  if (members.length > 0) return members.length;
  return Math.max(0, Number(fallback) || 0);
}

const mapMember = (member: any): GuildMember => ({
  userId: String(member.user_id ?? member.userId ?? ''),
  name: String(member.username || member.name || 'user'),
  level: Number(member.level || 0),
  role: (member.role || 'member') as GuildMember['role'],
  totalWeight: Number(member.total_weight || member.totalWeight || member.tournament_weight || 0),
  joinedAt: member.joined_at ? String(member.joined_at) : undefined,
});

export function guildExcessMemberIds(members: GuildMember[], capacity: number): Set<string> {
  const total = members.length;
  const excess = Math.max(0, total - Math.max(1, capacity));
  if (excess <= 0) return new Set();
  const candidates = members
    .filter(m => m.role !== 'leader')
    .sort((a, b) => {
      const ta = a.joinedAt ? new Date(a.joinedAt).getTime() : 0;
      const tb = b.joinedAt ? new Date(b.joinedAt).getTime() : 0;
      return tb - ta;
    })
    .slice(0, excess);
  return new Set(candidates.map(m => m.userId));
}

function mapGuildItem(g: any, extra?: Partial<Guild>): Guild {
  const members = Array.isArray(g.members) ? g.members.map(mapMember) : (extra?.members || []);
  const requests = extra?.requests ?? (Array.isArray(g.requests)
    ? g.requests.map((request: any) => ({
      requestId: String(request.request_id ?? request.id ?? ''),
      userId: String(request.user_id ?? request.requester_user_id ?? ''),
      name: String(request.username || 'user'),
      level: Number(request.level || 0),
      userAvatar: String(request.user_avatar || '👤')
    }))
    : []);
  const upgradeProgress = extra?.upgradeProgress ?? (Array.isArray(g.upgrade_progress)
    ? g.upgrade_progress.map((p: any) => ({
      item: String(p.item || ''),
      required: Number(p.required || 0),
      current: Number(p.current || 0)
    }))
    : []);

  return {
    id: String(g.id),
    name: g.name,
    avatar: g.avatar_emoji || '🔱',
    borderColor: g.color_hex || '#00b4d8',
    type: g.access_type || 'open',
    level: g.level || 1,
    members,
    requests,
    upgradeProgress,
    memberCount: guildMemberCount(members, g.members_count ?? g.member_count),
    capacity: guildCapacityForLevel(g.level || 1, g.max_members),
    minLevel: g.min_level || 0,
    totalWeight: Number(g.total_catch_weight || 0),
    totalFish: Number(g.total_catch_count || 0),
    canUpgrade: Boolean(g.can_upgrade),
    ...extra
  };
}

export function getMyGuild(): Guild | null {
  if (myGuild) return myGuild;
  if (!currentUserGuildId) return null;
  return guilds.find(g => g.id === currentUserGuildId) || null;
}

export async function loadClans(): Promise<void> {
  try {
    const data = await fetchApi<any>('/api/guilds');
    if (data && data.ok) {
      currentUserIsAdmin = Boolean(data.is_admin);
      guilds = (data.items || []).map((g: any) => mapGuildItem(g));

      const myClanData = data.my_clan;
      if (myClanData && myClanData.id) {
        const members = Array.isArray(myClanData.members) ? myClanData.members.map(mapMember) : [];
        const requests = Array.isArray(myClanData.requests)
          ? myClanData.requests.map((request: any) => ({
            requestId: String(request.request_id ?? request.id ?? ''),
            userId: String(request.user_id ?? request.requester_user_id ?? ''),
            name: String(request.username || 'user'),
            level: Number(request.level || 0),
            userAvatar: String(request.user_avatar || '👤')
          }))
          : [];
        const upgradeProgress = Array.isArray(myClanData.upgrade_progress)
          ? myClanData.upgrade_progress.map((p: any) => ({
            item: String(p.item || ''),
            required: Number(p.required || 0),
            current: Number(p.current || 0)
          }))
          : [];

        myGuild = mapGuildItem(myClanData, { members, requests, upgradeProgress, canUpgrade: Boolean(myClanData.can_upgrade) });
        currentUserGuildId = myGuild.id;
        currentUserIsOwner = myClanData.role === 'leader';

        const idx = guilds.findIndex(g => g.id === myGuild!.id);
        if (idx >= 0) guilds[idx] = myGuild;
        else guilds.unshift(myGuild);
      } else {
        myGuild = null;
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
      myGuild = null;
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
  const cached = guilds.find(g => g.id === guildId);
  try {
    const data = await fetchApi<any>(`/api/guilds/members?guild_id=${encodeURIComponent(guildId)}`);
    if (data && data.ok) {
      const members = Array.isArray(data.members) ? data.members.map(mapMember) : [];
      const guild = guilds.find(g => g.id === guildId);
      if (guild) {
        guild.members = members;
        guild.memberCount = guildMemberCount(members, data.members_count);
      }
      if (myGuild && myGuild.id === guildId) {
        myGuild.members = members;
        myGuild.memberCount = guildMemberCount(members, data.members_count);
      }
      return members;
    }
    if (data && !data.ok) {
      console.error('loadClanMembers:', data.error || data.reason);
    }
  } catch (e) {
    console.error('Failed to load clan members:', e);
  }
  return cached?.members?.length ? [...cached.members] : [];
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
      } else if (data.reason === 'not_in_clan') {
        alert('Вы не состоите в артели.');
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
      if (data.reason === 'not_enough_resources' || data.reason === 'not_enough_donations') {
        const missing = data.missing || {};
        const lines = Object.entries(missing).map(([item, qty]) => `${item}: не хватает ${qty}`);
        alert(lines.length ? `Нужно ещё ресурсов:\n${lines.join('\n')}` : 'Не хватает ресурсов для улучшения.');
      } else if (data.reason === 'max_level') {
        alert('Артель уже максимального уровня.');
      } else if (data.reason === 'leader_only' || data.reason === 'not_leader') {
        alert('Улучшать артель может только лидер.');
      } else {
        alert(`Не удалось улучшить артель: ${data.reason || data.error || 'неизвестная ошибка'}`);
      }
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

function mapTournament(t: any, activeId: string | null, phase?: string): ClanTournament {
  return {
    id: String(t.id),
    title: String(t.title || ''),
    startsAt: String(t.starts_at || ''),
    endsAt: String(t.ends_at || ''),
    createdBy: String(t.created_by || ''),
    createdAt: String(t.created_at || ''),
    isActive: activeId === String(t.id),
    phase: phase === 'active' || phase === 'grace' ? phase : undefined
  };
}

export async function loadClanTournaments(): Promise<{
  items: ClanTournament[];
  activeId: string | null;
  active?: ClanTournament | null;
  visibleId: string | null;
  visible?: ClanTournament | null;
  phase: 'active' | 'grace' | null;
}> {
  try {
    const data = await fetchApi<any>('/api/guilds/tournaments');
    if (data && data.ok) {
      const activeId = data.active_id ? String(data.active_id) : null;
      const visibleId = data.visible_id ? String(data.visible_id) : null;
      const phase = data.phase === 'active' || data.phase === 'grace' ? data.phase : null;
      const items = (data.items || []).map((t: any) => mapTournament(t, activeId));
      const active = data.active ? mapTournament(data.active, activeId, 'active') : null;
      const visible = data.visible ? mapTournament(data.visible, visibleId, phase || undefined) : null;
      return { items, activeId, active, visibleId, visible, phase };
    }
  } catch (e) {
    console.error('Failed to load clan tournaments:', e);
  }
  return { items: [], activeId: null, active: null, visibleId: null, visible: null, phase: null };
}

export async function loadClanTournamentMembers(guildId: string, tournamentId: string): Promise<GuildMember[]> {
  try {
    const data = await fetchApi<any>(
      `/api/guilds/tournaments/members?guild_id=${encodeURIComponent(guildId)}&tournament_id=${encodeURIComponent(tournamentId)}`
    );
    if (data && data.ok) {
      return Array.isArray(data.members) ? data.members.map(mapMember) : [];
    }
  } catch (e) {
    console.error('Failed to load tournament members:', e);
  }
  return [];
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
