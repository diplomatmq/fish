// ─────────────────────────────────────────────────────────────────────────────
// TabBar — animated tab navigation
// ─────────────────────────────────────────────────────────────────────────────
import { TABS } from '../data';
import { tgService } from '../modules/telegram';
import { ScreenTransition } from '../animations/effects';
import { getIcon } from './icons';
import type { ScreenId } from '../types';

type TabChangeCallback = (prev: ScreenId, next: ScreenId) => void;

export class TabBar {
  private el: HTMLElement;
  private activeId: ScreenId = 'home';
  private buttons: Map<ScreenId, HTMLButtonElement> = new Map();
  private screens: Map<ScreenId, HTMLElement> = new Map();
  private onChangeCallbacks: TabChangeCallback[] = [];

  constructor(parentEl: HTMLElement, screensContainer: HTMLElement) {
    this.el = this.build();
    parentEl.appendChild(this.el);

    // Collect screens
    TABS.forEach(tab => {
      const screen = screensContainer.querySelector<HTMLElement>(`#screen-${tab.id}`);
      if (screen) this.screens.set(tab.id, screen);
    });

    // Show home, hide rest
    this.screens.forEach((screen, id) => {
      if (id === 'home') {
        screen.style.display = 'flex';
        screen.style.opacity = '1';
        screen.style.pointerEvents = 'all';
      } else {
        screen.style.display = 'none';
        screen.style.opacity = '0';
      }
    });
  }

  // ── Build DOM ──────────────────────────────────────────────────────────────
  private build(): HTMLElement {
    const nav = document.createElement('nav');
    nav.id        = 'tab-bar';
    nav.className = 'tab-bar';
    nav.setAttribute('role', 'tablist');

    TABS.forEach(tab => {
      const btn = document.createElement('button');
      btn.id        = `tab-${tab.id}`;
      btn.className = `tab-btn ${tab.id === 'home' ? 'is-active' : ''}`;
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-selected', tab.id === 'home' ? 'true' : 'false');
      btn.dataset['tab'] = tab.id;
      btn.innerHTML = `
        <span class="tab-icon" aria-hidden="true">${getIcon(tab.id)}</span>
        <span class="tab-label">${tab.label}</span>
      `;

      btn.addEventListener('click', () => this.switchTo(tab.id));

      // Active-state press scale
      btn.addEventListener('pointerdown', () => {
        btn.style.transform = 'scale(0.92)';
      });
      btn.addEventListener('pointerup', () => {
        btn.style.transform = '';
      });
      btn.addEventListener('pointerleave', () => {
        btn.style.transform = '';
      });

      nav.appendChild(btn);
      this.buttons.set(tab.id, btn);
    });

    return nav;
  }

  // ── Switch tab ─────────────────────────────────────────────────────────────
  switchTo(id: ScreenId): void {
    if (id === this.activeId) return;

    tgService.haptic('selection');

    const prevId   = this.activeId;
    const fromScreen = this.screens.get(prevId);
    const toScreen   = this.screens.get(id);
    if (!fromScreen || !toScreen) {
      return;
    }

    // Animate screens
    ScreenTransition.transitionTo(fromScreen, toScreen);

    // Update button states
    this.buttons.forEach((btn, tabId) => {
      const isActive = tabId === id;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-selected', String(isActive));
    });

    this.activeId = id;
    this.onChangeCallbacks.forEach(cb => cb(prevId, id));
  }

  onChange(cb: TabChangeCallback): void {
    this.onChangeCallbacks.push(cb);
  }

  getActive(): ScreenId { return this.activeId; }
}
