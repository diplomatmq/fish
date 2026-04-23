import { fetchApi } from './api';

export interface Friend {
  id: string;
  name: string;
  level: number;
  avatar: string;
  online: boolean;
  xp?: number;
}

export interface FriendRequest {
  id: string;
  name: string;
  level: number;
  avatar: string;
}

export let friends: Friend[] = [];
export let friendRequests: FriendRequest[] = [];

export async function loadFriends(): Promise<void> {
  try {
    const data = await fetchApi<any>('/api/friends');
    if (data && data.ok) {
      friends = data.friends.map((f: any) => ({
        id: String(f.user_id),
        name: f.username,
        level: f.level,
        avatar: '👤',
        online: true, // В БД пока нет статуса онлайн, можно добавить позже
        xp: f.xp
      }));
    }
  } catch (e) {
    console.error('Failed to load friends:', e);
  }
}

export function sendFriendRequest(target: string): boolean {
  // Mock logic: adding a request would normally go to backend
  console.log(`Friend request sent to: ${target}`);
  return true;
}

export function acceptRequest(id: string): void {
  const req = friendRequests.find(r => r.id === id);
  if (req) {
    friends.push({
      ...req,
      online: Math.random() > 0.5
    });
    friendRequests = friendRequests.filter(r => r.id !== id);
  }
}

export function declineRequest(id: string): void {
  friendRequests = friendRequests.filter(r => r.id !== id);
}
