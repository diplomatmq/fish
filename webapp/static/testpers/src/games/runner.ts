import { tgService } from '../modules/telegram';

export class RunnerGame {
  private el: HTMLElement;
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private onExit: () => void;
  
  // Game state
  private isPlaying = false;
  private isGameOver = false;
  private distance = 0;
  private coins = 0;
  private speed = 3;
  private animationId = 0;
  
  // Entities
  private player = { x: 80, y: 0, targetY: 0, size: 40 };
  private angler = { x: -20, y: 0, size: 80, baseY: 0, time: 0 };
  private obstacles: any[] = [];
  private collectibles: any[] = [];
  private particles: any[] = [];
  
  // UI
  private menuOverlay!: HTMLElement;
  private gameOverOverlay!: HTMLElement;
  private distanceEl!: HTMLElement;
  private coinsEl!: HTMLElement;

  constructor(parent: HTMLElement, onExit: () => void) {
    this.onExit = onExit;
    this.el = document.createElement('div');
    this.el.className = 'game-container';
    this.el.innerHTML = `
      <div class="adv-hud">
        <div class="adv-stat">ДИСТАНЦИЯ: <span id="adv-dist">0</span> м</div>
        <div class="adv-title">УКЛОНЯЙСЯ ОТ УДИЛЬЩИКА!</div>
        <div class="adv-stat">МОНЕТЫ: <span id="adv-coins">0</span></div>
      </div>
      
      <canvas id="runner-canvas" class="runner-canvas"></canvas>
      
      <div id="adv-menu" class="adv-overlay">
        <h2>ПОБЕГ ОТ УДИЛЬЩИКА</h2>
        <p>Свайпай вверх и вниз, чтобы уклоняться от препятствий и собирать монеты!</p>
        <button id="adv-start-btn" class="adv-btn">ИГРАТЬ</button>
        <button id="adv-exit-btn" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>

      <div id="adv-gameover" class="adv-overlay" style="display:none;">
        <h2>СЪЕДЕН!</h2>
        <p>Дистанция: <span id="adv-final-dist">0</span> м</p>
        <p>Собрано монет: <span id="adv-final-coins">0</span></p>
        <button id="adv-restart-btn" class="adv-btn">ПОВТОРИТЬ</button>
        <button id="adv-exit-btn2" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
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
    this.canvas = s.querySelector('#runner-canvas') as HTMLCanvasElement;
    this.ctx = this.canvas.getContext('2d')!;
    
    this.menuOverlay = s.querySelector('#adv-menu')!;
    this.gameOverOverlay = s.querySelector('#adv-gameover')!;
    this.distanceEl = s.querySelector('#adv-dist')!;
    this.coinsEl = s.querySelector('#adv-coins')!;
    
    s.querySelector('#adv-start-btn')!.addEventListener('click', () => this.startGame());
    s.querySelector('#adv-restart-btn')!.addEventListener('click', () => this.startGame());
    s.querySelector('#adv-exit-btn')!.addEventListener('click', () => this.onExit());
    s.querySelector('#adv-exit-btn2')!.addEventListener('click', () => this.onExit());
    
    // Resize
    const resize = () => {
      this.canvas.width = window.innerWidth;
      this.canvas.height = s.clientHeight || window.innerHeight;
      if (!this.isPlaying) this.drawStaticBackground();
    };
    window.addEventListener('resize', resize);
    setTimeout(resize, 100);

    // Controls
    let startY = 0;
    this.canvas.addEventListener('touchstart', e => {
      startY = e.touches[0].clientY;
    });
    this.canvas.addEventListener('touchmove', e => {
      e.preventDefault(); 
      const currentY = e.touches[0].clientY;
      const dy = currentY - startY;
      this.player.targetY += dy * 1.5;
      
      if (this.player.targetY < 50) this.player.targetY = 50;
      if (this.player.targetY > this.canvas.height - 50) this.player.targetY = this.canvas.height - 50;
      
      startY = currentY;
    }, { passive: false });
    
    // Mouse fallback
    let isDown = false;
    this.canvas.addEventListener('mousedown', e => { isDown = true; startY = e.clientY; });
    window.addEventListener('mouseup', () => isDown = false);
    this.canvas.addEventListener('mousemove', e => {
      if (!isDown) return;
      const dy = e.clientY - startY;
      this.player.targetY += dy * 1.5;
      if (this.player.targetY < 50) this.player.targetY = 50;
      if (this.player.targetY > this.canvas.height - 50) this.player.targetY = this.canvas.height - 50;
      startY = e.clientY;
    });
  }

  private startGame(): void {
    tgService.haptic('impact');
    this.isPlaying = true;
    this.isGameOver = false;
    this.distance = 0;
    this.coins = 0;
    this.speed = 3;
    this.obstacles = [];
    this.collectibles = [];
    this.particles = [];
    
    this.player.y = this.canvas.height / 2;
    this.player.targetY = this.player.y;
    this.angler.y = this.canvas.height / 2;
    
    this.menuOverlay.style.display = 'none';
    this.gameOverOverlay.style.display = 'none';
    
    cancelAnimationFrame(this.animationId);
    this.lastTime = performance.now();
    this.gameLoop(this.lastTime);
  }

  private spawnObstacle() {
    const type = Math.random() > 0.5 ? '🪨' : '🦑';
    const size = 50 + Math.random() * 30;
    this.obstacles.push({
      x: this.canvas.width + 50,
      y: 50 + Math.random() * (this.canvas.height - 100),
      size,
      type,
      wobble: Math.random() * Math.PI * 2
    });
  }

  private spawnCollectible() {
    this.collectibles.push({
      x: this.canvas.width + 50,
      y: 50 + Math.random() * (this.canvas.height - 100),
      size: 30,
      type: '💎'
    });
  }

  private spawnParticles(x: number, y: number, color: string) {
    for (let i = 0; i < 10; i++) {
      this.particles.push({
        x, y,
        vx: (Math.random() - 0.5) * 10,
        vy: (Math.random() - 0.5) * 10,
        life: 1.0,
        color
      });
    }
  }

  private endGame() {
    this.isPlaying = false;
    this.isGameOver = true;
    tgService.haptic('heavy');
    
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    this.el.querySelector('#adv-final-dist')!.textContent = Math.floor(this.distance).toString();
    this.el.querySelector('#adv-final-coins')!.textContent = this.coins.toString();
    this.gameOverOverlay.style.display = 'flex';
  }

  private lastTime = 0;
  private spawnTimer = 0;

  private gameLoop(time: number) {
    if (!this.isPlaying) return;
    
    const dt = (time - this.lastTime) / 1000;
    this.lastTime = time;
    
    this.distance += this.speed * dt * 10;
    this.speed += dt * 0.05; 
    
    this.distanceEl.textContent = Math.floor(this.distance).toString();
    
    this.spawnTimer += dt;
    if (this.spawnTimer > 1.2 * (3 / this.speed)) {
      this.spawnTimer = 0;
      this.spawnObstacle();
      if (Math.random() > 0.4) this.spawnCollectible();
    }
    
    this.player.y += (this.player.targetY - this.player.y) * 0.1;
    this.angler.time += dt * 5;
    this.angler.baseY += (this.player.y - this.angler.baseY) * 0.02; 
    this.angler.y = this.angler.baseY + Math.sin(this.angler.time) * 20; 
    
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    if (Math.random() > 0.9) {
      this.particles.push({
        x: this.canvas.width + 10,
        y: Math.random() * this.canvas.height,
        vx: -this.speed * 0.5,
        vy: -1 - Math.random() * 2,
        life: 2.0,
        color: 'rgba(255, 255, 255, 0.2)',
        isBubble: true
      });
    }

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      if (!p.isBubble) p.life -= dt * 1.5;
      else p.life -= dt * 0.2;
      
      if (p.life <= 0) {
        this.particles.splice(i, 1);
        continue;
      }
      
      this.ctx.globalAlpha = p.life;
      this.ctx.fillStyle = p.color;
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.isBubble ? 4 : 3, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.globalAlpha = 1;
    }

    this.ctx.font = '30px Arial';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    
    for (let i = this.collectibles.length - 1; i >= 0; i--) {
      const c = this.collectibles[i];
      c.x -= this.speed;
      
      const dist = Math.hypot(c.x - this.player.x, c.y - this.player.y);
      if (dist < this.player.size / 2 + c.size / 2) {
        this.coins++;
        this.coinsEl.textContent = this.coins.toString();
        this.spawnParticles(c.x, c.y, '#00b4d8');
        this.collectibles.splice(i, 1);
        tgService.haptic('light');
        continue;
      }
      
      if (c.x < -50) {
        this.collectibles.splice(i, 1);
        continue;
      }
      
      this.ctx.shadowColor = '#00b4d8';
      this.ctx.shadowBlur = 10;
      this.ctx.fillText(c.type, c.x, c.y + Math.sin(time/200 + c.x)*5);
      this.ctx.shadowBlur = 0;
    }

    for (let i = this.obstacles.length - 1; i >= 0; i--) {
      const obs = this.obstacles[i];
      obs.x -= this.speed;
      obs.wobble += dt * 3;
      
      const realY = obs.type === '🦑' ? obs.y + Math.sin(obs.wobble)*15 : obs.y;
      
      const dist = Math.hypot(obs.x - this.player.x, realY - this.player.y);
      if (dist < this.player.size / 2 + obs.size * 0.35) { 
        this.endGame();
        return;
      }

      if (obs.x < -100) {
        this.obstacles.splice(i, 1);
        continue;
      }
      
      this.ctx.font = `${obs.size}px Arial`;
      this.ctx.fillText(obs.type, obs.x, realY);
    }

    this.ctx.font = `${this.player.size}px Arial`;
    this.ctx.shadowColor = '#00b4d8';
    this.ctx.shadowBlur = 15;
    
    const tilt = (this.player.targetY - this.player.y) * 0.05;
    this.ctx.save();
    this.ctx.translate(this.player.x, this.player.y);
    this.ctx.rotate(tilt);
    this.ctx.fillText('🦁', 0, 0);
    this.ctx.restore();
    this.ctx.shadowBlur = 0;

    this.ctx.font = `${this.angler.size}px Arial`;
    this.ctx.shadowColor = '#ff0055';
    this.ctx.shadowBlur = 20;
    this.ctx.fillText('👾', this.angler.x, this.angler.y);
    this.ctx.shadowBlur = 0;
    
    this.ctx.beginPath();
    this.ctx.moveTo(this.angler.x + 10, this.angler.y - 30);
    this.ctx.lineTo(this.angler.x + 30, this.angler.y - 40);
    this.ctx.strokeStyle = '#00ffcc';
    this.ctx.lineWidth = 2;
    this.ctx.stroke();
    this.ctx.beginPath();
    this.ctx.fillStyle = '#00ffcc';
    this.ctx.arc(this.angler.x + 30, this.angler.y - 40, 4, 0, Math.PI*2);
    this.ctx.fill();

    this.animationId = requestAnimationFrame((t) => this.gameLoop(t));
  }

  private drawStaticBackground() {
    this.ctx.fillStyle = 'rgba(0,10,30,0.5)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.font = '50px Arial';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('👾', 50, this.canvas.height / 2);
    this.ctx.fillText('🦁', 150, this.canvas.height / 2);
  }
}
