// ─────────────────────────────────────────────────────────────────────────────
// ParallaxController — mouse / tilt driven background parallax
// ─────────────────────────────────────────────────────────────────────────────

export class ParallaxController {
  private el: HTMLElement;
  private targetX = 0;
  private targetY = 0;
  private currentX = 0;
  private currentY = 0;
  private rafId = 0;

  constructor(bgElement: HTMLElement) {
    this.el = bgElement;
    this.bindEvents();
    this.loop();
  }

  private bindEvents(): void {
    // Desktop: mouse move
    window.addEventListener('mousemove', (e: MouseEvent) => {
      this.targetX = ((e.clientX / window.innerWidth)  - 0.5) * 14;
      this.targetY = ((e.clientY / window.innerHeight) - 0.5) * 8;
    });

    // Mobile: device orientation
    window.addEventListener('deviceorientation', (e: DeviceOrientationEvent) => {
      if (e.gamma === null || e.beta === null) return;
      this.targetX = Math.max(-12, Math.min(12, e.gamma * 0.25));
      this.targetY = Math.max(-7,  Math.min(7,  (e.beta - 45) * 0.15));
    });
  }

  private loop(): void {
    // Smooth interpolation (lerp)
    this.currentX += (this.targetX - this.currentX) * 0.06;
    this.currentY += (this.targetY - this.currentY) * 0.06;

    this.el.style.transform =
      `scale(1.14) translate(${-this.currentX * 0.08}%, ${-this.currentY * 0.06}%)`;

    this.rafId = requestAnimationFrame(this.loop.bind(this));
  }

  destroy(): void {
    cancelAnimationFrame(this.rafId);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// BubbleSpawner — floating bubbles around the active trophy card
// ─────────────────────────────────────────────────────────────────────────────
export class BubbleSpawner {
  private container: HTMLElement;
  private intervalId = 0;

  constructor(container: HTMLElement) {
    this.container = container;
    this.start();
  }

  private spawnOne(): void {
    if (document.hidden) return;

    const b = document.createElement('div');
    b.className = 'trophy-bubble';

    const size = 4 + Math.random() * 9;
    const x    = 20 + Math.random() * 60;  // % from left (centered on card)
    const dur  = 2.8 + Math.random() * 2.8;

    b.style.cssText = `
      width:${size}px; height:${size}px;
      left:${x}%; bottom:${8 + Math.random() * 12}%;
      animation-duration:${dur}s;
      animation-delay:${Math.random() * 0.3}s;
    `;

    this.container.appendChild(b);
    setTimeout(() => b.remove(), (dur + 0.5) * 1000);
  }

  start(): void {
    this.intervalId = window.setInterval(() => this.spawnOne(), 380);
  }

  stop(): void {
    clearInterval(this.intervalId);
    this.container.querySelectorAll('.trophy-bubble').forEach(b => b.remove());
  }

  restart(): void {
    this.stop();
    this.start();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ScreenTransition — depth-of-water page transitions
// ─────────────────────────────────────────────────────────────────────────────
export class ScreenTransition {
  private static transitionToken = 0;
  private static pendingTimeout = 0;

  static transitionTo(from: HTMLElement, to: HTMLElement): void {
    if (this.pendingTimeout) {
      clearTimeout(this.pendingTimeout);
      this.pendingTimeout = 0;
    }

    const token = ++this.transitionToken;

    // Fade out current screen
    from.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
    from.style.opacity    = '0';
    from.style.transform  = 'scale(0.93)';
    from.style.pointerEvents = 'none';

    // Prepare incoming screen - сразу показываем и делаем кликабельным
    to.style.display      = 'flex';
    to.style.transition   = 'none';
    to.style.opacity      = '0';
    to.style.transform    = 'scale(1.06)';
    to.style.pointerEvents = 'all'; // ИСПРАВЛЕНИЕ: включаем сразу

    // After exit completes — bring in new screen
    this.pendingTimeout = window.setTimeout(() => {
      if (token !== this.transitionToken) {
        return;
      }

      from.style.display = 'none';
      from.style.opacity = '';
      from.style.transform = '';
      from.style.transition = '';

      requestAnimationFrame(() => {
        if (token !== this.transitionToken) {
          return;
        }
        to.style.transition  = 'opacity 0.38s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.38s cubic-bezier(0.25,0.46,0.45,0.94)';
        to.style.opacity     = '1';
        to.style.transform   = 'scale(1)';
      });
    }, 300);
  }
}
