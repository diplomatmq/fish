// ─────────────────────────────────────────────────────────────────────────────
// ResultsScreen — Lottery results (view for all, create for owner)
// ─────────────────────────────────────────────────────────────────────────────
import { apiRequest } from '../modules/api';
import { tgService } from '../modules/telegram';

const OWNER_ID = 793216884;

interface Winner {
  place: number;
  ticket_code: string;
  user_id: number;
  username: string;
  created_at?: string;
  source_type?: string;
  source_ref?: string;
  tickets_in_period?: number;
}

interface ResultsResponse {
  ok: boolean;
  items: Winner[];
  ticket_type: string;
  period: {
    start_date: string;
    end_date: string;
    count: number;
  } | null;
}

export class ResultsScreen {
  private el: HTMLElement;
  private currentType: 'normal' | 'gold' = 'normal';
  private isLoading = false;
  private isOwner = false;

  constructor() {
    this.el = this.build();
    this.checkOwner();
  }

  private checkOwner(): void {
    const user = tgService.getUser();
    this.isOwner = user?.id === OWNER_ID;
  }

  private build(): HTMLElement {
    const screen = document.createElement('section');
    screen.id = 'screen-results';
    screen.className = 'screen';
    screen.setAttribute('role', 'main');
    screen.setAttribute('aria-label', 'Результаты');

    screen.innerHTML = `
      <div class="screen-header">
        <button class="back-btn" id="results-back-btn">← Назад</button>
        <h1 class="page-title">РЕЗУЛЬТАТЫ</h1>
        <div class="back-btn-spacer"></div>
      </div>
      
      <div class="results-tabs">
        <button class="results-tab is-active" data-type="normal">
          🎟️ Обычные билеты
        </button>
        <button class="results-tab" data-type="gold">
          🎫 Золотые билеты
        </button>
      </div>

      <div id="results-owner-panel" class="results-owner-panel glass" style="display: none;">
        <h3 class="results-panel-title">Создать розыгрыш</h3>
        <div class="results-form">
          <div class="results-form-row">
            <label class="results-label">Дата начала</label>
            <input type="datetime-local" id="results-start-date" class="results-input" />
          </div>
          <div class="results-form-row">
            <label class="results-label">Дата окончания</label>
            <input type="datetime-local" id="results-end-date" class="results-input" />
          </div>
          <div class="results-form-row">
            <label class="results-label">Количество победителей</label>
            <input type="number" id="results-count" class="results-input" min="1" max="100" value="3" />
          </div>
          <button id="results-create-btn" class="results-create-btn">
            🎲 Провести розыгрыш
          </button>
        </div>
      </div>

      <div class="results-list glass" id="results-list">
        <div class="results-loading">Загрузка результатов...</div>
      </div>
    `;

    return screen;
  }

  getElement(): HTMLElement {
    return this.el;
  }

  async init(): Promise<void> {
    if (this.isOwner) {
      const ownerPanel = this.el.querySelector('#results-owner-panel') as HTMLElement;
      if (ownerPanel) ownerPanel.style.display = 'block';
    }

    this.bindEvents();
    await this.loadResults();
  }

  private bindEvents(): void {
    // Back button
    const backBtn = this.el.querySelector('#results-back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        const event = new CustomEvent('navigate-home');
        window.dispatchEvent(event);
      });
    }

    // Tab switching
    const tabs = this.el.querySelectorAll('.results-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const type = (tab as HTMLElement).dataset.type as 'normal' | 'gold';
        if (type === this.currentType || this.isLoading) return;

        tgService.haptic('selection');
        
        tabs.forEach(t => t.classList.remove('is-active'));
        tab.classList.add('is-active');
        
        this.currentType = type;
        this.loadResults();
      });
    });

    // Create draw button (owner only)
    if (this.isOwner) {
      const createBtn = this.el.querySelector('#results-create-btn') as HTMLButtonElement;
      if (createBtn) {
        createBtn.addEventListener('click', () => this.createDraw());
      }
    }
  }

  private async loadResults(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    const listEl = this.el.querySelector('#results-list') as HTMLElement;
    listEl.innerHTML = '<div class="results-loading">Загрузка...</div>';

    try {
      const response = await apiRequest<ResultsResponse>(
        `/api/tickets/results?ticket_type=${this.currentType}`
      );

      if (!response.ok) {
        throw new Error('Failed to load results');
      }

      this.renderResults(listEl, response);
    } catch (error) {
      console.error('Failed to load results:', error);
      listEl.innerHTML = '<div class="results-error">Ошибка загрузки результатов</div>';
    } finally {
      this.isLoading = false;
    }
  }

  private async createDraw(): Promise<void> {
    if (this.isLoading) return;

    const startInput = this.el.querySelector('#results-start-date') as HTMLInputElement;
    const endInput = this.el.querySelector('#results-end-date') as HTMLInputElement;
    const countInput = this.el.querySelector('#results-count') as HTMLInputElement;

    const startDate = startInput.value;
    const endDate = endInput.value;
    const count = parseInt(countInput.value) || 3;

    if (!startDate || !endDate) {
      tgService.showAlert('Укажите даты начала и окончания розыгрыша');
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      tgService.showAlert('Дата начала не может быть позже даты окончания');
      return;
    }

    this.isLoading = true;
    tgService.haptic('medium');

    try {
      const response = await apiRequest<ResultsResponse>('/api/tickets/draw', {
        method: 'POST',
        body: JSON.stringify({
          ticket_type: this.currentType,
          start_date: startDate,
          end_date: endDate,
          count: count,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create draw');
      }

      tgService.showAlert(`Розыгрыш проведен! Победителей: ${response.items?.length || 0}`);
      
      // Reload results
      await this.loadResults();
    } catch (error) {
      console.error('Failed to create draw:', error);
      tgService.showAlert('Ошибка при проведении розыгрыша');
    } finally {
      this.isLoading = false;
    }
  }

  private renderResults(container: HTMLElement, response: ResultsResponse): void {
    if (!response.items || response.items.length === 0) {
      container.innerHTML = `
        <div class="results-empty">
          <div class="results-empty-icon">🎲</div>
          <div class="results-empty-text">Результатов розыгрышей пока нет</div>
        </div>
      `;
      return;
    }

    const period = response.period;
    const periodHtml = period ? `
      <div class="results-period">
        <div class="results-period-title">Период розыгрыша</div>
        <div class="results-period-dates">
          ${this.formatDate(period.start_date)} — ${this.formatDate(period.end_date)}
        </div>
        <div class="results-period-count">Победителей: ${period.count}</div>
      </div>
    ` : '';

    const winnersHtml = response.items.map(winner => {
      const medal = winner.place === 1 ? '🥇' : winner.place === 2 ? '🥈' : winner.place === 3 ? '🥉' : '🎖️';
      const placeClass = winner.place <= 3 ? 'results-winner-top' : '';
      
      return `
        <div class="results-winner ${placeClass}">
          <div class="results-winner-place">
            <span class="results-medal">${medal}</span>
            <span class="results-place-number">#${winner.place}</span>
          </div>
          <div class="results-winner-info">
            <div class="results-winner-username">${this.escapeHtml(winner.username)}</div>
            <div class="results-winner-id">ID: ${winner.user_id}</div>
            <div class="results-winner-ticket">Билет: <strong>${winner.ticket_code}</strong></div>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = periodHtml + '<div class="results-winners">' + winnersHtml + '</div>';
  }

  private formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
