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
      <!-- Underwater background -->
      <div class="fishing-background">
        <div class="fishing-bubbles">
          <div class="bubble"></div>
          <div class="bubble"></div>
          <div class="bubble"></div>
          <div class="bubble"></div>
          <div class="bubble"></div>
        </div>
      </div>

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
              <div class="balance-icon" id="balance-icon">⭐</div>
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

        <!-- Single slot reel with scroll animation -->
        <div class="fishing-slot-container">
          <div class="fishing-slot-frame">
            <div class="slot-reel-single" id="slot-reel">
              <img src="/api/fish-image/fishdef.webp" alt="Fish" class="slot-image" />
            </div>
          </div>
        </div>

        <!-- Fish button - large circular with glow -->
        <button class="fishing-fish-btn-circular" id="fishing-fish-btn">
          <span class="fish-btn-text">ФИШ</span>
          <span class="fish-btn-cooldown" id="fish-btn-cooldown" style="display: none;"></span>
        </button>

        <!-- Location card -->
        <div class="fishing-location-card" id="fishing-location-card">
          <div class="location-card-icon">
            <div class="location-preview-image" id="location-preview-icon">🏞️</div>
          </div>
          <div class="location-card-info">
            <div class="location-card-name" id="location-card-name">Городской пруд</div>
            <div class="location-card-subtitle">Базовая локация</div>
          </div>
          <div class="location-card-status">
            <div class="boat-status-compact" id="boat-status-compact">
              <div class="boat-icon-compact">🚣</div>
              <div class="boat-text-compact">ЛОДКА</div>
              <div class="boat-status-indicator" id="boat-status-indicator">АКТИВНА</div>
            </div>
          </div>
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
    const locationCard = this.el.querySelector('#fishing-location-card') as HTMLElement;
    const locationModal = this.el.querySelector('#location-modal') as HTMLElement;
    const locationModalClose = this.el.querySelector('#location-modal-close') as HTMLButtonElement;
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

    // Balance toggle dropdown
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

    // Top-up buttons
    if (topupStarsBtn) {
      topupStarsBtn.addEventListener('click', () => {
        this.openTopupModal('stars');
        balanceDropdown.classList.remove('visible');
      });
    }

    if (topupTonBtn) {
      topupTonBtn.addEventListener('click', () => {
        this.openTopupModal('ton');
        balanceDropdown.classList.remove('visible');
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

    // Location card click - open modal
    if (locationCard) {
      locationCard.addEventListener('click', () => {
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
    const locationCardName = this.el.querySelector('#location-card-name') as HTMLElement;
    const locationPreviewIcon = this.el.querySelector('#location-preview-icon') as HTMLElement;
    
    if (locationCardName) {
      locationCardName.textContent = this.currentLocation;
    }
    
    // Set appropriate icon
    if (locationPreviewIcon) {
      const loc = this.LOCATIONS.find(l => l.name === this.currentLocation);
      locationPreviewIcon.textContent = loc?.icon || '🏞️';
    }
  }

  private updateBoatStatus(isOnBoat: boolean): void {
    const boatStatusIndicator = this.el.querySelector('#boat-status-indicator') as HTMLElement;
    const boatIconCompact = this.el.querySelector('.boat-icon-compact') as HTMLElement;
    
    if (boatStatusIndicator) {
      if (isOnBoat) {
        boatStatusIndicator.textContent = 'АКТИВНА';
        boatStatusIndicator.style.color = '#4ade80';
      } else {
        boatStatusIndicator.textContent = 'НЕТ';
        boatStatusIndicator.style.color = '#6b7280';
      }
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

  private selectCurrency(currency: 'stars' | 'ton'): void {
    this.selectedCurrency = currency;
    this.updateBalanceDisplay();
  }

  private updateBalanceDisplay(): void {
    const balanceValue = this.el.querySelector('#balance-value') as HTMLElement;
    const balanceIcon = this.el.querySelector('#balance-icon') as HTMLElement;
    const starsBalanceOpt = this.el.querySelector('#stars-balance-opt') as HTMLElement;
    const tonBalanceOpt = this.el.querySelector('#ton-balance-opt') as HTMLElement;

    if (this.selectedCurrency === 'stars') {
      if (balanceValue) balanceValue.textContent = this.starsBalance.toString();
      if (balanceIcon) balanceIcon.textContent = '⭐';
    } else {
      if (balanceValue) balanceValue.textContent = this.tonBalance.toFixed(2);
      if (balanceIcon) balanceIcon.textContent = '💎';
    }

    if (starsBalanceOpt) starsBalanceOpt.textContent = this.starsBalance.toString();
    if (tonBalanceOpt) tonBalanceOpt.textContent = this.tonBalance.toFixed(2);
  }

  private spinSlots(): void {
    const reel = this.el.querySelector('#slot-reel') as HTMLElement;
    
    if (!reel) return;
    
    // Use actual fish images from repository
    const commonFishImages = [
      'carp.webp',
      'bream.webp',
      'catfish.webp',
      'pike.webp',
      'perch.webp',
      'roach.webp',
      'trout.webp',
      'salmon.webp',
      'bass.webp',
      'crucian.webp'
    ];
    
    const drumImages = [...commonFishImages, ...commonFishImages, ...commonFishImages]; // Repeat for smooth loop
    
    try {
      // Build drum HTML directly with actual fish images
      reel.innerHTML = drumImages.map(img => `
        <div class="drum-item">
          <img src="/api/fish-image/${img}" alt="fish" class="drum-image" 
               onerror="this.src='/api/fish-image/fishdef.webp'" 
               style="width: 100%; height: 100%; object-fit: contain;" />
        </div>
      `).join('');
      
      // Add drum container
      const drumContainer = document.createElement('div');
      drumContainer.className = 'drum-container';
      drumContainer.innerHTML = reel.innerHTML;
      reel.innerHTML = '';
      reel.appendChild(drumContainer);
      
      let spinCount = 0;
      const maxSpins = 30;
      let position = 0;
      const itemHeight = 180; // Height of each drum item
      
      reel.classList.add('spinning');
      
      const animate = () => {
        if (spinCount >= maxSpins) {
          reel.classList.remove('spinning');
          return;
        }
        
        spinCount++;
        position -= 15; // Scroll speed
        
        // Reset position for infinite loop
        if (position <= -itemHeight * drumImages.length / 3) {
          position = 0;
        }
        
        drumContainer.style.transform = `translateY(${position}px)`;
        
        // Slow down at the end
        const delay = spinCount > maxSpins - 5 ? 50 : 20;
        setTimeout(() => requestAnimationFrame(animate), delay);
      };
      
      requestAnimationFrame(animate);
    } catch (error) {
      console.error('Spin slots error:', error);
      // Fallback: show single fish image
      reel.innerHTML = `
        <div class="drum-item">
          <img src="/api/fish-image/fishdef.webp" alt="fish" class="drum-image" />
        </div>
      `;
    }
  }

  private async fish(): Promise<void> {
    if (this.isSpinning) return;

    // Check if cooldown is active and user wants guaranteed catch
    const guaranteedCatch = this.cooldownEndTime > 0;
    
    if (guaranteedCatch) {
      const confirmed = await this.confirmGuaranteedCatch();
      if (!confirmed) return;

      // Process payment BEFORE fishing
      const paymentSuccess = await this.processGuaranteedPayment();
      if (!paymentSuccess) {
        // Restore balance if payment failed
        await this.loadPlayerData();
        return;
      }
    }

    this.isSpinning = true;
    const fishBtn = this.el.querySelector('#fishing-fish-btn') as HTMLButtonElement;
    fishBtn.classList.add('disabled');

    // Start slot animation
    this.spinSlots();

    try {
      // Call API with guaranteed flag and currency
      const result = await apiService.fish(this.currentLocation, guaranteedCatch, this.selectedCurrency);
      
      // ВАЖНО: Проверяем любой результат - успех ИЛИ неудача
      // Backend всегда устанавливает cooldown после попытки
      
      // Show fish result for all cases (success, trash, snap, no_bite, etc.)
      await this.showFishResult(result);
      
      // ВСЕГДА запускаем кулдаун после любой попытки рыбалки
      // Кулдаун = 10 минут = 600 секунд
      this.startCooldown(600);
      
      // Reload balance from server to sync
      await this.loadPlayerData();
      
    } catch (error) {
      console.error('Fishing failed:', error);
      // Show error in modal
      await this.showFishResult({ 
        error: 'Ошибка при ловле рыбы', 
        no_bite: true,
        message: 'Произошла ошибка. Попробуйте снова.'
      });
      
      // Restore balance on error
      await this.loadPlayerData();
    } finally {
      this.isSpinning = false;
      // Button state controlled by cooldown
      if (this.cooldownEndTime === 0) {
        fishBtn.classList.remove('disabled');
      }
    }
  }

  private async confirmGuaranteedCatch(): Promise<boolean> {
    const currency = this.selectedCurrency === 'stars' ? '1 звезду' : '0.01 TON';
    const message = `Кулдаун активен. Хотите потратить ${currency} на гарантированный результат? (Может выпасть рыба, мусор или NFT)`;
    
    return new Promise((resolve) => {
      if (confirm(message)) {
        resolve(true);
      } else {
        resolve(false);
      }
    });
  }

  private async processGuaranteedPayment(): Promise<boolean> {
    // ВАЖНО: Оплата дает ГАРАНТИРОВАННЫЙ РЕЗУЛЬТАТ (рыба/мусор/NFT), БЕЗ срывов!
    // Деньги списываются за пропуск кулдауна + гарантию получить хоть что-то
    try {
      if (this.selectedCurrency === 'stars') {
        // Check stars balance
        if (this.starsBalance < 1) {
          tgService.showAlert('Недостаточно звезд. Пополните баланс.');
          return false;
        }
        // DON'T deduct locally - backend will handle it
        // Just return true to proceed with fishing
        return true;
      } else {
        // TON payment
        if (this.tonBalance < 0.01) {
          tgService.showAlert('Недостаточно TON. Пополните баланс.');
          return false;
        }
        
        // Send TON transaction
        const result = await tonConnectService.sendTransaction(0.01, 'Fishing Attempt');
        
        if (!result.success) {
          tgService.showAlert(`Ошибка оплаты: ${result.error || 'Неизвестная ошибка'}`);
          return false;
        }
        
        // DON'T deduct locally - backend will handle it after transaction confirmation
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
    
    // Determine final image based on result
    let fishImageUrl: string | null = null;
    let detailsMessage = '';
    let modalTitle = 'Результат';
    
    if (result.fish) {
      fishImageUrl = result.fish.image_url || `/api/fish-image/${result.fish.sticker_id || result.fish.name}.webp`;
      modalTitle = result.fish.name;
      
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
      modalTitle = trashName;
      detailsMessage = `🗑️ Выловлен мусор: ${trashName}`;
      
      if (result.xp_earned) {
        detailsMessage += `\n\n+${result.xp_earned} опыта`;
      }
      
      if (result.treasure_caught) {
        detailsMessage += `\n\n💎 Бонус! Найдено сокровище: ${result.treasure_name}`;
      }
    } else if (result.no_bite) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      modalTitle = 'Не клюёт';
      // Use message from backend or default messages
      const noBiteMessages = [
        "❌ Рыба не клюет...",
        "🐟 Поклевки нет",
        "💤 Рыба спит на дне",
        "🌊 Сегодня плохой клев",
        "🎣 Рыба не интересуется приманкой",
        "🗺️ Попробуйте другую локацию",
        "🧊 Вода слишком холодная",
        "⬇️ Рыба ушла на глубину"
      ];
      detailsMessage = result.message || noBiteMessages[Math.floor(Math.random() * noBiteMessages.length)];
    } else if (result.fish_inspector) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      modalTitle = 'Рыбнадзор!';
      detailsMessage = result.message || '🚨 Рыбнадзор конфисковал улов! Вас оштрафовали.';
    } else if (result.snap) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      modalTitle = 'Сорвалась!';
      detailsMessage = result.message || '💔 Рыба сорвалась с крючка! Попробуйте снова.';
    } else if (result.error) {
      fishImageUrl = '/api/fish-image/fishdef.webp';
      modalTitle = 'Ошибка';
      detailsMessage = result.message || '❌ ' + (result.error || 'Произошла ошибка');
    } else {
      // Fallback for unknown result type
      fishImageUrl = '/api/fish-image/fishdef.webp';
      modalTitle = 'Результат';
      detailsMessage = result.message || '🎣 Попытка не удалась. Попробуйте снова.';
    }

    // Stop spinning and show final result
    if (reel) {
      reel.classList.remove('spinning');
      
      // Replace drum with single result image
      if (fishImageUrl) {
        setTimeout(() => {
          reel.innerHTML = `
            <div class="drum-item">
              <img src="${fishImageUrl}" alt="result" class="drum-image result-shown" />
            </div>
          `;
        }, 300);
      }
    }

    // Dispatch event to refresh profile catches
    window.dispatchEvent(new CustomEvent('refresh-profile'));

    // Show result modal ALWAYS (for all cases)
    setTimeout(() => {
      tgService.haptic(result.fish || result.is_trash ? 'success' : 'light');
      this.showFishModal(
        modalTitle,
        result.weight || result.trash?.weight || 0,
        result.length || 0,
        result.fish?.rarity || (result.is_trash ? 'Мусор' : '-'),
        fishImageUrl || '/api/fish-image/fishdef.webp',
        detailsMessage
      );
      
      // Show special events as additional alerts after modal
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
          tgService.showAlert(`🐠 Стайный инстинкт! Бонус к весу: +${result.school_bonus_percent}%`);
        }, 2000);
      }
      
      if (result.boat_crash) {
        setTimeout(() => {
          tgService.showAlert(result.boat_crash_message || '⚠️ КРУШЕНИЕ! Лодка затонула!');
        }, 2500);
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
    
    // Show with animation - need delay for CSS transition
    setTimeout(() => {
      modal.classList.add('visible');
    }, 10);
    
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
        // Create invoice through backend API
        const result = await apiService.createStarsInvoice(amount);
        if (result.invoice_link) {
          // Open Telegram Stars payment directly in WebApp
          if (tgService.webApp && tgService.webApp.openInvoice) {
            tgService.webApp.openInvoice(result.invoice_link, (status: string) => {
              if (status === 'paid') {
                tgService.showAlert(`✅ Баланс пополнен на ${amount} ⭐`);
                this.starsBalance += amount;
                this.updateBalanceDisplay();
                this.closeTopupModal();
              } else if (status === 'cancelled') {
                tgService.showAlert('Оплата отменена');
              } else if (status === 'failed') {
                tgService.showAlert('Ошибка оплаты');
              }
            });
          } else {
            // Fallback - open in new window
            window.open(result.invoice_link, '_blank');
            this.closeTopupModal();
          }
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
