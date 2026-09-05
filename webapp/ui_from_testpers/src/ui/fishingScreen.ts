// ─────────────────────────────────────────────────────────────────────────────
// FishingScreen — Full-featured fishing interface with slots, location selection
// ─────────────────────────────────────────────────────────────────────────────
import { tgService } from '../modules/telegram';
import { apiService } from '../modules/api';
import { tonConnectService } from '../modules/tonConnect';

export class FishingScreen {
  private el: HTMLElement;
  private currentLocation: string = 'Городской пруд';
  private isSpinning: boolean = false;
  private cooldownEndTime: number = 0;
  private cooldownInterval: any = null;
  private starsBalance: number = 0;
  private tonBalance: number = 0;
  private selectedCurrency: 'stars' | 'ton' = 'stars';

  constructor() {
    this.el = this.build();
  }

  private build(): HTMLElement {
    const screen = document.createElement('div');
    screen.id = 'screen-fishing';
    screen.className = 'screen fishing-screen';
    screen.innerHTML = `
      <div class="fishing-container">
        <!-- Header with balance and back button -->
        <div class="fishing-header">
          <button class="fishing-back-btn" id="fishing-back-btn">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          
          <div class="fishing-balance-container">
            <button class="fishing-balance-btn" id="balance-toggle-btn">
              <div class="balance-icon stars-icon">⭐</div>
              <div class="balance-value" id="balance-value">0</div>
              <div class="balance-arrow">▼</div>
            </button>
            
            <div class="balance-dropdown" id="balance-dropdown">
              <div class="balance-option" data-currency="stars">
                <span class="balance-opt-icon">⭐</span>
                <span class="balance-opt-label">Звезды</span>
                <span class="balance-opt-value" id="stars-balance-opt">0</span>
              </div>
              <button class="balance-action-btn" id="topup-stars-btn">
                Пополнить звезды
              </button>
              
              <div class="balance-divider"></div>
              
              <div class="balance-option" data-currency="ton">
                <span class="balance-opt-icon">💎</span>
                <span class="balance-opt-label">TON</span>
                <span class="balance-opt-value" id="ton-balance-opt">0.00</span>
              </div>
              <button class="balance-action-btn" id="topup-ton-btn">
                Пополнить TON
              </button>
            </div>
          </div>
        </div>

        <!-- Slot machine area -->
        <div class="fishing-slots">
          <div class="slot-reel" id="slot-reel-1">
            <div class="slot-symbol">🐟</div>
          </div>
          <div class="slot-reel" id="slot-reel-2">
            <div class="slot-symbol">🦈</div>
          </div>
          <div class="slot-reel" id="slot-reel-3">
            <div class="slot-symbol">🐠</div>
          </div>
        </div>

        <!-- Fish button -->
        <button class="fishing-fish-btn" id="fishing-fish-btn">
          <span class="fish-btn-text">FISH</span>
          <span class="fish-btn-cooldown" id="fish-btn-cooldown" style="display: none;"></span>
        </button>

        <!-- Location selector -->
        <div class="fishing-locations">
          <button class="location-btn location-btn--active" data-location="Городской пруд">
            🏞️ Городской пруд
          </button>
          <button class="location-btn" data-location="Река">
            🌊 Река
          </button>
          <button class="location-btn" data-location="Озеро">
            🏔️ Озеро
          </button>
          <button class="location-btn" data-location="Море">
            🌅 Море
          </button>
        </div>

        <!-- Boat status -->
        <div class="fishing-boat-status" id="boat-status">
          <div class="boat-icon">🚣</div>
          <div class="boat-text">На берегу</div>
        </div>
      </div>

      <!-- Top-up modal -->
      <div class="topup-modal" id="topup-modal">
        <div class="topup-content">
          <button class="topup-close" id="topup-close">&times;</button>
          <h3 class="topup-title" id="topup-title">Пополнить баланс</h3>
          <input type="number" class="topup-input" id="topup-amount" placeholder="Введите сумму" min="1" />
          <button class="topup-pay-btn" id="topup-pay-btn">Оплатить</button>
        </div>
      </div>
    `;

    return screen;
  }

  async init(): Promise<void> {
    // Initialize TON Connect
    await tonConnectService.init();

    // Bind events
    const backBtn = this.el.querySelector('#fishing-back-btn') as HTMLButtonElement;
    const balanceToggleBtn = this.el.querySelector('#balance-toggle-btn') as HTMLButtonElement;
    const balanceDropdown = this.el.querySelector('#balance-dropdown') as HTMLElement;
    const fishBtn = this.el.querySelector('#fishing-fish-btn') as HTMLButtonElement;
    const locationBtns = this.el.querySelectorAll('.location-btn') as NodeListOf<HTMLButtonElement>;
    const topupStarsBtn = this.el.querySelector('#topup-stars-btn') as HTMLButtonElement;
    const topupTonBtn = this.el.querySelector('#topup-ton-btn') as HTMLButtonElement;
    const topupModal = this.el.querySelector('#topup-modal') as HTMLElement;
    const topupClose = this.el.querySelector('#topup-close') as HTMLButtonElement;
    const topupPayBtn = this.el.querySelector('#topup-pay-btn') as HTMLButtonElement;

    // Back button
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        tgService.haptic('light');
        window.dispatchEvent(new CustomEvent('navigate-home'));
      });
    }

    // Balance toggle
    if (balanceToggleBtn && balanceDropdown) {
      balanceToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        tgService.haptic('selection');
        balanceDropdown.classList.toggle('visible');
      });

      // Close dropdown on outside click
      document.addEventListener('click', (e) => {
        if (!balanceToggleBtn.contains(e.target as Node) && !balanceDropdown.contains(e.target as Node)) {
          balanceDropdown.classList.remove('visible');
        }
      });

      // Currency selection
      const currencyOptions = balanceDropdown.querySelectorAll('.balance-option');
      currencyOptions.forEach(option => {
        option.addEventListener('click', () => {
          const currency = option.getAttribute('data-currency') as 'stars' | 'ton';
          this.selectCurrency(currency);
          tgService.haptic('selection');
        });
      });
    }

    // Fish button
    if (fishBtn) {
      fishBtn.addEventListener('click', () => {
        if (!this.isSpinning && this.cooldownEndTime === 0) {
          tgService.haptic('medium');
          this.fish();
        } else if (this.cooldownEndTime > 0) {
          // Cooldown active - offer guaranteed catch
          tgService.haptic('light');
          this.fish(); // Will handle guaranteed catch inside
        }
      });
    }

    // Location buttons
    locationBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const location = btn.getAttribute('data-location') || 'Городской пруд';
        this.selectLocation(location);
        tgService.haptic('selection');
      });
    });

    // Top-up buttons
    if (topupStarsBtn) {
      topupStarsBtn.addEventListener('click', () => {
        this.openTopupModal('stars');
      });
    }

    if (topupTonBtn) {
      topupTonBtn.addEventListener('click', () => {
        this.openTopupModal('ton');
      });
    }

    // Top-up modal close
    if (topupClose) {
      topupClose.addEventListener('click', () => {
        this.closeTopupModal();
      });
    }

    // Top-up payment
    if (topupPayBtn) {
      topupPayBtn.addEventListener('click', () => {
        this.processTopup();
      });
    }

    // Load initial data
    await this.loadPlayerData();
    
    // Check for active cooldown
    await this.checkCooldown();
  }

  private async loadPlayerData(): Promise<void> {
    try {
      const profile = await apiService.getProfile();
      if (profile) {
        this.starsBalance = profile.stars || 0;
        this.tonBalance = profile.ton_balance || 0;
        this.currentLocation = profile.current_location || 'Городской пруд';
        
        this.updateBalanceDisplay();
        this.selectLocation(this.currentLocation);
        
        // Update boat status
        this.updateBoatStatus(profile.is_on_boat || false);
      }
    } catch (error) {
      console.error('Failed to load player data:', error);
    }
  }

  private async checkCooldown(): Promise<void> {
    try {
      const cooldownData = await apiService.checkCooldown();
      if (cooldownData && cooldownData.cooldown_remaining > 0) {
        this.startCooldown(cooldownData.cooldown_remaining);
      }
    } catch (error) {
      console.error('Failed to check cooldown:', error);
    }
  }

  private updateBoatStatus(isOnBoat: boolean): void {
    const boatStatus = this.el.querySelector('#boat-status') as HTMLElement;
    if (!boatStatus) return;

    const boatIcon = boatStatus.querySelector('.boat-icon') as HTMLElement;
    const boatText = boatStatus.querySelector('.boat-text') as HTMLElement;

    if (isOnBoat) {
      if (boatIcon) boatIcon.textContent = '⛵';
      if (boatText) boatText.textContent = 'В лодке';
      boatStatus.style.borderColor = 'rgba(244, 168, 46, 0.5)';
    } else {
      if (boatIcon) boatIcon.textContent = '🚣';
      if (boatText) boatText.textContent = 'На берегу';
      boatStatus.style.borderColor = 'rgba(72, 202, 228, 0.3)';
    }
  }

  private selectCurrency(currency: 'stars' | 'ton'): void {
    this.selectedCurrency = currency;
    this.updateBalanceDisplay();
  }

  private updateBalanceDisplay(): void {
    const balanceValue = this.el.querySelector('#balance-value') as HTMLElement;
    const balanceIcon = this.el.querySelector('.balance-icon') as HTMLElement;
    const starsBalanceOpt = this.el.querySelector('#stars-balance-opt') as HTMLElement;
    const tonBalanceOpt = this.el.querySelector('#ton-balance-opt') as HTMLElement;

    if (this.selectedCurrency === 'stars') {
      balanceValue.textContent = this.starsBalance.toString();
      balanceIcon.textContent = '⭐';
      balanceIcon.className = 'balance-icon stars-icon';
    } else {
      balanceValue.textContent = this.tonBalance.toFixed(2);
      balanceIcon.textContent = '💎';
      balanceIcon.className = 'balance-icon ton-icon';
    }

    if (starsBalanceOpt) starsBalanceOpt.textContent = this.starsBalance.toString();
    if (tonBalanceOpt) tonBalanceOpt.textContent = this.tonBalance.toFixed(2);
  }

  private selectLocation(location: string): void {
    this.currentLocation = location;
    
    // Update button states
    const locationBtns = this.el.querySelectorAll('.location-btn') as NodeListOf<HTMLButtonElement>;
    locationBtns.forEach(btn => {
      if (btn.getAttribute('data-location') === location) {
        btn.classList.add('location-btn--active');
      } else {
        btn.classList.remove('location-btn--active');
      }
    });

    // Save to API
    apiService.updateLocation(location).catch(err => {
      console.error('Failed to update location:', err);
    });
  }

  private async fish(): Promise<void> {
    if (this.isSpinning) return;

    // Check if cooldown is active and user wants guaranteed catch
    if (this.cooldownEndTime > 0) {
      const guaranteed = await this.confirmGuaranteedCatch();
      if (!guaranteed) return;

      // Process payment and guaranteed catch
      const paymentSuccess = await this.processGuaranteedPayment();
      if (!paymentSuccess) return;
    }

    this.isSpinning = true;
    const fishBtn = this.el.querySelector('#fishing-fish-btn') as HTMLButtonElement;
    fishBtn.classList.add('disabled');

    // Start slot animation
    this.spinSlots();

    try {
      // Call API with guaranteed flag if cooldown was active
      const guaranteed = this.cooldownEndTime > 0;
      const result = await apiService.fish(this.currentLocation, guaranteed);
      
      if (result.success) {
        // Show fish result
        await this.showFishResult(result);
        
        // Start cooldown (10 minutes = 600 seconds)
        this.startCooldown(600);
        
        // Reload balance
        await this.loadPlayerData();
      } else if (result.cooldown_remaining) {
        this.startCooldown(result.cooldown_remaining);
      } else if (result.error) {
        tgService.showAlert(`Ошибка: ${result.error}`);
      }
    } catch (error) {
      console.error('Fishing failed:', error);
      tgService.showAlert('Ошибка при ловле рыбы');
    } finally {
      this.isSpinning = false;
      if (this.cooldownEndTime === 0) {
        fishBtn.classList.remove('disabled');
      }
    }
  }

  private async confirmGuaranteedCatch(): Promise<boolean> {
    const currency = this.selectedCurrency === 'stars' ? 'звезду' : '0.01 TON';
    const message = `Кулдаун активен. Хотите потратить ${currency} на гарантированный улов?`;
    
    return new Promise((resolve) => {
      if (confirm(message)) {
        resolve(true);
      } else {
        resolve(false);
      }
    });
  }

  private async processGuaranteedPayment(): Promise<boolean> {
    try {
      if (this.selectedCurrency === 'stars') {
        // Check stars balance
        if (this.starsBalance < 1) {
          tgService.showAlert('Недостаточно звезд. Пополните баланс.');
          return false;
        }
        // Stars will be deducted by backend
        return true;
      } else {
        // TON payment
        if (this.tonBalance < 0.01) {
          tgService.showAlert('Недостаточно TON. Пополните баланс.');
          return false;
        }
        
        // Send TON transaction
        const result = await tonConnectService.sendTransaction(0.01, 'Guaranteed Fish');
        
        if (!result.success) {
          tgService.showAlert(`Ошибка оплаты: ${result.error || 'Неизвестная ошибка'}`);
          return false;
        }
        
        // Deduct from local balance (will be synced with backend)
        this.tonBalance -= 0.01;
        this.updateBalanceDisplay();
        
        return true;
      }
    } catch (error) {
      console.error('Payment failed:', error);
      tgService.showAlert('Ошибка при обработке платежа');
      return false;
    }
  }

  private spinSlots(): void {
    const reels = [
      this.el.querySelector('#slot-reel-1'),
      this.el.querySelector('#slot-reel-2'),
      this.el.querySelector('#slot-reel-3')
    ];

    const symbols = ['🐟', '🦈', '🐠', '🐡', '🦑', '🦐', '🦞', '🐙', '🗑️', '❌'];

    reels.forEach((reel, index) => {
      if (!reel) return;
      
      let spinCount = 0;
      const maxSpins = 20 + index * 5;
      
      const spinInterval = setInterval(() => {
        const randomSymbol = symbols[Math.floor(Math.random() * symbols.length)];
        const symbolEl = reel.querySelector('.slot-symbol');
        if (symbolEl) {
          symbolEl.textContent = randomSymbol;
          symbolEl.classList.add('spinning');
        }
        
        spinCount++;
        if (spinCount >= maxSpins) {
          clearInterval(spinInterval);
          if (symbolEl) {
            symbolEl.classList.remove('spinning');
          }
        }
      }, 100);
    });
  }

  private async showFishResult(result: any): Promise<void> {
    const reels = [
      this.el.querySelector('#slot-reel-1'),
      this.el.querySelector('#slot-reel-2'),
      this.el.querySelector('#slot-reel-3')
    ];

    // Determine symbols based on result
    let symbols: string[] = [];
    let fishImageUrl: string | null = null;
    
    if (result.fish) {
      const raritySymbols: Record<string, string> = {
        'Обычная': '🐟',
        'Редкая': '🦈',
        'Легендарная': '🐡',
        'Мифическая': '🦑',
        'Аномалия': '🐙',
        'Аквариумная': '🐠'
      };
      const symbol = raritySymbols[result.fish.rarity] || '🐟';
      symbols = [symbol, symbol, symbol];
      
      // Get fish image URL
      fishImageUrl = result.fish.image_url || `/api/fish-image/${result.fish.sticker_id || result.fish.name}.webp`;
    } else if (result.is_trash) {
      symbols = ['🗑️', '🗑️', '🗑️'];
      if (result.trash) {
        fishImageUrl = `/api/fish-image/${result.trash.sticker_id || result.trash.name}.webp`;
      }
    } else if (result.no_bite) {
      symbols = ['❌', '❌', '❌'];
    } else if (result.fish_inspector) {
      symbols = ['👮', '👮', '👮'];
    } else if (result.snap) {
      symbols = ['💔', '💔', '💔'];
    }

    // Set final symbols
    reels.forEach((reel, index) => {
      if (!reel) return;
      const symbolEl = reel.querySelector('.slot-symbol');
      if (symbolEl) {
        symbolEl.textContent = symbols[index] || '❓';
      }
    });

    // Show result message with image
    setTimeout(() => {
      let message = '';
      
      if (result.fish_inspector) {
        message = result.message || '🚨 Рыбнадзор конфисковал улов!';
        tgService.showAlert(message);
      } else if (result.snap) {
        message = result.message || '💔 Рыба сорвалась!';
        tgService.showAlert(message);
      } else if (result.fish) {
        message = `🎣 Поймана рыба!\n\n${result.fish.name}\n`;
        message += `Вес: ${result.weight}кг\n`;
        message += `Длина: ${result.length || 0}см\n`;
        message += `Редкость: ${result.fish.rarity}\n`;
        
        if (result.xp_earned) {
          message += `\n+${result.xp_earned} опыта`;
        }
        
        // Show with image if available
        if (fishImageUrl) {
          this.showFishModal(result.fish.name, result.weight, result.length, result.fish.rarity, fishImageUrl, message);
        } else {
          tgService.showAlert(message);
        }
      } else if (result.is_trash) {
        const trashName = result.trash?.name || 'Мусор';
        message = `🗑️ Выловлен мусор: ${trashName}`;
        
        if (result.treasure_caught) {
          message += `\n\n💎 Бонус! Найдено сокровище: ${result.treasure_name}`;
        }
        
        if (fishImageUrl) {
          this.showFishModal(trashName, result.trash?.weight || 0, 0, 'Мусор', fishImageUrl, message);
        } else {
          tgService.showAlert(message);
        }
      } else if (result.no_bite) {
        message = result.message || '❌ Рыба не клюет...';
        tgService.showAlert(message);
      }
      
      // Show special events
      if (result.spawn_event_active) {
        setTimeout(() => {
          tgService.showAlert('🐟 На локации активен нерест! Повышенный шанс улова!');
        }, 1500);
      }
      
      if (result.murder_event_active && result.murder_fish_name) {
        setTimeout(() => {
          tgService.showAlert(`☠️ На локации объявлена охота на ${result.murder_fish_name}!`);
        }, 1500);
      }
      
      if (result.school_event_active && result.school_bonus_percent > 0) {
        setTimeout(() => {
          tgService.showAlert(`🐠 Стайный инстинкт! Бонус к весу: +${result.school_bonus_percent}% (цепочка: ${result.school_chain_count})`);
        }, 1500);
      }
    }, 500);
  }

  private showFishModal(name: string, _weight: number, _length: number, _rarity: string, imageUrl: string, message: string): void {
    // Create modal for fish result with image
    const modal = document.createElement('div');
    modal.className = 'fish-result-modal';
    modal.innerHTML = `
      <div class="fish-result-content">
        <button class="fish-result-close" id="fish-result-close">&times;</button>
        <div class="fish-result-image-container">
          <img src="${imageUrl}" alt="${name}" class="fish-result-image" onerror="this.src='/api/fish-image/fishdef.webp'" />
        </div>
        <div class="fish-result-info">
          <h3 class="fish-result-name">${name}</h3>
          <p class="fish-result-details">${message}</p>
        </div>
        <button class="fish-result-ok-btn" id="fish-result-ok">OK</button>
      </div>
    `;
    
    this.el.appendChild(modal);
    
    // Show with animation
    requestAnimationFrame(() => {
      modal.classList.add('visible');
    });
    
    // Close handlers
    const closeBtn = modal.querySelector('#fish-result-close') as HTMLButtonElement;
    const okBtn = modal.querySelector('#fish-result-ok') as HTMLButtonElement;
    
    const closeModal = () => {
      modal.classList.remove('visible');
      setTimeout(() => {
        modal.remove();
      }, 300);
    };
    
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (okBtn) okBtn.addEventListener('click', closeModal);
    
    tgService.haptic('success');
  }

  private startCooldown(seconds: number): void {
    this.cooldownEndTime = Date.now() + seconds * 1000;
    
    const fishBtn = this.el.querySelector('#fishing-fish-btn') as HTMLButtonElement;
    const cooldownEl = this.el.querySelector('#fish-btn-cooldown') as HTMLElement;
    const textEl = this.el.querySelector('.fish-btn-text') as HTMLElement;

    if (fishBtn) fishBtn.classList.add('disabled');
    if (textEl) textEl.style.display = 'none';
    if (cooldownEl) cooldownEl.style.display = 'block';

    this.cooldownInterval = setInterval(() => {
      const remaining = Math.max(0, Math.floor((this.cooldownEndTime - Date.now()) / 1000));
      
      if (remaining <= 0) {
        this.stopCooldown();
      } else {
        const minutes = Math.floor(remaining / 60);
        const secs = remaining % 60;
        if (cooldownEl) {
          cooldownEl.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
      }
    }, 1000);
  }

  private stopCooldown(): void {
    if (this.cooldownInterval) {
      clearInterval(this.cooldownInterval);
      this.cooldownInterval = null;
    }

    this.cooldownEndTime = 0;

    const fishBtn = this.el.querySelector('#fishing-fish-btn') as HTMLButtonElement;
    const cooldownEl = this.el.querySelector('#fish-btn-cooldown') as HTMLElement;
    const textEl = this.el.querySelector('.fish-btn-text') as HTMLElement;

    if (fishBtn) fishBtn.classList.remove('disabled');
    if (textEl) textEl.style.display = 'block';
    if (cooldownEl) cooldownEl.style.display = 'none';
  }

  private openTopupModal(currency: 'stars' | 'ton'): void {
    const modal = this.el.querySelector('#topup-modal') as HTMLElement;
    const title = this.el.querySelector('#topup-title') as HTMLElement;
    const amountInput = this.el.querySelector('#topup-amount') as HTMLInputElement;

    if (title) {
      title.textContent = currency === 'stars' ? 'Пополнить звезды' : 'Пополнить TON';
    }

    if (amountInput) {
      amountInput.value = '';
      amountInput.setAttribute('data-currency', currency);
    }

    if (modal) {
      modal.classList.add('visible');
    }

    tgService.haptic('light');
  }

  private closeTopupModal(): void {
    const modal = this.el.querySelector('#topup-modal') as HTMLElement;
    if (modal) {
      modal.classList.remove('visible');
    }
    tgService.haptic('light');
  }

  private async processTopup(): Promise<void> {
    const amountInput = this.el.querySelector('#topup-amount') as HTMLInputElement;
    const currency = amountInput.getAttribute('data-currency') as 'stars' | 'ton';
    const amount = parseFloat(amountInput.value);

    if (!amount || amount <= 0) {
      tgService.showAlert('Введите корректную сумму');
      return;
    }

    try {
      if (currency === 'stars') {
        // Use Telegram Stars payment
        // This should call backend API that creates invoice
        const result = await apiService.createStarsInvoice(amount);
        if (result.invoice_link) {
          // Open Telegram invoice
          window.open(result.invoice_link, '_blank');
          this.closeTopupModal();
        } else {
          tgService.showAlert('Ошибка создания счета');
        }
      } else {
        // TON payment
        if (!tonConnectService.isConnected()) {
          const connected = await tonConnectService.connect();
          if (!connected) {
            tgService.showAlert('Не удалось подключить кошелек');
            return;
          }
        }

        // Send transaction
        const result = await tonConnectService.sendTransaction(amount, `TopUp:TON:${Date.now()}`);
        
        if (result.success) {
          // Update balance locally
          this.tonBalance += amount;
          this.updateBalanceDisplay();
          
          // Notify backend
          await apiService.confirmTonTopup(amount);
          
          tgService.showAlert(`✅ Баланс пополнен на ${amount} TON`);
          this.closeTopupModal();
        } else {
          tgService.showAlert(`Ошибка оплаты: ${result.error || 'Неизвестная ошибка'}`);
        }
      }
    } catch (error) {
      console.error('Top-up failed:', error);
      tgService.showAlert('Ошибка оплаты');
    }
  }

  getElement(): HTMLElement {
    return this.el;
  }
}
