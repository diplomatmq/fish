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

export interface ApiResponse<T> {
  ok: boolean;
  error?: string;
  data?: T;
  [key: string]: any;
}
