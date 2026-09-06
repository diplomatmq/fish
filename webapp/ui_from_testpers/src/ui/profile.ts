// ─────────────────────────────────────────────────────────────────────────────
// ProfilePanel — porthole avatar, name, progress bar, recent catches
// ─────────────────────────────────────────────────────────────────────────────
import { USER_PROFILE } from '../data';
import { tgService } from '../modules/telegram';
import { fetchApi } from '../modules/api';
import { UserProfile } from '../types';

export class ProfilePanel {
  private el: HTMLElement;
  private fillEl: HTMLElement | null = null;
  private wobbling = false;
  private profile: UserProfile = { ...USER_PROFILE };
  private recentCatches: any[] = [];

  constructor() {
    this.el = this.build();
    this.loadProfile();
    this.loadRecentCatches();
  }

  private async loadProfile() {
    try {
      const data = await fetchApi<any>('/api/profile');
      if (data) {
        this.profile.name = data.username || this.profile.name;
        this.profile.level = data.level || this.profile.level;
        this.profile.xp = data.xp || this.profile.xp;
        this.profile.maxXp = 10000; // Можно высчитывать на основе уровня если нужно
        this.profile.tag = `@${data.user_id}` || this.profile.tag;
        this.updateUI();
      }
    } catch (e) {
      console.error('Failed to load profile:', e);
    }
  }

  private async loadRecentCatches() {
    try {
      const data = await fetchApi<any>('/api/inventory');
      if (data && data.items) {
        this.recentCatches = data.items.slice(0, 5); // Show last 5 catches
        this.renderRecentCatches();
      }
    } catch (e) {
      console.error('Failed to load recent catches:', e);
    }
  }

  private renderRecentCatches() {
    const catchesContainer = this.el.querySelector('#recent-catches-container') as HTMLElement;
    if (!catchesContainer) return;

    if (this.recentCatches.length === 0) {
      catchesContainer.innerHTML = '<p class="no-catches">Пока нет улова</p>';
      return;
    }

    catchesContainer.innerHTML = `
      <div class="catches-grid">
        ${this.recentCatches.map(item => `
          <div class="catch-item">
            <img src="${item.image_url}" alt="${item.name}" class="catch-image" />
            <div class="catch-info">
              <div class="catch-name">${item.name}</div>
              <div class="catch-details">
                ${item.weight ? `<span>⚖️ ${item.weight}кг</span>` : ''}
                ${item.rarity ? `<span>✨ ${item.rarity}</span>` : ''}
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  private updateUI() {
    const nameEl = this.el.querySelector<HTMLElement>('#profile-name');
    const tagEl = this.el.querySelector<HTMLElement>('#profile-tag');
    const levelEl = this.el.querySelector<HTMLElement>('.level-label');
    const xpEl = this.el.querySelector<HTMLElement>('.xp-label');

    if (nameEl) nameEl.textContent = this.profile.name.toUpperCase();
    if (tagEl) tagEl.textContent = this.profile.tag;
    if (levelEl) levelEl.textContent = `Уровень ${this.profile.level}`;
    if (xpEl) xpEl.textContent = `${this.profile.xp.toLocaleString('ru')} XP`;

    this.animateProgress(0);
  }

  getElement(): HTMLElement { return this.el; }

  // ── Build DOM ──────────────────────────────────────────────────────────────
  private build(): HTMLElement {
    const profile = USER_PROFILE;
    const pct     = Math.round((profile.xp / profile.maxXp) * 100);

    const panel = document.createElement('div');
    panel.id        = 'profile-panel';
    panel.className = 'profile-panel glass';

    panel.innerHTML = `
      <div id="porthole-wrap" class="porthole" role="button" tabindex="0" aria-label="Аватар игрока">
        <div class="porthole__ring"></div>
        <div class="porthole__inner">${profile.avatar}</div>
      </div>

      <div class="profile-info">
        <div class="profile-name" id="profile-name">${profile.name}</div>
        <div class="profile-tag"  id="profile-tag">${profile.tag}</div>

        <button class="edit-btn" id="edit-btn" aria-label="Редактировать профиль">
          ✏️ Редактировать
        </button>

        <div class="level-row">
          <span class="level-label">Уровень ${profile.level}</span>
          <span class="xp-label">${profile.xp.toLocaleString('ru')} / ${profile.maxXp.toLocaleString('ru')} XP</span>
        </div>
        <div class="progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
          <div class="progress-fill" id="progress-fill"></div>
        </div>
      </div>

      <div class="recent-catches-section">
        <h3 class="catches-title">🎣 Последний улов</h3>
        <div id="recent-catches-container" class="catches-container">
          <div class="loader-wrap"><div class="loader"></div></div>
        </div>
      </div>
    `;

    // Porthole wobble on click
    const porthole = panel.querySelector<HTMLElement>('#porthole-wrap')!;
    porthole.addEventListener('click', () => this.wobble(porthole));
    porthole.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') this.wobble(porthole);
    });

    // Edit button
    const editBtn = panel.querySelector<HTMLElement>('#edit-btn')!;
    editBtn.addEventListener('click', () => {
      tgService.haptic('light');
      editBtn.textContent = '⏳ Загрузка...';
      setTimeout(() => { editBtn.innerHTML = '✏️ Редактировать'; }, 1800);
    });
    editBtn.addEventListener('pointerdown', () => {
      editBtn.style.transform = 'scale(0.96)';
    });
    editBtn.addEventListener('pointerup', () => {
      editBtn.style.transform = '';
    });

    this.fillEl = panel.querySelector('#progress-fill');
    return panel;
  }

  // ── Animate progress bar on reveal ────────────────────────────────────────
  animateProgress(delay = 200): void {
    if (!this.fillEl) return;
    const pct = Math.round((USER_PROFILE.xp / USER_PROFILE.maxXp) * 100);
    this.fillEl.style.width = '0%';
    setTimeout(() => {
      this.fillEl!.style.width = `${pct}%`;
    }, delay);
  }

  // ── Porthole Wobble ────────────────────────────────────────────────────────
  private wobble(el: HTMLElement): void {
    if (this.wobbling) return;
    this.wobbling = true;
    tgService.haptic('light');
    el.classList.add('porthole--wobble');
    el.addEventListener('animationend', () => {
      el.classList.remove('porthole--wobble');
      this.wobbling = false;
    }, { once: true });
  }

  // ── Update profile from Telegram user data ─────────────────────────────────
  updateFromTelegram(): void {
    const name = tgService.getUserName();
    const tag  = tgService.getUserTag();
    if (name) {
      const nameEl = this.el.querySelector<HTMLElement>('#profile-name');
      if (nameEl) nameEl.textContent = name.toUpperCase();
    }
    if (tag) {
      const tagEl = this.el.querySelector<HTMLElement>('#profile-tag');
      if (tagEl) tagEl.textContent = tag;
    }
  }

  // ── Refresh catches after fishing ────────────────────────────────────────
  refreshCatches(): void {
    this.loadRecentCatches();
  }
}
