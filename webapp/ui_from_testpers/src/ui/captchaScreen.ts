import { fetchApi } from '../modules/api';
import { tgService } from '../modules/telegram';

interface CaptchaChallenge {
  token: string;
  question: string;
  map?: Record<string, string>;
  steps?: string[];
  expires_at: string;
}

interface CaptchaResponse {
  ok: boolean;
  challenge?: CaptchaChallenge;
  penalty_active?: boolean;
  penalty_until?: string;
  error?: string;
}

export class CaptchaScreen {
  private el: HTMLElement;
  private token: string = '';
  private challenge: CaptchaChallenge | null = null;
  private loading = false;

  constructor() {
    this.el = this.buildShell();
  }

  getElement(): HTMLElement {
    return this.el;
  }

  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id = 'screen-captcha';
    s.className = 'screen captcha-screen';
    s.setAttribute('role', 'main');

    s.innerHTML = `
      <div class="captcha-container">
        <h1 class="captcha-title">🧩 Проверка рыбака</h1>
        <p class="captcha-subtitle">Подтвердите, что вы человек</p>
        
        <div id="captcha-status" class="captcha-status loading">
          ⏳ Загрузка капчи...
        </div>
        
        <div id="captcha-content" style="display:none;">
          <div class="captcha-block">
            <h3>💡 Подсказка</h3>
            <ul id="captcha-map" class="captcha-map"></ul>
          </div>

          <div class="captcha-block">
            <h3>📜 Условия</h3>
            <ol id="captcha-steps" class="captcha-steps"></ol>
          </div>

          <div class="captcha-input-group">
            <input
              id="captcha-answer"
              class="captcha-input"
              type="text"
              inputmode="text"
              autocomplete="off"
              placeholder="Введите ответ"
            />
            <button id="captcha-submit" class="captcha-submit-btn">✅ Проверить</button>
          </div>

          <div id="captcha-timer" class="captcha-timer"></div>
        </div>
      </div>
    `;
    return s;
  }

  async init(): Promise<void> {
    // Получаем токен из URL
    const urlParams = new URLSearchParams(window.location.search);
    this.token = urlParams.get('captcha_token') || '';

    if (!this.token) {
      this.showError('Токен капчи не найден. Откройте апку по ссылке из бота.');
      return;
    }

    await this.loadChallenge();
    this.bindEvents();
  }

  private bindEvents(): void {
    const submitBtn = this.el.querySelector('#captcha-submit');
    const answerInput = this.el.querySelector('#captcha-answer') as HTMLInputElement;

    if (submitBtn && answerInput) {
      submitBtn.addEventListener('click', () => {
        tgService.haptic('medium');
        this.submitAnswer(answerInput.value);
      });

      answerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          tgService.haptic('medium');
          this.submitAnswer(answerInput.value);
        }
      });
    }
  }

  private async loadChallenge(): Promise<void> {
    this.loading = true;
    this.showStatus('loading', '⏳ Загрузка капчи...');

    try {
      const data = await fetchApi<CaptchaResponse>(`/api/captcha/challenge?token=${this.token}`);

      if (!data || !data.ok) {
        const error = data?.error || 'unknown_error';
        
        if (error === 'penalty_active') {
          const penaltyUntil = data?.penalty_until || '';
          this.showPenalty(penaltyUntil);
        } else if (error === 'challenge_expired') {
          this.showError('⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте.');
        } else if (error === 'challenge_not_found') {
          this.showError('❌ Капча не найдена. Запросите новую капчу в боте.');
        } else {
          this.showError(`❌ Ошибка: ${error}`);
        }
        return;
      }

      if (data.penalty_active) {
        const penaltyUntil = data.penalty_until || '';
        this.showPenalty(penaltyUntil);
        return;
      }

      this.challenge = data.challenge || null;
      if (!this.challenge) {
        this.showError('❌ Капча не найдена');
        return;
      }

      this.renderChallenge();
      this.startTimer();
    } catch (e) {
      console.error('Failed to load captcha:', e);
      this.showError('❌ Ошибка загрузки капчи. Попробуйте позже.');
    } finally {
      this.loading = false;
    }
  }

  private renderChallenge(): void {
    if (!this.challenge) return;

    const content = this.el.querySelector('#captcha-content') as HTMLElement;
    const mapEl = this.el.querySelector('#captcha-map');
    const stepsEl = this.el.querySelector('#captcha-steps');

    // Показываем контент
    content.style.display = 'block';
    this.showStatus('', '');

    // Рендерим карту (подсказки)
    if (mapEl && this.challenge.map) {
      mapEl.innerHTML = Object.entries(this.challenge.map)
        .map(([key, value]) => `<li><strong>${key}</strong> = ${value}</li>`)
        .join('');
    }

    // Рендерим шаги (условия)
    if (stepsEl && this.challenge.steps) {
      stepsEl.innerHTML = this.challenge.steps
        .map(step => `<li>${step}</li>`)
        .join('');
    }
  }

  private startTimer(): void {
    if (!this.challenge) return;

    const timerEl = this.el.querySelector('#captcha-timer');
    if (!timerEl) return;

    const updateTimer = () => {
      if (!this.challenge) return;

      const expiresAt = new Date(this.challenge.expires_at);
      const now = new Date();
      const diff = expiresAt.getTime() - now.getTime();

      if (diff <= 0) {
        timerEl.textContent = '⏰ Время истекло';
        this.showError('⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте.');
        return;
      }

      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      timerEl.textContent = `⏳ Осталось: ${minutes}:${seconds.toString().padStart(2, '0')}`;

      setTimeout(updateTimer, 1000);
    };

    updateTimer();
  }

  private async submitAnswer(answer: string): Promise<void> {
    if (!answer.trim()) {
      alert('Введите ответ');
      return;
    }

    if (this.loading) return;

    this.loading = true;
    this.showStatus('loading', '⏳ Проверка ответа...');

    try {
      const data = await fetchApi<{ ok: boolean; error?: string }>('/api/captcha/solve', {
        method: 'POST',
        body: JSON.stringify({
          token: this.token,
          answer: answer.trim()
        })
      });

      if (data && data.ok) {
        tgService.haptic('success');
        this.showStatus('success', '✅ Капча пройдена! Ограничение снято.');
        
        // Закрываем апку через 2 секунды
        setTimeout(() => {
          tgService.close();
        }, 2000);
      } else {
        const error = data?.error || 'wrong_answer';
        
        if (error === 'wrong_answer') {
          tgService.haptic('error');
          this.showStatus('error', '❌ Неверный ответ. Попробуйте еще раз.');
        } else if (error === 'challenge_expired') {
          this.showError('⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте.');
        } else {
          this.showError(`❌ Ошибка: ${error}`);
        }
      }
    } catch (e) {
      console.error('Failed to submit captcha:', e);
      tgService.haptic('error');
      this.showStatus('error', '❌ Ошибка отправки ответа. Попробуйте еще раз.');
    } finally {
      this.loading = false;
    }
  }

  private showStatus(type: 'loading' | 'error' | 'success' | '', message: string): void {
    const statusEl = this.el.querySelector('#captcha-status') as HTMLElement;
    if (!statusEl) return;

    statusEl.className = `captcha-status ${type}`;
    statusEl.textContent = message;
    statusEl.style.display = message ? 'block' : 'none';
  }

  private showError(message: string): void {
    this.showStatus('error', message);
    const content = this.el.querySelector('#captcha-content') as HTMLElement;
    if (content) content.style.display = 'none';
  }

  private showPenalty(penaltyUntil: string): void {
    const statusEl = this.el.querySelector('#captcha-status') as HTMLElement;
    if (!statusEl) return;

    const until = new Date(penaltyUntil);
    const now = new Date();
    const diff = until.getTime() - now.getTime();

    if (diff <= 0) {
      this.showError('⏰ Блокировка истекла. Обновите страницу.');
      return;
    }

    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);

    statusEl.className = 'captcha-status penalty';
    statusEl.textContent = `🚫 Вы заблокированы за подозрительную активность. Осталось: ${hours}ч ${minutes}м`;
    statusEl.style.display = 'block';

    const content = this.el.querySelector('#captcha-content') as HTMLElement;
    if (content) content.style.display = 'none';
  }
}
