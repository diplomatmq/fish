// ─────────────────────────────────────────────────────────────────────────────
// TrophyModal — bottom sheet modal for choosing trophy
// ─────────────────────────────────────────────────────────────────────────────
import { RARITY_COLORS } from '../data';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';
import type { FishData } from '../types';

export class TrophyModal {
  private overlay: HTMLElement;
  private sheet:   HTMLElement;
  private listEl:  HTMLElement;
  private isOpen  = false;
  private bgBlurTarget: HTMLElement | null = null;
  private trophies: FishData[] = [];

  private onSelectCallback: ((index: number) => void) | null = null;
  private currentActiveIndex = 0;

  // Swipe-to-close state
  private sheetStartY = 0;
  private sheetDragging = false;

  constructor() {
    this.overlay = this.buildOverlay();
    this.sheet   = this.overlay.querySelector('#modal-sheet')!;
    this.listEl  = this.overlay.querySelector('#modal-fish-list')!;
    document.body.appendChild(this.overlay);
    this.bindClose();
  }

  setTrophies(trophies: FishData[]): void {
    this.trophies = trophies;
  }

  // ── Build DOM ──────────────────────────────────────────────────────────────
  private buildOverlay(): HTMLElement {
    const el = document.createElement('div');
    el.id        = 'modal-overlay';
    el.className = 'modal-overlay';
    el.innerHTML = `
      <div id="modal-sheet" class="modal-sheet">
        <div class="modal-handle"></div>
        <p class="modal-title">🏆 Выбор трофея</p>
        <div id="modal-fish-list" class="modal-fish-list"></div>
      </div>
    `;
    return el;
  }

  private buildList(): void {
    this.listEl.innerHTML = this.trophies.map((f, i) => {
      const color   = RARITY_COLORS[f.rarity] || '#ffffff';
      const isActive = i === this.currentActiveIndex;
      return `
        <div
          class="modal-fish-item ${isActive ? 'is-selected' : ''}"
          data-index="${i}"
          style="--accent:${color}"
          role="button"
          tabindex="0"
          aria-label="${f.name}"
        >
          <span class="modal-fish-emoji">${getIcon(f.id)}</span>
          <div class="modal-fish-info">
            <div class="modal-fish-name">${f.name}</div>
            <div class="modal-fish-rarity" style="color:${color}">${f.rarityStars} ${f.rarityLabel}</div>
            <div class="modal-fish-stats">⚖️ ${f.weight} · 🌊 ${f.depth}</div>
          </div>
          ${isActive ? '<span class="modal-check">✓</span>' : ''}
        </div>
      `;
    }).join('');

    // Click handlers on each item
    this.listEl.querySelectorAll<HTMLElement>('.modal-fish-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset['index'] ?? '0', 10);
        this.select(idx);
      });
    });
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  open(activeIndex: number, bgBlurTarget?: HTMLElement): void {
    if (this.isOpen) return;
    this.currentActiveIndex = activeIndex;
    this.bgBlurTarget = bgBlurTarget ?? null;
    this.buildList();

    this.overlay.style.display = 'flex';
    requestAnimationFrame(() => {
      this.overlay.classList.add('is-open');
      if (this.bgBlurTarget) this.bgBlurTarget.style.filter = 'blur(4px)';
    });

    this.isOpen = true;
    tgService.haptic('medium');
  }

  close(): void {
    if (!this.isOpen) return;
    this.overlay.classList.remove('is-open');
    if (this.bgBlurTarget) this.bgBlurTarget.style.filter = '';

    setTimeout(() => {
      this.overlay.style.display = 'none';
    }, 420);

    this.isOpen = false;
  }

  onSelect(cb: (index: number) => void): void {
    this.onSelectCallback = cb;
  }

  // ── Internal ───────────────────────────────────────────────────────────────
  private select(index: number): void {
    this.currentActiveIndex = index;
    tgService.haptic('medium');
    this.onSelectCallback?.(index);
    this.close();
  }

  private bindClose(): void {
    // Tap outside sheet
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) this.close();
    });

    // Swipe-down to close
    const sheet = this.sheet;

    sheet.addEventListener('touchstart', (e: TouchEvent) => {
      this.sheetStartY  = e.touches[0].clientY;
      this.sheetDragging = true;
    }, { passive: true });

    sheet.addEventListener('touchmove', (e: TouchEvent) => {
      if (!this.sheetDragging) return;
      const dy = e.touches[0].clientY - this.sheetStartY;
      if (dy > 0) {
        sheet.style.transform = `translateY(${dy * 0.55}px)`;
        sheet.style.transition = 'none';
      }
    }, { passive: true });

    sheet.addEventListener('touchend', (e: TouchEvent) => {
      if (!this.sheetDragging) return;
      const dy = e.changedTouches[0].clientY - this.sheetStartY;
      sheet.style.transform  = '';
      sheet.style.transition = '';
      if (dy > 80) this.close();
      this.sheetDragging = false;
    }, { passive: true });
  }

  get fish(): FishData[] { return this.trophies; }
}
