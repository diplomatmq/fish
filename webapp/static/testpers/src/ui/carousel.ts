// ─────────────────────────────────────────────────────────────────────────────
// FishCarousel — swipeable trophy carousel with momentum & rubber-band
// ─────────────────────────────────────────────────────────────────────────────
import { FISH_DATA, RARITY_COLORS } from '../data';
import { tgService } from '../modules/telegram';
import { BubbleSpawner } from '../animations/effects';
import { getIcon } from './icons';
import type { FishData } from '../types';

export class FishCarousel {
  private container: HTMLElement;
  private activeIndex: number;
  private cards: HTMLElement[] = [];
  private bubbleSpawner: BubbleSpawner | null = null;

  // Swipe state
  private startX = 0;
  private isDragging = false;

  private onChangeCallback: ((fish: FishData) => void) | null = null;

  constructor(container: HTMLElement, initialIndex = 2) {
    this.container    = container;
    this.activeIndex  = initialIndex;
    this.build();
    this.bindSwipe();
    this.update();
  }

  // ── Build DOM ──────────────────────────────────────────────────────────────
  private build(): void {
    this.container.innerHTML = '';
    this.cards = [];

    // Bubble layer (behind cards)
    const bubbleLayer = document.createElement('div');
    bubbleLayer.className = 'carousel__bubbles';
    this.container.appendChild(bubbleLayer);
    this.bubbleSpawner = new BubbleSpawner(bubbleLayer);

    // Track
    const track = document.createElement('div');
    track.className = 'carousel__track';
    this.container.appendChild(track);

    FISH_DATA.forEach((fish, i) => {
      const card = document.createElement('div');
      card.className   = 'carousel__card';
      card.dataset['index'] = String(i);

      const accentColor = RARITY_COLORS[fish.rarity];
      card.innerHTML = `
        <div class="carousel__card-inner" style="--accent:${accentColor}">
          <div class="carousel__fish-emoji">${getIcon(fish.id)}</div>
          <div class="carousel__rarity" style="color:${accentColor}">${fish.rarityStars} ${fish.rarityLabel}</div>
          <div class="carousel__fish-name">${fish.name}</div>
          <div class="carousel__fish-latin">${fish.latinName}</div>
          <div class="carousel__fish-stats">
            <span>⚖️ ${fish.weight}</span>
            <span>🌊 ${fish.depth}</span>
          </div>
        </div>
      `;

      track.appendChild(card);
      this.cards.push(card);
    });
  }

  // ── Update card positions & styles ────────────────────────────────────────
  update(): void {
    this.cards.forEach((card, i) => {
      const offset = i - this.activeIndex;
      const abs    = Math.abs(offset);

      // Remove all state classes
      card.classList.remove('is-active', 'is-side', 'is-far');

      let translateX: number;
      let scale:   number;
      let opacity: number;
      let zIndex:  number;

      switch (abs) {
        case 0:
          translateX = 0;
          scale   = 1;
          opacity = 1;
          zIndex  = 10;
          card.classList.add('is-active');
          break;
        case 1:
          translateX = offset * 148;
          scale   = 0.78;
          opacity = 0.60;
          zIndex  = 5;
          card.classList.add('is-side');
          break;
        case 2:
          translateX = offset * 185;
          scale   = 0.62;
          opacity = 0.28;
          zIndex  = 2;
          card.classList.add('is-far');
          break;
        default:
          translateX = offset * 200;
          scale   = 0.5;
          opacity = 0;
          zIndex  = 0;
      }

      card.style.transform = `translateX(${translateX}px) scale(${scale})`;
      card.style.opacity   = String(opacity);
      card.style.zIndex    = String(zIndex);
    });

    this.onChangeCallback?.(FISH_DATA[this.activeIndex]);
  }

  // ── Navigate ───────────────────────────────────────────────────────────────
  next(): void {
    if (this.activeIndex < FISH_DATA.length - 1) {
      this.activeIndex++;
      this.update();
      tgService.haptic('light');
    }
  }

  prev(): void {
    if (this.activeIndex > 0) {
      this.activeIndex--;
      this.update();
      tgService.haptic('light');
    }
  }

  goTo(index: number): void {
    this.activeIndex = Math.max(0, Math.min(index, FISH_DATA.length - 1));
    this.update();
  }

  getActiveIndex(): number { return this.activeIndex; }
  getActiveFish():  FishData { return FISH_DATA[this.activeIndex]; }

  onChange(cb: (fish: FishData) => void): void {
    this.onChangeCallback = cb;
  }

  // ── Swipe (touch + mouse) ─────────────────────────────────────────────────
  private bindSwipe(): void {
    const el = this.container;

    el.addEventListener('touchstart', (e: TouchEvent) => {
      this.startX    = e.touches[0].clientX;
      this.isDragging = true;
    }, { passive: true });

    el.addEventListener('touchend', (e: TouchEvent) => {
      if (!this.isDragging) return;
      const dx = e.changedTouches[0].clientX - this.startX;
      this.handleSwipeEnd(dx);
      this.isDragging = false;
    }, { passive: true });

    el.addEventListener('mousedown', (e: MouseEvent) => {
      this.startX    = e.clientX;
      this.isDragging = true;
      e.preventDefault();
    });

    window.addEventListener('mouseup', (e: MouseEvent) => {
      if (!this.isDragging) return;
      const dx = e.clientX - this.startX;
      this.handleSwipeEnd(dx);
      this.isDragging = false;
    });
  }

  private handleSwipeEnd(dx: number): void {
    const threshold = 42;
    if (dx < -threshold)       this.next();
    else if (dx > threshold)   this.prev();
  }
}
