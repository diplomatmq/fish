(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))s(a);new MutationObserver(a=>{for(const n of a)if(n.type==="childList")for(const r of n.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&s(r)}).observe(document,{childList:!0,subtree:!0});function e(a){const n={};return a.integrity&&(n.integrity=a.integrity),a.referrerPolicy&&(n.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?n.credentials="include":a.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function s(a){if(a.ep)return;a.ep=!0;const n=e(a);fetch(a.href,n)}})();class Lt{constructor(){var t,e,s;this.tg=((t=window.Telegram)==null?void 0:t.WebApp)??null,this.tg&&(this.tg.ready(),this.tg.expand(),(s=(e=this.tg).disableVerticalSwipes)==null||s.call(e),this.tg.setHeaderColor("#0a1628"),this.tg.setBackgroundColor("#0a1628"))}haptic(t){var e;(e=this.tg)!=null&&e.HapticFeedback&&(t==="selection"?this.tg.HapticFeedback.selectionChanged():t==="success"||t==="error"?this.tg.HapticFeedback.notificationOccurred(t):t==="impact"?this.tg.HapticFeedback.impactOccurred("medium"):["light","medium","heavy"].includes(t)&&this.tg.HapticFeedback.impactOccurred(t))}getUserName(){var t,e,s;return((s=(e=(t=this.tg)==null?void 0:t.initDataUnsafe)==null?void 0:e.user)==null?void 0:s.first_name)??null}getUserTag(){var e,s,a;const t=(a=(s=(e=this.tg)==null?void 0:e.initDataUnsafe)==null?void 0:s.user)==null?void 0:a.username;return t?`@${t}`:null}getUser(){var e,s;const t=(s=(e=this.tg)==null?void 0:e.initDataUnsafe)==null?void 0:s.user;return!t||!t.id?null:{id:t.id,first_name:t.first_name,username:t.username}}showAlert(t){var e;(e=this.tg)!=null&&e.showAlert?this.tg.showAlert(t):alert(t)}}const o=new Lt,dt={home:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="currentColor" stroke-width="2" />
      <path d="M12 3V9" stroke="#ff6b6b" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="12" cy="12" r="3" fill="#ff6b6b" stroke="currentColor" stroke-width="1"/>
      <path d="M12 15L12 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `,shop:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 9H21L19 21H5L3 9Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M9 12V6C9 4.34315 10.3431 3 12 3C13.6569 3 15 4.34315 15 6V12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `,friends:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 8C6 9 8 7 10 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M14 12C16 13 18 11 20 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M6 16C8 17 10 15 12 16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <circle cx="4" cy="8" r="1.5" fill="currentColor"/>
      <circle cx="14" cy="12" r="1.5" fill="currentColor"/>
      <circle cx="6" cy="16" r="1.5" fill="currentColor"/>
    </svg>
  `,guilds:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 22V10M12 22C11.5 22 8 21 8 16M12 22C12.5 22 16 21 16 16M12 5V10M5 10H19" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="12" cy="4" r="2" stroke="currentColor" stroke-width="2"/>
    </svg>
  `,book:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="3" width="16" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
      <path d="M9 3V21M13 7H17M13 11H17M13 15H17M4 7H9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M18 3C18 3 19 5 19 7C19 9 18 11 18 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  `,lanternfish:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 12C2 12 5 7 12 7C19 7 22 12 22 12C22 12 19 17 12 17C5 17 2 12 2 12Z" fill="url(#grad-blue)" stroke="#00b4d8" stroke-width="1.5"/>
      <circle cx="17" cy="12" r="1.5" fill="#fff">
        <animate attributeName="opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite" />
      </circle>
      <path d="M12 7V5M12 17V19" stroke="#00b4d8" stroke-width="1" stroke-linecap="round"/>
      <defs>
        <linearGradient id="grad-blue" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#0077b6;stop-opacity:0.8" />
          <stop offset="100%" style="stop-color:#00b4d8;stop-opacity:0.4" />
        </linearGradient>
      </defs>
    </svg>
  `,anglerfish:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 13C3 13 6 8 13 8C20 8 21 15 21 15C21 15 18 19 13 19C8 19 3 13 3 13Z" fill="#2a1b3d" stroke="#9b5de5" stroke-width="1.5"/>
      <path d="M13 8C13 8 13 4 17 3" stroke="#f4a82e" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="17" cy="3" r="2" fill="#f4a82e">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="1.5s" repeatCount="indefinite" />
      </circle>
      <path d="M6 13L8 14L6 15" stroke="#9b5de5" stroke-width="1" />
    </svg>
  `,lionfish:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 12C4 12 7 8 14 8C21 8 20 16 14 16C8 16 4 12 4 12Z" fill="#4a0e0e" stroke="#ff6b6b" stroke-width="1.5"/>
      <path d="M10 8V4M12 8V3M14 8V4M16 8V5" stroke="#ff6b6b" stroke-width="1" stroke-linecap="round"/>
      <path d="M10 16V20M12 16V21M14 16V20" stroke="#ff6b6b" stroke-width="1" stroke-linecap="round"/>
    </svg>
  `,clownfish:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 12C2 12 6 7 14 7C22 7 22 17 14 17C6 17 2 12 2 12Z" fill="#e67e22" stroke="#fff" stroke-width="1.5"/>
      <path d="M7 7.5V16.5M12 7V17M17 7.5V16.5" stroke="#fff" stroke-width="2" opacity="0.6"/>
    </svg>
  `,seahorse:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 4C12 4 9 4 9 7C9 10 13 11 13 14C13 17 10 20 9 20" stroke="#9b5de5" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M12 4C14 4 15 5 15 7C15 9 13 10 13 14" stroke="#9b5de5" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="10.5" cy="6.5" r="1" fill="#fff" opacity="0.8"/>
    </svg>
  `,pufferfish:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="7" fill="#1b4d3e" stroke="#48cae4" stroke-width="1.5"/>
      <path d="M12 5V3M17 7L18.5 5.5M19 12H21M17 17L18.5 18.5M12 19V21" stroke="#48cae4" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  `,barracuda:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 12C2 12 5 9 12 9C19 9 22 12 22 12C22 12 19 15 12 15C5 15 2 12 2 12Z" fill="#2c3e50" stroke="#00b4d8" stroke-width="1.5"/>
      <path d="M18 12H20M5 12H10" stroke="#fff" stroke-width="1" opacity="0.3"/>
      <path d="M20 12L22 11M20 12L22 13" stroke="#00b4d8" stroke-width="1.5"/>
    </svg>
  `,shark:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 14C2 14 6 7 16 7C23 7 23 14 23 14C23 14 18 19 12 19C6 19 2 14 2 14Z" fill="#2c3e50" stroke="#c0c0c0" stroke-width="1.5"/>
      <path d="M12 7L14 3L16 7" fill="#2c3e50" stroke="#c0c0c0" stroke-width="1.5" stroke-linejoin="round"/>
      <path d="M6 12H8M6 14H8M6 16H8" stroke="#fff" stroke-width="0.5" opacity="0.4"/>
    </svg>
  `,guild_beer:`
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="glass-body" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#f1c40f" />
          <stop offset="100%" stop-color="#e67e22" />
        </linearGradient>
        <linearGradient id="foam-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="100%" stop-color="#ecf0f1" />
        </linearGradient>
      </defs>
      <path d="M12 12V32C12 34.2091 13.7909 36 16 36H24C26.2091 36 28 34.2091 28 32V12" fill="url(#glass-body)" stroke="#fff" stroke-width="0.5"/>
      <path d="M28 16H32C34.2091 16 36 17.7909 36 20V26C36 28.2091 34.2091 30 32 30H28" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M10 10C10 8 13 6 20 6C27 6 30 8 30 10V14H10V10Z" fill="url(#foam-grad)" />
      <circle cx="14" cy="9" r="2.5" fill="#fff" opacity="0.8" />
      <circle cx="20" cy="7" r="3" fill="#fff" />
      <circle cx="26" cy="9" r="2.5" fill="#fff" opacity="0.8" />
      <!-- Shine -->
      <path d="M14 15V30" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity="0.3"/>
    </svg>
  `,guild_rich:`
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="chest-brown" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5d4037" />
          <stop offset="100%" stop-color="#3e2723" />
        </linearGradient>
      </defs>
      <rect x="6" y="16" width="28" height="18" rx="2" fill="url(#chest-brown)" stroke="#f4a82e" stroke-width="1.5"/>
      <path d="M6 16C6 11 11 7 20 7C29 7 34 11 34 16" fill="#4e342e" stroke="#f4a82e" stroke-width="2"/>
      <rect x="18" y="14" width="4" height="6" rx="1" fill="#f4a82e" />
      <circle cx="20" cy="17" r="1.5" fill="#3e2723" />
      <!-- Gold Glow -->
      <circle cx="28" cy="18" r="3" fill="#f1c40f">
        <animate attributeName="opacity" values="0;1;0" dur="2.5s" repeatCount="indefinite" />
        <animate attributeName="r" values="1;4;1" dur="2.5s" repeatCount="indefinite" />
      </circle>
      <circle cx="12" cy="22" r="2" fill="#f1c40f">
        <animate attributeName="opacity" values="0;0.8;0" dur="3s" repeatCount="indefinite" />
      </circle>
    </svg>
  `,guild_cthulhu:`
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="cth-eye" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ff0000" />
          <stop offset="100%" stop-color="#800000" />
        </radialGradient>
      </defs>
      <path d="M20 4C14 4 9 8 9 16C9 19 10 22 12 24C10 26 8 30 8 34" stroke="#143612" stroke-width="3" stroke-linecap="round"/>
      <path d="M20 4C26 4 31 8 31 16C31 19 30 22 28 24C30 26 32 30 32 34" stroke="#143612" stroke-width="3" stroke-linecap="round"/>
      <!-- Head Details -->
      <path d="M15 10C15 8 17 6 20 6C23 6 25 8 25 10" stroke="#2e7d32" stroke-width="1.5" opacity="0.4"/>
      <!-- Main Tentacles -->
      <g>
        <path d="M16 24C14 28 12 32 12 38" stroke="#1b5e20" stroke-width="3" stroke-linecap="round" />
        <circle cx="13" cy="30" r="1" fill="#4caf50" opacity="0.6"/>
        <circle cx="12.5" cy="34" r="1" fill="#4caf50" opacity="0.6"/>
        <animateTransform attributeName="transform" type="rotate" values="-2 20 24; 2 20 24; -2 20 24" dur="3s" repeatCount="indefinite" />
      </g>
      <g>
        <path d="M24 24C26 28 28 32 28 38" stroke="#1b5e20" stroke-width="3" stroke-linecap="round" />
        <circle cx="27" cy="30" r="1" fill="#4caf50" opacity="0.6"/>
        <circle cx="27.5" cy="34" r="1" fill="#4caf50" opacity="0.6"/>
        <animateTransform attributeName="transform" type="rotate" values="2 20 24; -2 20 24; 2 20 24" dur="3s" repeatCount="indefinite" />
      </g>
      <path d="M20 24V38" stroke="#1b5e20" stroke-width="4" stroke-linecap="round" />
      <!-- Glowing Eyes -->
      <circle cx="15" cy="16" r="2.5" fill="url(#cth-eye)">
        <animate attributeName="r" values="2;3;2" dur="1s" repeatCount="indefinite" />
      </circle>
      <circle cx="25" cy="16" r="2.5" fill="url(#cth-eye)">
        <animate attributeName="r" values="2;3;2" dur="1s" repeatCount="indefinite" />
      </circle>
      <path d="M18 14H22" stroke="#000" stroke-width="1" opacity="0.2" />
    </svg>
  `,guild_king:`
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gold-metal" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#fff9c4" />
          <stop offset="50%" stop-color="#fbc02d" />
          <stop offset="100%" stop-color="#f57f17" />
        </linearGradient>
      </defs>
      <!-- Elaborate Crown -->
      <path d="M6 20L8 10L14 14L20 6L26 14L32 10L34 20H6Z" fill="url(#gold-metal)" stroke="#9e7c10" stroke-width="1"/>
      <path d="M10 20V32C10 35 14 38 20 38C26 38 30 35 30 32V20" stroke="url(#gold-metal)" stroke-width="4" stroke-linecap="round"/>
      <!-- Gemstones -->
      <circle cx="14" cy="17" r="1.5" fill="#e91e63" />
      <circle cx="26" cy="17" r="1.5" fill="#e91e63" />
      <path d="M20 12L20 16" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity="0.6"/>
      <!-- Floating Orb -->
      <circle cx="20" cy="27" r="5" fill="#00e5ff" opacity="0.8">
        <animate attributeName="r" values="4;6;4" dur="2s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.4;0.9;0.4" dur="2s" repeatCount="indefinite" />
      </circle>
      <path d="M17 27H23M20 24V30" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
      <!-- Shimmer -->
      <path d="M8 12L12 16M28 16L32 12" stroke="#fff" stroke-width="1" opacity="0.4"/>
    </svg>
  `,achievements:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 6V18M20 6V18M4 6C4 6 8 4 12 4C16 4 20 6 20 6M4 18C4 18 8 20 12 20C16 20 20 18 20 18" stroke="#f4a82e" stroke-width="2"/>
      <path d="M4 12H20M12 4V20" stroke="#f4a82e" stroke-width="1.5" opacity="0.6"/>
      <circle cx="12" cy="12" r="3" fill="#f4a82e" />
    </svg>
  `,rating:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 12C2 12 5 7 12 7C19 7 22 12 22 12C22 12 19 17 12 17C5 17 2 12 2 12Z" fill="none" stroke="currentColor" stroke-width="2"/>
      <path d="M10 5L12 2L14 5" stroke="#f4a82e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="12" cy="12" r="2" fill="#f4a82e"/>
    </svg>
  `,results:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="3" width="16" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
      <path d="M8 8H16M8 12H16M8 16H12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <path d="M16 16L19 19M19 19L22 16M19 19V13" stroke="#f4a82e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `,trophy:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 9C6 9 6 3 12 3C18 3 18 9 18 9M6 9C6 14 10 17 12 17C14 17 18 14 18 9M6 9H3V11C3 13 5 13 5 13M18 9H21V11C21 13 19 13 19 13M12 17V21M9 21H15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `};function b(i,t=""){const e=dt[i]||dt.home;return t?e.replace("<svg",`<svg class="${t}"`):e}function Mt(){const i=document.getElementById("app");return i.innerHTML=`
    <div id="bg-parallax"  class="bg-parallax"></div>
    <div id="bg-overlay"   class="bg-overlay"></div>

    <div class="sunrays" aria-hidden="true">
      <div class="sunray"></div>
      <div class="sunray"></div>
      <div class="sunray"></div>
      <div class="sunray"></div>
    </div>

    <canvas id="particles-canvas" class="particles-canvas" aria-hidden="true"></canvas>

    <!-- ═══ SCREENS ═══ -->
    <div id="screens-wrap" class="screens-wrap">

      <!-- HOME -->
      <section id="screen-home" class="screen is-active" role="main" aria-label="Главная">
        <h1 class="page-title slide-up" style="animation-delay:1.8s">ПОДВОДНЫЙ МИР</h1>

        <!-- Profile injected by ProfilePanel -->
        <div id="profile-mount" class="slide-up" style="animation-delay:1.9s"></div>

        <!-- Trophy -->
        <div id="trophy-section" class="trophy-section slide-up" style="animation-delay:2.0s">
          <p class="section-title">ТРОФЕЙ</p>
          <div id="carousel-mount" class="carousel-wrap"></div>
          <button id="select-trophy-btn" class="select-trophy-btn" aria-label="Выбрать трофей">
            ${b("trophy")} &nbsp;ВЫБРАТЬ ТРОФЕЙ
          </button>
        </div>

        <!-- Quick actions -->
        <div class="quick-actions slide-up" style="animation-delay:2.1s">
          <button class="quick-card glass" id="btn-rating" aria-label="Рейтинг">
            <span class="quick-icon" aria-hidden="true">${b("rating")}</span>
            <span class="quick-label">Рейтинг</span>
          </button>
          <button class="quick-card glass" id="btn-results" aria-label="Результаты">
            <span class="quick-icon" aria-hidden="true">${b("results")}</span>
            <span class="quick-label">Результаты</span>
          </button>
          <button class="quick-card glass" id="btn-achievements" aria-label="Достижения">
            <span class="quick-icon" aria-hidden="true">${b("achievements")}</span>
            <span class="quick-label">Достижения</span>
          </button>
        </div>
      </section>

      <!-- SHOP -->
      <section id="screen-shop" class="screen" role="main" aria-label="Лавка">
        <h1 class="page-title">ЛАВКА</h1>
        <div class="glass shop-container">
          <div class="shop-empty">
            <div class="shop-soon-icon">${b("shop")}</div>
            <h3>Лавка скоро откроется!</h3>
            <p>Здесь вы сможете продавать рыбу и покупать снаряжение прямо в приложении.</p>
          </div>
        </div>
      </section>

      <!-- FRIENDS -->
      <section id="screen-friends" class="screen" role="main" aria-label="Друзья"></section>

      <!-- GUILDS (ARTELS) -->
      <section id="screen-guilds" class="screen" role="main" aria-label="Артели"></section>

      <!-- BOOK -->
      ${Ct("book","📖","Книга рыбака",`Здесь появится ваш
рыболовный журнал`)}

    </div>

    <!-- Tab bar injected by TabBar -->
    <div id="tabbar-mount"></div>

    <!-- Modal injected by TrophyModal -->
  `,i}function Ct(i,t,e,s){return`
    <section id="screen-${i}" class="screen screen--empty" role="main" aria-label="${e}">
      <h1 class="page-title">${e.toUpperCase()}</h1>
      <div class="glass empty-content">
        <div class="empty-icon" aria-hidden="true">${b(i)}</div>
        <p class="empty-text">${s.replace(`
`,"<br>")}</p>
      </div>
    </section>
  `}function Tt(){const i=document.createElement("div");return i.id="entry-overlay",i.className="entry-overlay",i.innerHTML=`
    <div class="entry-logo" aria-hidden="true">🌊</div>
    <p class="entry-title">ПОДВОДНЫЙ МИР</p>
    <p class="entry-subtitle">Загрузка…</p>
  `,document.body.appendChild(i),i}function qt(i,t=1600){setTimeout(()=>{i.style.transition="opacity 0.6s ease",i.style.opacity="0",setTimeout(()=>i.remove(),700)},t)}function _t(i,t){const e=document.getElementById("btn-achievements"),s=document.getElementById("btn-rating"),a=document.getElementById("btn-results");[e,s,a].forEach(n=>{n&&n.addEventListener("click",()=>{o.haptic("light"),n.classList.remove("bounce"),n.offsetWidth,n.classList.add("bounce"),n.addEventListener("animationend",()=>n.classList.remove("bounce"),{once:!0})})}),s&&i&&s.addEventListener("click",i),a&&t&&a.addEventListener("click",t)}function It(i){const t=document.getElementById("select-trophy-btn");t&&(t.addEventListener("click",i),t.addEventListener("pointerdown",()=>{t.style.transform="scale(0.96)"}),t.addEventListener("pointerup",()=>{t.style.transform=""}),t.addEventListener("pointerleave",()=>{t.style.transform=""}))}const ht=[{id:"home",icon:"🧭",label:"ГЛАВНАЯ"},{id:"shop",icon:"🧺",label:"ЛАВКА"},{id:"friends",icon:"👤",label:"ДРУЗЬЯ"},{id:"guilds",icon:"🔱",label:"АРТЕЛИ"},{id:"book",icon:"📖",label:"КНИГА"}],A={name:"АКВАМАН_01",tag:"@aquaman01",level:15,xp:7200,maxXp:1e4,avatar:"🤿"},T={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"},At=()=>{var i,t;return((t=(i=window.Telegram)==null?void 0:i.WebApp)==null?void 0:t.initData)||""};async function u(i,t={}){const s={"Content-Type":"application/json","X-Telegram-Init-Data":At(),...t.headers||{}},a=await fetch(i,{...t,headers:s});if(!a.ok){const n=await a.json().catch(()=>({error:"Unknown error"}));throw new Error(n.error||`HTTP error! status: ${a.status}`)}return a.json()}const J=u;class Ht{constructor(){this.fillEl=null,this.wobbling=!1,this.profile={...A},this.el=this.build(),this.loadProfile()}async loadProfile(){try{const t=await u("/api/profile");t&&(this.profile.name=t.username||this.profile.name,this.profile.level=t.level||this.profile.level,this.profile.xp=t.xp||this.profile.xp,this.profile.maxXp=1e4,this.profile.tag=`@${t.user_id}`||this.profile.tag,this.updateUI())}catch(t){console.error("Failed to load profile:",t)}}updateUI(){const t=this.el.querySelector("#profile-name"),e=this.el.querySelector("#profile-tag"),s=this.el.querySelector(".level-label"),a=this.el.querySelector(".xp-label");t&&(t.textContent=this.profile.name.toUpperCase()),e&&(e.textContent=this.profile.tag),s&&(s.textContent=`Уровень ${this.profile.level}`),a&&(a.textContent=`${this.profile.xp.toLocaleString("ru")} XP`),this.animateProgress(0)}getElement(){return this.el}build(){const t=A,e=Math.round(t.xp/t.maxXp*100),s=document.createElement("div");s.id="profile-panel",s.className="profile-panel glass",s.innerHTML=`
      <div id="porthole-wrap" class="porthole" role="button" tabindex="0" aria-label="Аватар игрока">
        <div class="porthole__ring"></div>
        <div class="porthole__inner">${t.avatar}</div>
      </div>

      <div class="profile-info">
        <div class="profile-name" id="profile-name">${t.name}</div>
        <div class="profile-tag"  id="profile-tag">${t.tag}</div>

        <button class="edit-btn" id="edit-btn" aria-label="Редактировать профиль">
          ✏️ Редактировать
        </button>

        <div class="level-row">
          <span class="level-label">Уровень ${t.level}</span>
          <span class="xp-label">${t.xp.toLocaleString("ru")} / ${t.maxXp.toLocaleString("ru")} XP</span>
        </div>
        <div class="progress-track" role="progressbar" aria-valuenow="${e}" aria-valuemin="0" aria-valuemax="100">
          <div class="progress-fill" id="progress-fill"></div>
        </div>
      </div>
    `;const a=s.querySelector("#porthole-wrap");a.addEventListener("click",()=>this.wobble(a)),a.addEventListener("keydown",r=>{(r.key==="Enter"||r.key===" ")&&this.wobble(a)});const n=s.querySelector("#edit-btn");return n.addEventListener("click",()=>{o.haptic("light"),n.textContent="⏳ Загрузка...",setTimeout(()=>{n.innerHTML="✏️ Редактировать"},1800)}),n.addEventListener("pointerdown",()=>{n.style.transform="scale(0.96)"}),n.addEventListener("pointerup",()=>{n.style.transform=""}),this.fillEl=s.querySelector("#progress-fill"),s}animateProgress(t=200){if(!this.fillEl)return;const e=Math.round(A.xp/A.maxXp*100);this.fillEl.style.width="0%",setTimeout(()=>{this.fillEl.style.width=`${e}%`},t)}wobble(t){this.wobbling||(this.wobbling=!0,o.haptic("light"),t.classList.add("porthole--wobble"),t.addEventListener("animationend",()=>{t.classList.remove("porthole--wobble"),this.wobbling=!1},{once:!0}))}updateFromTelegram(){const t=o.getUserName(),e=o.getUserTag();if(t){const s=this.el.querySelector("#profile-name");s&&(s.textContent=t.toUpperCase())}if(e){const s=this.el.querySelector("#profile-tag");s&&(s.textContent=e)}}}class Bt{constructor(t){this.targetX=0,this.targetY=0,this.currentX=0,this.currentY=0,this.rafId=0,this.el=t,this.bindEvents(),this.loop()}bindEvents(){window.addEventListener("mousemove",t=>{this.targetX=(t.clientX/window.innerWidth-.5)*14,this.targetY=(t.clientY/window.innerHeight-.5)*8}),window.addEventListener("deviceorientation",t=>{t.gamma===null||t.beta===null||(this.targetX=Math.max(-12,Math.min(12,t.gamma*.25)),this.targetY=Math.max(-7,Math.min(7,(t.beta-45)*.15)))})}loop(){this.currentX+=(this.targetX-this.currentX)*.06,this.currentY+=(this.targetY-this.currentY)*.06,this.el.style.transform=`scale(1.14) translate(${-this.currentX*.08}%, ${-this.currentY*.06}%)`,this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId)}}class Ft{constructor(t){this.intervalId=0,this.container=t,this.start()}spawnOne(){if(document.hidden)return;const t=document.createElement("div");t.className="trophy-bubble";const e=4+Math.random()*9,s=20+Math.random()*60,a=2.8+Math.random()*2.8;t.style.cssText=`
      width:${e}px; height:${e}px;
      left:${s}%; bottom:${8+Math.random()*12}%;
      animation-duration:${a}s;
      animation-delay:${Math.random()*.3}s;
    `,this.container.appendChild(t),setTimeout(()=>t.remove(),(a+.5)*1e3)}start(){this.intervalId=window.setInterval(()=>this.spawnOne(),380)}stop(){clearInterval(this.intervalId),this.container.querySelectorAll(".trophy-bubble").forEach(t=>t.remove())}restart(){this.stop(),this.start()}}const P=class P{static transitionTo(t,e){this.pendingTimeout&&(clearTimeout(this.pendingTimeout),this.pendingTimeout=0);const s=++this.transitionToken;t.style.transition="opacity 0.35s ease, transform 0.35s ease",t.style.opacity="0",t.style.transform="scale(0.93)",t.style.pointerEvents="none",t.classList.remove("is-active"),e.style.display="flex",e.style.transition="none",e.style.opacity="0",e.style.transform="scale(1.06)",e.style.pointerEvents="all",e.classList.add("is-active"),this.pendingTimeout=window.setTimeout(()=>{s===this.transitionToken&&(t.style.display="none",t.style.opacity="",t.style.transform="",t.style.transition="",requestAnimationFrame(()=>{s===this.transitionToken&&(e.style.transition="opacity 0.38s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.38s cubic-bezier(0.25,0.46,0.45,0.94)",e.style.opacity="1",e.style.transform="scale(1)",window.setTimeout(()=>{s===this.transitionToken&&(t.style.transform="",e.style.transform="",t.style.transition="",e.style.transition="")},400))}))},300)}};P.transitionToken=0,P.pendingTimeout=0;let Z=P;const Nt={id:"no-trophy",emoji:"🐟",name:"Нет трофеев",latinName:"",rarity:"common",rarityLabel:"Обычная",rarityStars:"",weight:"0 кг",depth:"0 см"};class Pt{constructor(t,e=2){this.cards=[],this.bubbleSpawner=null,this.fishData=[],this.startX=0,this.isDragging=!1,this.onChangeCallback=null,this.container=t,this.activeIndex=e,this.build(),this.bindSwipe(),this.update()}build(){this.container.innerHTML="",this.cards=[];const t=document.createElement("div");t.className="carousel__bubbles",this.container.appendChild(t),this.bubbleSpawner=new Ft(t);const e=document.createElement("div");if(e.className="carousel__track",this.container.appendChild(e),this.fishData.length===0){e.innerHTML=`
        <div class="carousel__card is-active" style="opacity:1; transform:translateX(0) scale(1);">
          <div class="carousel__card-inner" style="--accent:${T.common}">
            <div class="carousel__fish-emoji">${b("trophy")}</div>
            <div class="carousel__rarity" style="color:${T.common}">ТРОФЕЕВ ПОКА НЕТ</div>
            <div class="carousel__fish-name">Поймай рыбу и создай трофей</div>
            <div class="carousel__fish-latin">Карточки появятся автоматически</div>
          </div>
        </div>
      `;return}this.fishData.forEach((s,a)=>{const n=document.createElement("div");n.className="carousel__card",n.dataset.index=String(a);const r=T[s.rarity];n.innerHTML=`
        <div class="carousel__card-inner" style="--accent:${r}">
          <div class="carousel__fish-emoji">${s.imageUrl?`<img src="${s.imageUrl}" alt="${s.name}" class="carousel__fish-image" loading="lazy">`:b(s.id)}</div>
          <div class="carousel__rarity" style="color:${r}">${s.rarityStars} ${s.rarityLabel}</div>
          <div class="carousel__fish-name">${s.name}</div>
          <div class="carousel__fish-latin">${s.latinName}</div>
          <div class="carousel__fish-stats">
            <span>⚖️ ${s.weight}</span>
            <span>📏 ${s.depth}</span>
          </div>
        </div>
      `,e.appendChild(n),this.cards.push(n)})}update(){var e;if(this.cards.length===0)return;this.cards.forEach((s,a)=>{const n=a-this.activeIndex,r=Math.abs(n);s.classList.remove("is-active","is-side","is-far");let l,d,c,p;switch(r){case 0:l=0,d=1,c=1,p=10,s.classList.add("is-active");break;case 1:l=n*148,d=.78,c=.6,p=5,s.classList.add("is-side");break;case 2:l=n*185,d=.62,c=.28,p=2,s.classList.add("is-far");break;default:l=n*200,d=.5,c=0,p=0}s.style.transform=`translateX(${l}px) scale(${d})`,s.style.opacity=String(c),s.style.zIndex=String(p)});const t=this.fishData[this.activeIndex];t&&((e=this.onChangeCallback)==null||e.call(this,t))}next(){this.fishData.length!==0&&this.activeIndex<this.fishData.length-1&&(this.activeIndex++,this.update(),o.haptic("light"))}prev(){this.fishData.length!==0&&this.activeIndex>0&&(this.activeIndex--,this.update(),o.haptic("light"))}goTo(t){this.fishData.length!==0&&(this.activeIndex=Math.max(0,Math.min(t,this.fishData.length-1)),this.update())}getActiveIndex(){return this.activeIndex}getActiveFish(){return this.fishData[this.activeIndex]||Nt}getItems(){return this.fishData}setFishData(t,e){if(this.fishData=[...t],e){const s=this.fishData.findIndex(a=>a.trophyId===e||a.id===e);this.activeIndex=s>=0?s:0}else this.activeIndex=this.fishData.length?Math.max(0,Math.min(this.activeIndex,this.fishData.length-1)):0;this.build(),this.update()}onChange(t){this.onChangeCallback=t}bindSwipe(){const t=this.container;t.addEventListener("touchstart",e=>{this.startX=e.touches[0].clientX,this.isDragging=!0},{passive:!0}),t.addEventListener("touchend",e=>{if(!this.isDragging)return;const s=e.changedTouches[0].clientX-this.startX;this.handleSwipeEnd(s),this.isDragging=!1},{passive:!0}),t.addEventListener("mousedown",e=>{this.startX=e.clientX,this.isDragging=!0,e.preventDefault()}),window.addEventListener("mouseup",e=>{if(!this.isDragging)return;const s=e.clientX-this.startX;this.handleSwipeEnd(s),this.isDragging=!1})}handleSwipeEnd(t){t<-42?this.next():t>42&&this.prev()}}const Ot={обычная:"common",редкая:"rare",легендарная:"legendary",аквариумная:"aquarium",мифическая:"mythical",аномалия:"anomaly"},Dt={common:"Обычная",rare:"Редкая",legendary:"Легендарная",aquarium:"Аквариумная",mythical:"Мифическая",anomaly:"Аномалия"},Rt={common:"★★",rare:"★★★",legendary:"★★★★★",aquarium:"★★★★",mythical:"★★★★★",anomaly:"★★★★★★"},jt={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"};function C(i){const t=String(i||"").trim().toLowerCase();return Ot[t]||"common"}function K(i){return Dt[C(i)]}function Ut(i){return Rt[C(i)]}function Gt(i){return jt[C(i)]}let H=[],Q="";function zt(i){return`${(Number.isFinite(i)?Math.max(0,i):0).toLocaleString("ru-RU",{maximumFractionDigits:2})} кг`}function Vt(i){return`${(Number.isFinite(i)?Math.max(0,i):0).toLocaleString("ru-RU",{maximumFractionDigits:1})} см`}function Wt(i){const t=i.rarity||"Обычная";return{id:i.id,emoji:"🐟",name:i.fish_name||i.name||"Неизвестная рыба",latinName:"",rarity:C(t),rarityLabel:K(t),rarityStars:Ut(t),weight:zt(Number(i.weight||0)),depth:Vt(Number(i.length||0)),imageUrl:i.image_url||void 0,trophyId:i.id}}async function Yt(){var i;try{const t=await u("/api/trophies"),e=Array.isArray(t==null?void 0:t.items)?t.items:[];return Q=((i=e.find(s=>!!s.is_active))==null?void 0:i.id)||"",H=e.filter(s=>s.id!=="none").map(Wt),H}catch(t){return console.error("Failed to load trophies:",t),H=[],Q="",H}}async function Xt(i){if(!i)return!1;try{const t=await u("/api/trophy/select",{method:"POST",body:JSON.stringify({trophy_id:i})});return!!(t!=null&&t.ok)}catch(t){return console.error("Failed to select trophy:",t),!1}}class Jt{constructor(){this.isOpen=!1,this.bgBlurTarget=null,this.onSelectCallback=null,this.currentActiveIndex=0,this.items=[],this.sheetStartY=0,this.sheetDragging=!1,this.overlay=this.buildOverlay(),this.sheet=this.overlay.querySelector("#modal-sheet"),this.listEl=this.overlay.querySelector("#modal-fish-list"),document.body.appendChild(this.overlay),this.bindClose()}buildOverlay(){const t=document.createElement("div");return t.id="modal-overlay",t.className="modal-overlay",t.innerHTML=`
      <div id="modal-sheet" class="modal-sheet">
        <div class="modal-handle"></div>
        <p class="modal-title">🏆 Выбор трофея</p>
        <div id="modal-fish-list" class="modal-fish-list"></div>
      </div>
    `,t}buildList(){if(this.items.length===0){this.listEl.innerHTML='<div class="modal-empty">У вас пока нет трофеев</div>';return}this.listEl.innerHTML=this.items.map((t,e)=>{const s=T[t.rarity],a=e===this.currentActiveIndex;return`
        <div
          class="modal-fish-item ${a?"is-selected":""}"
          data-index="${e}"
          style="--accent:${s}"
          role="button"
          tabindex="0"
          aria-label="${t.name}"
        >
          <span class="modal-fish-emoji">${t.imageUrl?`<img src="${t.imageUrl}" alt="${t.name}" class="modal-fish-image" loading="lazy">`:b(t.id)}</span>
          <div class="modal-fish-info">
            <div class="modal-fish-name">${t.name}</div>
            <div class="modal-fish-rarity" style="color:${s}">${t.rarityStars} ${t.rarityLabel}</div>
            <div class="modal-fish-stats">⚖️ ${t.weight} · 📏 ${t.depth}</div>
          </div>
          ${a?'<span class="modal-check">✓</span>':""}
        </div>
      `}).join(""),this.listEl.querySelectorAll(".modal-fish-item").forEach(t=>{t.addEventListener("click",()=>{const e=parseInt(t.dataset.index??"0",10);this.select(e)})})}open(t,e){this.isOpen||(this.currentActiveIndex=t,this.bgBlurTarget=e??null,this.buildList(),this.overlay.style.display="flex",requestAnimationFrame(()=>{this.overlay.classList.add("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter="blur(4px)")}),this.isOpen=!0,o.haptic("medium"))}close(){this.isOpen&&(this.overlay.classList.remove("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter=""),setTimeout(()=>{this.overlay.style.display="none"},420),this.isOpen=!1)}onSelect(t){this.onSelectCallback=t}setItems(t){this.items=[...t],this.currentActiveIndex=Math.max(0,Math.min(this.currentActiveIndex,this.items.length-1))}async select(t){var a;this.currentActiveIndex=t;const e=this.items[t],s=e!=null&&e.trophyId?await Xt(e.trophyId):!0;if(o.haptic(s?"medium":"error"),!s){alert("Не удалось выбрать трофей. Попробуйте еще раз.");return}(a=this.onSelectCallback)==null||a.call(this,t),this.close()}bindClose(){this.overlay.addEventListener("click",e=>{e.target===this.overlay&&this.close()});const t=this.sheet;t.addEventListener("touchstart",e=>{this.sheetStartY=e.touches[0].clientY,this.sheetDragging=!0},{passive:!0}),t.addEventListener("touchmove",e=>{if(!this.sheetDragging)return;const s=e.touches[0].clientY-this.sheetStartY;s>0&&(t.style.transform=`translateY(${s*.55}px)`,t.style.transition="none")},{passive:!0}),t.addEventListener("touchend",e=>{if(!this.sheetDragging)return;const s=e.changedTouches[0].clientY-this.sheetStartY;t.style.transform="",t.style.transition="",s>80&&this.close(),this.sheetDragging=!1},{passive:!0})}get fish(){return this.items}}class Zt{constructor(t,e){this.activeId="home",this.buttons=new Map,this.screens=new Map,this.onChangeCallbacks=[],this.el=this.build(),t.appendChild(this.el),ht.forEach(s=>{const a=e.querySelector(`#screen-${s.id}`);a&&this.screens.set(s.id,a)}),this.screens.forEach((s,a)=>{a==="home"?(s.style.display="flex",s.style.opacity="1",s.style.transform="scale(1)",s.style.pointerEvents="all"):(s.style.display="none",s.style.opacity="0",s.style.transform="",s.style.pointerEvents="all")})}build(){const t=document.createElement("nav");return t.id="tab-bar",t.className="tab-bar",t.setAttribute("role","tablist"),ht.forEach(e=>{const s=document.createElement("button");s.id=`tab-${e.id}`,s.className=`tab-btn ${e.id==="home"?"is-active":""}`,s.setAttribute("role","tab"),s.setAttribute("aria-selected",e.id==="home"?"true":"false"),s.dataset.tab=e.id,s.innerHTML=`
        <span class="tab-icon" aria-hidden="true">${b(e.id)}</span>
        <span class="tab-label">${e.label}</span>
      `,s.addEventListener("click",()=>this.switchTo(e.id)),s.addEventListener("pointerdown",()=>{s.style.transform="scale(0.92)"}),s.addEventListener("pointerup",()=>{s.style.transform=""}),s.addEventListener("pointerleave",()=>{s.style.transform=""}),t.appendChild(s),this.buttons.set(e.id,s)}),t}switchTo(t){if(t===this.activeId)return;o.haptic("selection");const e=this.activeId;let s=this.screens.get(e);s||(s=document.getElementById(`screen-${e}`));let a=this.screens.get(t);if(a||(a=document.getElementById(`screen-${t}`)),!s||!a){console.warn(`Screen not found: from=${e} (${!!s}), to=${t} (${!!a})`);return}console.log(`Switching from ${e} to ${t}`),Z.transitionTo(s,a),this.buttons.forEach((n,r)=>{const l=r===t;n.classList.toggle("is-active",l),n.setAttribute("aria-selected",String(l))}),this.activeId=t,this.onChangeCallbacks.forEach(n=>n(e,t))}onChange(t){this.onChangeCallbacks.push(t)}getActive(){return this.activeId}}let tt=[],bt=0;async function yt(){try{const i=await u("/api/book?limit=500");i&&i.ok&&(bt=Number(i.total_all||0),tt=i.items.map(t=>({id:t.image_file||"fishdef",emoji:"🐟",name:t.name,latinName:t.name,rarity:Kt(t.rarity),glowColor:Qt(t.rarity),depth:`${t.min_weight}-${t.max_weight} кг`,habitat:t.locations,length:`${t.min_length}-${t.max_length} см`,description:t.lore||`Рыба вида ${t.name}.`,funFact:t.baits?`Лучше ловится на: ${t.baits}.`:"Информации пока нет.",chapter:"Общий атлас",isCaught:t.is_caught,imageUrl:t.image_url||void 0})))}catch(i){console.error("Failed to load encyclopedia:",i)}}function Kt(i){return C(i)}function Qt(i){return Gt(i)}const te={common:"★★ Обычная",rare:"★★★ Редкая",legendary:"★★★★★ Легендарная",aquarium:"★★★★ Аквариумная",mythical:"★★★★★ Мифическая",anomaly:"★★★★★★ Аномалия"};class ee{constructor(){this.entries=[],this.filtered=[],this.index=0,this.loading=!1,this.pageFlip=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-book",t.className="screen book-screen",t.setAttribute("role","main"),t.innerHTML=`
      <div class="book-search-wrap">
        <div class="book-search-bar" role="search">
          <span class="search-compass" aria-hidden="true">🧭</span>
          <input id="book-search-input" class="book-search-input" type="search" placeholder="ПОИСК..." autocomplete="off">
          <button class="search-icon-btn" id="book-search-btn"><span class="search-loupe">🔍</span></button>
        </div>
      </div>

      <div class="book-wrap">
        <div class="book-spine"></div>
        <div class="spine-hinge"></div>
        
        <!-- StPageFlip container -->
        <div id="st-book" class="st-book"></div>
      </div>

      <div class="book-nav">
        <button class="book-nav-arrow" id="book-prev-btn"><span class="arrow-ornament">◂</span></button>
        <div class="book-counter">
          <span class="counter-current" id="counter-cur">1</span>
          <span class="counter-sep">/</span>
          <span class="counter-total" id="counter-tot">?</span>
        </div>
        <button class="book-nav-arrow" id="book-next-btn"><span class="arrow-ornament">▸</span></button>
      </div>
    `,t}async init(){this.bookContainer=this.el.querySelector(".book-wrap"),this.stBook=this.el.querySelector("#st-book"),this.searchInput=this.el.querySelector("#book-search-input"),this.prevBtn=this.el.querySelector("#book-prev-btn"),this.nextBtn=this.el.querySelector("#book-next-btn"),this.counterCur=this.el.querySelector("#counter-cur"),this.counterTot=this.el.querySelector("#counter-tot"),this.loading=!0,await yt(),this.entries=[...tt],this.filtered=[...tt],this.loading=!1,this.renderPages(),this.bindEvents()}buildPage(t){const e=t.isCaught??!1;return`
      <div class="my-page ${e?"":"not-caught"}">
        <div class="ph-content parchment">
          <div class="ph-chapter">${t.chapter}</div>
          <div class="ph-chapter-divider"><span class="ph-chapter-rule">✦ · ✦</span></div>

          <div class="ph-fish-block">
            <div class="ph-fish-emoji" style="--glow: ${e?t.glowColor:"#555"}; filter: ${e?"none":"grayscale(100%) contrast(50%) brightness(70%)"}">
              ${t.imageUrl?`<img src="${t.imageUrl}" alt="${t.name}" class="ph-fish-image" loading="lazy">`:b(t.id)}
            </div>
          </div>
          
          <div class="ph-fish-name">${t.name.toUpperCase()}</div>
          <div class="ph-fish-latin">${t.latinName}</div>
          
          <div class="ph-rarity-wrap">
            <div class="ph-rarity" style="color:${e?t.glowColor:"#777"}; border-color:${e?t.glowColor:"#777"}55">
              ${e?te[t.rarity]:'<span style="color: #ff4d4d; font-weight: bold;">НЕ СЛОВЛЕНА</span>'}
            </div>
          </div>

          <div class="ph-stats">
            <div class="ph-stat"><span>🌊 Глуб</span><strong>${t.depth}</strong></div>
            <div class="ph-stat"><span>📏 Длина</span><strong>${t.length}</strong></div>
            <div class="ph-stat"><span>📍 Среда</span><strong>${t.habitat}</strong></div>
          </div>

          <p class="ph-desc">${t.description}</p>
          
          ${e?`
          <div class="ph-funfact">
            <div class="ph-ff-head">💡 Факт</div>
            <div class="ph-ff-body">${t.funFact}</div>
          </div>
          `:""}
        </div>
      </div>
    `}renderPages(){this.pageFlip&&(this.pageFlip.destroy(),this.pageFlip=null);const t=this.el.querySelector("#st-book");t&&t.remove(),this.stBook=document.createElement("div"),this.stBook.id="st-book",this.stBook.className="st-book",this.bookContainer.appendChild(this.stBook),this.filtered.length!==0&&(this.stBook.innerHTML=this.filtered.map(e=>this.buildPage(e)).join(""),window.St&&window.St.PageFlip&&(this.pageFlip=new window.St.PageFlip(this.stBook,{width:320,height:480,size:"stretch",minWidth:280,maxWidth:600,minHeight:400,maxHeight:900,usePortrait:!0,showCover:!1,useMouseEvents:!1,maxShadowOpacity:.7,mobileScrollSupport:!1,flippingTime:600}),this.pageFlip.loadFromHTML(this.stBook.querySelectorAll(".my-page")),this.pageFlip.on("flip",e=>{this.index=e.data,this.syncUI()}),this.pageFlip.on("changeState",e=>{e.data==="flipping"&&o.haptic("light")})),this.index=0,this.syncUI())}syncUI(){this.counterCur.textContent=String(this.index+1),this.counterTot.textContent=String(Math.max(this.filtered.length,bt||0)),this.prevBtn.disabled=this.index===0,this.nextBtn.disabled=this.index===this.filtered.length-1}applySearch(t){const e=t.trim().toLowerCase();this.filtered=e?this.entries.filter(s=>s.name.toLowerCase().includes(e)||s.latinName.toLowerCase().includes(e)||s.description.toLowerCase().includes(e)):[...this.entries],this.filtered.length||(this.filtered=[...this.entries]),this.renderPages()}bindEvents(){this.prevBtn.addEventListener("click",()=>{this.pageFlip&&this.index>0&&this.pageFlip.flipPrev()}),this.nextBtn.addEventListener("click",()=>{this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext()});let t=0,e=0;this.bookContainer.addEventListener("pointerdown",a=>{t=a.clientX,e=a.clientY},{passive:!0}),this.bookContainer.addEventListener("pointerup",a=>{if(this.pageFlip&&this.pageFlip.getState()!=="read")return;const n=a.clientX,r=a.clientY,l=t-n,d=Math.abs(e-r);Math.abs(l)>40&&d<60&&(l>0?this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext():this.pageFlip&&this.index>0&&this.pageFlip.flipPrev())},{passive:!0}),this.searchInput.addEventListener("keydown",a=>{a.key==="Enter"&&(a.preventDefault(),this.applySearch(this.searchInput.value))});const s=this.el.querySelector("#book-search-btn");s&&s.addEventListener("click",()=>{this.applySearch(this.searchInput.value)})}}class se{constructor(){this.items=[],this.loading=!1,this.mode="view",this.selectedIds=new Set,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-shop",t.className="screen shop-screen",t.setAttribute("role","main"),t.innerHTML=`
      <div class="shop-header">
        <h1 class="page-title">ЛАВКА</h1>
      </div>
      <div class="shop-container">
        <div id="shop-content" class="shop-content">
          <div class="loader-wrap"><div class="loader"></div></div>
        </div>
      </div>
      <button id="shop-sell-btn" class="shop-floating-btn" style="display:none;">
        ПРОДАТЬ
      </button>
      <div id="shop-select-actions" class="shop-select-actions" style="display:none;">
        <div class="select-info">Выбрано: <span id="select-count">0</span></div>
        <div class="select-buttons">
          <button id="cancel-select-btn" class="glass-btn">ОТМЕНА</button>
          <button id="confirm-sell-btn" class="glass-btn primary-btn">ПРОДАТЬ</button>
        </div>
      </div>
    `,t}async init(){await this.loadInventory(),this.bindEvents()}bindEvents(){const t=this.el.querySelector("#shop-sell-btn");t&&t.addEventListener("click",()=>{o.haptic("light"),this.showSellModal()});const e=this.el.querySelector("#cancel-select-btn");e&&e.addEventListener("click",()=>{o.haptic("light"),this.mode="view",this.selectedIds.clear(),this.renderInventory()});const s=this.el.querySelector("#confirm-sell-btn");s&&s.addEventListener("click",()=>{this.selectedIds.size!==0&&(o.haptic("medium"),this.sellBulk({ids:Array.from(this.selectedIds)}))})}showSellModal(){const t=`
      <div class="sell-options">
        <button class="glass-btn sell-opt-btn" data-cat="all">💰 Продать всю рыбу</button>
        <button class="glass-btn sell-opt-btn" data-cat="trash">🗑 Продать весь мусор</button>
        <button class="glass-btn sell-opt-btn" data-cat="common" style="color:var(--r-common)">Продать все обычные</button>
        <button class="glass-btn sell-opt-btn" data-cat="rare" style="color:var(--r-rare)">Продать все редкие</button>
        <button class="glass-btn sell-opt-btn" data-cat="legendary" style="color:var(--r-legendary)">Продать все легендарные</button>
        <button class="glass-btn sell-opt-btn" data-cat="anomaly" style="color:var(--r-anomaly)">Продать все аномалии</button>
        <button class="glass-btn sell-opt-btn" data-cat="aquarium" style="color:var(--r-aquarium)">Продать все аквариумные</button>
        <button class="glass-btn sell-opt-btn" data-cat="mythic" style="color:var(--r-mythic)">Продать все мифические</button>
        <button class="glass-btn sell-opt-btn select-mode-btn">✅ Выбрать</button>
      </div>
    `,e=document.createElement("div");e.className="modal-overlay is-open",e.style.display="flex",e.innerHTML=`
      <div class="modal-sheet" style="transform:none; bottom:0;">
        <div class="modal-handle"></div>
        <p class="modal-title">ПРОДАЖА РЫБЫ</p>
        <div style="padding:10px;">${t}</div>
      </div>
    `,document.body.appendChild(e),e.addEventListener("click",s=>{s.target===e&&document.body.removeChild(e)}),e.querySelectorAll(".sell-opt-btn").forEach(s=>{s.addEventListener("click",()=>{const a=s.dataset.cat;o.haptic("light"),document.body.removeChild(e),a?this.sellBulk({category:a}):s.classList.contains("select-mode-btn")&&(this.mode="select",this.selectedIds.clear(),this.renderInventory())})})}async showFishDetailModal(t){var e,s,a;try{const n=await u("/api/inventory"),r=((n==null?void 0:n.items)||[]).filter(m=>t.ids.includes(m.id));if(r.length===0)return;const l=C(t.rarity),d=T[l]||"#ccc",c=document.createElement("div");c.className="modal-overlay is-open",c.style.display="flex";const p=`
        <div class="modal-sheet" style="transform:none; bottom:0; max-height: 80vh;">
          <div class="modal-handle"></div>
          <p class="modal-title">${t.name}</p>
          <p style="text-align:center; color:${d}; font-size:12px; margin-top:-10px;">${K(t.rarity)}</p>
          
          <div class="fish-action-buttons">
            <button class="glass-btn primary-btn" id="make-trophy-btn">🏆 Сделать трофеем</button>
            <button class="glass-btn" id="select-to-sell-btn">💰 Выбрать для продажи</button>
          </div>
          
          <div id="fish-detail-content" style="display:none;">
            <p style="text-align:center; font-size:14px; margin:10px 0;">Выберите рыбу:</p>
            <div class="fish-detail-grid">
              ${r.map(m=>`
                <div class="fish-detail-card" data-id="${m.id}">
                  <img src="${m.image_url}" alt="${m.name}">
                  <div class="fish-detail-weight">⚖️ ${m.weight.toFixed(2)} кг</div>
                  <div class="fish-detail-weight">📏 ${m.length.toFixed(1)} см</div>
                </div>
              `).join("")}
            </div>
            <div style="padding:10px; display:flex; gap:10px; justify-content:center;">
              <button class="glass-btn" id="cancel-detail-btn">ОТМЕНА</button>
              <button class="glass-btn primary-btn" id="confirm-detail-btn" style="display:none;">ПОДТВЕРДИТЬ</button>
            </div>
          </div>
        </div>
      `;c.innerHTML=p,document.body.appendChild(c);let g=new Set,E=null;const h=c.querySelector("#fish-detail-content"),y=c.querySelector(".fish-action-buttons"),w=c.querySelector("#confirm-detail-btn");(e=c.querySelector("#make-trophy-btn"))==null||e.addEventListener("click",()=>{o.haptic("light"),E="trophy",y.style.display="none",h.style.display="block",w.style.display="block",w.textContent="СДЕЛАТЬ ТРОФЕЕМ"}),(s=c.querySelector("#select-to-sell-btn"))==null||s.addEventListener("click",()=>{o.haptic("light"),E="sell",y.style.display="none",h.style.display="block",w.style.display="block",w.textContent="ПРОДАТЬ"}),c.querySelectorAll(".fish-detail-card").forEach(m=>{m.addEventListener("click",()=>{o.haptic("light");const M=parseInt(m.dataset.id||"0");g.has(M)?(g.delete(M),m.classList.remove("selected")):(g.add(M),m.classList.add("selected"))})}),(a=c.querySelector("#cancel-detail-btn"))==null||a.addEventListener("click",()=>{o.haptic("light"),document.body.removeChild(c)}),w==null||w.addEventListener("click",async()=>{if(g.size===0){alert("Выберите хотя бы одну рыбу");return}o.haptic("medium"),document.body.removeChild(c),E==="trophy"?await this.makeTrophies(Array.from(g)):E==="sell"&&await this.sellBulk({ids:Array.from(g)})}),c.addEventListener("click",m=>{m.target===c&&document.body.removeChild(c)})}catch(n){console.error("Failed to load fish details:",n),alert("Ошибка загрузки деталей рыбы")}}async makeTrophies(t){try{let e=0,s=!1,a=0,n=0;for(const r of t){const l=await u("/api/make-trophy",{method:"POST",body:JSON.stringify({id:r})});if(l!=null&&l.ok)e++;else if((l==null?void 0:l.error)==="insufficient_coins"){s=!0,a=l.required||1e4,n=l.current||0;break}}s?alert(`Недостаточно монет!
Требуется: ${a} 🪙
У вас: ${n} 🪙`):e>0&&(o.haptic("success"),alert(`Создано трофеев: ${e}
Списано: ${e*1e4} 🪙`),await this.loadInventory(),window.dispatchEvent(new CustomEvent("refresh-profile")))}catch{alert("Ошибка при создании трофеев")}}async sellBulk(t){try{const e=await u("/api/sell-bulk",{method:"POST",body:JSON.stringify(t)});e&&e.earned_coins!==void 0&&(o.haptic("success"),alert(`Успешно продано!
Получено: ${e.earned_coins} 🪙
Опыт: ${e.earned_xp} ✨`),this.mode="view",this.selectedIds.clear(),await this.loadInventory())}catch{alert("Ошибка при продаже")}}async loadInventory(){this.loading=!0;try{const t=await u("/api/inventory/grouped");this.items=(t==null?void 0:t.items)||[],this.renderInventory()}catch(t){console.error("Failed to load inventory:",t),this.renderError()}finally{this.loading=!1}}renderInventory(){const t=this.el.querySelector("#shop-content"),e=this.el.querySelector("#shop-sell-btn"),s=this.el.querySelector("#shop-select-actions");if(this.mode==="select"?(e.style.display="none",s.style.display="flex",this.updateSelectCount()):(e.style.display=this.items.length>0?"block":"none",s.style.display="none"),this.items.length===0){t.innerHTML=`
        <div class="shop-empty">
          <div class="shop-soon-icon">${b("shop")}</div>
          <h3>Садок пуст</h3>
          <p>Поймайте рыбу, чтобы она появилась здесь.</p>
        </div>
      `;return}t.innerHTML=`
      <div class="inventory-grid">
        ${this.items.map((a,n)=>{const r=C(a.rarity),l=T[r]||"#ccc",d=a.ids.every(g=>this.selectedIds.has(g)),c=a.ids.some(g=>this.selectedIds.has(g))&&!d;let p="";return this.mode==="select"&&(d?p="is-selected":c&&(p="is-partial")),`
            <div class="inv-card glass ${p}" style="--card-color: ${l}" data-idx="${n}">
              ${a.count>1?`<div class="inv-badge">${a.count}x</div>`:""}
              <div class="inv-img-wrap">
                <img src="${a.image_url}" alt="${a.name}" loading="lazy">
              </div>
              <div class="inv-details">
                <div class="inv-name">${a.name}</div>
                <div class="inv-rarity" style="color:${l}">${K(a.rarity)}</div>
                <div class="inv-weight">⚖️ ${a.total_weight.toFixed(2)} кг</div>
              </div>
              <div class="inv-price">
                <span>${a.price}</span> 🪙
              </div>
              ${this.mode==="select"?`<div class="select-indicator">${d?"✅":""}</div>`:""}
            </div>
          `}).join("")}
      </div>
    `,t.querySelectorAll(".inv-card").forEach(a=>{a.addEventListener("click",()=>{o.haptic("light");const n=parseInt(a.dataset.idx||"0"),r=this.items[n];this.mode==="select"?(r.ids.every(d=>this.selectedIds.has(d))?r.ids.forEach(d=>this.selectedIds.delete(d)):r.ids.forEach(d=>this.selectedIds.add(d)),this.renderInventory()):this.showFishDetailModal(r)})})}updateSelectCount(){const t=this.el.querySelector("#select-count");t&&(t.textContent=this.selectedIds.size.toString())}renderError(){const t=this.el.querySelector("#shop-content");t.innerHTML=`
      <div class="shop-empty">
        <div class="shop-soon-icon">❌</div>
        <h3>Ошибка загрузки</h3>
        <p>Не удалось загрузить инвентарь. Попробуйте позже.</p>
      </div>
    `}}const ut=["guild_beer","guild_rich","guild_cthulhu","guild_king"],pt=["#00b4d8","#f4a82e","#9b5de5","#ff6b6b","#a5a5a5","#4d908e"];let f=[],L=null,$=null,v=null,B=!1,F=!1;const mt={1:5,2:10,3:20,4:25,5:30};function wt(i,t){const e=Number(t);return e>0?e:mt[i]??mt[3]??20}function q(i,t=0){return i.length>0?i.length:Math.max(0,Number(t)||0)}const O=i=>({userId:String(i.user_id??i.userId??""),name:String(i.username||i.name||"user"),level:Number(i.level||0),role:i.role||"member",totalWeight:Number(i.total_weight||i.totalWeight||i.tournament_weight||0),joinedAt:i.joined_at?String(i.joined_at):void 0});function ie(i,t){const e=i.length,s=Math.max(0,e-Math.max(1,t));if(s<=0)return new Set;const a=i.filter(n=>n.role!=="leader").sort((n,r)=>{const l=n.joinedAt?new Date(n.joinedAt).getTime():0;return(r.joinedAt?new Date(r.joinedAt).getTime():0)-l}).slice(0,s);return new Set(a.map(n=>n.userId))}function vt(i,t){const e=Array.isArray(i.members)?i.members.map(O):(t==null?void 0:t.members)||[],s=(t==null?void 0:t.requests)??(Array.isArray(i.requests)?i.requests.map(n=>({requestId:String(n.request_id??n.id??""),userId:String(n.user_id??n.requester_user_id??""),name:String(n.username||"user"),level:Number(n.level||0),userAvatar:String(n.user_avatar||"👤")})):[]),a=(t==null?void 0:t.upgradeProgress)??(Array.isArray(i.upgrade_progress)?i.upgrade_progress.map(n=>({item:String(n.item||""),required:Number(n.required||0),current:Number(n.current||0)})):[]);return{id:String(i.id),name:i.name,avatar:i.avatar_emoji||"🔱",borderColor:i.color_hex||"#00b4d8",type:i.access_type||"open",level:i.level||1,members:e,requests:s,upgradeProgress:a,memberCount:q(e,i.members_count??i.member_count),capacity:wt(i.level||1,i.max_members),minLevel:i.min_level||0,totalWeight:Number(i.total_catch_weight||0),totalFish:Number(i.total_catch_count||0),canUpgrade:!!i.can_upgrade,...t}}function gt(){return $||v&&f.find(i=>i.id===v)||null}async function x(){try{const i=await u("/api/guilds");if(i&&i.ok){L=null,F=!!i.is_admin,f=(i.items||[]).map(e=>vt(e));const t=i.my_clan;if(t&&t.id){const e=Array.isArray(t.members)?t.members.map(O):[],s=Array.isArray(t.requests)?t.requests.map(r=>({requestId:String(r.request_id??r.id??""),userId:String(r.user_id??r.requester_user_id??""),name:String(r.username||"user"),level:Number(r.level||0),userAvatar:String(r.user_avatar||"👤")})):[],a=Array.isArray(t.upgrade_progress)?t.upgrade_progress.map(r=>({item:String(r.item||""),required:Number(r.required||0),current:Number(r.current||0)})):[];$=vt(t,{members:e,requests:s,upgradeProgress:a,canUpgrade:!!t.can_upgrade}),v=$.id,B=t.role==="leader";const n=f.findIndex(r=>r.id===$.id);n>=0?f[n]=$:f.unshift($)}else $=null,v=null,B=!1;return!0}return L=String((i==null?void 0:i.error)||"load_failed"),console.error("loadClans:",L),!1}catch(i){return L=i instanceof Error?i.message:"network_error",console.error("Failed to load clans:",i),!1}}async function ae(i){var t,e;try{const s=await u("/api/guilds/create",{method:"POST",body:JSON.stringify({name:i.name,avatar:i.avatar,color:i.borderColor,type:i.type,min_level:i.minLevel})});if(s&&s.ok)return await x(),f.find(a=>a.id===String(s.clan_id))||null;if(s&&!s.ok)if(s.reason==="not_enough_coins")alert(`Недостаточно монет для создания артели! Нужно ${s.cost.toLocaleString()} 🪙`);else if(s.reason==="tournament_active"){const a=((t=s.tournament)==null?void 0:t.ends_at)||((e=s.tournament)==null?void 0:e.endsAt),n=a?` до ${String(a).replace("T"," ").slice(0,16)}`:"";alert(`Во время турнира нельзя создавать артели${n}.`)}else alert(`Ошибка создания: ${s.reason||"неизвестная ошибка"}`)}catch(s){console.error("Failed to create guild:",s)}return null}async function ne(i){const t=f.find(e=>e.id===i);if(!t)return!1;try{const e=t.type==="open"?"/api/guilds/join":"/api/guilds/apply",s=await u(e,{method:"POST",body:JSON.stringify({guild_id:i})});if(s&&s.ok)return t.type==="open"&&(v=t.id),!0;s&&!s.ok&&(s.reason==="level_too_low"?alert(`Ваш уровень слишком низок! Требуется уровень ${s.required}`):s.reason==="not_enough_coins"?alert(`Недостаточно монет! Требуется ${s.cost} 🪙`):alert(`Ошибка: ${s.reason||s.error||"неизвестная ошибка"}`))}catch(e){console.error("Failed to join guild:",e)}return!1}async function ft(i,t){try{const e=await u("/api/guilds/request/respond",{method:"POST",body:JSON.stringify({request_id:i,action:t})});if(e&&e.ok)return await x(),!0;e&&!e.ok&&alert(`Ошибка обработки заявки: ${e.error||"неизвестная ошибка"}`)}catch(e){console.error("Failed to respond to clan request:",e)}return!1}async function re(){if(v)try{const i=await u("/api/guilds/leave",{method:"POST"});if(i&&i.ok){v=null,$=null,B=!1,F=!!(i.is_admin||F),await x();return}i&&!i.ok&&alert(`Не удалось покинуть артель: ${i.reason||i.error||"неизвестная ошибка"}`)}catch(i){console.error("Failed to leave guild:",i)}}async function Y(i){var e;const t=f.find(s=>s.id===i);try{const s=await u(`/api/guilds/members?guild_id=${encodeURIComponent(i)}`);if(s&&s.ok){const a=Array.isArray(s.members)?s.members.map(O):[],n=f.find(r=>r.id===i);return n&&(n.members=a,n.memberCount=q(a,s.members_count)),$&&$.id===i&&($.members=a,$.memberCount=q(a,s.members_count)),a}s&&!s.ok&&console.error("loadClanMembers:",s.error||s.reason)}catch(s){console.error("Failed to load clan members:",s)}return(e=t==null?void 0:t.members)!=null&&e.length?[...t.members]:[]}async function le(i,t=1){try{const e=await u("/api/guilds/donate",{method:"POST",body:JSON.stringify({item_name:i,quantity:t})});if(e&&e.ok)return await x(),!0;e&&!e.ok&&(e.reason==="not_enough_trash"?alert(`Недостаточно предметов. Есть ${e.available||0} из ${e.required||t}.`):e.reason==="not_in_clan"?alert("Вы не состоите в артели."):alert(`Ошибка пожертвования: ${e.reason||e.error||"неизвестная ошибка"}`))}catch(e){console.error("Failed to donate to guild:",e)}return!1}async function oe(){try{const i=await u("/api/guilds/upgrade",{method:"POST"});if(i&&i.ok)return await x(),!0;if(i&&!i.ok)if(i.reason==="not_enough_resources"||i.reason==="not_enough_donations"){const t=i.missing||{},e=Object.entries(t).map(([s,a])=>`${s}: не хватает ${a}`);alert(e.length?`Нужно ещё ресурсов:
${e.join(`
`)}`:"Не хватает ресурсов для улучшения.")}else i.reason==="max_level"?alert("Артель уже максимального уровня."):i.reason==="leader_only"||i.reason==="not_leader"?alert("Улучшать артель может только лидер."):alert(`Не удалось улучшить артель: ${i.reason||i.error||"неизвестная ошибка"}`)}catch(i){console.error("Failed to upgrade guild:",i)}return!1}async function ce(i){try{const t=await u("/api/guilds/members/remove",{method:"POST",body:JSON.stringify({member_id:i})});if(t&&t.ok)return await x(),!0;t&&!t.ok&&alert(`Не удалось удалить участника: ${t.reason||t.error||"неизвестная ошибка"}`)}catch(t){console.error("Failed to remove guild member:",t)}return!1}function X(i,t,e){return{id:String(i.id),title:String(i.title||""),startsAt:String(i.starts_at||""),endsAt:String(i.ends_at||""),createdBy:String(i.created_by||""),createdAt:String(i.created_at||""),isActive:t===String(i.id),phase:e==="active"||e==="grace"?e:void 0}}async function de(){try{const i=await u("/api/guilds/tournaments");if(i&&i.ok){const t=i.active_id?String(i.active_id):null,e=i.visible_id?String(i.visible_id):null,s=i.phase==="active"||i.phase==="grace"?i.phase:null,a=(i.items||[]).map(l=>X(l,t)),n=i.active?X(i.active,t,"active"):null,r=i.visible?X(i.visible,e,s||void 0):null;return{items:a,activeId:t,active:n,visibleId:e,visible:r,phase:s}}}catch(i){console.error("Failed to load clan tournaments:",i)}return{items:[],activeId:null,active:null,visibleId:null,visible:null,phase:null}}async function he(i,t){try{const e=await u(`/api/guilds/tournaments/members?guild_id=${encodeURIComponent(i)}&tournament_id=${encodeURIComponent(t)}`);if(e&&e.ok)return Array.isArray(e.members)?e.members.map(O):[]}catch(e){console.error("Failed to load tournament members:",e)}return[]}async function ue(i,t,e){try{const s=await u("/api/guilds/tournaments/create",{method:"POST",body:JSON.stringify({title:i,starts_at:t,ends_at:e})});if(s&&s.ok&&s.tournament){const a=s.tournament;return{id:String(a.id),title:String(a.title||""),startsAt:String(a.starts_at||""),endsAt:String(a.ends_at||""),createdBy:String(a.created_by||""),createdAt:String(a.created_at||""),isActive:!1}}}catch(s){console.error("Failed to create clan tournament:",s)}return null}async function pe(i){try{const t=await u(`/api/guilds/tournaments/leaderboard?tournament_id=${encodeURIComponent(i)}`);if(t&&t.ok)return(t.items||[]).map(e=>({clanId:String(e.clan_id??e.clanId??""),name:String(e.name||""),totalWeight:Number(e.total_weight||0),totalFish:Number(e.total_fish||0)}))}catch(t){console.error("Failed to load clan tournament leaderboard:",t)}return[]}class me{constructor(){this.contentEl=null,this.toolbarEl=null,this.tab="list",this.loading=!1,this.newGuildName="",this.selectedAvatar=ut[0],this.selectedColor=pt[0],this.selectedType="open",this.selectedMinLevel=0,this.visibleTournament=null,this.tournamentPhase=null,this.tournamentLeaderboard=[],this.showAdminTournamentForm=!1,this.tournamentTitle="",this.tournamentStarts="",this.tournamentEnds="",this.clanModalGuildId=null,this.clanModalGuildName="",this.clanModalMembers=[],this.clanModalLoading=!1,this.clanModalTournament=!1,this.el=this.buildShell(),this.modalHost=document.createElement("div"),this.modalHost.id="guild-modals-root",this.modalHost.className="guild-modals-root",document.body.appendChild(this.modalHost),document.body.classList.remove("guild-modal-open")}getElement(){return this.el}closeModals(){this.clanModalGuildId=null,this.clanModalMembers=[],this.showAdminTournamentForm=!1,this.renderModals()}buildShell(){const t=document.createElement("section");return t.id="screen-guilds",t.className="screen guilds-screen",t.setAttribute("role","main"),t.innerHTML=`
      <div class="guilds-header">
        <h1 class="page-title" id="guilds-page-title">АРТЕЛИ</h1>
      </div>
      <div class="guilds-toolbar" id="guilds-toolbar"></div>
      <div class="guild-container">
        <div id="guild-scroll-content" class="guild-content">
          <div class="guild-loading">Загрузка...</div>
        </div>
      </div>
    `,this.contentEl=t.querySelector("#guild-scroll-content"),this.toolbarEl=t.querySelector("#guilds-toolbar"),t}async init(){this.closeModals(),this.loading=!0,this.tab=v?"my":"list",this.render(),await x(),v&&await Y(v),await this.refreshTournaments(),this.loading=!1,this.render()}async refreshTournaments(){const t=await de();this.visibleTournament=t.visible||null,this.tournamentPhase=t.phase,this.visibleTournament?this.tournamentLeaderboard=await pe(this.visibleTournament.id):(this.tournamentLeaderboard=[],this.tab==="tournament"&&(this.tab="rating"))}formatWeight(t){return Number(t||0).toLocaleString("ru-RU",{minimumFractionDigits:2,maximumFractionDigits:2})}formatDate(t){if(!t)return"";const e=String(t);return e.includes("T")?e.replace("T"," ").slice(0,16):e.slice(0,16)}showTournamentTab(){return!!this.visibleTournament}renderTabs(){const t=[];return v&&t.push({id:"my",label:"МОЯ"}),t.push({id:"list",label:"АРТЕЛИ"}),t.push({id:"rating",label:"РЕЙТИНГ"}),this.showTournamentTab()&&t.push({id:"tournament",label:"ТУРНИР"}),`
      <div class="guild-tabs">
        ${t.map(e=>`
          <button type="button" class="guild-tab ${this.tab===e.id?"is-active":""}" data-tab="${e.id}">${e.label}</button>
        `).join("")}
      </div>
    `}render(){if(this.tab==="create"){this.renderCreate();return}const t=this.el.querySelector("#guilds-page-title");t&&(t.textContent="АРТЕЛИ");const e=F?`
      <button type="button" class="guild-admin-create-btn" id="guild-admin-tournament">
        🏆 СОЗДАТЬ ТУРНИР АРТЕЛЕЙ
      </button>
    `:"";this.toolbarEl&&(this.toolbarEl.innerHTML=`${this.renderTabs()}${e}`),this.contentEl&&(this.contentEl.innerHTML=this.loading?'<div class="guild-loading">Загрузка...</div>':`<div class="guild-tab-content">
            ${this.tab==="my"?this.renderManageContent():""}
            ${this.tab==="list"?this.renderListContent():""}
            ${this.tab==="rating"?this.renderRatingContent():""}
            ${this.tab==="tournament"?this.renderTournamentContent():""}
          </div>`),this.bindTabs(),this.bindTabContent(),this.bindAdminFab(),this.renderModals()}renderModals(){this.showAdminTournamentForm?(this.modalHost.innerHTML=this.renderAdminTournamentModalHtml(),this.bindAdminTournamentModal()):this.clanModalGuildId?(this.modalHost.innerHTML=this.renderClanModalHtml(),this.bindClanModal()):this.modalHost.innerHTML="",document.body.classList.toggle("guild-modal-open",!!this.modalHost.innerHTML)}bindTabs(){this.el.querySelectorAll(".guild-tab").forEach(t=>{t.addEventListener("click",async()=>{const e=t.getAttribute("data-tab");!e||e===this.tab||(this.tab=e,o.haptic("medium"),(e==="list"||e==="rating"||e==="tournament"||e==="my"||L)&&(this.loading=!0,this.render(),await x(),await this.refreshTournaments(),v&&await Y(v),this.loading=!1),this.render())})})}bindAdminFab(){var t;(t=this.el.querySelector("#guild-admin-tournament"))==null||t.addEventListener("click",()=>{this.clanModalGuildId=null,this.clanModalMembers=[],this.showAdminTournamentForm=!0,this.renderModals(),o.haptic("medium")})}renderLoadError(){return L?`<div class="guild-load-error glass">Не удалось загрузить артели.<br><span>${L}</span>
      <button type="button" class="guild-create-btn" id="guild-retry-load" style="margin-top:10px;width:100%;">ПОВТОРИТЬ</button></div>`:""}renderListContent(){if(L)return`${this.renderLoadError()}<div class="members-empty">Список временно недоступен.</div>`;const t=f.length?f.map(e=>`
      <div class="guild-card glass" data-id="${e.id}">
        <div class="guild-avatar" style="--border-color: ${e.borderColor}">${b(e.avatar)}</div>
        <div class="guild-info">
          <div class="guild-name">${e.name}${e.id===v?' <span class="guild-you-badge">вы</span>':""}</div>
          <div class="guild-meta">
            <span>⭐ Ур. ${e.level}</span>
            <span>👤 ${q(e.members,e.memberCount)}/${e.capacity}</span>
            <span>⚖️ ${this.formatWeight(e.totalWeight)} кг</span>
            <span>${e.type==="open"?"🔓":"🔒"}</span>
          </div>
        </div>
        ${e.id!==v?`
          <button type="button" class="adv-play-btn guild-join-btn" data-id="${e.id}" style="padding: 8px 12px; font-size: 9px;">
            ${e.type==="open"?"ВСТУПИТЬ":"ЗАЯВКА"}
          </button>
        `:""}
      </div>
    `).join(""):'<div class="members-empty">Пока нет артелей.</div>';return`
      <div class="guilds-header">
        ${v?"":'<button type="button" class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>'}
      </div>
      <div class="guild-list">${t}</div>
    `}bindTabContent(){var t;(t=this.el.querySelector("#guild-retry-load"))==null||t.addEventListener("click",async()=>{this.loading=!0,this.render(),await x(),await this.refreshTournaments(),this.loading=!1,this.render(),o.haptic("medium")}),this.tab==="list"&&this.bindList(),this.tab==="my"&&this.bindManage(),this.tab==="rating"&&this.bindRating(),this.tab==="tournament"&&this.bindTournament()}bindList(){var t;(t=this.el.querySelector("#guild-create-trigger"))==null||t.addEventListener("click",()=>{this.tab="create",this.render(),o.haptic("medium")}),this.el.querySelectorAll(".guild-join-btn").forEach(e=>{e.addEventListener("click",async s=>{s.stopPropagation();const a=e.getAttribute("data-id");if(await ne(a)){o.haptic("heavy");const r=f.find(l=>l.id===a);(r==null?void 0:r.type)==="invite"?alert("Заявка отправлена!"):(this.tab="my",await this.init())}else o.haptic("error")})})}renderRatingContent(){return L?`${this.renderLoadError()}<div class="members-empty">Рейтинг временно недоступен.</div>`:`
      <p class="guild-section-hint">Рейтинг по суммарному весу улова всех участников артели</p>
      <div class="guild-total-weight-hero glass">
        <div class="hero-label">Топ артелей по улову</div>
        <div class="hero-sub">Вес сохраняется в артели, даже если рыбак вышел</div>
      </div>
      <div class="guild-rating-list">
        ${[...f].sort((e,s)=>s.totalWeight-e.totalWeight).map((e,s)=>`
          <button type="button" class="guild-rating-card glass" data-id="${e.id}" data-tournament="0">
            <div class="guild-rank">#${s+1}</div>
            <div class="guild-avatar" style="--border-color: ${e.borderColor}">${b(e.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${e.name}</div>
              <div class="guild-meta">
                <span>👤 ${q(e.members,e.memberCount)}</span>
                <span class="guild-weight-highlight">⚖️ ${this.formatWeight(e.totalWeight)} кг</span>
              </div>
            </div>
          </button>
        `).join("")}
      </div>
    `}bindRating(){this.el.querySelectorAll('.guild-rating-card[data-tournament="0"]').forEach(t=>{t.addEventListener("click",async()=>{var n,r;const e=t.getAttribute("data-id");if(!e)return;const s=f.find(l=>l.id===e);this.clanModalGuildId=e,this.clanModalGuildName=(s==null?void 0:s.name)||"Артель",this.clanModalTournament=!1,this.clanModalLoading=!0,this.clanModalMembers=(n=s==null?void 0:s.members)!=null&&n.length?[...s.members]:[],this.renderModals();const a=await Y(e);this.clanModalMembers=a.length?a:((r=f.find(l=>l.id===e))==null?void 0:r.members)||[],this.clanModalLoading=!1,this.renderModals()})})}renderTournamentContent(){const t=this.visibleTournament;if(!t)return'<div class="members-empty">Турнир недоступен.</div>';const e=this.tournamentPhase==="grace"?"Турнир завершён — итоги ещё сутки":"Идёт турнир",s=`${this.formatDate(t.startsAt)} → ${this.formatDate(t.endsAt)}`,a=this.tournamentLeaderboard.length?this.tournamentLeaderboard.map((n,r)=>`
          <button type="button" class="tournament-row glass" data-id="${n.clanId}" data-tournament="1">
            <div class="tournament-rank">#${r+1}</div>
            <div class="tournament-name">${n.name}</div>
            <div class="tournament-weight">${this.formatWeight(n.totalWeight)} кг</div>
          </button>
        `).join(""):'<div class="members-empty">Пока нет улова за период турнира.</div>';return`
      <div class="tournament-block glass">
        <div class="tournament-header">
          <div>
            <div class="tournament-title">${t.title}</div>
            <div class="tournament-range">${s}</div>
            <div class="tournament-phase-badge">${e}</div>
          </div>
        </div>
        <p class="guild-section-hint">Учитывается только улов с ${this.formatDate(t.startsAt)} по ${this.formatDate(t.endsAt)}</p>
        <div class="tournament-list">${a}</div>
      </div>
    `}bindTournament(){this.el.querySelectorAll('[data-tournament="1"]').forEach(t=>{t.addEventListener("click",async()=>{const e=t.getAttribute("data-id");if(!e||!this.visibleTournament)return;const s=this.tournamentLeaderboard.find(a=>a.clanId===e);this.clanModalGuildId=e,this.clanModalGuildName=(s==null?void 0:s.name)||"Артель",this.clanModalTournament=!0,this.clanModalLoading=!0,this.clanModalMembers=[],this.renderModals(),this.clanModalMembers=await he(e,this.visibleTournament.id),this.clanModalLoading=!1,this.renderModals()})})}renderClanModalHtml(){const t=this.clanModalTournament?"Улов за турнир":"Улов в артели",e=this.clanModalLoading?'<div class="members-empty">Загрузка...</div>':this.clanModalMembers.length?[...this.clanModalMembers].sort((s,a)=>a.totalWeight-s.totalWeight).map((s,a)=>`
            <div class="member-row">
              <div class="member-rank">#${a+1}</div>
              <div class="member-name">${s.name}${s.role==="leader"?" 👑":""}</div>
              <div class="member-meta">Ур. ${s.level}</div>
              <div class="member-weight">${this.formatWeight(s.totalWeight)} кг</div>
            </div>
          `).join(""):'<div class="members-empty">Нет участников.</div>';return`
      <div class="guild-modal-backdrop" id="clan-modal-backdrop">
        <div class="guild-modal-sheet" role="dialog" aria-modal="true">
          <div class="guild-modal-handle"></div>
          <div class="guild-modal-header">
            <div class="guild-modal-title">${this.clanModalGuildName}</div>
            <button type="button" class="guild-modal-close" id="clan-modal-close" aria-label="Закрыть">✕</button>
          </div>
          <p class="form-label guild-modal-sub">Участники · ${t}</p>
          <div class="members-list modal-members">${e}</div>
        </div>
      </div>
    `}bindClanModal(){var e,s,a;const t=()=>{this.clanModalGuildId=null,this.clanModalMembers=[],this.renderModals()};(e=this.modalHost.querySelector("#clan-modal-close"))==null||e.addEventListener("click",t),(s=this.modalHost.querySelector("#clan-modal-backdrop"))==null||s.addEventListener("click",n=>{n.target===n.currentTarget&&t()}),(a=this.modalHost.querySelector(".guild-modal-sheet"))==null||a.addEventListener("click",n=>n.stopPropagation())}renderAdminTournamentModalHtml(){return`
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
    `}bindAdminTournamentModal(){var n,r,l,d;const t=()=>{this.showAdminTournamentForm=!1,this.renderModals()};(n=this.modalHost.querySelector("#admin-tournament-close"))==null||n.addEventListener("click",t),(r=this.modalHost.querySelector("#admin-tournament-backdrop"))==null||r.addEventListener("click",c=>{c.target===c.currentTarget&&t()}),(l=this.modalHost.querySelector(".guild-modal-sheet"))==null||l.addEventListener("click",c=>c.stopPropagation());const e=this.modalHost.querySelector("#tournament-title");e==null||e.addEventListener("input",()=>{this.tournamentTitle=e.value});const s=this.modalHost.querySelector("#tournament-start");s==null||s.addEventListener("input",()=>{this.tournamentStarts=s.value});const a=this.modalHost.querySelector("#tournament-end");a==null||a.addEventListener("input",()=>{this.tournamentEnds=a.value}),(d=this.modalHost.querySelector("#tournament-create"))==null||d.addEventListener("click",async()=>{const c=this.tournamentTitle.trim();if(!c||!this.tournamentStarts||!this.tournamentEnds){alert("Заполните название и даты.");return}await ue(c,this.tournamentStarts,this.tournamentEnds)?(this.tournamentTitle="",this.tournamentStarts="",this.tournamentEnds="",this.showAdminTournamentForm=!1,await this.refreshTournaments(),this.tab="tournament",o.haptic("heavy"),this.render()):(alert("Не удалось создать турнир."),o.haptic("error"))})}renderManageContent(){const t=gt();if(!t)return'<div class="members-empty">Вы не состоите в артели.</div>';const e=B,s=[...t.members||[]],a=q(s,t.memberCount),n=e?ie(s,t.capacity):new Set,r=n.size,l=[...s].sort((h,y)=>{const w=h.joinedAt?new Date(h.joinedAt).getTime():0,m=y.joinedAt?new Date(y.joinedAt).getTime():0;return w-m}),d=t.upgradeProgress||[],c=wt(t.level+1),p=[...f].sort((h,y)=>y.totalWeight-h.totalWeight).findIndex(h=>h.id===t.id),g=p>=0?`#${p+1}`:"—",E=`
      <div class="glass" style="padding: 12px; margin-bottom: 12px;">
        <p class="form-label" style="margin-bottom: 10px; color: var(--gold); font-size: 10px;">
          ${d.length?`Улучшение до ур. ${t.level+1} · лимит ${c} участников`:"Максимальный уровень артели"}
        </p>
        ${d.length?`
          <p class="guild-section-hint" style="margin-bottom:8px;">Сдайте мусор из инвентаря в склад артели, затем улучшите.</p>
          <div class="upgrade-section">
            ${d.map((h,y)=>{const w=h.required>0?Math.min(100,h.current/h.required*100):0;return`
              <div class="upgrade-item">
                <div class="upgrade-main">
                  <div class="upgrade-labels"><span>${h.item}</span><span>${h.current}/${h.required}</span></div>
                  <div class="upgrade-bar"><div class="upgrade-fill" style="width: ${w}%"></div></div>
                </div>
                <button type="button" class="donate-btn" data-idx="${y}">+1</button>
              </div>
            `}).join("")}
          </div>
          ${e?`
            <div class="guild-upgrade-actions">
              <button type="button" class="guild-create-btn" id="guild-upgrade" ${t.canUpgrade?"":"disabled"}>
                ${t.canUpgrade?`УЛУЧШИТЬ ДО УР. ${t.level+1}`:"СНАЧАЛА СОБЕРИТЕ РЕСУРСЫ"}
              </button>
            </div>
          `:'<p class="guild-section-hint">Вклады могут делать все участники. Улучшает лидер.</p>'}
        `:'<div class="members-empty">Артель на максимальном уровне.</div>'}
      </div>
    `;return`
      <div class="glass guild-my-header" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${t.borderColor}">${b(t.avatar)}</div>
        <div class="guild-info">
          <div class="guild-name" style="font-size:17px;">${t.name}</div>
          <div class="guild-meta" style="font-size:10px;">Ур. ${t.level} · ${a}/${t.capacity} участников</div>
        </div>
      </div>

      <div class="guild-catch-hero glass">
        <div class="catch-hero-value">${this.formatWeight(t.totalWeight)} <span>кг</span></div>
        <div class="catch-hero-label">Общий улов артели</div>
        <div class="catch-hero-fish">🐟 ${t.totalFish||0} рыб</div>
      </div>

      <div class="my-guild-stats">
        <div class="glass stat-box">
          <div class="stat-val">${t.type==="open"?"🔓":"🔒"}</div>
          <div class="stat-lab">Доступ</div>
        </div>
        <div class="glass stat-box">
          <div class="stat-val">${g}</div>
          <div class="stat-lab">В рейтинге</div>
        </div>
      </div>

      ${E}

      <div class="glass members-panel">
        <p class="form-label" style="margin-bottom: 10px;">Участники</p>
        ${r>0?`
          <div class="guild-over-capacity-banner">
            Превышен лимит на ${r} чел. Исключите последних вступивших (отмечены ниже).
          </div>
        `:""}
        <div class="members-list">
          ${l.length?l.map((h,y)=>`
            <div class="member-row ${n.has(h.userId)?"member-row--excess":""}">
              <div class="member-rank">#${y+1}</div>
              <div class="member-name">${h.name}${h.role==="leader"?" 👑":""}${n.has(h.userId)?' <span style="color:#ff8a6a;font-size:9px">лишний</span>':""}</div>
              <div class="member-meta">Ур. ${h.level}</div>
              <div class="member-weight">${this.formatWeight(h.totalWeight)} кг</div>
              ${e&&h.role!=="leader"?`<button type="button" class="member-remove-btn" data-id="${h.userId}" title="Исключить">✕</button>`:""}
            </div>
          `).join(""):'<div class="members-empty">Пока нет участников.</div>'}
        </div>
      </div>

      ${e&&t.requests.length>0?`
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки</p>
          <div class="requests-list">
            ${t.requests.map(h=>`
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${h.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${h.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${h.level}</div>
                </div>
                <div class="req-btns">
                  <button type="button" class="req-btn req-btn--no" data-req="${h.requestId}">✕</button>
                  <button type="button" class="req-btn req-btn--yes" data-req="${h.requestId}">✓</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `:""}

      <div class="guild-actions">
        <button type="button" class="guild-leave-btn" id="btn-leave">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `}bindManage(){var e,s;const t=gt();t&&((e=this.el.querySelector("#btn-leave"))==null||e.addEventListener("click",async()=>{confirm("Покинуть артель? Ваш улов останется в статистике этой артели.")&&(await re(),o.haptic("medium"),this.tab="list",await this.init())}),this.el.querySelectorAll(".donate-btn").forEach(a=>{a.addEventListener("click",()=>{const n=parseInt(a.getAttribute("data-idx"),10),r=t.upgradeProgress[n];le(r.item,1).then(async l=>{o.haptic(l?"selection":"error"),l&&await this.init()})})}),(s=this.el.querySelector("#guild-upgrade"))==null||s.addEventListener("click",async()=>{const a=await oe();o.haptic(a?"heavy":"error"),a&&await this.init()}),this.el.querySelectorAll(".req-btn--yes").forEach(a=>{a.addEventListener("click",async()=>{const n=a.getAttribute("data-req");n&&await ft(n,"accept")&&await this.init()})}),this.el.querySelectorAll(".req-btn--no").forEach(a=>{a.addEventListener("click",async()=>{const n=a.getAttribute("data-req");n&&await ft(n,"decline")&&await this.init()})}),this.el.querySelectorAll(".member-remove-btn").forEach(a=>{a.addEventListener("click",async()=>{const n=a.getAttribute("data-id");!n||!confirm("Удалить участника?")||await ce(n)&&await this.init()})}))}renderCreate(){var n,r;const t=this.el.querySelector("#guilds-page-title");t&&(t.textContent="НОВАЯ АРТЕЛЬ"),this.toolbarEl&&(this.toolbarEl.innerHTML="");const e=`
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" value="${this.newGuildName}">
        </div>
        <div class="form-group">
          <label class="form-label">Герб</label>
          <div class="avatar-grid">
            ${ut.map(l=>`<div class="avatar-opt ${this.selectedAvatar===l?"is-selected":""}" data-val="${l}">${b(l)}</div>`).join("")}
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Цвет</label>
          <div class="color-row">
            ${pt.map(l=>`<div class="color-opt ${this.selectedColor===l?"is-selected":""}" data-val="${l}" style="background:${l}"></div>`).join("")}
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Вход</label>
          <div class="type-row">
            <div class="type-opt ${this.selectedType==="open"?"is-selected":""}" data-val="open">СВОБОДНЫЙ</div>
            <div class="type-opt ${this.selectedType==="invite"?"is-selected":""}" data-val="invite">ПО ПРИГЛАШЕНИЮ</div>
          </div>
        </div>
        ${this.selectedType==="open"?`
        <div class="form-group">
          <label class="form-label" id="min-level-label">Мин. уровень: ${this.selectedMinLevel}</label>
          <input type="range" id="min-level-slider" min="0" max="100" value="${this.selectedMinLevel}" style="width:100%; accent-color:var(--gold);">
        </div>`:""}
        <div style="text-align:center; margin:15px 0; color:var(--gold); font-weight:bold;">Стоимость: 100 000 🪙</div>
        <div style="display:flex; gap:10px;">
          <button type="button" class="guild-leave-btn" id="create-cancel" style="flex:1">ОТМЕНА</button>
          <button type="button" class="guild-create-btn" id="create-confirm" style="flex:2">СОЗДАТЬ</button>
        </div>
      </div>
    `;this.contentEl&&(this.contentEl.innerHTML=e);const s=this.el.querySelector("#guild-name-input");s==null||s.addEventListener("input",()=>{this.newGuildName=s.value}),this.el.querySelectorAll(".avatar-opt").forEach(l=>{l.addEventListener("click",()=>{this.selectedAvatar=l.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".color-opt").forEach(l=>{l.addEventListener("click",()=>{this.selectedColor=l.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".type-opt").forEach(l=>{l.addEventListener("click",()=>{this.selectedType=l.getAttribute("data-val"),this.render()})});const a=this.el.querySelector("#min-level-slider");a==null||a.addEventListener("input",()=>{this.selectedMinLevel=parseInt(a.value,10);const l=this.el.querySelector("#min-level-label");l&&(l.textContent=`Мин. уровень: ${this.selectedMinLevel}`)}),(n=this.el.querySelector("#create-cancel"))==null||n.addEventListener("click",()=>{this.tab=v?"my":"list",this.render()}),(r=this.el.querySelector("#create-confirm"))==null||r.addEventListener("click",async()=>{if(this.newGuildName.trim().length<3){alert("Слишком короткое название!");return}await ae({name:this.newGuildName,avatar:this.selectedAvatar,borderColor:this.selectedColor,type:this.selectedType,minLevel:this.selectedMinLevel})?(o.haptic("heavy"),this.tab="my",await this.init()):o.haptic("error")})}}let et=[],_=[];async function N(){try{const i=await u("/api/friends");if(i&&i.ok){const t=Array.isArray(i.items)?i.items:[],e=Array.isArray(i.incoming_requests)?i.incoming_requests:[];et=t.map(s=>({id:String(s.user_id),name:s.username,level:Number(s.level||0),avatar:"👤",online:!!s.is_online,xp:Number(s.xp||0)})),_=e.map(s=>({id:String(s.request_id||s.id),name:String(s.username||"user"),level:Number(s.level||0),avatar:"👤"}))}}catch(i){console.error("Failed to load friends:",i)}}async function ve(i){try{const t=await u("/api/friends/add",{method:"POST",body:JSON.stringify({username:i})});return!!(t!=null&&t.ok)}catch(t){return console.error("Failed to send friend request:",t),!1}}async function ge(i){return kt(i,"accept")}async function fe(i){return kt(i,"decline")}async function kt(i,t){try{const e=await u("/api/friends/request/respond",{method:"POST",body:JSON.stringify({request_id:i,action:t})});if(e!=null&&e.ok)return await N(),!0}catch(e){console.error("Failed to respond friend request:",e)}return!1}class be{constructor(){this.currentView="list",this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-friends",t.className="screen friends-screen",t.setAttribute("role","main"),t}async init(){this.loading=!0,this.render(),await N(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}this.currentView==="requests"?this.renderRequests():this.renderList()}renderList(){var t,e;this.el.innerHTML=`
      <div class="friends-header-row">
        <h1 class="page-title" style="margin-bottom:0">ДРУЗЬЯ</h1>
        <div class="friends-notif-btn" id="btn-show-requests">
          <span>🔔</span>
          ${_.length>0?`<div class="notif-badge">${_.length}</div>`:""}
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
        ${et.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:20px;">У вас пока нет друзей</p>':""}
        ${et.map(s=>`
          <div class="friend-card glass">
            <div class="friend-avatar">${s.avatar}</div>
            <div class="friend-info">
              <div class="friend-name">${s.name}</div>
              <div class="friend-meta">Ур. ${s.level} · ${s.online?'<span style="color:#2ecc71">Online</span>':'<span style="opacity:0.5">Offline</span>'}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `,(t=this.el.querySelector("#btn-show-requests"))==null||t.addEventListener("click",()=>{this.currentView="requests",this.render(),o.haptic("medium")}),(e=this.el.querySelector("#btn-add-search"))==null||e.addEventListener("click",async()=>{const s=this.el.querySelector("#friend-search");s.value.trim()&&(await ve(s.value.trim())?(alert("Запрос отправлен!"),s.value="",o.haptic("light"),await N(),this.render()):(o.haptic("error"),alert("Не удалось отправить заявку.")))})}renderRequests(){var t;this.el.innerHTML=`
      <div class="friends-header-row">
        <button class="back-btn" id="btn-back-list">←</button>
        <h1 class="page-title" style="margin:0; flex:1">ЗАЯВКИ</h1>
      </div>

      <div class="requests-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${_.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:40px;">Нет новых заявок</p>':""}
        ${_.map(e=>`
          <div class="request-card glass">
            <div class="req-avatar">${e.avatar}</div>
            <div class="req-info">
              <div class="req-name">${e.name}</div>
              <div class="req-lvl">Ур. ${e.level} хочет в друзья!</div>
            </div>
            <div class="req-btns">
               <button class="req-btn req-btn--no" data-id="${e.id}">✕</button>
               <button class="req-btn req-btn--yes" data-id="${e.id}">✓</button>
            </div>
          </div>
        `).join("")}
      </div>
    `,(t=this.el.querySelector("#btn-back-list"))==null||t.addEventListener("click",()=>{this.currentView="list",this.render(),o.haptic("light")}),this.el.querySelectorAll(".req-btn--yes").forEach(e=>{e.addEventListener("click",async()=>{const s=e.getAttribute("data-id"),a=await ge(s);o.haptic(a?"heavy":"error"),this.render()})}),this.el.querySelectorAll(".req-btn--no").forEach(e=>{e.addEventListener("click",async()=>{const s=e.getAttribute("data-id"),a=await fe(s);o.haptic(a?"medium":"error"),this.render()})})}}class ye{constructor(){this.currentType="normal",this.isLoading=!1,this.el=this.build()}build(){const t=document.createElement("section");return t.id="screen-rating",t.className="screen",t.setAttribute("role","main"),t.setAttribute("aria-label","Рейтинг"),t.innerHTML=`
      <div class="screen-header">
        <button class="back-btn" id="rating-back-btn">← Назад</button>
        <h1 class="page-title">РЕЙТИНГ</h1>
        <div></div>
      </div>
      
      <div class="rating-tabs">
        <button class="rating-tab is-active" data-type="normal">
          🎟️ Обычные билеты
        </button>
        <button class="rating-tab" data-type="gold">
          🎫 Золотые билеты
        </button>
      </div>

      <div class="rating-my-rank glass" id="rating-my-rank">
        <div class="rating-loading">Загрузка...</div>
      </div>

      <div class="rating-list glass" id="rating-list">
        <div class="rating-loading">Загрузка рейтинга...</div>
      </div>
    `,t}getElement(){return this.el}async init(){this.bindEvents(),await this.loadRating()}bindEvents(){setTimeout(()=>{const e=this.el.querySelector("#rating-back-btn");e&&e.addEventListener("click",s=>{s.preventDefault(),s.stopPropagation(),console.log("Rating back button clicked");const a=new CustomEvent("navigate-home");window.dispatchEvent(a)})},100);const t=this.el.querySelectorAll(".rating-tab");t.forEach(e=>{e.addEventListener("click",()=>{const s=e.dataset.type;s===this.currentType||this.isLoading||(o.haptic("selection"),t.forEach(a=>a.classList.remove("is-active")),e.classList.add("is-active"),this.currentType=s,this.loadRating())})})}async loadRating(){if(this.isLoading)return;this.isLoading=!0;const t=this.el.querySelector("#rating-list"),e=this.el.querySelector("#rating-my-rank");t.innerHTML='<div class="rating-loading">Загрузка...</div>',e.innerHTML='<div class="rating-loading">Загрузка...</div>';try{const s=await J(`/api/tickets/rating?ticket_type=${this.currentType}&limit=50`);if(!s.ok||!s.items)throw new Error("Failed to load rating");this.renderMyRank(e,s.my_rank,s.ticket_type),this.renderList(t,s.items)}catch(s){console.error("Failed to load rating:",s),t.innerHTML='<div class="rating-error">Ошибка загрузки рейтинга</div>',e.innerHTML='<div class="rating-error">Ошибка загрузки</div>'}finally{this.isLoading=!1}}renderMyRank(t,e,s){const a=s==="gold"?"🎫":"🎟️",n=s==="gold"?"золотых":"обычных";if(e===null||e===0)t.innerHTML=`
        <div class="my-rank-content">
          <div class="my-rank-icon">${a}</div>
          <div class="my-rank-text">
            <div class="my-rank-label">Ваше место</div>
            <div class="my-rank-value">Нет ${n} билетов</div>
          </div>
        </div>
      `;else{const r=e===1?"🥇":e===2?"🥈":e===3?"🥉":"";t.innerHTML=`
        <div class="my-rank-content">
          <div class="my-rank-icon">${r||a}</div>
          <div class="my-rank-text">
            <div class="my-rank-label">Ваше место в топе</div>
            <div class="my-rank-value">#${e}</div>
          </div>
        </div>
      `}}renderList(t,e){if(!e||e.length===0){t.innerHTML='<div class="rating-empty">Рейтинг пуст</div>';return}const s=e.map(a=>{const n=a.place===1?"🥇":a.place===2?"🥈":a.place===3?"🥉":"";return`
        <div class="rating-item ${a.place<=3?"rating-item-top":""}">
          <div class="rating-place">
            ${n?`<span class="rating-medal">${n}</span>`:`<span class="rating-number">#${a.place}</span>`}
          </div>
          <div class="rating-user">
            <div class="rating-username">${this.escapeHtml(a.username)}</div>
            <div class="rating-user-id">ID: ${a.user_id}</div>
          </div>
          <div class="rating-tickets">
            <div class="rating-tickets-value">${a.tickets}</div>
            <div class="rating-tickets-label">билетов</div>
          </div>
        </div>
      `}).join("");t.innerHTML=s}escapeHtml(t){const e=document.createElement("div");return e.textContent=t,e.innerHTML}}const we=793216884;class ke{constructor(){this.currentType="normal",this.isLoading=!1,this.isOwner=!1,this.el=this.build(),this.checkOwner()}checkOwner(){const t=o.getUser();this.isOwner=(t==null?void 0:t.id)===we}build(){const t=document.createElement("section");return t.id="screen-results",t.className="screen",t.setAttribute("role","main"),t.setAttribute("aria-label","Результаты"),t.innerHTML=`
      <div class="screen-header">
        <button class="back-btn" id="results-back-btn">← Назад</button>
        <h1 class="page-title">РЕЗУЛЬТАТЫ</h1>
        <div></div>
      </div>
      
      <div class="results-tabs">
        <button class="results-tab is-active" data-type="normal">
          🎟️ Обычные билеты
        </button>
        <button class="results-tab" data-type="gold">
          🎫 Золотые билеты
        </button>
      </div>

      <div id="results-owner-panel" class="results-owner-panel glass" style="display: none;">
        <h3 class="results-panel-title">Создать розыгрыш</h3>
        <div class="results-form">
          <div class="results-form-row">
            <label class="results-label">Дата начала</label>
            <input type="datetime-local" id="results-start-date" class="results-input" />
          </div>
          <div class="results-form-row">
            <label class="results-label">Дата окончания</label>
            <input type="datetime-local" id="results-end-date" class="results-input" />
          </div>
          <div class="results-form-row">
            <label class="results-label">Количество победителей</label>
            <input type="number" id="results-count" class="results-input" min="1" max="100" value="3" />
          </div>
          <button id="results-create-btn" class="results-create-btn">
            🎲 Провести розыгрыш
          </button>
        </div>
      </div>

      <div class="results-list glass" id="results-list">
        <div class="results-loading">Загрузка результатов...</div>
      </div>
    `,t}getElement(){return this.el}async init(){if(this.isOwner){const t=this.el.querySelector("#results-owner-panel");t&&(t.style.display="block")}this.bindEvents(),await this.loadResults()}bindEvents(){setTimeout(()=>{const e=this.el.querySelector("#results-back-btn");e&&e.addEventListener("click",s=>{s.preventDefault(),s.stopPropagation(),console.log("Results back button clicked");const a=new CustomEvent("navigate-home");window.dispatchEvent(a)})},100);const t=this.el.querySelectorAll(".results-tab");if(t.forEach(e=>{e.addEventListener("click",()=>{const s=e.dataset.type;s===this.currentType||this.isLoading||(o.haptic("selection"),t.forEach(a=>a.classList.remove("is-active")),e.classList.add("is-active"),this.currentType=s,this.loadResults())})}),this.isOwner){const e=this.el.querySelector("#results-create-btn");e&&e.addEventListener("click",()=>this.createDraw())}}async loadResults(){if(this.isLoading)return;this.isLoading=!0;const t=this.el.querySelector("#results-list");t.innerHTML='<div class="results-loading">Загрузка...</div>';try{const e=await J(`/api/tickets/results?ticket_type=${this.currentType}`);if(!e.ok)throw new Error("Failed to load results");this.renderResults(t,e)}catch(e){console.error("Failed to load results:",e),t.innerHTML='<div class="results-error">Ошибка загрузки результатов</div>'}finally{this.isLoading=!1}}async createDraw(){var l;if(this.isLoading)return;const t=this.el.querySelector("#results-start-date"),e=this.el.querySelector("#results-end-date"),s=this.el.querySelector("#results-count"),a=t.value,n=e.value,r=parseInt(s.value)||3;if(!a||!n){o.showAlert("Укажите даты начала и окончания розыгрыша");return}if(new Date(a)>new Date(n)){o.showAlert("Дата начала не может быть позже даты окончания");return}this.isLoading=!0,o.haptic("medium");try{const d=await J("/api/tickets/draw",{method:"POST",body:JSON.stringify({ticket_type:this.currentType,start_date:a,end_date:n,count:r})});if(!d.ok)throw new Error("Failed to create draw");o.showAlert(`Розыгрыш проведен! Победителей: ${((l=d.items)==null?void 0:l.length)||0}`),await this.loadResults()}catch(d){console.error("Failed to create draw:",d),o.showAlert("Ошибка при проведении розыгрыша")}finally{this.isLoading=!1}}renderResults(t,e){if(!e.items||e.items.length===0){t.innerHTML=`
        <div class="results-empty">
          <div class="results-empty-icon">🎲</div>
          <div class="results-empty-text">Результатов розыгрышей пока нет</div>
        </div>
      `;return}const s=e.period,a=s?`
      <button class="results-period-btn" id="results-toggle-btn">
        <div class="results-period-btn-icon">📅</div>
        <div class="results-period-btn-text">
          <div class="results-period-btn-label">Результаты розыгрыша</div>
          <div class="results-period-btn-date">${this.formatDate(s.start_date)} — ${this.formatDate(s.end_date)}</div>
        </div>
        <div class="results-period-btn-arrow">▼</div>
      </button>
    `:"",n=e.items.map(c=>{const p=c.place===1?"🥇":c.place===2?"🥈":c.place===3?"🥉":"🎖️";return`
        <div class="results-winner ${c.place<=3?"results-winner-top":""}">
          <div class="results-winner-place">
            <span class="results-medal">${p}</span>
            <span class="results-place-number">#${c.place}</span>
          </div>
          <div class="results-winner-info">
            <div class="results-winner-username">${this.escapeHtml(c.username)}</div>
            <div class="results-winner-id">ID: ${c.user_id}</div>
            <div class="results-winner-ticket">Билет: <strong>${c.ticket_code}</strong></div>
          </div>
        </div>
      `}).join("");t.innerHTML=`
      ${a}
      <div class="results-winners" id="results-winners-list" style="display: none;">
        ${n}
      </div>
    `;const r=t.querySelector("#results-toggle-btn"),l=t.querySelector("#results-winners-list"),d=t.querySelector(".results-period-btn-arrow");r&&l&&r.addEventListener("click",()=>{const c=l.style.display!=="none";l.style.display=c?"none":"flex",d&&(d.textContent=c?"▼":"▲"),o.haptic("selection")})}formatDate(t){try{return new Date(t).toLocaleDateString("ru-RU",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return t}}escapeHtml(t){const e=document.createElement("div");return e.textContent=t,e.innerHTML}}class $e{constructor(){this.token="",this.challenge=null,this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-captcha",t.className="screen captcha-screen",t.setAttribute("role","main"),t.innerHTML=`
      <div class="captcha-container">
        <h1 class="captcha-title">🧩 Проверка рыбака</h1>
        <p class="captcha-subtitle">Подтвердите, что вы человек</p>
        
        <div id="captcha-status" class="captcha-status loading">
          ⏳ Загрузка капчи...
        </div>
        
        <div id="captcha-content" style="display:none;">
          <div class="captcha-block captcha-question-block">
            <h3>❓ Вопрос</h3>
            <p id="captcha-question" class="captcha-question">Загрузка вопроса...</p>
          </div>

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
    `,t}async init(){const t=new URLSearchParams(window.location.search);if(this.token=t.get("captcha_token")||"",!this.token){this.showError("Токен капчи не найден. Откройте апку по ссылке из бота.");return}await this.loadChallenge(),this.bindEvents()}bindEvents(){const t=this.el.querySelector("#captcha-submit"),e=this.el.querySelector("#captcha-answer");t&&e&&(t.addEventListener("click",()=>{o.haptic("medium"),this.submitAnswer(e.value)}),e.addEventListener("keypress",s=>{s.key==="Enter"&&(o.haptic("medium"),this.submitAnswer(e.value))}))}async loadChallenge(){this.loading=!0,this.showStatus("loading","⏳ Загрузка капчи...");try{const t=await u(`/api/captcha/challenge?token=${this.token}`);if(!t||!t.ok){const e=(t==null?void 0:t.error)||"unknown_error";if(e==="penalty_active"){const s=(t==null?void 0:t.penalty_until)||"";this.showPenalty(s)}else e==="challenge_expired"?this.showError("⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте."):e==="challenge_not_found"?this.showError("❌ Капча не найдена. Запросите новую капчу в боте."):this.showError(`❌ Ошибка: ${e}`);return}if(t.penalty_active){const e=t.penalty_until||"";this.showPenalty(e);return}if(this.challenge=t.challenge||null,!this.challenge){this.showError("❌ Капча не найдена");return}this.renderChallenge(),this.startTimer()}catch(t){console.error("Failed to load captcha:",t),this.showError("❌ Ошибка загрузки капчи. Попробуйте позже.")}finally{this.loading=!1}}renderChallenge(){if(!this.challenge)return;const t=this.el.querySelector("#captcha-content"),e=this.el.querySelector("#captcha-question"),s=this.el.querySelector("#captcha-map"),a=this.el.querySelector("#captcha-steps");t.style.display="block",this.showStatus("",""),e&&this.challenge.question?(e.textContent=this.challenge.question,console.log("Captcha question:",this.challenge.question)):console.warn("No question in challenge:",this.challenge),s&&this.challenge.map?s.innerHTML=Object.entries(this.challenge.map).map(([n,r])=>`<li><strong>${n}</strong> = ${r}</li>`).join(""):s&&(s.innerHTML='<li style="opacity: 0.6;">Подсказок нет</li>'),a&&this.challenge.steps?a.innerHTML=this.challenge.steps.map(n=>`<li>${n}</li>`).join(""):a&&(a.innerHTML='<li style="opacity: 0.6;">Условий нет</li>')}startTimer(){if(!this.challenge)return;const t=this.el.querySelector("#captcha-timer");if(!t)return;const e=()=>{if(!this.challenge)return;const s=new Date(this.challenge.expires_at),a=new Date,n=s.getTime()-a.getTime();if(n<=0){t.textContent="⏰ Время истекло",this.showError("⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте.");return}const r=Math.floor(n/6e4),l=Math.floor(n%6e4/1e3);t.textContent=`⏳ Осталось: ${r}:${l.toString().padStart(2,"0")}`,setTimeout(e,1e3)};e()}async submitAnswer(t){if(!t.trim()){o.haptic("error"),this.showStatus("error","❌ Введите ответ");return}if(!this.loading){this.loading=!0,this.showStatus("loading","⏳ Проверка ответа...");try{const e=await u("/api/captcha/solve",{method:"POST",body:JSON.stringify({token:this.token,answer:t.trim()})});if(e&&e.ok)o.haptic("success"),this.showStatus("success","✅ Капча пройдена! Ограничение снято."),setTimeout(()=>{var s,a,n;(s=window.Telegram)!=null&&s.WebApp&&((n=(a=window.Telegram.WebApp).close)==null||n.call(a))},2e3);else{const s=(e==null?void 0:e.error)||"wrong_answer";s==="wrong_answer"?(o.haptic("error"),this.showStatus("error","❌ Неверный ответ. Попробуйте еще раз.")):s==="challenge_expired"?this.showError("⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте."):this.showError(`❌ Ошибка: ${s}`)}}catch(e){console.error("Failed to submit captcha:",e),o.haptic("error"),this.showStatus("error","❌ Ошибка отправки ответа. Проверьте соединение и попробуйте еще раз.")}finally{this.loading=!1}}}showStatus(t,e){const s=this.el.querySelector("#captcha-status");s&&(s.className=`captcha-status ${t}`,s.textContent=e,s.style.display=e?"block":"none")}showError(t){this.showStatus("error",t);const e=this.el.querySelector("#captcha-content");e&&(e.style.display="none")}showPenalty(t){const e=this.el.querySelector("#captcha-status");if(!e)return;const s=new Date(t),a=new Date,n=s.getTime()-a.getTime();if(n<=0){this.showError("⏰ Блокировка истекла. Обновите страницу.");return}const r=Math.floor(n/36e5),l=Math.floor(n%36e5/6e4);e.className="captcha-status penalty",e.textContent=`🚫 Вы заблокированы за подозрительную активность. Осталось: ${r}ч ${l}м`,e.style.display="block";const d=this.el.querySelector("#captcha-content");d&&(d.style.display="none")}}class Se{constructor(t){this.particles=[],this.W=0,this.H=0,this.rafId=0,this.COUNT=60,this.canvas=t,this.ctx=t.getContext("2d"),this.resize(),window.addEventListener("resize",this.resize.bind(this));for(let e=0;e<this.COUNT;e++){const s=this.createParticle();s.y=Math.random()*this.H,s.life=Math.floor(Math.random()*s.maxLife*.5),this.particles.push(s)}this.loop()}resize(){this.W=this.canvas.width=this.canvas.offsetWidth,this.H=this.canvas.height=this.canvas.offsetHeight}createParticle(){const t=Math.random()<.28;return{x:Math.random()*this.W,y:this.H+12,r:t?1.5+Math.random()*2:1.2+Math.random()*3,vx:(Math.random()-.5)*.4,vy:-(.2+Math.random()*.55),alpha:0,alphaTarget:.12+Math.random()*.4,life:0,maxLife:180+Math.random()*420,isSediment:t,wobble:Math.random()*Math.PI*2,wobbleSpeed:.02+Math.random()*.03}}drawBubble(t){const e=this.ctx;t.wobble+=t.wobbleSpeed;const s=t.x+Math.sin(t.wobble)*1.8;e.save(),e.globalAlpha=t.alpha,e.strokeStyle="rgba(160,220,255,0.65)",e.lineWidth=.7,e.beginPath(),e.arc(s,t.y,t.r,0,Math.PI*2),e.stroke(),e.fillStyle="rgba(255,255,255,0.35)",e.beginPath(),e.arc(s-t.r*.28,t.y-t.r*.28,t.r*.38,0,Math.PI*2),e.fill(),e.restore()}drawSediment(t){const e=this.ctx;e.save(),e.globalAlpha=t.alpha,e.fillStyle="rgba(180,150,90,0.7)",e.beginPath(),e.ellipse(t.x,t.y,t.r*1.6,t.r*.55,t.wobble,0,Math.PI*2),e.fill(),e.restore()}updateParticle(t){t.x+=t.vx,t.y+=t.vy,t.life+=1;const e=40,s=50;return t.life<e?t.alpha=t.life/e*t.alphaTarget:t.life>t.maxLife-s?t.alpha=(t.maxLife-t.life)/s*t.alphaTarget:t.alpha=t.alphaTarget,t.life<t.maxLife&&t.y>-10}loop(){this.ctx.clearRect(0,0,this.W,this.H);for(let t=0;t<this.particles.length;t++){const e=this.particles[t];this.updateParticle(e)?e.isSediment?this.drawSediment(e):this.drawBubble(e):this.particles[t]=this.createParticle()}this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId),window.removeEventListener("resize",this.resize.bind(this))}}const xe=new URLSearchParams(window.location.search),Ee=xe.get("captcha_mode");if(Ee==="antibot"){const i=new $e,t=i.getElement();document.body.innerHTML="",document.body.appendChild(t),i.init()}else Le();function Le(){document.body.classList.remove("guild-modal-open");const i=Tt();Mt();const t=document.getElementById("particles-canvas");new Se(t);const e=document.getElementById("bg-parallax");new Bt(e);const s=new Ht;s.updateFromTelegram(),document.getElementById("profile-mount").appendChild(s.getElement());async function n(){try{await Promise.all([N(),x(),yt()]),console.log("Initial data loaded")}catch(S){console.error("Failed to load initial data:",S)}}n();const r=document.getElementById("carousel-mount"),l=new Pt(r,2),d=document.getElementById("screens-wrap"),c=new Jt;async function p(){const S=await Yt();l.setFishData(S,Q),c.setItems(l.getItems())}p(),c.onSelect(S=>{l.goTo(S)}),It(()=>{c.open(l.getActiveIndex(),d)});const g=new ee,E=g.getElement(),h=document.getElementById("screen-book");h?h.replaceWith(E):d.appendChild(E);const y=new se,w=y.getElement(),m=document.getElementById("screen-shop");m?m.replaceWith(w):d.appendChild(w);const M=new me,st=M.getElement(),it=document.getElementById("screen-guilds");it?it.replaceWith(st):d.appendChild(st);const D=new be,at=D.getElement(),nt=document.getElementById("screen-friends");nt?nt.replaceWith(at):d.appendChild(at);const R=new ye,$t=R.getElement();d.appendChild($t);const j=new ke,St=j.getElement();d.appendChild(St);let rt=!1,lt=!1,ot=!1,U=!1,G=!1,z=!1;const xt=document.getElementById("tabbar-mount"),I=new Zt(xt,d);I.onChange((S,k)=>{console.log(`Screen transition: ${S} -> ${k}`),S==="guilds"&&M.closeModals();const V=document.getElementById("tab-bar");if(V&&(k==="rating"||k==="results"?V.classList.add("hide-tabbar"):V.classList.remove("hide-tabbar")),k==="book"&&!rt&&(g.init(),rt=!0),k==="shop"&&!lt&&(y.init(),lt=!0),k==="guilds"&&!ot&&(M.init(),ot=!0),k==="friends"&&!U?(D.init(),U=!0):k==="friends"&&U&&D.init(),k==="rating"&&!G?(R.init(),G=!0):k==="rating"&&G&&R.init(),k==="results"&&!z?(j.init(),z=!0):k==="results"&&z&&j.init(),k==="home"){const ct=document.getElementById("screen-home");ct&&ct.querySelectorAll(".slide-up").forEach(Et=>{const W=Et;W.style.animation="none",W.style.opacity="1",W.style.transform="translateY(0)"})}}),_t(()=>I.switchTo("rating"),()=>I.switchTo("results")),window.addEventListener("navigate-home",()=>{console.log("Navigate home event received");const S=document.getElementById("tab-bar");S&&S.classList.remove("hide-tabbar"),I.switchTo("home")}),setTimeout(()=>s.animateProgress(0),2e3),qt(i,1600)}
