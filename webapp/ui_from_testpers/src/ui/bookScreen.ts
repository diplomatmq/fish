// ─────────────────────────────────────────────────────────────────────────────
// BookScreen — Single Page Layout with PageFlip Engine (Turn.js-like)
// ─────────────────────────────────────────────────────────────────────────────
import { ENCYCLOPEDIA, ENCYCLOPEDIA_TOTAL_ALL, type EncyclopediaEntry, loadEncyclopedia } from '../modules/encyclopediaData';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';

const RARITY_LABELS: Record<string, string> = {
  common:    '★★ Обычная',
  rare:      '★★★ Редкая',
  legendary: '★★★★★ Легендарная',
  aquarium:  '★★★★ Аквариумная',
  mythical:  '★★★★★ Мифическая',
  anomaly:   '★★★★★★ Аномалия',
};

export class BookScreen {
  private el: HTMLElement;

  private entries:  EncyclopediaEntry[] = [];
  private filtered: EncyclopediaEntry[] = [];
  private index = 0;
  private loading = false;
  
  private pageFlip: any = null; // St.PageFlip instance

  // DOM
  private bookContainer!: HTMLElement;
  private stBook!: HTMLElement;

  private searchInput!: HTMLInputElement;
  private prevBtn!:    HTMLButtonElement;
  private nextBtn!:    HTMLButtonElement;
  private counterCur!: HTMLElement;
  private counterTot!: HTMLElement;

  constructor() {
    this.el = this.buildShell();
  }

  getElement(): HTMLElement { return this.el; }

  // ═══════════════════════════════════════════════════════════════════════════
  //  BUILD
  // ═══════════════════════════════════════════════════════════════════════════
  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id        = 'screen-book';
    s.className = 'screen book-screen';
    s.setAttribute('role', 'main');

    s.innerHTML = `
      <div class="book-search-wrap">
        <div class="book-search-bar" role="search">
          <span class="search-compass" aria-hidden="true">🧭</span>
          <input id="book-search-input" class="book-search-input" type="search" placeholder="ПОИСК..." autocomplete="off">
          <button class="search-icon-btn" id="book-search-btn"><span class="search-loupe">🔍</span></button>
        </div>
      </div>

      <div class="book-wrap">
        <div class="book-spine"></div>
        <div class="spine-hinge"></div>
        
        <!-- StPageFlip container -->
        <div id="st-book" class="st-book"></div>
      </div>

      <div class="book-nav">
        <button class="book-nav-arrow" id="book-prev-btn"><span class="arrow-ornament">◂</span></button>
        <div class="book-counter">
          <span class="counter-current" id="counter-cur">1</span>
          <span class="counter-sep">/</span>
          <span class="counter-total" id="counter-tot">?</span>
        </div>
        <button class="book-nav-arrow" id="book-next-btn"><span class="arrow-ornament">▸</span></button>
      </div>
    `;
    return s;
  }

  async init(): Promise<void> {
    this.bookContainer = this.el.querySelector<HTMLElement>('.book-wrap')!;
    this.stBook      = this.el.querySelector<HTMLElement>('#st-book')!;
    
    this.searchInput = this.el.querySelector<HTMLInputElement>('#book-search-input')!;
    this.prevBtn     = this.el.querySelector<HTMLButtonElement>('#book-prev-btn')!;
    this.nextBtn     = this.el.querySelector<HTMLButtonElement>('#book-next-btn')!;
    this.counterCur  = this.el.querySelector<HTMLElement>('#counter-cur')!;
    this.counterTot  = this.el.querySelector<HTMLElement>('#counter-tot')!;

    this.loading = true;
    await loadEncyclopedia();
    this.entries = [...ENCYCLOPEDIA];
    this.filtered = [...ENCYCLOPEDIA];
    this.loading = false;

    this.renderPages();
    this.bindEvents();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  HTML PAGE GENERATOR
  // ═══════════════════════════════════════════════════════════════════════════
  private buildPage(e: EncyclopediaEntry): string {
    const isCaught = e.isCaught ?? false;
    return `
      <div class="my-page ${!isCaught ? 'not-caught' : ''}">
        <div class="ph-content parchment">
          <div class="ph-chapter">${e.chapter}</div>
          <div class="ph-chapter-divider"><span class="ph-chapter-rule">✦ · ✦</span></div>

          <div class="ph-fish-block">
            <div class="ph-fish-emoji" style="--glow: ${isCaught ? e.glowColor : '#555'}; filter: ${isCaught ? 'none' : 'grayscale(100%) contrast(50%) brightness(70%)'}">
              ${e.imageUrl ? `<img src="${e.imageUrl}" alt="${e.name}" class="ph-fish-image" loading="lazy">` : getIcon(e.id)}
            </div>
          </div>
          
          <div class="ph-fish-name">${e.name.toUpperCase()}</div>
          <div class="ph-fish-latin">${e.latinName}</div>
          
          <div class="ph-rarity-wrap">
            <div class="ph-rarity" style="color:${isCaught ? e.glowColor : '#777'}; border-color:${isCaught ? e.glowColor : '#777'}55">
              ${isCaught ? RARITY_LABELS[e.rarity] : '<span style="color: #ff4d4d; font-weight: bold;">НЕ СЛОВЛЕНА</span>'}
            </div>
          </div>

          <div class="ph-stats">
            <div class="ph-stat"><span>🌊 Глуб</span><strong>${e.depth}</strong></div>
            <div class="ph-stat"><span>📏 Длина</span><strong>${e.length}</strong></div>
            <div class="ph-stat"><span>📍 Среда</span><strong>${e.habitat}</strong></div>
          </div>

          <p class="ph-desc">${e.description}</p>
          
          ${isCaught ? `
          <div class="ph-funfact">
            <div class="ph-ff-head">💡 Факт</div>
            <div class="ph-ff-body">${e.funFact}</div>
          </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  private renderPages(): void {
    if (this.pageFlip) {
      this.pageFlip.destroy();
      this.pageFlip = null;
    }

    // Полностью пересоздаем контейнер книги, чтобы плагин не ломался от остаточных стилей после destroy()
    const oldStBook = this.el.querySelector('#st-book');
    if (oldStBook) {
      oldStBook.remove();
    }

    this.stBook = document.createElement('div');
    this.stBook.id = 'st-book';
    this.stBook.className = 'st-book';
    this.bookContainer.appendChild(this.stBook);

    if (this.filtered.length === 0) return;

    this.stBook.innerHTML = this.filtered.map(e => this.buildPage(e)).join('');
    
    // Initialize StPageFlip
    // @ts-ignore
    if (window.St && window.St.PageFlip) {
      // @ts-ignore
      this.pageFlip = new window.St.PageFlip(this.stBook, {
        width: 320, 
        height: 480,
        size: 'stretch',
        minWidth: 280,
        maxWidth: 600,
        minHeight: 400,
        maxHeight: 900,
        usePortrait: true,
        showCover: false,
        useMouseEvents: false, // Отключаем встроенный drag (чтобы наш кастомный свайп всегда работал чётко)
        maxShadowOpacity: 0.7,
        mobileScrollSupport: false,
        flippingTime: 600
      });
      
      this.pageFlip.loadFromHTML(this.stBook.querySelectorAll('.my-page'));
      
      this.pageFlip.on('flip', (e: any) => {
        this.index = e.data;
        this.syncUI();
      });
      
      this.pageFlip.on('changeState', (e: any) => {
         if (e.data === 'flipping') tgService.haptic('light');
      });
    }

    this.index = 0;
    this.syncUI();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  UI & EVENTS
  // ═══════════════════════════════════════════════════════════════════════════
  private syncUI(): void {
    this.counterCur.textContent = String(this.index + 1);
    this.counterTot.textContent = String(Math.max(this.filtered.length, ENCYCLOPEDIA_TOTAL_ALL || 0));
    this.prevBtn.disabled = this.index === 0;
    this.nextBtn.disabled = this.index === this.filtered.length - 1;
  }

  private applySearch(query: string): void {
    const q = query.trim().toLowerCase();
    this.filtered = q
      ? this.entries.filter(e =>
          e.name.toLowerCase().includes(q)      ||
          e.latinName.toLowerCase().includes(q) ||
          e.description.toLowerCase().includes(q)
        )
      : [...this.entries];

    if (!this.filtered.length) this.filtered = [...this.entries];
    this.renderPages();
  }

  private bindEvents(): void {
    this.prevBtn.addEventListener('click', () => {
      if (this.pageFlip && this.index > 0) this.pageFlip.flipPrev();
    });
    this.nextBtn.addEventListener('click', () => {
      if (this.pageFlip && this.index < this.filtered.length - 1) this.pageFlip.flipNext();
    });

    // ─────────────────────────────────────────────────────────────────
    // Свайпы для перелистывания (Swipe gestures)
    // Вешаем на bookContainer, чтобы они работали даже после пересоздания st-book
    // ─────────────────────────────────────────────────────────────────
    let startX = 0;
    let startY = 0;

    this.bookContainer.addEventListener('pointerdown', (e: PointerEvent) => {
      startX = e.clientX;
      startY = e.clientY;
    }, { passive: true });

    this.bookContainer.addEventListener('pointerup', (e: PointerEvent) => {
      // Не обрабатывать свайп, если страница уже перелистывается плагином PageFlip
      if (this.pageFlip && this.pageFlip.getState() !== 'read') {
        return;
      }

      const endX = e.clientX;
      const endY = e.clientY;

      const deltaX = startX - endX;
      const deltaY = Math.abs(startY - endY);

      // Проверяем, что это акцентированный горизонтальный свайп
      if (Math.abs(deltaX) > 40 && deltaY < 60) {
        if (deltaX > 0) {
          // Свайп влево (Справа налево) -> Следующая страница
          if (this.pageFlip && this.index < this.filtered.length - 1) {
            this.pageFlip.flipNext();
          }
        } else {
          // Свайп вправо (Слева направо) -> Предыдущая страница
          if (this.pageFlip && this.index > 0) {
            this.pageFlip.flipPrev();
          }
        }
      }
    }, { passive: true });

    // Поиск только по нажатию Enter или клику на кнопку
    this.searchInput.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.applySearch(this.searchInput.value);
      }
    });

    const searchBtn = this.el.querySelector<HTMLButtonElement>('#book-search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', () => {
        this.applySearch(this.searchInput.value);
      });
    }
  }
}
