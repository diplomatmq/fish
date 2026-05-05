// ─────────────────────────────────────────────────────────────────────────────
// AppLayout — builds entire DOM structure & wires everything together
// ─────────────────────────────────────────────────────────────────────────────
import { TABS, FISH_DATA } from '../data';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';
import type { ScreenId, FishData } from '../types';

export function buildLayout(): HTMLElement {
  const app = document.getElementById('app')!;

  // ── Background + Sunrays ──────────────────────────────────────────────────
  app.innerHTML = `
    <div id="bg-parallax"  class="bg-parallax"></div>
    <div id="bg-overlay"   class="bg-overlay"></div>

    <div class="sunrays" aria-hidden="true">
      <div class="sunray"></div>
      <div class="sunray"></div>
      <div class="sunray"></div>
      <div class="sunray"></div>
    </div>

    <canvas id="particles-canvas" class="particles-canvas" aria-hidden="true"></canvas>

    <!-- ═══ SCREENS ═══ -->
    <div id="screens-wrap" class="screens-wrap">

      <!-- HOME -->
      <section id="screen-home" class="screen is-active" role="main" aria-label="Главная">
        <h1 class="page-title slide-up" style="animation-delay:1.8s">ПОДВОДНЫЙ МИР</h1>

        <!-- Profile injected by ProfilePanel -->
        <div id="profile-mount" class="slide-up" style="animation-delay:1.9s"></div>

        <!-- Trophy -->
        <div id="trophy-section" class="trophy-section slide-up" style="animation-delay:2.0s">
          <p class="section-title">ТРОФЕЙ</p>
          <div id="carousel-mount" class="carousel-wrap"></div>
          <button id="select-trophy-btn" class="select-trophy-btn" aria-label="Выбрать трофей">
            ${getIcon('trophy')} &nbsp;ВЫБРАТЬ ТРОФЕЙ
          </button>
        </div>

        <!-- Quick actions -->
        <div class="quick-actions slide-up" style="animation-delay:2.1s">
          <button class="quick-card glass" id="btn-achievements" aria-label="Достижения">
            <span class="quick-icon" aria-hidden="true">${getIcon('achievements')}</span>
            <span class="quick-label">Достижения</span>
          </button>
          <button class="quick-card glass" id="btn-rating" aria-label="Рейтинг">
            <span class="quick-icon" aria-hidden="true">${getIcon('rating')}</span>
            <span class="quick-label">Рейтинг</span>
          </button>
        </div>
      </section>

      <!-- SHOP -->
      <section id="screen-shop" class="screen" role="main" aria-label="Лавка">
        <h1 class="page-title">ЛАВКА</h1>
        <div class="glass shop-container">
          <div class="shop-empty">
            <div class="shop-soon-icon">${getIcon('shop')}</div>
            <h3>Лавка скоро откроется!</h3>
            <p>Здесь вы сможете продавать рыбу и покупать снаряжение прямо в приложении.</p>
          </div>
        </div>
      </section>

      <!-- FRIENDS -->
      <section id="screen-friends" class="screen" role="main" aria-label="Друзья"></section>

      <!-- GUILDS (ARTELS) -->
      <section id="screen-guilds" class="screen" role="main" aria-label="Артели"></section>

      <!-- BOOK -->
      ${emptyScreen('book', '📖', 'Книга рыбака', 'Здесь появится ваш\nрыболовный журнал')}

    </div>

    <!-- Tab bar injected by TabBar -->
    <div id="tabbar-mount"></div>

    <!-- Modal injected by TrophyModal -->
  `;

  return app;
}

function emptyScreen(id: ScreenId, _icon: string, title: string, text: string): string {
  return `
    <section id="screen-${id}" class="screen screen--empty" role="main" aria-label="${title}">
      <h1 class="page-title">${title.toUpperCase()}</h1>
      <div class="glass empty-content">
        <div class="empty-icon" aria-hidden="true">${getIcon(id)}</div>
        <p class="empty-text">${text.replace('\n', '<br>')}</p>
      </div>
    </section>
  `;
}

// ── Entry animation overlay ─────────────────────────────────────────────────
export function buildEntryOverlay(): HTMLElement {
  const overlay = document.createElement('div');
  overlay.id        = 'entry-overlay';
  overlay.className = 'entry-overlay';
  overlay.innerHTML = `
    <div class="entry-logo" aria-hidden="true">🌊</div>
    <p class="entry-title">ПОДВОДНЫЙ МИР</p>
    <p class="entry-subtitle">Загрузка…</p>
  `;
  document.body.appendChild(overlay);
  return overlay;
}

export function hideEntryOverlay(overlay: HTMLElement, delay = 1600): void {
  setTimeout(() => {
    overlay.style.transition = 'opacity 0.6s ease';
    overlay.style.opacity    = '0';
    setTimeout(() => overlay.remove(), 700);
  }, delay);
}

// ── Quick action bounce helper ──────────────────────────────────────────────
export function bindQuickActions(onShopClick?: () => void): void {
  const achievementsBtn = document.getElementById('btn-achievements');
  const ratingBtn       = document.getElementById('btn-rating');

  [achievementsBtn, ratingBtn].forEach(btn => {
    if (!btn) return;
    btn.addEventListener('click', () => {
      tgService.haptic('light');
      btn.classList.remove('bounce');
      void (btn as HTMLElement).offsetWidth; // reflow
      btn.classList.add('bounce');
      btn.addEventListener('animationend', () => btn.classList.remove('bounce'), { once: true });
    });
  });
}

// ── Trophy button helper ────────────────────────────────────────────────────
export function bindTrophyButton(onOpen: () => void): void {
  const btn = document.getElementById('select-trophy-btn');
  if (!btn) return;
  btn.addEventListener('click', onOpen);
  btn.addEventListener('pointerdown', () => { btn.style.transform = 'scale(0.96)'; });
  btn.addEventListener('pointerup',   () => { btn.style.transform = ''; });
  btn.addEventListener('pointerleave',() => { btn.style.transform = ''; });
}

// ── Active trophy label ─────────────────────────────────────────────────────
export function updateActiveTrophyLabel(fish: FishData): void {
  const existingLabel = document.getElementById('active-trophy-label');
  if (existingLabel) existingLabel.textContent = `ГЛАВНЫЙ ТРОФЕЙ: ${fish.name.toUpperCase()}`;
}
