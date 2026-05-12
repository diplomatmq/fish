import { fetchApi } from '../modules/api';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';
import { normalizeRarity, rarityColor, rarityStars, rarityLabel } from '../modules/rarity';
import { RARITY_COLORS } from '../data';

interface GroupedInventoryItem {
  ids: number[];
  name: string;
  count: number;
  total_weight: number;
  rarity: string;
  price: number;
  unit_price: number;
  image_url: string;
}

export class ShopScreen {
  private el: HTMLElement;
  private items: GroupedInventoryItem[] = [];
  private loading = false;
  private mode: 'view' | 'select' = 'view';
  private selectedIds: Set<number> = new Set();

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
      <div class="shop-header">
        <h1 class="page-title">ЛАВКА</h1>
        <button id="shop-sell-btn" class="glass-btn primary-btn" style="display:none;">${getIcon('shop')} ПРОДАТЬ</button>
      </div>
      <div class="shop-container">
        <div id="shop-content" class="shop-content">
          <div class="loader-wrap"><div class="loader"></div></div>
        </div>
      </div>
      <div id="shop-select-actions" class="shop-select-actions" style="display:none;">
        <div class="select-info">Выбрано: <span id="select-count">0</span></div>
        <div class="select-buttons">
          <button id="cancel-select-btn" class="glass-btn">ОТМЕНА</button>
          <button id="confirm-sell-btn" class="glass-btn primary-btn">ПРОДАТЬ</button>
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
    const sellBtn = this.el.querySelector('#shop-sell-btn');
    if (sellBtn) {
      sellBtn.addEventListener('click', () => {
        tgService.haptic('light');
        this.showSellModal();
      });
    }

    const cancelBtn = this.el.querySelector('#cancel-select-btn');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        tgService.haptic('light');
        this.mode = 'view';
        this.selectedIds.clear();
        this.renderInventory();
      });
    }

    const confirmBtn = this.el.querySelector('#confirm-sell-btn');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => {
        if (this.selectedIds.size === 0) return;
        tgService.haptic('medium');
        this.sellBulk({ ids: Array.from(this.selectedIds) });
      });
    }
  }

  private showSellModal(): void {
    const content = `
      <div class="sell-options">
        <button class="glass-btn sell-opt-btn" data-cat="all">💰 Продать всю рыбу</button>
        <button class="glass-btn sell-opt-btn" data-cat="trash">🗑 Продать весь мусор</button>
        <button class="glass-btn sell-opt-btn" data-cat="common" style="color:var(--r-common)">Продать все обычные</button>
        <button class="glass-btn sell-opt-btn" data-cat="rare" style="color:var(--r-rare)">Продать все редкие</button>
        <button class="glass-btn sell-opt-btn" data-cat="legendary" style="color:var(--r-legendary)">Продать все легендарные</button>
        <button class="glass-btn sell-opt-btn" data-cat="anomaly" style="color:var(--r-anomaly)">Продать все аномалии</button>
        <button class="glass-btn sell-opt-btn" data-cat="aquarium" style="color:var(--r-aquarium)">Продать все аквариумные</button>
        <button class="glass-btn sell-opt-btn" data-cat="mythic" style="color:var(--r-mythic)">Продать все мифические</button>
        <button class="glass-btn sell-opt-btn select-mode-btn">✅ Выбрать</button>
      </div>
    `;
    
    // Quick modal implementation
    const modal = document.createElement('div');
    modal.className = 'modal-overlay is-open';
    modal.style.display = 'flex';
    modal.innerHTML = `
      <div class="modal-sheet" style="transform:none; bottom:0;">
        <div class="modal-handle"></div>
        <p class="modal-title">ПРОДАЖА РЫБЫ</p>
        <div style="padding:10px;">${content}</div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) document.body.removeChild(modal);
    });
    
    modal.querySelectorAll('.sell-opt-btn').forEach((btn: Element) => {
      btn.addEventListener('click', () => {
        const cat = (btn as HTMLElement).dataset['cat'];
        tgService.haptic('light');
        document.body.removeChild(modal);
        if (cat) {
          this.sellBulk({ category: cat });
        } else if (btn.classList.contains('select-mode-btn')) {
          this.mode = 'select';
          this.selectedIds.clear();
          this.renderInventory();
        }
      });
    });
  }

  private async sellBulk(payload: {category?: string, ids?: number[]}): Promise<void> {
    try {
      const res = await fetchApi<{earned_coins: number, earned_xp: number}>('/api/sell-bulk', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      if (res && res.earned_coins !== undefined) {
        tgService.haptic('success');
        alert(`Успешно продано!\nПолучено: ${res.earned_coins} 🪙\nОпыт: ${res.earned_xp} ✨`);
        this.mode = 'view';
        this.selectedIds.clear();
        await this.loadInventory();
      }
    } catch(e) {
      alert('Ошибка при продаже');
    }
  }

  private async loadInventory(): Promise<void> {
    this.loading = true;
    try {
      const data = await fetchApi<{ items?: GroupedInventoryItem[] }>('/api/inventory/grouped');
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
    const sellBtn = this.el.querySelector('#shop-sell-btn') as HTMLElement;
    const selectActions = this.el.querySelector('#shop-select-actions') as HTMLElement;
    
    if (this.mode === 'select') {
      sellBtn.style.display = 'none';
      selectActions.style.display = 'flex';
      this.updateSelectCount();
    } else {
      sellBtn.style.display = this.items.length > 0 ? 'block' : 'none';
      selectActions.style.display = 'none';
    }

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
      <div class="inventory-grid">
        ${this.items.map((item, idx) => {
          const rarityKey = normalizeRarity(item.rarity);
          const color = RARITY_COLORS[rarityKey] || '#ccc';
          const isSelected = item.ids.every(id => this.selectedIds.has(id));
          const partialSelect = item.ids.some(id => this.selectedIds.has(id)) && !isSelected;
          
          let selectClass = '';
          if (this.mode === 'select') {
            if (isSelected) selectClass = 'is-selected';
            else if (partialSelect) selectClass = 'is-partial';
          }
          
          return `
            <div class="inv-card glass ${selectClass}" style="--card-color: ${color}" data-idx="${idx}">
              ${item.count > 1 ? `<div class="inv-badge">${item.count}x</div>` : ''}
              <div class="inv-img-wrap">
                <img src="${item.image_url}" alt="${item.name}" loading="lazy">
              </div>
              <div class="inv-details">
                <div class="inv-name">${item.name}</div>
                <div class="inv-rarity" style="color:${color}">${rarityLabel(item.rarity)}</div>
                <div class="inv-weight">⚖️ ${item.total_weight.toFixed(2)} кг</div>
              </div>
              <div class="inv-price">
                <span>${item.price}</span> 🪙
              </div>
              ${this.mode === 'select' ? `<div class="select-indicator">${isSelected ? '✅' : ''}</div>` : ''}
            </div>
          `;
        }).join('')}
      </div>
    `;

    // Bind card clicks
    content.querySelectorAll('.inv-card').forEach(card => {
      card.addEventListener('click', () => {
        if (this.mode !== 'select') return;
        tgService.haptic('light');
        const idx = parseInt((card as HTMLElement).dataset['idx'] || '0');
        const item = this.items[idx];
        
        // Toggle all ids for this item group
        const allSelected = item.ids.every(id => this.selectedIds.has(id));
        if (allSelected) {
          item.ids.forEach(id => this.selectedIds.delete(id));
        } else {
          item.ids.forEach(id => this.selectedIds.add(id));
        }
        this.renderInventory();
      });
    });
  }
  
  private updateSelectCount() {
    const countEl = this.el.querySelector('#select-count');
    if (countEl) countEl.textContent = this.selectedIds.size.toString();
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
