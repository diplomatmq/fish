// ─────────────────────────────────────────────────────────────────────────────
// RatingScreen — Leaderboard for tickets
// ─────────────────────────────────────────────────────────────────────────────
import { apiRequest } from '../modules/api';
import { tgService } from '../modules/telegram';

interface LeaderboardItem {
  place: number;
  user_id: number;
  username: string;
  tickets: number;
}

interface LeaderboardResponse {
  ok: boolean;
  items: LeaderboardItem[];
  my_rank: number | null;
  ticket_type: string;
}

export class RatingScreen {
  private el: HTMLElement;
  private currentType: 'normal' | 'gold' = 'normal';
  private isLoading = false;

  constructor() {
    this.el = this.build();
  }

  private build(): HTMLElement {
    const screen = document.createElement('section');
    screen.id = 'screen-rating';
    screen.className = 'screen';
    screen.setAttribute('role', 'main');
    screen.setAttribute('aria-label', 'Рейтинг');

    screen.innerHTML = `
      <h1 class="page-title">РЕЙТИНГ</h1>
      
      <div class="rating-tabs">
        <button class="rating-tab is-active" data-type="normal">
          🎟️ Обычные билеты
        </button>
        <button class="rating-tab" data-type="gold">
          🎫 Золотые билеты
        </button>
      </div>

      <div class="rating-my-rank glass" id="rating-my-rank">
        <div class="rating-loading">Загрузка...</div>
      </div>

      <div class="rating-list glass" id="rating-list">
        <div class="rating-loading">Загрузка рейтинга...</div>
      </div>
    `;

    return screen;
  }

  getElement(): HTMLElement {
    return this.el;
  }

  async init(): Promise<void> {
    this.bindEvents();
    await this.loadRating();
  }

  private bindEvents(): void {
    const tabs = this.el.querySelectorAll('.rating-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const type = (tab as HTMLElement).dataset.type as 'normal' | 'gold';
        if (type === this.currentType || this.isLoading) return;

        tgService.haptic('selection');
        
        tabs.forEach(t => t.classList.remove('is-active'));
        tab.classList.add('is-active');
        
        this.currentType = type;
        this.loadRating();
      });
    });
  }

  private async loadRating(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    const listEl = this.el.querySelector('#rating-list') as HTMLElement;
    const myRankEl = this.el.querySelector('#rating-my-rank') as HTMLElement;

    listEl.innerHTML = '<div class="rating-loading">Загрузка...</div>';
    myRankEl.innerHTML = '<div class="rating-loading">Загрузка...</div>';

    try {
      const response = await apiRequest<LeaderboardResponse>(
        `/api/tickets/rating?ticket_type=${this.currentType}&limit=50`
      );

      if (!response.ok || !response.items) {
        throw new Error('Failed to load rating');
      }

      this.renderMyRank(myRankEl, response.my_rank, response.ticket_type);
      this.renderList(listEl, response.items);
    } catch (error) {
      console.error('Failed to load rating:', error);
      listEl.innerHTML = '<div class="rating-error">Ошибка загрузки рейтинга</div>';
      myRankEl.innerHTML = '<div class="rating-error">Ошибка загрузки</div>';
    } finally {
      this.isLoading = false;
    }
  }

  private renderMyRank(container: HTMLElement, rank: number | null, ticketType: string): void {
    const emoji = ticketType === 'gold' ? '🎫' : '🎟️';
    const typeName = ticketType === 'gold' ? 'золотых' : 'обычных';

    if (rank === null || rank === 0) {
      container.innerHTML = `
        <div class="my-rank-content">
          <div class="my-rank-icon">${emoji}</div>
          <div class="my-rank-text">
            <div class="my-rank-label">Ваше место</div>
            <div class="my-rank-value">Нет ${typeName} билетов</div>
          </div>
        </div>
      `;
    } else {
      const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
      container.innerHTML = `
        <div class="my-rank-content">
          <div class="my-rank-icon">${medal || emoji}</div>
          <div class="my-rank-text">
            <div class="my-rank-label">Ваше место в топе</div>
            <div class="my-rank-value">#${rank}</div>
          </div>
        </div>
      `;
    }
  }

  private renderList(container: HTMLElement, items: LeaderboardItem[]): void {
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="rating-empty">Рейтинг пуст</div>';
      return;
    }

    const html = items.map(item => {
      const medal = item.place === 1 ? '🥇' : item.place === 2 ? '🥈' : item.place === 3 ? '🥉' : '';
      const placeClass = item.place <= 3 ? 'rating-item-top' : '';
      
      return `
        <div class="rating-item ${placeClass}">
          <div class="rating-place">
            ${medal ? `<span class="rating-medal">${medal}</span>` : `<span class="rating-number">#${item.place}</span>`}
          </div>
          <div class="rating-user">
            <div class="rating-username">${this.escapeHtml(item.username)}</div>
            <div class="rating-user-id">ID: ${item.user_id}</div>
          </div>
          <div class="rating-tickets">
            <div class="rating-tickets-value">${item.tickets}</div>
            <div class="rating-tickets-label">билетов</div>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = html;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
