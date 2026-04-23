import { tgService } from '../modules/telegram';

type CellType = 'floor' | 'wall' | 'chest' | 'eel' | 'pearl' | 'start';

export class MazeGame {
  private el: HTMLElement;
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private onExit: () => void;
  
  private animationId = 0;
  private isPlaying = false;
  
  // Game state
  private grid: CellType[][] = [];
  private cols = 6;
  private rows = 8;
  private player = { gx: 0, gy: 0 };
  private pearls = 0;
  private moves = 15;
  
  // Rendering
  private tileW = 60;
  private tileH = 30; // isometric
  
  private overlay!: HTMLElement;

  constructor(parent: HTMLElement, onExit: () => void) {
    this.onExit = onExit;
    this.el = document.createElement('div');
    this.el.className = 'game-container';
    
    this.el.innerHTML = `
      <div class="adv-hud">
        <div class="adv-stat">ХОДОВ: <span id="maze-moves">15</span></div>
        <div class="adv-title">НАЙДИ ПУТЬ К СОКРОВИЩУ</div>
        <div class="adv-stat">ЖЕМЧУГ: <span id="maze-pearls">0</span></div>
      </div>
      
      <canvas id="maze-canvas" class="runner-canvas"></canvas>
      
      <div id="maze-menu" class="adv-overlay">
        <h2>МОРСКОЙ НАВИГАТОР</h2>
        <p>Свайпай (Вверх, Вниз, Влево, Вправо) чтобы довести Конька до сундука.</p>
        <p>Опасайся угрей 🐍 и планируй ходы!</p>
        <button id="maze-start-btn" class="adv-btn">ИГРАТЬ</button>
        <button id="maze-exit-btn" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>

      <div id="maze-gameover" class="adv-overlay" style="display:none;">
        <h2 id="maze-result-title">ПОБЕДА!</h2>
        <p>Собрано жемчуга: <span id="maze-final-pearls">0</span></p>
        <button id="maze-restart-btn" class="adv-btn">СЫГРАТЬ ЕЩЕ</button>
        <button id="maze-exit-btn2" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>
    `;
    parent.appendChild(this.el);
    this.init();
  }

  destroy() {
    this.isPlaying = false;
    cancelAnimationFrame(this.animationId);
    this.el.remove();
  }

  private init(): void {
    const s = this.el;
    this.canvas = s.querySelector('#maze-canvas') as HTMLCanvasElement;
    this.ctx = this.canvas.getContext('2d')!;
    this.overlay = s.querySelector('#maze-gameover')!;
    
    s.querySelector('#maze-start-btn')!.addEventListener('click', () => this.startGame());
    s.querySelector('#maze-restart-btn')!.addEventListener('click', () => this.startGame());
    s.querySelector('#maze-exit-btn')!.addEventListener('click', () => this.onExit());
    s.querySelector('#maze-exit-btn2')!.addEventListener('click', () => this.onExit());
    
    const resize = () => {
      this.canvas.width = window.innerWidth;
      this.canvas.height = s.clientHeight || window.innerHeight;
      this.tileW = Math.min(60, this.canvas.width / (this.cols + 2));
      this.tileH = this.tileW * 0.55;
    };
    window.addEventListener('resize', resize);
    setTimeout(resize, 100);

    const processSwipe = (dx: number, dy: number) => {
      if (!this.isPlaying) return;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 30) {
        if (dx > 0) this.tryMove(1, 0); // Right
        else this.tryMove(-1, 0);       // Left
      } else if (Math.abs(dy) > 30) {
        if (dy > 0) this.tryMove(0, 1); // Down
        else this.tryMove(0, -1);       // Up
      }
    };

    // Touch Swipe
    let sx = 0, sy = 0;
    this.canvas.addEventListener('touchstart', e => {
      sx = e.touches[0].clientX; sy = e.touches[0].clientY;
    }, {passive: true});
    this.canvas.addEventListener('touchend', e => {
      const ex = e.changedTouches[0].clientX, ey = e.changedTouches[0].clientY;
      processSwipe(ex - sx, ey - sy);
    });

    // Mouse Swipe (Desktop fallback)
    let isMouseDown = false;
    this.canvas.addEventListener('mousedown', e => {
      isMouseDown = true;
      sx = e.clientX; sy = e.clientY;
    });
    window.addEventListener('mouseup', e => {
      if (!isMouseDown) return;
      isMouseDown = false;
      processSwipe(e.clientX - sx, e.clientY - sy);
    });

    // Keyboard (Desktop fallback)
    window.addEventListener('keydown', e => {
      if (!this.isPlaying) return;
      switch(e.key) {
        case 'ArrowUp': case 'w': case 'W': case 'Ц': case 'ц': this.tryMove(0, -1); break;
        case 'ArrowDown': case 's': case 'S': case 'Ы': case 'ы': this.tryMove(0, 1); break;
        case 'ArrowLeft': case 'a': case 'A': case 'Ф': case 'ф': this.tryMove(-1, 0); break;
        case 'ArrowRight': case 'd': case 'D': case 'В': case 'в': this.tryMove(1, 0); break;
      }
    });
  }

  private generateMaze() {
    // 6x8 hardcoded maze prototype
    const map = [
      ['start', 'floor', 'wall',  'floor', 'pearl', 'floor'],
      ['wall',  'floor', 'wall',  'floor', 'wall',  'floor'],
      ['floor', 'floor', 'floor', 'floor', 'wall',  'floor'],
      ['floor', 'wall',  'wall',  'floor', 'eel',   'floor'],
      ['pearl', 'floor', 'wall',  'floor', 'floor', 'floor'],
      ['wall',  'floor', 'floor', 'eel',   'wall',  'wall'],
      ['floor', 'floor', 'wall',  'floor', 'floor', 'pearl'],
      ['floor', 'eel',   'floor', 'floor', 'wall',  'chest'],
    ];
    this.grid = map as CellType[][];
  }

  private startGame(): void {
    tgService.haptic('impact');
    this.generateMaze();
    this.player = { gx: 0, gy: 0 };
    this.moves = 20;
    this.pearls = 0;
    this.isPlaying = true;
    
    this.el.querySelector<HTMLElement>('#maze-menu')!.style.display = 'none';
    this.el.querySelector<HTMLElement>('#maze-gameover')!.style.display = 'none';
    
    this.updateUI();
    cancelAnimationFrame(this.animationId);
    this.renderLoop(performance.now());
  }

  private tryMove(dx: number, dy: number) {
    if (this.moves <= 0) return;
    
    const nx = this.player.gx + dx;
    const ny = this.player.gy + dy;
    
    if (nx >= 0 && nx < this.cols && ny >= 0 && ny < this.rows) {
      const cell = this.grid[ny][nx];
      if (cell === 'wall') {
        tgService.haptic('error');
        return; // blocked
      }
      
      this.player.gx = nx;
      this.player.gy = ny;
      this.moves--;
      tgService.haptic('light');
      
      if (cell === 'pearl') {
        this.pearls++;
        this.grid[ny][nx] = 'floor';
        tgService.haptic('success');
      } else if (cell === 'eel') {
        this.endGame(false, 'СЪЕДЕН УГРЕМ!');
        return;
      } else if (cell === 'chest') {
        this.endGame(true, 'СОКРОВИЩЕ НАЙДЕНО!');
        return;
      }
      
      this.updateUI();
      if (this.moves <= 0) {
        this.endGame(false, 'ЗАКОНЧИЛИСЬ ХОДЫ!');
      }
    }
  }

  private updateUI() {
    this.el.querySelector('#maze-moves')!.textContent = this.moves.toString();
    this.el.querySelector('#maze-pearls')!.textContent = this.pearls.toString();
  }

  private endGame(win: boolean, text: string) {
    this.isPlaying = false;
    tgService.haptic(win ? 'success' : 'heavy');
    
    this.el.querySelector('#maze-result-title')!.textContent = text;
    this.el.querySelector('#maze-final-pearls')!.textContent = this.pearls.toString();
    this.el.querySelector<HTMLElement>('#maze-gameover')!.style.display = 'flex';
  }

  private renderLoop(time: number) {
    if (!this.isPlaying) return;
    
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Background
    this.ctx.fillStyle = 'rgba(0,10,25,0.8)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    const ox = this.canvas.width / 2;
    const oy = 100;
    
    // Draw cells (painters algorithm: back to front)
    for (let y = 0; y < this.rows; y++) {
      for (let x = 0; x < this.cols; x++) {
        const type = this.grid[y][x];
        
        // Isometric projection formulas
        const sx = ox + (x - y) * this.tileW;
        const sy = oy + (x + y) * this.tileH;
        
        this.drawTile(sx, sy, type, time);
        
        // Draw Player if here
        if (this.player.gx === x && this.player.gy === y) {
           this.ctx.font = '34px Arial';
           this.ctx.textAlign = 'center';
           this.ctx.shadowColor = '#00f0ff';
           this.ctx.shadowBlur = 15;
           // pulse
           const lift = Math.abs(Math.sin(time / 200)) * 10;
           this.ctx.fillText('🦑', sx, sy - 15 - lift);
           this.ctx.shadowBlur = 0;
           
           // Light cast from player
           this.ctx.beginPath();
           this.ctx.ellipse(sx, sy, this.tileW, this.tileH, 0, 0, Math.PI*2);
           const pGlow = this.ctx.createRadialGradient(sx, sy, 0, sx, sy, this.tileW);
           pGlow.addColorStop(0, 'rgba(0, 240, 255, 0.4)');
           pGlow.addColorStop(1, 'rgba(0, 240, 255, 0)');
           this.ctx.fillStyle = pGlow;
           this.ctx.fill();
        }
      }
    }
    
    this.animationId = requestAnimationFrame((t) => this.renderLoop(t));
  }

  private drawTile(x: number, y: number, type: CellType, time: number) {
    const tw = this.tileW;
    const th = this.tileH;
    
    // Base Floor
    this.ctx.beginPath();
    this.ctx.moveTo(x, y - th);     // top
    this.ctx.lineTo(x + tw, y);     // right
    this.ctx.lineTo(x, y + th);     // bottom
    this.ctx.lineTo(x - tw, y);     // left
    this.ctx.closePath();
    
    this.ctx.fillStyle = type === 'wall' ? '#14314c' : '#081f33';
    this.ctx.fill();
    this.ctx.strokeStyle = 'rgba(0,180,216,0.3)';
    this.ctx.lineWidth = 1;
    this.ctx.stroke();
    
    // Draw content
    this.ctx.font = '24px Arial';
    this.ctx.textAlign = 'center';
    
    if (type === 'wall') {
      // Draw pseudo 3D block
      this.ctx.beginPath();
      this.ctx.moveTo(x - tw, y);
      this.ctx.lineTo(x, y + th);
      this.ctx.lineTo(x, y + th - 20);
      this.ctx.lineTo(x - tw, y - 20);
      this.ctx.fillStyle = '#104d7d';
      this.ctx.fill();
      
      this.ctx.beginPath();
      this.ctx.moveTo(x, y + th);
      this.ctx.lineTo(x + tw, y);
      this.ctx.lineTo(x + tw, y - 20);
      this.ctx.lineTo(x, y + th - 20);
      this.ctx.fillStyle = '#0b3558';
      this.ctx.fill();
      
      this.ctx.beginPath();
      this.ctx.moveTo(x, y - th - 20);
      this.ctx.lineTo(x + tw, y - 20);
      this.ctx.lineTo(x, y + th - 20);
      this.ctx.lineTo(x - tw, y - 20);
      this.ctx.fillStyle = '#18649e';
      this.ctx.fill();
      
      this.ctx.fillText('🪸', x, y - 5);
    } else if (type === 'chest') {
      this.ctx.shadowColor = '#ffe259';
      this.ctx.shadowBlur = 20;
      this.ctx.fillText('🧰', x, y);
      this.ctx.shadowBlur = 0;
    } else if (type === 'pearl') {
      this.ctx.fillText('⚪', x, y + Math.sin(time/300 + x)*5);
    } else if (type === 'eel') {
      this.ctx.shadowColor = '#ff6b6b';
      this.ctx.shadowBlur = 10;
      this.ctx.fillText('🐍', x, y);
      this.ctx.shadowBlur = 0;
    }
  }
}
