// ─────────────────────────────────────────────────────────────────────────────
// api.ts — Communication with backend
// ─────────────────────────────────────────────────────────────────────────────

const getInitData = () => {
  return (window as any).Telegram?.WebApp?.initData || '';
};

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const initData = getInitData();
  const headers = {
    'Content-Type': 'application/json',
    'X-Telegram-Init-Data': initData,
    ...(options.headers || {}),
  };

  const response = await fetch(endpoint, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || `HTTP error! status: ${response.status}`);
  }
  return response.json();
}

// Alias for compatibility
export const apiRequest = fetchApi;

export interface ApiResponse<T> {
  ok: boolean;
  error?: string;
  data?: T;
  [key: string]: any;
}

// API Service class
class ApiService {
  async getProfile() {
    try {
      const response = await fetchApi<any>('/api/profile');
      return response;
    } catch (error) {
      console.error('Failed to get profile:', error);
      throw error;
    }
  }

  async updateLocation(location: string) {
    try {
      const response = await fetchApi<any>('/api/update-location', {
        method: 'POST',
        body: JSON.stringify({ location })
      });
      return response;
    } catch (error) {
      console.error('Failed to update location:', error);
      throw error;
    }
  }

  async fish(location: string, guaranteed: boolean = false, currency: 'stars' | 'ton' = 'stars') {
    try {
      const response = await fetchApi<any>('/api/fish', {
        method: 'POST',
        body: JSON.stringify({ location, guaranteed, currency })
      });
      return response;
    } catch (error) {
      console.error('Failed to fish:', error);
      throw error;
    }
  }

  async checkCooldown() {
    try {
      const response = await fetchApi<any>('/api/cooldown');
      return response;
    } catch (error) {
      console.error('Failed to check cooldown:', error);
      throw error;
    }
  }

  async getInventory() {
    try {
      const response = await fetchApi<any>('/api/inventory');
      return response;
    } catch (error) {
      console.error('Failed to get inventory:', error);
      throw error;
    }
  }

  async createStarsInvoice(amount: number) {
    try {
      const response = await fetchApi<any>('/api/create-stars-invoice', {
        method: 'POST',
        body: JSON.stringify({ amount })
      });
      return response;
    } catch (error) {
      console.error('Failed to create stars invoice:', error);
      throw error;
    }
  }

  async confirmTonTopup(amount: number) {
    try {
      const response = await fetchApi<any>('/api/confirm-ton-topup', {
        method: 'POST',
        body: JSON.stringify({ amount })
      });
      return response;
    } catch (error) {
      console.error('Failed to confirm TON topup:', error);
      throw error;
    }
  }
}

export const apiService = new ApiService();
