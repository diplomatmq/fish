// ─────────────────────────────────────────────────────────────────────────────
// Telegram Mini App wrapper (typed)
// ─────────────────────────────────────────────────────────────────────────────
import type { HapticStyle } from '../types';

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

interface TelegramWebApp {
  ready(): void;
  expand(): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  HapticFeedback?: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void;
    notificationOccurred(type: 'error' | 'success' | 'warning'): void;
    selectionChanged(): void;
  };
  initDataUnsafe?: {
    user?: {
      first_name?: string;
      username?: string;
    };
  };
}

class TelegramService {
  private tg: TelegramWebApp | null;

  constructor() {
    this.tg = window.Telegram?.WebApp ?? null;

    if (this.tg) {
      this.tg.ready();
      this.tg.expand();
      this.tg.setHeaderColor('#0a1628');
      this.tg.setBackgroundColor('#0a1628');
    }
  }

  haptic(style: HapticStyle): void {
    if (!this.tg?.HapticFeedback) return;
    
    if (style === 'selection') {
      this.tg.HapticFeedback.selectionChanged();
    } else if (style === 'success' || style === 'error') {
      this.tg.HapticFeedback.notificationOccurred(style);
    } else if (style === 'impact') {
      this.tg.HapticFeedback.impactOccurred('medium');
    } else if (['light', 'medium', 'heavy'].includes(style)) {
      this.tg.HapticFeedback.impactOccurred(style as any);
    }
  }

  getUserName(): string | null {
    return this.tg?.initDataUnsafe?.user?.first_name ?? null;
  }

  getUserTag(): string | null {
    const username = this.tg?.initDataUnsafe?.user?.username;
    return username ? `@${username}` : null;
  }
}

export const tgService = new TelegramService();
