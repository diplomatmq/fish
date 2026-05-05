import { fetchApi } from '../modules/api';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';
import { normalizeRarity, rarityColor, rarityStars, rarityLabel } from '../modules/rarity';
import { RARITY_COLORS } from '../data';

interface InventoryItem {
  id: number;
  name: string;
  weight: number;
  length: number;
  location: string;
  rarity: string;
  price: number;
  image_url: string;
}

export class ShopScreen {
  private el: HTMLElement;
  private items: InventoryItem[] = [];
  private loading = false;

  constructor() {
    this.el = this.buildShell();
  }

  getElement(): HTMLElement {
    return this.el;
  }

  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id = 'screen-shop';
    s.className = 'screen shop-screen';
    s.setAttribute('role', 'main');

    s.innerHTML = `
      <h1 class="page-title">ЛАВКА</h1>
      <div class="shop-container">
        <div class="shop-tabs">
          <button class="shop-tab-btn is-active" data-tab="inventory">ИНВЕНТАРЬ</button>
          <button class="shop-tab-btn" data-tab="market">РЫНОК (SOON)</button>
        </div>
        
        <div id="shop-content" class="shop-content">
          <div class="loader-wrap"><div class="loader"></div></div>
        </div>
      </div>
    `;
    return s;
  }

  async init(): Promise<void> {
    await this.loadInventory();
    this.bindEvents();
  }

  private bindEvents(): void {
    const tabs = this.el.querySelectorAll('.shop-tab-btn');
    tabs.forEach(btn => {
      btn.addEventListener('click', () => {
        if (btn.classList.contains('is-active')) return;
        tgService.haptic('light');
        tabs.forEach(t => t.classList.remove('is-active'));
        btn.classList.add('is-active');
        const tab = (btn as HTMLElement).dataset['tab'];
        if (tab === 'inventory') this.renderInventory();
        else this.renderMarketSoon();
      });
    });
  }

  private async loadInventory(): Promise<void> {
    this.loading = true;
    try {
      const data = await fetchApi<{ items?: InventoryItem[] }>('/api/inventory');
      this.items = data?.items || [];
      this.renderInventory();
    } catch (e) {
      console.error('Failed to load inventory:', e);
      this.renderError();
    } finally {
      this.loading = false;
    }
  }

  private renderInventory(): void {
    const content = this.el.querySelector('#shop-content')!;
    if (this.items.length === 0) {
      content.innerHTML = `
        <div class="shop-empty">
          <div class="shop-soon-icon">${getIcon('shop')}</div>
          <h3>Садок пуст</h3>
          <p>Поймайте рыбу, чтобы она появилась здесь.</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="inventory-list">
        ${this.items.map(item => {
          const rarityKey = normalizeRarity(item.rarity);
          const color = RARITY_COLORS[rarityKey];
          return `
            <div class="inventory-item glass" style="--accent: ${color}">
              <div class="inv-item-img">
                <img src="${item.image_url}" alt="${item.name}" loading="lazy">
              </div>
              <div class="inv-item-info">
                <div class="inv-item-name">${item.name}</div>
                <div class="inv-item-rarity" style="color: ${color}">${rarityStars(item.rarity)} ${rarityLabel(item.rarity)}</div>
                <div class="inv-item-stats">
                  <span>⚖️ ${item.weight.toFixed(2)} кг</span>
                  <span>📏 ${item.length.toFixed(1)} см</span>
                </div>
              </div>
              <div class="inv-item-price">
                <span class="price-val">${item.price}</span>
                <span class="price-icon">🪙</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private renderMarketSoon(): void {
    const content = this.el.querySelector('#shop-content')!;
    content.innerHTML = `
      <div class="shop-empty">
        <div class="shop-soon-icon">${getIcon('shop')}</div>
        <h3>Рынок скоро откроется!</h3>
        <p>Здесь вы сможете покупать снаряжение, наживку и другие полезные вещи.</p>
      </div>
    `;
  }

  private renderError(): void {
    const content = this.el.querySelector('#shop-content')!;
    content.innerHTML = `
      <div class="shop-empty">
        <div class="shop-soon-icon">❌</div>
        <h3>Ошибка загрузки</h3>
        <p>Не удалось загрузить инвентарь. Попробуйте позже.</p>
      </div>
    `;
  }
}
