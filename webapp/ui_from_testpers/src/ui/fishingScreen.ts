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
  private playerLevel: number = 0;

  // Location requirements
  private readonly LOCATIONS: Array<{name: string, icon: string, minLevel: number}> = [
    { name: 'Городской пруд', icon: '🏞️', minLevel: 0 },
    { name: 'Река', icon: '🌊', minLevel: 0 },
    { name: 'Озеро', icon: '🏔️', minLevel: 0 },
    { name: 'Море', icon: '🌅', minLevel: 0 },
    { name: 'Коралловый риф', icon: '🪸', minLevel: 5 },
    { name: 'Глубоководный желоб', icon: '🌊', minLevel: 8 },
    { name: 'Мангровые заросли', icon: '🌴', minLevel: 10 },
  ];

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

        <!-- Current location display -->
        <div class="fishing-current-location" id="current-location-display">
          <span class="location-icon">🏞️</span>
          <span class="location-name">Городской пруд</span>
        </div>

        <!-- Single slot reel -->
        <div class="fishing-slots">
          <div class="slot-reel-single" id="slot-reel">
            <img src="/api/fish-image/fishdef.webp" alt="Fish" class="slot-image" />
          </div>
        </div>

        <!-- Fish button -->
        <button class="fishing-fish-btn" id="fishing-fish-btn">
          <span class="fish-btn-text">FISH</span>
          <span class="fish-btn-cooldown" id="fish-btn-cooldown" style="display: none;"></span>
        </button>

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

      <!-- Location selection modal -->
      <div class="location-modal" id="location-modal">
        <div class="location-modal-content">
          <button class="location-modal-close" id="location-modal-close">&times;</button>
          <h3 class="location-modal-title">Выбор локации</h3>
          <div class="location-list" id="location-list"></div>
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
    const topupStarsBtn = this.el.querySelector('#topup-stars-btn') as HTMLButtonElement;
    const topupTonBtn = this.el.querySelector('#topup-ton-btn') as HTMLButtonElement;
    const topupModal = this.el.querySelector('#topup-modal') as HTMLElement;
    const topupClose = this.el.querySelector('#topup-close') as HTMLButtonElement;
    const topupPayBtn = this.el.querySelector('#topup-pay-btn') as HTMLButtonElement;
    const locationDisplay = this.el.querySelector('#current-location-display') as HTMLElement;
    const locationModal = this.el.querySelector('#location-modal') as HTMLElement;
    const locationModalClose = this.el.querySelector('#location-modal-close') as HTMLButtonElement;

    // Back button
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        tgService.haptic('light');
        window.dispatchEvent(new CustomEvent('navigate-home'));
      });
    }

    // Location click - open modal
    if (locationDisplay) {
      locationDisplay.addEventListener('click', () => {
        tgService.haptic('selection');
        this.openLocationModal();
      });
    }

    // Location modal close
    if (locationModalClose) {
      locationModalClose.addEventListener('click', () => {
        this.closeLocationModal();
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
        this.playerLevel = profile.level || 0;
        
        this.updateBalanceDisplay();
        this.updateLocationDisplay();
        
        // Update boat status
        this.updateBoatStatus(profile.is_on_boat || false);
      }
    } catch (error) {
      console.error('Failed to load player data:', error);
    }
  }

  private updateLocationDisplay(): void {
    const locationDisplay = this.el.querySelector('#current-location-display') as HTMLElement;
    const locationName = locationDisplay?.querySelector('.location-name') as HTMLElement;
    const locationIcon = locationDisplay?.querySelector('.location-icon') as HTMLElement;
    
    if (locationName) {
      locationName.textContent = this.currentLocation;
    }
    
    // Set appropriate icon
    if (locationIcon) {
      const loc = this.LOCATIONS.find(l => l.name === this.currentLocation);
      locationIcon.textContent = loc?.icon || '🏞️';
    }
  }

  private openLocationModal(): void {
    const modal = this.el.querySelector('#location-modal') as HTMLElement;
    const locationList = this.el.querySelector('#location-list') as HTMLElement;
    
    if (!locationList) return;
    
    // Clear and rebuild location list
    locationList.innerHTML = '';
    
    this.LOCATIONS.forEach(location => {
      const isLocked = this.playerLevel < location.minLevel;
      const isCurrent = location.name === this.currentLocation;
      
      const btn = document.createElement('button');
      btn.className = `location-modal-btn ${isCurrent ? 'location-modal-btn--active' : ''} ${isLocked ? 'location-modal-btn--locked' : ''}`;
      btn.innerHTML = `
        <span class="location-modal-icon">${location.icon}</span>
        <span class="location-modal-name">${location.name}</span>
        ${isLocked ? `<span class="location-modal-lock">🔒 ${location.minLevel} ур.</span>` : ''}
        ${isCurrent ? '<span class="location-modal-check">✓</span>' : ''}
      `;
      
      if (!isLocked) {
        btn.addEventListener('click', () => {
          this.selectLocation(location.name);
          this.closeLocationModal();
          tgService.haptic('selection');
        });
      } else {
        btn.addEventListener('click', () => {
          tgService.showAlert(`Локация "${location.name}" откроется на ${location.minLevel} уровне. Ваш уровень: ${this.playerLevel}`);
          tgService.haptic('error');
        });
      }
      
      locationList.appendChild(btn);
    });
    
    if (modal) {
      modal.classList.add('visible');
    }
    
    tgService.haptic('light');
  }

  private closeLocationModal(): void {
    const modal = this.el.querySelector('#location-modal') as HTMLElement;
    if (modal) {
      modal.classList.remove('visible');
    }
    tgService.haptic('light');
  }

  private async selectLocation(location: string): Promise<void> {
    this.currentLocation = location;
    this.updateLocationDisplay();
    
    // Save to API
    try {
      await apiService.updateLocation(location);
    } catch (error) {
      console.error('Failed to update location:', error);
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

  private spinSlots(): void {
    const reel = this.el.querySelector('#slot-reel') as HTMLElement;
    const slotImage = reel?.querySelector('.slot-image') as HTMLImageElement;
    
    if (!slotImage) return;

    // Массив случайных рыб для анимации
    const fishImages = [
      'amur_gudgeon.webp',
      'carp.webp',
      'pike.webp',
      'perch.webp',
      'catfish.webp',
      'salmon.webp',
      'trout.webp',
      'tuna.webp',
      'shark.webp',
      'octopus.webp',
      'jellyfish.webp',
      'boot.webp',
      'bottle.webp',
      'can.webp'
    ];

    let spinCount = 0;
    const maxSpins = 30;
    
    reel.classList.add('spinning');
    
    const spinInterval = setInterval(() => {
      const randomFish = fishImages[Math.floor(Math.random() * fishImages.length)];
      slotImage.src = `/api/fish-image/${randomFish}`;
      slotImage.classList.add('spinning');
      
      spinCount++;
      if (spinCount >= maxSpins) {
        clearInterval(spinInterval);
        slotImage.classList.remove('spinning');
        reel.classList.remove('spinning');
      }
    }, 100);
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

  private async showFishResult(result: any): Promise<void> {
    const reel = this.el.querySelector('#slot-reel') as HTMLElement;
    const slotImage = reel?.querySelector('.slot-image') as HTMLImageElement;

    // Determine final image based on result
    let fishImageUrl: string | null = null;
    let detailsMessage = '';
    
    if (result.fish) {
      fishImageUrl = result.fish.image_url || `/api/fish-image/${result.fish.sticker_id || result.fish.name}.webp`;
      
      // Build detailed message like in bot
      detailsMessage = `🎣 Поймана рыба!\n\n`;
      detailsMessage += `🐟 ${result.fish.name}\n`;
      detailsMessage += `⚖️ Вес: ${result.weight}кг\n`;
      if (result.length) {
        detailsMessage += `📏 Длина: ${result.length}см\n`;
      }
      detailsMessage += `✨ Редкость: ${result.fish.rarity}\n`;
      detailsMessage += `📍 Локация: ${this.currentLocation}\n`;
      
      if (result.xp_earned) {
        detailsMessage += `\n+${result.xp_earned} опыта`;
      }
      
      if (result.level_info && result.level_info.leveled_up) {
        detailsMessage += `\n\n🎉 Уровень повышен до ${result.level_info.new_level}!`;
      }
    } else if (result.is_trash) {
      const trashName = result.trash?.name || 'Мусор';
      fishImageUrl = result.trash?.image_url || `/api/fish-image/${result.trash?.sticker_id || trashName}.webp`;
      detailsMessage = `🗑️ Выловлен мусор: ${trashName}`;
      
      if (result.treasure_caught) {
        detailsMessage += `\n\n💎 Бонус! Найдено сокровище: ${result.treasure_name}`;
      }
    } else if (result.no_bite) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      detailsMessage = result.message || '❌ Рыба не клюет...';
    } else if (result.fish_inspector) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      detailsMessage = result.message || '🚨 Рыбнадзор конфисковал улов!';
    } else if (result.snap) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      detailsMessage = result.message || '💔 Рыба сорвалась!';
    }

    // Set final image in slot
    if (slotImage && fishImageUrl) {
      setTimeout(() => {
        slotImage.src = fishImageUrl;
        slotImage.classList.add('result-shown');
      }, 500);
    }

    // Show result modal with detailed info
    setTimeout(() => {
      if (result.fish || result.is_trash) {
        this.showFishModal(
          result.fish?.name || result.trash?.name || 'Результат',
          result.weight || result.trash?.weight || 0,
          result.length || 0,
          result.fish?.rarity || 'Мусор',
          fishImageUrl || '/api/fish-image/fishdef.webp',
          detailsMessage
        );
      } else {
        tgService.showAlert(detailsMessage);
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
      
      if (result.boat_crash) {
        setTimeout(() => {
          tgService.showAlert(result.boat_crash_message || '⚠️ КРУШЕНИЕ! Лодка затонула!');
        }, 2000);
      }
    }, 1000);
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
