import {
  guilds,
  createGuild,
  joinGuild,
  leaveGuild,
  currentUserGuildId,
  currentUserIsOwner,
  currentUserIsAdmin,
  GUILD_AVATARS,
  GUILD_COLORS,
  Guild,
  GuildMember,
  ClanTournament,
  ClanTournamentEntry,
  loadClans,
  loadClanMembers,
  loadClanTournaments,
  loadClanTournamentLeaderboard,
  createClanTournament,
  donateToGuild,
  upgradeGuild,
  removeGuildMember,
  respondClanRequest
} from '../modules/guildsData';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';

const SHOW_GUILD_UPGRADES = true;

export class GuildsScreen {
  private el: HTMLElement;
  private view: 'list' | 'create' | 'manage' | 'rating' | 'detail' = 'list';
  private loading = false;

  // Creation State
  private newGuildName = '';
  private selectedAvatar = GUILD_AVATARS[0];
  private selectedColor = GUILD_COLORS[0];
  private selectedType: 'open' | 'invite' = 'open';
  private selectedMinLevel = 0;

  // Detail State
  private selectedGuildId: string | null = null;
  private detailLoading = false;

  // Rating State
  private expandedClanId: string | null = null;
  private memberLoadingId: string | null = null;

  // Tournament State
  private tournaments: ClanTournament[] = [];
  private activeTournament: ClanTournament | null = null;
  private activeTournamentId: string | null = null;
  private tournamentLeaderboard: ClanTournamentEntry[] = [];
  private tournamentTitle = '';
  private tournamentStarts = '';
  private tournamentEnds = '';

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
    // Load members for user's guild to get accurate count and list
    if (currentUserGuildId) {
      await loadClanMembers(currentUserGuildId);
    }
    this.loading = false;
    this.render();
  }

  private formatWeight(value: number): string {
    const safe = Number(value || 0);
    return safe.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  private formatDate(value: string): string {
    if (!value) return '';
    const raw = String(value);
    if (raw.includes('T')) {
      return raw.replace('T', ' ').slice(0, 16);
    }
    return raw.slice(0, 16);
  }

  private async loadTournaments(): Promise<void> {
    const data = await loadClanTournaments();
    this.tournaments = data.items || [];
    this.activeTournamentId = data.activeId || null;
    this.activeTournament = data.active || (this.activeTournamentId ? this.tournaments.find(t => t.id === this.activeTournamentId) || null : null);
    if (this.activeTournamentId) {
      this.tournamentLeaderboard = await loadClanTournamentLeaderboard(this.activeTournamentId);
    } else {
      this.tournamentLeaderboard = [];
    }
  }

  private async openRating(): Promise<void> {
    this.loading = true;
    this.render();
    await loadClans();
    await this.loadTournaments();
    this.expandedClanId = null;
    this.memberLoadingId = null;
    this.view = 'rating';
    this.loading = false;
    this.render();
  }

  private render(): void {
    if (this.loading) {
      this.el.innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';
      return;
    }
    if (this.view === 'rating') {
      this.renderRating();
      return;
    }
    if (currentUserGuildId) {
      this.renderManage();
      return;
    }
    if (this.view === 'create') {
      this.renderCreate();
      return;
    }
    this.renderList();
  }

  // ── LIST VIEW ──
  private renderList(): void {
    this.el.innerHTML = `
      <h1 class="page-title">АРТЕЛИ</h1>
      <div class="guilds-header">
        <button class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>
        <button class="guild-rating-btn" id="guild-rating-trigger">РЕЙТИНГ</button>
      </div>
      <div class="guild-list">
        ${guilds.map(g => `
          <div class="guild-card glass" data-id="${g.id}">
            <div class="guild-avatar" style="--border-color: ${g.borderColor}">${getIcon(g.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${g.name}</div>
              <div class="guild-meta">
                <span>⭐ Ур. ${g.level}</span>
                <span>👤 ${g.memberCount}/${g.capacity}</span>
                <span>⚖️ ${this.formatWeight(g.totalWeight)} кг</span>
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

    this.el.querySelector('#guild-rating-trigger')?.addEventListener('click', () => {
      this.openRating();
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

  private renderMemberPreview(members: GuildMember[], limit = 8): string {
    const sorted = [...(members || [])].sort((a, b) => b.totalWeight - a.totalWeight);
    const items = sorted.slice(0, limit);
    if (!items.length) {
      return '<div class="members-empty">Нет данных об участниках.</div>';
    }
    return items.map((m, idx) => `
      <div class="member-row">
        <div class="member-rank">#${idx + 1}</div>
        <div class="member-name">${m.name}${m.role === 'leader' ? ' 👑' : ''}</div>
        <div class="member-meta">Ур. ${m.level}</div>
        <div class="member-weight">${this.formatWeight(m.totalWeight)} кг</div>
      </div>
    `).join('');
  }

  private renderTournamentSection(): string {
    const active = this.activeTournament;
    const leaderboard = this.tournamentLeaderboard || [];
    const activeRange = active ? `${this.formatDate(active.startsAt)} → ${this.formatDate(active.endsAt)}` : '';
    const leaderboardHtml = leaderboard.length ? leaderboard.map((row, idx) => `
      <div class="tournament-row">
        <div class="tournament-rank">#${idx + 1}</div>
        <div class="tournament-name">${row.name}</div>
        <div class="tournament-weight">${this.formatWeight(row.totalWeight)} кг</div>
      </div>
    `).join('') : '<div class="members-empty">Пока нет улова в турнире.</div>';

    const createForm = currentUserIsAdmin ? `
      <div class="glass tournament-form">
        <p class="form-label" style="margin-bottom: 10px;">Создать турнир артелей</p>
        <div class="form-group">
          <label class="form-label">Название</label>
          <input type="text" id="tournament-title" class="form-input" maxlength="32" placeholder="Название турнира" value="${this.tournamentTitle}">
        </div>
        <div class="form-group">
          <label class="form-label">Дата начала</label>
          <input type="date" id="tournament-start" class="form-input" value="${this.tournamentStarts}">
        </div>
        <div class="form-group">
          <label class="form-label">Дата окончания</label>
          <input type="date" id="tournament-end" class="form-input" value="${this.tournamentEnds}">
        </div>
        <button class="guild-create-btn" id="tournament-create">СОЗДАТЬ ТУРНИР</button>
      </div>
    ` : '';

    return `
      <div class="tournament-block glass">
        <div class="tournament-header">
          <div>
            <div class="tournament-title">Турнир артелей</div>
            <div class="tournament-range">${active ? activeRange : 'Нет активного турнира'}</div>
          </div>
        </div>
        ${active ? `<div class="tournament-list">${leaderboardHtml}</div>` : '<div class="members-empty">Создайте турнир, чтобы начать соревнование.</div>'}
      </div>
      ${createForm}
    `;
  }

  private renderRating(): void {
    const ranked = [...guilds].sort((a, b) => b.totalWeight - a.totalWeight);
    this.el.innerHTML = `
      <h1 class="page-title">РЕЙТИНГ АРТЕЛЕЙ</h1>
      <div class="guilds-header">
        <button class="guild-leave-btn" id="rating-back">НАЗАД</button>
        <button class="guild-rating-btn" id="rating-refresh">ОБНОВИТЬ</button>
      </div>
      <div class="guild-rating-list">
        ${ranked.map((g, idx) => `
          <div class="guild-rating-card glass" data-id="${g.id}">
            <div class="guild-rank">#${idx + 1}</div>
            <div class="guild-avatar" style="--border-color: ${g.borderColor}">${getIcon(g.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${g.name}</div>
              <div class="guild-meta">
                <span>👤 ${g.memberCount}</span>
                <span>⚖️ ${this.formatWeight(g.totalWeight)} кг</span>
              </div>
            </div>
          </div>
          ${this.expandedClanId === g.id ? `
            <div class="guild-rating-members glass">
              <div class="form-label" style="margin-bottom: 8px;">Топ рыболовов</div>
              ${this.memberLoadingId === g.id ? '<div class="members-empty">Загрузка...</div>' : this.renderMemberPreview(g.members)}
            </div>
          ` : ''}
        `).join('')}
      </div>
      ${this.renderTournamentSection()}
    `;

    this.el.querySelector('#rating-back')?.addEventListener('click', () => {
      this.view = currentUserGuildId ? 'manage' : 'list';
      this.render();
      tgService.haptic('medium');
    });

    this.el.querySelector('#rating-refresh')?.addEventListener('click', () => {
      this.openRating();
      tgService.haptic('medium');
    });

    this.el.querySelectorAll('.guild-rating-card').forEach(card => {
      card.addEventListener('click', async () => {
        const id = card.getAttribute('data-id');
        if (!id) return;
        if (this.expandedClanId === id) {
          this.expandedClanId = null;
          this.render();
          return;
        }
        this.expandedClanId = id;
        const guild = guilds.find(g => g.id === id);
        if (guild && (!guild.members || guild.members.length === 0)) {
          this.memberLoadingId = id;
          this.render();
          await loadClanMembers(id);
          this.memberLoadingId = null;
        }
        this.render();
      });
    });

    const titleInput = this.el.querySelector('#tournament-title') as HTMLInputElement | null;
    if (titleInput) {
      titleInput.addEventListener('input', () => {
        this.tournamentTitle = titleInput.value;
      });
    }

    const startInput = this.el.querySelector('#tournament-start') as HTMLInputElement | null;
    if (startInput) {
      startInput.addEventListener('input', () => {
        this.tournamentStarts = startInput.value;
      });
    }

    const endInput = this.el.querySelector('#tournament-end') as HTMLInputElement | null;
    if (endInput) {
      endInput.addEventListener('input', () => {
        this.tournamentEnds = endInput.value;
      });
    }

    this.el.querySelector('#tournament-create')?.addEventListener('click', async () => {
      const title = this.tournamentTitle.trim();
      if (!title || !this.tournamentStarts || !this.tournamentEnds) {
        alert('Заполните название и даты турнира.');
        return;
      }
      const created = await createClanTournament(title, this.tournamentStarts, this.tournamentEnds);
      if (created) {
        this.tournamentTitle = '';
        this.tournamentStarts = '';
        this.tournamentEnds = '';
        await this.loadTournaments();
        this.render();
        tgService.haptic('heavy');
      } else {
        alert('Не удалось создать турнир.');
        tgService.haptic('error');
      }
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
    const isOwner = currentUserIsOwner;
    const members: GuildMember[] = [...(guild.members || [])].sort((a, b) => b.totalWeight - a.totalWeight);
    const actualMemberCount = members.length || guild.memberCount;
    const upgradeItems = guild.upgradeProgress || [];
    const upgradeBlock = SHOW_GUILD_UPGRADES ? `
      <div class="glass" style="padding: 12px; margin-bottom: 12px;">
        <p class="form-label" style="margin-bottom: 10px; color: var(--gold); font-size: 10px;">
          ${upgradeItems.length ? `Улучшение до ур. ${guild.level + 1}` : 'Максимальный уровень'}
        </p>
        ${upgradeItems.length ? `
          <div class="upgrade-section">
            ${upgradeItems.map((p, idx) => `
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
          ${isOwner ? `
            <button class="guild-create-btn" id="guild-upgrade" ${guild.canUpgrade ? '' : 'disabled'}>
              ${guild.canUpgrade ? 'УЛУЧШИТЬ' : 'НУЖНЫ РЕСУРСЫ'}
            </button>
          ` : ''}
        ` : '<div class="members-empty">Артель на максимальном уровне.</div>'}
      </div>
    ` : '';

    this.el.innerHTML = `
      <h1 class="page-title">${guild.name.toUpperCase()}</h1>

      <div class="guilds-header">
        <button class="guild-rating-btn" id="guild-rating-trigger">РЕЙТИНГ АРТЕЛЕЙ</button>
      </div>
      
      <div class="glass" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
         <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${guild.borderColor}">${getIcon(guild.avatar)}</div>
         <div class="guild-info">
           <div class="guild-name" style="font-size:17px;">Уровень ${guild.level}</div>
           <div class="guild-meta" style="font-size:10px;">${actualMemberCount}/${guild.capacity} участников</div>
         </div>
      </div>

      <div class="my-guild-stats">
        <div class="glass stat-box">
          <div class="stat-val">${guild.type === 'open' ? '🔓' : '🔒'}</div>
          <div class="stat-lab">Доступ</div>
        </div>
        <div class="glass stat-box">
          <div class="stat-val">${this.formatWeight(guild.totalWeight)} кг</div>
          <div class="stat-lab">Улов</div>
        </div>
      </div>

      <div class="glass members-panel">
        <p class="form-label" style="margin-bottom: 10px;">Участники</p>
        <div class="members-list">
          ${members.length ? members.map((m, idx) => `
            <div class="member-row">
              <div class="member-rank">#${idx + 1}</div>
              <div class="member-name">${m.name}${m.role === 'leader' ? ' 👑' : ''}</div>
              <div class="member-meta">Ур. ${m.level}</div>
              <div class="member-weight">${this.formatWeight(m.totalWeight)} кг</div>
              ${isOwner && m.role !== 'leader' ? `<button class="member-remove-btn" data-id="${m.userId}">✕</button>` : ''}
            </div>
          `).join('') : '<div class="members-empty">Пока нет участников.</div>'}
        </div>
      </div>

      ${upgradeBlock}

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
                  <button class="req-btn req-btn--no" data-id="${r.requestId}" style="width:28px; height:28px; font-size:12px;">✕</button>
                  <button class="req-btn req-btn--yes" data-id="${r.requestId}" style="width:28px; height:28px; font-size:12px;">✓</button>
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

    this.el.querySelector('#guild-rating-trigger')?.addEventListener('click', () => {
      this.openRating();
      tgService.haptic('medium');
    });

    if (SHOW_GUILD_UPGRADES) {
      this.el.querySelectorAll('.donate-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.getAttribute('data-idx')!, 10);
          const p = guild.upgradeProgress[idx];
          donateToGuild(p.item, 1).then(success => {
            tgService.haptic(success ? 'selection' : 'error');
            if (success) this.render();
          });
        });
      });

      this.el.querySelector('#guild-upgrade')?.addEventListener('click', async () => {
        const success = await upgradeGuild();
        tgService.haptic(success ? 'heavy' : 'error');
        if (success) {
          await this.init();
        }
      });
    }

    this.el.querySelectorAll('.req-btn--yes').forEach(btn => {
      btn.addEventListener('click', async () => {
        const requestId = btn.getAttribute('data-id');
        if (!requestId) return;
        const success = await respondClanRequest(requestId, 'accept');
        tgService.haptic(success ? 'heavy' : 'error');
        if (success) {
          await this.init();
        }
      });
    });

    this.el.querySelectorAll('.req-btn--no').forEach(btn => {
      btn.addEventListener('click', async () => {
        const requestId = btn.getAttribute('data-id');
        if (!requestId) return;
        const success = await respondClanRequest(requestId, 'decline');
        tgService.haptic(success ? 'medium' : 'error');
        if (success) {
          await this.init();
        }
      });
    });

    this.el.querySelectorAll('.member-remove-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const memberId = btn.getAttribute('data-id');
        if (!memberId) return;
        if (!confirm('Удалить участника из артели?')) return;
        const success = await removeGuildMember(memberId);
        tgService.haptic(success ? 'heavy' : 'error');
        if (success) {
          await this.init();
        }
      });
    });
  }
}
