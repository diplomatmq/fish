// ─────────────────────────────────────────────────────────────────────────────
// ParticleSystem — canvas-based bubbles & sediment animation
// ─────────────────────────────────────────────────────────────────────────────

interface Particle {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  alpha: number;
  alphaTarget: number;
  life: number;
  maxLife: number;
  isSediment: boolean;
  wobble: number;
  wobbleSpeed: number;
}

export class ParticleSystem {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private W = 0;
  private H = 0;
  private rafId = 0;
  private readonly COUNT = 60;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.resize();
    window.addEventListener('resize', this.resize.bind(this));

    // Pre-scatter particles so screen isn't empty on load
    for (let i = 0; i < this.COUNT; i++) {
      const p = this.createParticle();
      p.y = Math.random() * this.H;
      p.life = Math.floor(Math.random() * p.maxLife * 0.5);
      this.particles.push(p);
    }

    this.loop();
  }

  private resize(): void {
    this.W = this.canvas.width  = this.canvas.offsetWidth;
    this.H = this.canvas.height = this.canvas.offsetHeight;
  }

  private createParticle(): Particle {
    const isSediment = Math.random() < 0.28;
    return {
      x:           Math.random() * this.W,
      y:           this.H + 12,
      r:           isSediment ? 1.5 + Math.random() * 2 : 1.2 + Math.random() * 3,
      vx:          (Math.random() - 0.5) * 0.4,
      vy:          -(0.2 + Math.random() * 0.55),
      alpha:       0,
      alphaTarget: 0.12 + Math.random() * 0.4,
      life:        0,
      maxLife:     180 + Math.random() * 420,
      isSediment,
      wobble:      Math.random() * Math.PI * 2,
      wobbleSpeed: 0.02 + Math.random() * 0.03,
    };
  }

  private drawBubble(p: Particle): void {
    const ctx = this.ctx;
    p.wobble += p.wobbleSpeed;
    const wx = p.x + Math.sin(p.wobble) * 1.8;

    ctx.save();
    ctx.globalAlpha = p.alpha;

    // Outer ring
    ctx.strokeStyle = 'rgba(160,220,255,0.65)';
    ctx.lineWidth   = 0.7;
    ctx.beginPath();
    ctx.arc(wx, p.y, p.r, 0, Math.PI * 2);
    ctx.stroke();

    // Inner highlight
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    ctx.beginPath();
    ctx.arc(wx - p.r * 0.28, p.y - p.r * 0.28, p.r * 0.38, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  private drawSediment(p: Particle): void {
    const ctx = this.ctx;
    ctx.save();
    ctx.globalAlpha = p.alpha;
    ctx.fillStyle   = 'rgba(180,150,90,0.7)';
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, p.r * 1.6, p.r * 0.55, p.wobble, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  private updateParticle(p: Particle): boolean {
    p.x    += p.vx;
    p.y    += p.vy;
    p.life += 1;

    const fadeIn  = 40;
    const fadeOut = 50;
    if (p.life < fadeIn) {
      p.alpha = (p.life / fadeIn) * p.alphaTarget;
    } else if (p.life > p.maxLife - fadeOut) {
      p.alpha = ((p.maxLife - p.life) / fadeOut) * p.alphaTarget;
    } else {
      p.alpha = p.alphaTarget;
    }

    return p.life < p.maxLife && p.y > -10;
  }

  private loop(): void {
    this.ctx.clearRect(0, 0, this.W, this.H);

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      const alive = this.updateParticle(p);

      if (alive) {
        p.isSediment ? this.drawSediment(p) : this.drawBubble(p);
      } else {
        this.particles[i] = this.createParticle();
      }
    }

    this.rafId = requestAnimationFrame(this.loop.bind(this));
  }

  destroy(): void {
    cancelAnimationFrame(this.rafId);
    window.removeEventListener('resize', this.resize.bind(this));
  }
}
