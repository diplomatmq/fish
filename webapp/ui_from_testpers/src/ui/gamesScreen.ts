// ─────────────────────────────────────────────────────────────────────────────
// GamesScreen — Screen with two game buttons (Fishing and Mini Games)
// ─────────────────────────────────────────────────────────────────────────────
import { tgService } from '../modules/telegram';

export class GamesScreen {
  private el: HTMLElement;

  constructor() {
    this.el = this.build();
  }

  private build(): HTMLElement {
    const screen = document.createElement('div');
    screen.id = 'screen-games';
    screen.className = 'screen';
    screen.innerHTML = `
      <div class="games-container">
        <h2 class="games-title">🎮 ИГРЫ</h2>
        
        <div class="games-grid">
          <button class="game-card game-card--fishing" id="game-fishing-btn">
            <div class="game-card__icon">🎣</div>
            <div class="game-card__title">РЫБАЛКА</div>
            <div class="game-card__description">Отправляйтесь на рыбалку и поймайте редкую добычу</div>
          </button>
          
          <button class="game-card game-card--mini" id="game-mini-btn">
            <div class="game-card__icon">🎯</div>
            <div class="game-card__title">МИНИ ИГРЫ</div>
            <div class="game-card__description">Играйте в увлекательные мини-игры</div>
          </button>
        </div>
      </div>
    `;

    return screen;
  }

  init(): void {
    const fishingBtn = this.el.querySelector('#game-fishing-btn') as HTMLButtonElement;
    const miniBtn = this.el.querySelector('#game-mini-btn') as HTMLButtonElement;

    if (fishingBtn) {
      fishingBtn.addEventListener('click', () => {
        tgService.haptic('medium');
        this.openFishing();
      });
    }

    if (miniBtn) {
      miniBtn.addEventListener('click', () => {
        tgService.haptic('medium');
        this.openMiniGames();
      });
    }
  }

  private openFishing(): void {
    console.log('Opening Fishing...');
    // Переключаемся на экран рыбалки
    const fishingScreen = document.getElementById('screen-fishing');
    if (fishingScreen) {
      // Переключаем экраны через TabBar
      const event = new CustomEvent('switch-to-screen', { detail: { screenId: 'fishing' } });
      window.dispatchEvent(event);
    }
  }

  private openMiniGames(): void {
    console.log('Opening Mini Games...');
    // TODO: Implement mini games navigation
    // Здесь можно добавить переход к мини-играм
  }

  getElement(): HTMLElement {
    return this.el;
  }
}
