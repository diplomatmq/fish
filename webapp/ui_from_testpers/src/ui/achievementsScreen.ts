// ─────────────────────────────────────────────────────────────────────────────
// AchievementsScreen — player achievements with tiers
// ─────────────────────────────────────────────────────────────────────────────
import { apiRequest } from '../modules/api';
import { tgService } from '../modules/telegram';

interface AchievementItem {
  id: string;
  title: string;
  icon: string;
  current_tier: number;
  display_tier: number;
  display_title: string;
  description: string;
  unlocked_at: string | null;
  is_unlocked: boolean;
  holder_percent: number;
  holders_count: number;
  total_players: number;
  max_tier: number;
  next_tier: number | null;
  next_threshold: number | null;
  current_value: number;
  stat_label: string;
}

interface AchievementsResponse {
  ok: boolean;
  items: AchievementItem[];
  earned_count: number;
  total_count: number;
}

export class AchievementsScreen {
  private el: HTMLElement;
  private isLoading = false;

  constructor() {
    this.el = this.build();
  }

  private build(): HTMLElement {
    const screen = document.createElement('section');
    screen.id = 'screen-achievements';
    screen.className = 'screen';
    screen.setAttribute('role', 'main');
    screen.setAttribute('aria-label', 'Достижения');

    screen.innerHTML = `
      <div class="screen-header">
        <button class="back-btn" id="achievements-back-btn">← Назад</button>
        <h1 class="page-title">ДОСТИЖЕНИЯ</h1>
        <div></div>
      </div>

      <div class="achievements-summary glass" id="achievements-summary">
        <div class="achievements-loading">Загрузка...</div>
      </div>

      <div class="achievements-list glass" id="achievements-list">
        <div class="achievements-loading">Загрузка достижений...</div>
      </div>
    `;

    return screen;
  }

  getElement(): HTMLElement {
    return this.el;
  }

  async init(): Promise<void> {
    this.bindEvents();
    await this.loadAchievements();
  }

  private bindEvents(): void {
    setTimeout(() => {
      const backBtn = this.el.querySelector('#achievements-back-btn');
      backBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        tgService.haptic('light');
        window.dispatchEvent(new CustomEvent('navigate-home'));
      });
    }, 100);
  }

  private async loadAchievements(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    const summaryEl = this.el.querySelector('#achievements-summary') as HTMLElement;
    const listEl = this.el.querySelector('#achievements-list') as HTMLElement;

    summaryEl.innerHTML = '<div class="achievements-loading">Загрузка...</div>';
    listEl.innerHTML = '<div class="achievements-loading">Загрузка достижений...</div>';

    try {
      const response = await apiRequest<AchievementsResponse>('/api/achievements');
      if (!response.ok || !response.items) {
        throw new Error('Failed to load achievements');
      }

      summaryEl.innerHTML = `
        <div class="achievements-summary-value">${response.earned_count} / ${response.total_count}</div>
        <div class="achievements-summary-label">достижений получено</div>
      `;

      this.renderList(listEl, response.items);
    } catch (error) {
      console.error('Failed to load achievements:', error);
      summaryEl.innerHTML = '<div class="achievements-error">Ошибка</div>';
      listEl.innerHTML = '<div class="achievements-error">Не удалось загрузить достижения</div>';
    } finally {
      this.isLoading = false;
    }
  }

  private renderList(container: HTMLElement, items: AchievementItem[]): void {
    if (!items.length) {
      container.innerHTML = '<div class="achievements-empty">Достижений пока нет</div>';
      return;
    }

    const sorted = [...items].sort((a, b) => {
      if (a.is_unlocked !== b.is_unlocked) return a.is_unlocked ? -1 : 1;
      return a.title.localeCompare(b.title, 'ru');
    });

    container.innerHTML = sorted.map(item => this.renderCard(item)).join('');
  }

  private renderCard(item: AchievementItem): string {
    const unlocked = item.is_unlocked;
    const cardClass = unlocked ? 'is-unlocked' : 'is-locked';
    const title = unlocked ? item.display_title : item.title;
    const tierBadge = unlocked
      ? `<span class="achievement-tier-badge">Уровень ${item.current_tier}</span>`
      : `<span class="achievement-locked-label">Не получено</span>`;

    const unlockedLine = unlocked && item.unlocked_at
      ? `<div class="achievement-meta-item">📅 Получено: <strong>${this.formatDate(item.unlocked_at)}</strong></div>`
      : '';

    const percentTier = unlocked ? item.current_tier : 1;
    const percentLine = `
      <div class="achievement-meta-item">
        👥 У ${item.holder_percent}% игроков (ур. ${percentTier})
      </div>
    `;

    const progressHtml = this.renderProgress(item);

    return `
      <article class="achievement-card ${cardClass}">
        <div class="achievement-card-header">
          <div class="achievement-icon">${this.escapeHtml(item.icon)}</div>
          <div class="achievement-head-text">
            <div class="achievement-title">
              ${this.escapeHtml(title)}
              ${tierBadge}
            </div>
            <div class="achievement-desc">${this.escapeHtml(item.description)}</div>
          </div>
        </div>
        <div class="achievement-meta">
          ${unlockedLine}
          ${percentLine}
        </div>
        ${progressHtml}
      </article>
    `;
  }

  private renderProgress(item: AchievementItem): string {
    let threshold = item.next_threshold;
    if (!item.is_unlocked && threshold == null) {
      threshold = item.next_threshold;
    }

    if (threshold == null) {
      if (item.is_unlocked && item.current_tier >= item.max_tier) {
        return '<div class="achievement-progress-label">Максимальный уровень достигнут ✨</div>';
      }
      return '';
    }

    const current = item.current_value;
    const pct = Math.min(100, Math.max(0, (current / threshold) * 100));
    const label = item.is_unlocked && item.next_tier
      ? `До уровня ${item.next_tier}: ${this.formatNumber(current)} / ${this.formatNumber(threshold)} ${item.stat_label}`
      : `Прогресс: ${this.formatNumber(current)} / ${this.formatNumber(threshold)} ${item.stat_label}`;

    return `
      <div class="achievement-progress">
        <div class="achievement-progress-bar">
          <div class="achievement-progress-fill" style="width:${pct.toFixed(1)}%"></div>
        </div>
        <div class="achievement-progress-label">${this.escapeHtml(label)}</div>
      </div>
    `;
  }

  private formatDate(iso: string): string {
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
      return d.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso.slice(0, 16).replace('T', ' ');
    }
  }

  private formatNumber(value: number): string {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(1);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
