import {
  guilds,
  getMyGuild,
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
  guildMemberCount,
  guildCapacityForLevel,
  guildExcessMemberIds,
  loadClanTournaments,
  loadClanTournamentLeaderboard,
  loadClanTournamentMembers,
  createClanTournament,
  donateToGuild,
  upgradeGuild,
  removeGuildMember,
  respondClanRequest
} from '../modules/guildsData';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';

const SHOW_GUILD_UPGRADES = true;

type GuildTab = 'my' | 'list' | 'rating' | 'tournament' | 'create';

export class GuildsScreen {
  private el: HTMLElement;
  private modalHost: HTMLElement;
  private tab: GuildTab = 'list';
  private loading = false;

  private newGuildName = '';
  private selectedAvatar = GUILD_AVATARS[0];
  private selectedColor = GUILD_COLORS[0];
  private selectedType: 'open' | 'invite' = 'open';
  private selectedMinLevel = 0;

  private visibleTournament: ClanTournament | null = null;
  private tournamentPhase: 'active' | 'grace' | null = null;
  private tournamentLeaderboard: ClanTournamentEntry[] = [];

  private showAdminTournamentForm = false;
  private tournamentTitle = '';
  private tournamentStarts = '';
  private tournamentEnds = '';

  private clanModalGuildId: string | null = null;
  private clanModalGuildName = '';
  private clanModalMembers: GuildMember[] = [];
  private clanModalLoading = false;
  private clanModalTournament = false;

  constructor() {
    this.el = this.buildShell();
    this.modalHost = document.createElement('div');
    this.modalHost.id = 'guild-modals-root';
    this.modalHost.className = 'guild-modals-root';
    document.body.appendChild(this.modalHost);
    document.body.classList.remove('guild-modal-open');
  }

  getElement(): HTMLElement { return this.el; }

  /** Закрыть модалки (при уходе с вкладки — иначе блокируется всё приложение). */
  closeModals(): void {
    this.clanModalGuildId = null;
    this.clanModalMembers = [];
    this.showAdminTournamentForm = false;
    this.renderModals();
  }

  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id = 'screen-guilds';
    s.className = 'screen guilds-screen';
    s.setAttribute('role', 'main');
    return s;
  }

  async init(): Promise<void> {
    this.closeModals();
    this.loading = true;
    this.tab = currentUserGuildId ? 'my' : 'list';
    this.render();
    await loadClans();
    if (currentUserGuildId) {
      await loadClanMembers(currentUserGuildId);
    }
    await this.refreshTournaments();
    this.loading = false;
    this.render();
  }

  private async refreshTournaments(): Promise<void> {
    const data = await loadClanTournaments();
    this.visibleTournament = data.visible || null;
    this.tournamentPhase = data.phase;
    if (this.visibleTournament) {
      this.tournamentLeaderboard = await loadClanTournamentLeaderboard(this.visibleTournament.id);
    } else {
      this.tournamentLeaderboard = [];
      if (this.tab === 'tournament') this.tab = 'rating';
    }
  }

  private formatWeight(value: number): string {
    return Number(value || 0).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  private formatDate(value: string): string {
    if (!value) return '';
    const raw = String(value);
    return raw.includes('T') ? raw.replace('T', ' ').slice(0, 16) : raw.slice(0, 16);
  }

  private showTournamentTab(): boolean {
    return Boolean(this.visibleTournament);
  }

  private renderTabs(): string {
    const tabs: { id: GuildTab; label: string }[] = [];
    if (currentUserGuildId) tabs.push({ id: 'my', label: 'МОЯ' });
    tabs.push({ id: 'list', label: 'АРТЕЛИ' });
    tabs.push({ id: 'rating', label: 'РЕЙТИНГ' });
    if (this.showTournamentTab()) tabs.push({ id: 'tournament', label: 'ТУРНИР' });

    return `
      <div class="guild-tabs">
        ${tabs.map(t => `
          <button type="button" class="guild-tab ${this.tab === t.id ? 'is-active' : ''}" data-tab="${t.id}">${t.label}</button>
        `).join('')}
      </div>
    `;
  }

  private render(): void {
    if (this.tab === 'create') {
      this.renderCreate();
      return;
    }

    const adminBar = currentUserIsAdmin ? `
      <button type="button" class="guild-admin-create-btn" id="guild-admin-tournament">
        🏆 СОЗДАТЬ ТУРНИР АРТЕЛЕЙ
      </button>
    ` : '';

    const inner = this.loading
      ? '<div class="guild-loading">Загрузка...</div>'
      : `<div class="guild-tab-content">
          ${this.tab === 'my' ? this.renderManageContent() : ''}
          ${this.tab === 'list' ? this.renderListContent() : ''}
          ${this.tab === 'rating' ? this.renderRatingContent() : ''}
          ${this.tab === 'tournament' ? this.renderTournamentContent() : ''}
        </div>`;

    this.el.innerHTML = `
      <div class="guilds-header">
        <h1 class="page-title">АРТЕЛИ</h1>
      </div>
      <div class="guilds-toolbar">
        ${this.renderTabs()}
        ${adminBar}
      </div>
      <div class="guild-container">
        <div class="guild-content">
          ${inner}
        </div>
      </div>
    `;

    this.bindTabs();
    this.bindTabContent();
    this.bindAdminFab();
    this.renderModals();
  }

  private renderModals(): void {
    if (this.showAdminTournamentForm) {
      this.modalHost.innerHTML = this.renderAdminTournamentModalHtml();
      this.bindAdminTournamentModal();
    } else if (this.clanModalGuildId) {
      this.modalHost.innerHTML = this.renderClanModalHtml();
      this.bindClanModal();
    } else {
      this.modalHost.innerHTML = '';
    }
    document.body.classList.toggle('guild-modal-open', Boolean(this.modalHost.innerHTML));
  }

  private bindTabs(): void {
    this.el.querySelectorAll('.guild-tab').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tab = btn.getAttribute('data-tab') as GuildTab;
        if (!tab || tab === this.tab) return;
        this.tab = tab;
        tgService.haptic('medium');
        if (tab === 'rating' || tab === 'tournament' || tab === 'my') {
          this.loading = true;
          this.render();
          await loadClans();
          await this.refreshTournaments();
          if (currentUserGuildId) {
            await loadClanMembers(currentUserGuildId);
          }
          this.loading = false;
        }
        this.render();
      });
    });
  }

  private bindAdminFab(): void {
    this.el.querySelector('#guild-admin-tournament')?.addEventListener('click', () => {
      this.clanModalGuildId = null;
      this.clanModalMembers = [];
      this.showAdminTournamentForm = true;
      this.renderModals();
      tgService.haptic('medium');
    });
  }

  // ── LIST ──
  private renderListContent(): string {
    const list = guilds.length ? guilds.map(g => `
      <div class="guild-card glass" data-id="${g.id}">
        <div class="guild-avatar" style="--border-color: ${g.borderColor}">${getIcon(g.avatar)}</div>
        <div class="guild-info">
          <div class="guild-name">${g.name}${g.id === currentUserGuildId ? ' <span class="guild-you-badge">вы</span>' : ''}</div>
          <div class="guild-meta">
            <span>⭐ Ур. ${g.level}</span>
            <span>👤 ${guildMemberCount(g.members, g.memberCount)}/${g.capacity}</span>
            <span>⚖️ ${this.formatWeight(g.totalWeight)} кг</span>
            <span>${g.type === 'open' ? '🔓' : '🔒'}</span>
          </div>
        </div>
        ${g.id !== currentUserGuildId ? `
          <button type="button" class="adv-play-btn guild-join-btn" data-id="${g.id}" style="padding: 8px 12px; font-size: 9px;">
            ${g.type === 'open' ? 'ВСТУПИТЬ' : 'ЗАЯВКА'}
          </button>
        ` : ''}
      </div>
    `).join('') : '<div class="members-empty">Пока нет артелей.</div>';

    return `
      <div class="guilds-header">
        ${!currentUserGuildId ? '<button type="button" class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>' : ''}
      </div>
      <div class="guild-list">${list}</div>
    `;
  }

  private bindTabContent(): void {
    if (this.tab === 'list') this.bindList();
    if (this.tab === 'my') this.bindManage();
    if (this.tab === 'rating') this.bindRating();
    if (this.tab === 'tournament') this.bindTournament();
  }

  private bindList(): void {
    this.el.querySelector('#guild-create-trigger')?.addEventListener('click', () => {
      this.tab = 'create';
      this.render();
      tgService.haptic('medium');
    });

    this.el.querySelectorAll('.guild-join-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id')!;
        const success = await joinGuild(id);
        if (success) {
          tgService.haptic('heavy');
          const g = guilds.find(x => x.id === id);
          if (g?.type === 'invite') {
            alert('Заявка отправлена!');
          } else {
            this.tab = 'my';
            await this.init();
          }
        } else {
          tgService.haptic('error');
        }
      });
    });
  }

  // ── RATING ──
  private renderRatingContent(): string {
    const ranked = [...guilds].sort((a, b) => b.totalWeight - a.totalWeight);
    return `
      <p class="guild-section-hint">Рейтинг по суммарному весу улова всех участников артели</p>
      <div class="guild-total-weight-hero glass">
        <div class="hero-label">Топ артелей по улову</div>
        <div class="hero-sub">Вес сохраняется в артели, даже если рыбак вышел</div>
      </div>
      <div class="guild-rating-list">
        ${ranked.map((g, idx) => `
          <button type="button" class="guild-rating-card glass" data-id="${g.id}" data-tournament="0">
            <div class="guild-rank">#${idx + 1}</div>
            <div class="guild-avatar" style="--border-color: ${g.borderColor}">${getIcon(g.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${g.name}</div>
              <div class="guild-meta">
                <span>👤 ${guildMemberCount(g.members, g.memberCount)}</span>
                <span class="guild-weight-highlight">⚖️ ${this.formatWeight(g.totalWeight)} кг</span>
              </div>
            </div>
          </button>
        `).join('')}
      </div>
    `;
  }

  private bindRating(): void {
    this.el.querySelectorAll('.guild-rating-card[data-tournament="0"]').forEach(card => {
      card.addEventListener('click', async () => {
        const id = card.getAttribute('data-id');
        if (!id) return;
        const guild = guilds.find(g => g.id === id);
        this.clanModalGuildId = id;
        this.clanModalGuildName = guild?.name || 'Артель';
        this.clanModalTournament = false;
        this.clanModalLoading = true;
        this.clanModalMembers = [];
        this.renderModals();
        await loadClanMembers(id);
        const g2 = guilds.find(g => g.id === id);
        this.clanModalMembers = g2?.members || [];
        this.clanModalLoading = false;
        this.renderModals();
      });
    });
  }

  // ── TOURNAMENT ──
  private renderTournamentContent(): string {
    const t = this.visibleTournament;
    if (!t) return '<div class="members-empty">Турнир недоступен.</div>';

    const phaseLabel = this.tournamentPhase === 'grace'
      ? 'Турнир завершён — итоги ещё сутки'
      : 'Идёт турнир';
    const range = `${this.formatDate(t.startsAt)} → ${this.formatDate(t.endsAt)}`;
    const rows = this.tournamentLeaderboard.length
      ? this.tournamentLeaderboard.map((row, idx) => `
          <button type="button" class="tournament-row glass" data-id="${row.clanId}" data-tournament="1">
            <div class="tournament-rank">#${idx + 1}</div>
            <div class="tournament-name">${row.name}</div>
            <div class="tournament-weight">${this.formatWeight(row.totalWeight)} кг</div>
          </button>
        `).join('')
      : '<div class="members-empty">Пока нет улова за период турнира.</div>';

    return `
      <div class="tournament-block glass">
        <div class="tournament-header">
          <div>
            <div class="tournament-title">${t.title}</div>
            <div class="tournament-range">${range}</div>
            <div class="tournament-phase-badge">${phaseLabel}</div>
          </div>
        </div>
        <p class="guild-section-hint">Учитывается только улов с ${this.formatDate(t.startsAt)} по ${this.formatDate(t.endsAt)}</p>
        <div class="tournament-list">${rows}</div>
      </div>
    `;
  }

  private bindTournament(): void {
    this.el.querySelectorAll('[data-tournament="1"]').forEach(card => {
      card.addEventListener('click', async () => {
        const id = card.getAttribute('data-id');
        if (!id || !this.visibleTournament) return;
        const row = this.tournamentLeaderboard.find(r => r.clanId === id);
        this.clanModalGuildId = id;
        this.clanModalGuildName = row?.name || 'Артель';
        this.clanModalTournament = true;
        this.clanModalLoading = true;
        this.clanModalMembers = [];
        this.renderModals();
        this.clanModalMembers = await loadClanTournamentMembers(id, this.visibleTournament.id);
        this.clanModalLoading = false;
        this.renderModals();
      });
    });
  }

  // ── CLAN MODAL (on document.body) ──
  private renderClanModalHtml(): string {
    const weightLabel = this.clanModalTournament ? 'Улов за турнир' : 'Улов в артели';
    const membersHtml = this.clanModalLoading
      ? '<div class="members-empty">Загрузка...</div>'
      : (this.clanModalMembers.length
        ? [...this.clanModalMembers].sort((a, b) => b.totalWeight - a.totalWeight).map((m, idx) => `
            <div class="member-row">
              <div class="member-rank">#${idx + 1}</div>
              <div class="member-name">${m.name}${m.role === 'leader' ? ' 👑' : ''}</div>
              <div class="member-meta">Ур. ${m.level}</div>
              <div class="member-weight">${this.formatWeight(m.totalWeight)} кг</div>
            </div>
          `).join('')
        : '<div class="members-empty">Нет участников.</div>');

    return `
      <div class="guild-modal-backdrop" id="clan-modal-backdrop">
        <div class="guild-modal-sheet" role="dialog" aria-modal="true">
          <div class="guild-modal-handle"></div>
          <div class="guild-modal-header">
            <div class="guild-modal-title">${this.clanModalGuildName}</div>
            <button type="button" class="guild-modal-close" id="clan-modal-close" aria-label="Закрыть">✕</button>
          </div>
          <p class="form-label guild-modal-sub">Участники · ${weightLabel}</p>
          <div class="members-list modal-members">${membersHtml}</div>
        </div>
      </div>
    `;
  }

  private bindClanModal(): void {
    const close = () => {
      this.clanModalGuildId = null;
      this.clanModalMembers = [];
      this.renderModals();
    };
    this.modalHost.querySelector('#clan-modal-close')?.addEventListener('click', close);
    this.modalHost.querySelector('#clan-modal-backdrop')?.addEventListener('click', (e) => {
      if (e.target === e.currentTarget) close();
    });
    this.modalHost.querySelector('.guild-modal-sheet')?.addEventListener('click', (e) => e.stopPropagation());
  }

  // ── ADMIN TOURNAMENT MODAL ──
  private renderAdminTournamentModalHtml(): string {
    return `
      <div class="guild-modal-backdrop" id="admin-tournament-backdrop">
        <div class="guild-modal-sheet tournament-form" role="dialog" aria-modal="true">
          <div class="guild-modal-handle"></div>
          <div class="guild-modal-header">
            <div class="guild-modal-title">Новый турнир</div>
            <button type="button" class="guild-modal-close" id="admin-tournament-close" aria-label="Закрыть">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">Название</label>
            <input type="text" id="tournament-title" class="form-input" maxlength="32" placeholder="Название" value="${this.tournamentTitle}">
          </div>
          <div class="form-group">
            <label class="form-label">Начало</label>
            <input type="date" id="tournament-start" class="form-input" value="${this.tournamentStarts}">
          </div>
          <div class="form-group">
            <label class="form-label">Конец</label>
            <input type="date" id="tournament-end" class="form-input" value="${this.tournamentEnds}">
          </div>
          <button type="button" class="guild-create-btn" id="tournament-create">СОЗДАТЬ</button>
        </div>
      </div>
    `;
  }

  private bindAdminTournamentModal(): void {
    const close = () => {
      this.showAdminTournamentForm = false;
      this.renderModals();
    };
    this.modalHost.querySelector('#admin-tournament-close')?.addEventListener('click', close);
    this.modalHost.querySelector('#admin-tournament-backdrop')?.addEventListener('click', (e) => {
      if (e.target === e.currentTarget) close();
    });
    this.modalHost.querySelector('.guild-modal-sheet')?.addEventListener('click', (e) => e.stopPropagation());

    const titleInput = this.modalHost.querySelector('#tournament-title') as HTMLInputElement | null;
    titleInput?.addEventListener('input', () => { this.tournamentTitle = titleInput.value; });

    const startInput = this.modalHost.querySelector('#tournament-start') as HTMLInputElement | null;
    startInput?.addEventListener('input', () => { this.tournamentStarts = startInput.value; });

    const endInput = this.modalHost.querySelector('#tournament-end') as HTMLInputElement | null;
    endInput?.addEventListener('input', () => { this.tournamentEnds = endInput.value; });

    this.modalHost.querySelector('#tournament-create')?.addEventListener('click', async () => {
      const title = this.tournamentTitle.trim();
      if (!title || !this.tournamentStarts || !this.tournamentEnds) {
        alert('Заполните название и даты.');
        return;
      }
      const created = await createClanTournament(title, this.tournamentStarts, this.tournamentEnds);
      if (created) {
        this.tournamentTitle = '';
        this.tournamentStarts = '';
        this.tournamentEnds = '';
        this.showAdminTournamentForm = false;
        await this.refreshTournaments();
        this.tab = 'tournament';
        tgService.haptic('heavy');
        this.render();
      } else {
        alert('Не удалось создать турнир.');
        tgService.haptic('error');
      }
    });
  }

  // ── MANAGE (MY GUILD) ──
  private renderManageContent(): string {
    const guild = getMyGuild();
    if (!guild) {
      return '<div class="members-empty">Вы не состоите в артели.</div>';
    }

    const isOwner = currentUserIsOwner;
    const members = [...(guild.members || [])];
    const actualMemberCount = guildMemberCount(members, guild.memberCount);
    const excessIds = isOwner ? guildExcessMemberIds(members, guild.capacity) : new Set<string>();
    const excessCount = excessIds.size;
    const membersSorted = [...members].sort((a, b) => {
      const ta = a.joinedAt ? new Date(a.joinedAt).getTime() : 0;
      const tb = b.joinedAt ? new Date(b.joinedAt).getTime() : 0;
      return ta - tb;
    });
    const upgradeItems = guild.upgradeProgress || [];
    const nextCapacity = guildCapacityForLevel(guild.level + 1);
    const rankIdx = [...guilds].sort((a, b) => b.totalWeight - a.totalWeight).findIndex(g => g.id === guild.id);
    const rankLabel = rankIdx >= 0 ? `#${rankIdx + 1}` : '—';

    const upgradeBlock = SHOW_GUILD_UPGRADES ? `
      <div class="glass" style="padding: 12px; margin-bottom: 12px;">
        <p class="form-label" style="margin-bottom: 10px; color: var(--gold); font-size: 10px;">
          ${upgradeItems.length
            ? `Улучшение до ур. ${guild.level + 1} · лимит ${nextCapacity} участников`
            : 'Максимальный уровень артели'}
        </p>
        ${upgradeItems.length ? `
          <p class="guild-section-hint" style="margin-bottom:8px;">Сдайте мусор из инвентаря в склад артели, затем улучшите.</p>
          <div class="upgrade-section">
            ${upgradeItems.map((p, idx) => {
              const pct = p.required > 0 ? Math.min(100, (p.current / p.required) * 100) : 0;
              return `
              <div class="upgrade-item">
                <div class="upgrade-main">
                  <div class="upgrade-labels"><span>${p.item}</span><span>${p.current}/${p.required}</span></div>
                  <div class="upgrade-bar"><div class="upgrade-fill" style="width: ${pct}%"></div></div>
                </div>
                <button type="button" class="donate-btn" data-idx="${idx}">+1</button>
              </div>
            `;
            }).join('')}
          </div>
          ${isOwner ? `
            <div class="guild-upgrade-actions">
              <button type="button" class="guild-create-btn" id="guild-upgrade" ${guild.canUpgrade ? '' : 'disabled'}>
                ${guild.canUpgrade ? `УЛУЧШИТЬ ДО УР. ${guild.level + 1}` : 'СНАЧАЛА СОБЕРИТЕ РЕСУРСЫ'}
              </button>
            </div>
          ` : '<p class="guild-section-hint">Вклады могут делать все участники. Улучшает лидер.</p>'}
        ` : '<div class="members-empty">Артель на максимальном уровне.</div>'}
      </div>
    ` : '';

    return `
      <div class="glass guild-my-header" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${guild.borderColor}">${getIcon(guild.avatar)}</div>
        <div class="guild-info">
          <div class="guild-name" style="font-size:17px;">${guild.name}</div>
          <div class="guild-meta" style="font-size:10px;">Ур. ${guild.level} · ${actualMemberCount}/${guild.capacity} участников</div>
        </div>
      </div>

      <div class="guild-catch-hero glass">
        <div class="catch-hero-value">${this.formatWeight(guild.totalWeight)} <span>кг</span></div>
        <div class="catch-hero-label">Общий улов артели</div>
        <div class="catch-hero-fish">🐟 ${guild.totalFish || 0} рыб</div>
      </div>

      <div class="my-guild-stats">
        <div class="glass stat-box">
          <div class="stat-val">${guild.type === 'open' ? '🔓' : '🔒'}</div>
          <div class="stat-lab">Доступ</div>
        </div>
        <div class="glass stat-box">
          <div class="stat-val">${rankLabel}</div>
          <div class="stat-lab">В рейтинге</div>
        </div>
      </div>

      ${upgradeBlock}

      <div class="glass members-panel">
        <p class="form-label" style="margin-bottom: 10px;">Участники</p>
        ${excessCount > 0 ? `
          <div class="guild-over-capacity-banner">
            Превышен лимит на ${excessCount} чел. Исключите последних вступивших (отмечены ниже).
          </div>
        ` : ''}
        <div class="members-list">
          ${membersSorted.length ? membersSorted.map((m, idx) => `
            <div class="member-row ${excessIds.has(m.userId) ? 'member-row--excess' : ''}">
              <div class="member-rank">#${idx + 1}</div>
              <div class="member-name">${m.name}${m.role === 'leader' ? ' 👑' : ''}${excessIds.has(m.userId) ? ' <span style="color:#ff8a6a;font-size:9px">лишний</span>' : ''}</div>
              <div class="member-meta">Ур. ${m.level}</div>
              <div class="member-weight">${this.formatWeight(m.totalWeight)} кг</div>
              ${isOwner && m.role !== 'leader' ? `<button type="button" class="member-remove-btn" data-id="${m.userId}" title="Исключить">✕</button>` : ''}
            </div>
          `).join('') : '<div class="members-empty">Пока нет участников.</div>'}
        </div>
      </div>

      ${isOwner && guild.requests.length > 0 ? `
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки</p>
          <div class="requests-list">
            ${guild.requests.map(r => `
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${r.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${r.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${r.level}</div>
                </div>
                <div class="req-btns">
                  <button type="button" class="req-btn req-btn--no" data-req="${r.requestId}">✕</button>
                  <button type="button" class="req-btn req-btn--yes" data-req="${r.requestId}">✓</button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <div class="guild-actions">
        <button type="button" class="guild-leave-btn" id="btn-leave">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `;
  }

  private bindManage(): void {
    const guild = getMyGuild();
    if (!guild) return;

    this.el.querySelector('#btn-leave')?.addEventListener('click', async () => {
      if (!confirm('Покинуть артель? Ваш улов останется в статистике этой артели.')) return;
      await leaveGuild();
      tgService.haptic('medium');
      this.tab = 'list';
      await this.init();
    });

    if (SHOW_GUILD_UPGRADES) {
      this.el.querySelectorAll('.donate-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.getAttribute('data-idx')!, 10);
          const p = guild.upgradeProgress[idx];
          donateToGuild(p.item, 1).then(async success => {
            tgService.haptic(success ? 'selection' : 'error');
            if (success) await this.init();
          });
        });
      });

      this.el.querySelector('#guild-upgrade')?.addEventListener('click', async () => {
        const success = await upgradeGuild();
        tgService.haptic(success ? 'heavy' : 'error');
        if (success) await this.init();
      });
    }

    this.el.querySelectorAll('.req-btn--yes').forEach(btn => {
      btn.addEventListener('click', async () => {
        const requestId = btn.getAttribute('data-req');
        if (!requestId) return;
        if (await respondClanRequest(requestId, 'accept')) await this.init();
      });
    });

    this.el.querySelectorAll('.req-btn--no').forEach(btn => {
      btn.addEventListener('click', async () => {
        const requestId = btn.getAttribute('data-req');
        if (!requestId) return;
        if (await respondClanRequest(requestId, 'decline')) await this.init();
      });
    });

    this.el.querySelectorAll('.member-remove-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const memberId = btn.getAttribute('data-id');
        if (!memberId || !confirm('Удалить участника?')) return;
        if (await removeGuildMember(memberId)) await this.init();
      });
    });
  }

  // ── CREATE ──
  private renderCreate(): void {
    this.el.innerHTML = `
      <div class="guilds-header">
        <h1 class="page-title">НОВАЯ АРТЕЛЬ</h1>
      </div>
      <div class="guild-container">
        <div class="guild-content">
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" value="${this.newGuildName}">
        </div>
        <div class="form-group">
          <label class="form-label">Герб</label>
          <div class="avatar-grid">
            ${GUILD_AVATARS.map(a => `<div class="avatar-opt ${this.selectedAvatar === a ? 'is-selected' : ''}" data-val="${a}">${getIcon(a)}</div>`).join('')}
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Цвет</label>
          <div class="color-row">
            ${GUILD_COLORS.map(c => `<div class="color-opt ${this.selectedColor === c ? 'is-selected' : ''}" data-val="${c}" style="background:${c}"></div>`).join('')}
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Вход</label>
          <div class="type-row">
            <div class="type-opt ${this.selectedType === 'open' ? 'is-selected' : ''}" data-val="open">СВОБОДНЫЙ</div>
            <div class="type-opt ${this.selectedType === 'invite' ? 'is-selected' : ''}" data-val="invite">ПО ПРИГЛАШЕНИЮ</div>
          </div>
        </div>
        ${this.selectedType === 'open' ? `
        <div class="form-group">
          <label class="form-label" id="min-level-label">Мин. уровень: ${this.selectedMinLevel}</label>
          <input type="range" id="min-level-slider" min="0" max="100" value="${this.selectedMinLevel}" style="width:100%; accent-color:var(--gold);">
        </div>` : ''}
        <div style="text-align:center; margin:15px 0; color:var(--gold); font-weight:bold;">Стоимость: 100 000 🪙</div>
        <div style="display:flex; gap:10px;">
          <button type="button" class="guild-leave-btn" id="create-cancel" style="flex:1">ОТМЕНА</button>
          <button type="button" class="guild-create-btn" id="create-confirm" style="flex:2">СОЗДАТЬ</button>
        </div>
      </div>
        </div>
      </div>
    `;

    const nameInput = this.el.querySelector('#guild-name-input') as HTMLInputElement;
    nameInput?.addEventListener('input', () => { this.newGuildName = nameInput.value; });

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
        this.selectedType = opt.getAttribute('data-val') as 'open' | 'invite';
        this.render();
      });
    });

    const levelSlider = this.el.querySelector('#min-level-slider') as HTMLInputElement;
    levelSlider?.addEventListener('input', () => {
      this.selectedMinLevel = parseInt(levelSlider.value, 10);
      const label = this.el.querySelector('#min-level-label');
      if (label) label.textContent = `Мин. уровень: ${this.selectedMinLevel}`;
    });

    this.el.querySelector('#create-cancel')?.addEventListener('click', () => {
      this.tab = currentUserGuildId ? 'my' : 'list';
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
        this.tab = 'my';
        await this.init();
      } else {
        tgService.haptic('error');
      }
    });
  }
}
