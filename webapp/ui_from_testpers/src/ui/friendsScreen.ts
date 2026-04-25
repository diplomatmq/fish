import { friends, friendRequests, sendFriendRequest, acceptRequest, declineRequest, loadFriends } from '../modules/friendsData';
import { tgService } from '../modules/telegram';
import { getIcon } from './icons';

export class FriendsScreen {
  private el: HTMLElement;
  private currentView: 'list' | 'requests' = 'list';
  private loading = false;

  constructor() {
    this.el = this.buildShell();
  }

  getElement(): HTMLElement { return this.el; }

  private buildShell(): HTMLElement {
    const s = document.createElement('section');
    s.id = 'screen-friends';
    s.className = 'screen friends-screen';
    s.setAttribute('role', 'main');
    return s;
  }

  async init(): Promise<void> {
    this.loading = true;
    this.render();
    await loadFriends();
    this.loading = false;
    this.render();
  }

  private render(): void {
    if (this.loading) {
      this.el.innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';
      return;
    }
    if (this.currentView === 'requests') {
      this.renderRequests();
    } else {
      this.renderList();
    }
  }

  private renderList(): void {
    this.el.innerHTML = `
      <div class="friends-header-row">
        <h1 class="page-title" style="margin-bottom:0">ДРУЗЬЯ</h1>
        <div class="friends-notif-btn" id="btn-show-requests">
          <span>🔔</span>
          ${friendRequests.length > 0 ? `<div class="notif-badge">${friendRequests.length}</div>` : ''}
        </div>
      </div>

      <div class="glass friends-add-box" style="margin-top: 16px; padding: 12px;">
        <p class="form-label" style="font-size: 10px; margin-bottom: 8px;">ДОБАВИТЬ ДРУГА</p>
        <div style="display:flex; gap:10px;">
          <input type="text" id="friend-search" class="form-input" placeholder="ID или Username" style="flex:1; height:40px;">
          <button class="adv-play-btn" id="btn-add-search" style="padding: 0 16px;">OK</button>
        </div>
      </div>

      <div class="friends-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${friends.length === 0 ? '<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:20px;">У вас пока нет друзей</p>' : ''}
        ${friends.map(f => `
          <div class="friend-card glass">
            <div class="friend-avatar">${f.avatar}</div>
            <div class="friend-info">
              <div class="friend-name">${f.name}</div>
              <div class="friend-meta">Ур. ${f.level} · ${f.online ? '<span style="color:#2ecc71">Online</span>' : '<span style="opacity:0.5">Offline</span>'}</div>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    this.el.querySelector('#btn-show-requests')?.addEventListener('click', () => {
      this.currentView = 'requests';
      this.render();
      tgService.haptic('medium');
    });

    this.el.querySelector('#btn-add-search')?.addEventListener('click', async () => {
      const input = this.el.querySelector('#friend-search') as HTMLInputElement;
      if (input.value.trim()) {
        const success = await sendFriendRequest(input.value.trim());
        if (success) {
          alert('Запрос отправлен!');
          input.value = '';
          tgService.haptic('light');
          await loadFriends();
          this.render();
        } else {
          tgService.haptic('error');
          alert('Не удалось отправить заявку.');
        }
      }
    });
  }

  private renderRequests(): void {
    this.el.innerHTML = `
      <div class="friends-header-row">
        <button class="back-btn" id="btn-back-list">←</button>
        <h1 class="page-title" style="margin:0; flex:1">ЗАЯВКИ</h1>
      </div>

      <div class="requests-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${friendRequests.length === 0 ? '<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:40px;">Нет новых заявок</p>' : ''}
        ${friendRequests.map(r => `
          <div class="request-card glass">
            <div class="req-avatar">${r.avatar}</div>
            <div class="req-info">
              <div class="req-name">${r.name}</div>
              <div class="req-lvl">Ур. ${r.level} хочет в друзья!</div>
            </div>
            <div class="req-btns">
               <button class="req-btn req-btn--no" data-id="${r.id}">✕</button>
               <button class="req-btn req-btn--yes" data-id="${r.id}">✓</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    this.el.querySelector('#btn-back-list')?.addEventListener('click', () => {
      this.currentView = 'list';
      this.render();
      tgService.haptic('light');
    });

    this.el.querySelectorAll('.req-btn--yes').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id')!;
        const success = await acceptRequest(id);
        tgService.haptic(success ? 'heavy' : 'error');
        this.render();
      });
    });

    this.el.querySelectorAll('.req-btn--no').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id')!;
        const success = await declineRequest(id);
        tgService.haptic(success ? 'medium' : 'error');
        this.render();
      });
    });
  }
}
