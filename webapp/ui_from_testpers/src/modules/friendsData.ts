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
      const friendItems = Array.isArray(data.items) ? data.items : [];
      const requestItems = Array.isArray(data.incoming_requests) ? data.incoming_requests : [];

      friends = friendItems.map((f: any) => ({
        id: String(f.user_id),
        name: f.username,
        level: Number(f.level || 0),
        avatar: '👤',
        online: Boolean(f.is_online),
        xp: Number(f.xp || 0)
      }));

      friendRequests = requestItems.map((r: any) => ({
        id: String(r.request_id || r.id),
        name: String(r.username || 'user'),
        level: Number(r.level || 0),
        avatar: '👤'
      }));
    }
  } catch (e) {
    console.error('Failed to load friends:', e);
  }
}

export async function sendFriendRequest(target: string): Promise<boolean> {
  try {
    const data = await fetchApi<any>('/api/friends/add', {
      method: 'POST',
      body: JSON.stringify({ username: target })
    });
    return Boolean(data?.ok);
  } catch (e) {
    console.error('Failed to send friend request:', e);
    return false;
  }
}

export async function acceptRequest(id: string): Promise<boolean> {
  return respondToRequest(id, 'accept');
}

export async function declineRequest(id: string): Promise<boolean> {
  return respondToRequest(id, 'decline');
}

async function respondToRequest(requestId: string, action: 'accept' | 'decline'): Promise<boolean> {
  try {
    const data = await fetchApi<any>('/api/friends/request/respond', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, action })
    });

    if (data?.ok) {
      await loadFriends();
      return true;
    }
  } catch (e) {
    console.error('Failed to respond friend request:', e);
  }
  return false;
}
