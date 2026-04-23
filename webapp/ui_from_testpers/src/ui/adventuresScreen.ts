import { tgService } from '../modules/telegram';
import { RunnerGame } from '../games/runner';
import { MazeGame } from '../games/maze';
import { getIcon } from './icons';

export class AdventuresScreen {
  private el: HTMLElement;
  private currentGame: any = null;

  constructor() {
    this.el = this.buildShell();
  }

  getElement(): HTMLElement {
    return this.el;
  }

  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id = 'screen-adventures';
    s.className = 'screen adventures-main-screen';
    s.setAttribute('role', 'main');

    s.innerHTML = `
      <div class="adv-main-menu" id="adv-main-menu">
        <h1 class="page-title">ПРИКЛЮЧЕНИЯ</h1>
        <div class="adv-cards-wrap">
          
          <div class="adv-game-card" id="card-runner">
            <div class="adv-card-icon">${getIcon('anglerfish')}</div>
            <div class="adv-card-info">
              <h3>Бег от Удильщика</h3>
              <p>Ритмичный 2D раннер на выживание</p>
            </div>
            <div class="adv-soon-label">SOON</div>
          </div>

          <div class="adv-game-card" id="card-maze">
            <div class="adv-card-icon">${getIcon('seahorse')}</div>
            <div class="adv-card-info">
              <h3>Морской Навигатор</h3>
              <p>3D Головоломка-лабиринт</p>
            </div>
            <div class="adv-soon-label">SOON</div>
          </div>

        </div>
      </div>
    `;
    return s;
  }

  init(): void {
    const menu = this.el.querySelector('#adv-main-menu') as HTMLElement;
    
    this.el.querySelector('#card-runner button')!.addEventListener('click', () => {
      tgService.haptic('impact');
      menu.style.display = 'none';
      if (this.currentGame) this.currentGame.destroy();
      this.currentGame = new RunnerGame(this.el, () => {
         this.currentGame.destroy();
         this.currentGame = null;
         menu.style.display = 'flex';
      });
    });

    this.el.querySelector('#card-maze button')!.addEventListener('click', () => {
      tgService.haptic('impact');
      menu.style.display = 'none';
      if (this.currentGame) this.currentGame.destroy();
      this.currentGame = new MazeGame(this.el, () => {
         this.currentGame.destroy();
         this.currentGame = null;
         menu.style.display = 'flex';
      });
    });
  }
}
