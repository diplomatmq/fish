import { guilds, createGuild, joinGuild, leaveGuild, currentUserGuildId, GUILD_AVATARS, GUILD_COLORS, Guild, loadClans } from '../modules/guildsData';
import { tgService } from '../modules/telegram';
import { USER_PROFILE } from '../data';
import { getIcon } from './icons';

export class GuildsScreen {
  private el: HTMLElement;
  private view: 'list' | 'create' | 'manage' = 'list';
  private loading = false;

  // Creation State
  private newGuildName = '';
  private selectedAvatar = GUILD_AVATARS[0];
  private selectedColor = GUILD_COLORS[0];
  private selectedType: 'open' | 'invite' = 'open';
  private selectedMinLevel = 0;

  constructor() {
    this.el = this.buildShell();
  }

  getElement(): HTMLElement { return this.el; }

  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id = 'screen-guilds';
    s.className = 'screen guilds-screen';
    s.setAttribute('role', 'main');
    return s;
  }

  async init(): Promise<void> {
    this.loading = true;
    this.render();
    await loadClans();
    this.loading = false;
    this.render();
  }

  private render(): void {
    if (this.loading) {
      this.el.innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';
      return;
    }
    if (currentUserGuildId) {
      this.renderManage();
    } else if (this.view === 'create') {
      this.renderCreate();
    } else {
      this.renderList();
    }
  }

  // ── LIST VIEW ──
  private renderList(): void {
    this.el.innerHTML = `
      <h1 class="page-title">АРТЕЛИ</h1>
      <div class="guilds-header">
        <button class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>
      </div>
      <div class="guild-list">
        ${guilds.map(g => `
          <div class="guild-card glass" data-id="${g.id}">
            <div class="guild-avatar" style="--border-color: ${g.borderColor}">${getIcon(g.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${g.name}</div>
              <div class="guild-meta">
                <span>⭐ Ур. ${g.level}</span>
                <span>👤 ${g.members.length}/${g.capacity}</span>
                <span>${g.type === 'open' ? '🔓 Открыто' : '🔒 По приглашению'}</span>
                ${g.type === 'open' && g.minLevel > 0 ? `<span style="color: var(--gold)">⬆️ Ур. ${g.minLevel}+</span>` : ''}
              </div>
            </div>
            <button class="adv-play-btn" style="padding: 8px 12px; font-size: 9px;">${g.type === 'open' ? 'ВСТУПИТЬ' : 'ЗАЯВКА'}</button>
          </div>
        `).join('')}
      </div>
    `;

    this.el.querySelector('#guild-create-trigger')?.addEventListener('click', () => {
      this.view = 'create';
      this.render();
      tgService.haptic('medium');
    });

    this.el.querySelectorAll('.guild-card').forEach(card => {
      card.querySelector('button')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = card.getAttribute('data-id')!;
        const success = await joinGuild(id);
        if (success) {
          tgService.haptic('heavy');
          const g = guilds.find(x => x.id === id);
          if (g?.type === 'invite') {
             alert('Заявка отправлена!');
          } else {
             await this.init(); // Refresh to show manage view
          }
        } else {
          tgService.haptic('error');
          alert('Не удалось вступить в артель.');
        }
      });
    });
  }

  // ── CREATE VIEW ──
  private renderCreate(): void {
    this.el.innerHTML = `
      <h1 class="page-title">НОВАЯ АРТЕЛЬ</h1>
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14 симв.)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" placeholder="Введите название..." value="${this.newGuildName}">
        </div>

        <div class="form-group">
          <label class="form-label">Выберите герб</label>
          <div class="avatar-grid">
            ${GUILD_AVATARS.map(a => `
              <div class="avatar-opt ${this.selectedAvatar === a ? 'is-selected' : ''}" data-val="${a}">${getIcon(a)}</div>
            `).join('')}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Цвет каемки</label>
          <div class="color-row">
            ${GUILD_COLORS.map(c => `
              <div class="color-opt ${this.selectedColor === c ? 'is-selected' : ''}" data-val="${c}" style="background:${c}"></div>
            `).join('')}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Тип входа</label>
          <div class="type-row">
            <div class="type-opt ${this.selectedType === 'open' ? 'is-selected' : ''}" data-val="open">СВОБОДНЫЙ</div>
            <div class="type-opt ${this.selectedType === 'invite' ? 'is-selected' : ''}" data-val="invite">ПО ПРИГЛАШЕНИЮ</div>
          </div>
        </div>

        ${this.selectedType === 'open' ? `
        <div class="form-group">
          <label class="form-label" id="min-level-label">Минимальный уровень: ${this.selectedMinLevel}</label>
          <input type="range" id="min-level-slider" min="0" max="100" value="${this.selectedMinLevel}" style="width:100%; accent-color:var(--gold);">
        </div>
        ` : ''}

        <div style="text-align:center; margin: 15px 0; color: var(--gold); font-weight: bold; font-size: 14px;">
           Стоимость: 100 000 🪙
        </div>

        <div style="display:flex; gap:10px; margin-top:10px;">
          <button class="guild-leave-btn" id="create-cancel" style="flex:1">ОТМЕНА</button>
          <button class="guild-create-btn" id="create-confirm" style="flex:2">СОЗДАТЬ</button>
        </div>
      </div>
    `;

    const nameInput = this.el.querySelector('#guild-name-input') as HTMLInputElement;
    nameInput.addEventListener('input', () => { this.newGuildName = nameInput.value; });

    this.el.querySelectorAll('.avatar-opt').forEach(opt => {
      opt.addEventListener('click', () => {
        this.selectedAvatar = opt.getAttribute('data-val')!;
        this.render();
      });
    });

    this.el.querySelectorAll('.color-opt').forEach(opt => {
      opt.addEventListener('click', () => {
        this.selectedColor = opt.getAttribute('data-val')!;
        this.render();
      });
    });

    this.el.querySelectorAll('.type-opt').forEach(opt => {
      opt.addEventListener('click', () => {
        this.selectedType = opt.getAttribute('data-val') as any;
        this.render();
      });
    });

    const levelSlider = this.el.querySelector('#min-level-slider') as HTMLInputElement;
    if (levelSlider) {
      levelSlider.addEventListener('input', () => {
        this.selectedMinLevel = parseInt(levelSlider.value);
        const label = this.el.querySelector('#min-level-label');
        if (label) label.textContent = `Минимальный уровень: ${this.selectedMinLevel}`;
      });
    }

    this.el.querySelector('#create-cancel')?.addEventListener('click', () => {
      this.view = 'list';
      this.render();
    });

    this.el.querySelector('#create-confirm')?.addEventListener('click', async () => {
      if (this.newGuildName.trim().length < 3) {
        alert('Слишком короткое название!');
        return;
      }
      const newGuild = await createGuild({
        name: this.newGuildName,
        avatar: this.selectedAvatar,
        borderColor: this.selectedColor,
        type: this.selectedType,
        minLevel: this.selectedMinLevel
      });
      
      if (newGuild) {
        tgService.haptic('heavy');
        await this.init(); // Refresh to show manage view
      } else {
        tgService.haptic('error');
        alert('Ошибка при создании артели.');
      }
    });
  }

  // ── MANAGE VIEW ──
  private renderManage(): void {
    const guild = guilds.find(g => g.id === currentUserGuildId)!;
    const isOwner = guild.members.find(m => m.userId === 'current-user')?.role === 'owner';

    this.el.innerHTML = `
      <h1 class="page-title">${guild.name.toUpperCase()}</h1>
      
      <div class="glass" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
         <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${guild.borderColor}">${getIcon(guild.avatar)}</div>
         <div class="guild-info">
           <div class="guild-name" style="font-size:17px;">Уровень ${guild.level}</div>
           <div class="guild-meta" style="font-size:10px;">${guild.members.length}/${guild.capacity} участников</div>
         </div>
      </div>

      <div class="my-guild-stats">
        <div class="glass stat-box">
          <div class="stat-val">${guild.type === 'open' ? '🔓' : '🔒'}</div>
          <div class="stat-lab">Доступ</div>
        </div>
        <div class="glass stat-box">
          <div class="stat-val">⭐</div>
          <div class="stat-lab">Топ 100</div>
        </div>
      </div>

      <div class="glass" style="padding: 12px; margin-bottom: 12px;">
        <p class="form-label" style="margin-bottom: 10px; color: var(--gold); font-size: 10px;">Улучшение до ур. ${guild.level + 1}</p>
        <div class="upgrade-section">
          ${guild.upgradeProgress.map((p, idx) => `
            <div class="upgrade-item">
              <div class="upgrade-main">
                <div class="upgrade-labels">
                  <span>${p.item}</span>
                  <span>${p.current}/${p.required}</span>
                </div>
                <div class="upgrade-bar">
                  <div class="upgrade-fill" style="width: ${(p.current / p.required) * 100}%"></div>
                </div>
              </div>
              <button class="donate-btn" data-idx="${idx}">ВКЛАД</button>
            </div>
          `).join('')}
        </div>
      </div>

      ${isOwner && guild.requests.length > 0 ? `
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки на вступление</p>
          <div class="requests-list">
            ${guild.requests.map(r => `
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${r.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${r.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${r.level}</div>
                </div>
                <div class="req-btns">
                  <button class="req-btn req-btn--no" data-id="${r.userId}" style="width:28px; height:28px; font-size:12px;">✕</button>
                  <button class="req-btn req-btn--yes" data-id="${r.userId}" style="width:28px; height:28px; font-size:12px;">✓</button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div class="guild-actions">
        <button class="guild-leave-btn" id="btn-leave" style="height:44px; font-size:11px;">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `;

    this.el.querySelector('#btn-leave')?.addEventListener('click', () => {
      if (confirm('Вы уверены, что хотите покинуть артель?')) {
        leaveGuild();
        tgService.haptic('medium');
        this.render();
      }
    });

    this.el.querySelectorAll('.donate-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.getAttribute('data-idx')!, 10);
        const p = guild.upgradeProgress[idx];
        p.current = Math.min(p.required, p.current + Math.floor(Math.random() * 5) + 1);
        tgService.haptic('selection');
        this.render();
      });
    });

    this.el.querySelectorAll('.req-btn--yes').forEach(btn => {
      btn.addEventListener('click', () => {
        const uid = btn.getAttribute('data-id');
        const reqIndex = guild.requests.findIndex(r => r.userId === uid);
        if (reqIndex !== -1) {
          const r = guild.requests.splice(reqIndex, 1)[0];
          guild.members.push({ userId: r.userId, name: r.name, level: r.level, role: 'member' });
          tgService.haptic('heavy');
          this.render();
        }
      });
    });

    this.el.querySelectorAll('.req-btn--no').forEach(btn => {
      btn.addEventListener('click', () => {
        const uid = btn.getAttribute('data-id');
        guild.requests = guild.requests.filter(r => r.userId !== uid);
        tgService.haptic('medium');
        this.render();
      });
    });
  }
}
