(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const n of i)if(n.type==="childList")for(const r of n.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&s(r)}).observe(document,{childList:!0,subtree:!0});function t(i){const n={};return i.integrity&&(n.integrity=i.integrity),i.referrerPolicy&&(n.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?n.credentials="include":i.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function s(i){if(i.ep)return;i.ep=!0;const n=t(i);fetch(i.href,n)}})();class me{constructor(){var e;this.tg=((e=window.Telegram)==null?void 0:e.WebApp)??null,this.tg&&(this.tg.ready(),this.tg.expand(),this.tg.setHeaderColor("#0a1628"),this.tg.setBackgroundColor("#0a1628"))}haptic(e){var t;(t=this.tg)!=null&&t.HapticFeedback&&(e==="selection"?this.tg.HapticFeedback.selectionChanged():e==="success"||e==="error"?this.tg.HapticFeedback.notificationOccurred(e):e==="impact"?this.tg.HapticFeedback.impactOccurred("medium"):["light","medium","heavy"].includes(e)&&this.tg.HapticFeedback.impactOccurred(e))}getUserName(){var e,t,s;return((s=(t=(e=this.tg)==null?void 0:e.initDataUnsafe)==null?void 0:t.user)==null?void 0:s.first_name)??null}getUserTag(){var t,s,i;const e=(i=(s=(t=this.tg)==null?void 0:t.initDataUnsafe)==null?void 0:s.user)==null?void 0:i.username;return e?`@${e}`:null}getUser(){var t,s;const e=(s=(t=this.tg)==null?void 0:t.initDataUnsafe)==null?void 0:s.user;return!e||!e.id?null:{id:e.id,first_name:e.first_name,username:e.username}}showAlert(e){var t;(t=this.tg)!=null&&t.showAlert?this.tg.showAlert(e):alert(e)}}const l=new me,ie={home:`
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
  `};function p(a,e=""){const t=ie[a]||ie.home;return e?t.replace("<svg",`<svg class="${e}"`):t}function fe(){const a=document.getElementById("app");return a.innerHTML=`
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
            ${p("trophy")} &nbsp;ВЫБРАТЬ ТРОФЕЙ
          </button>
        </div>

        <!-- Quick actions -->
        <div class="quick-actions slide-up" style="animation-delay:2.1s">
          <button class="quick-card glass" id="btn-rating" aria-label="Рейтинг">
            <span class="quick-icon" aria-hidden="true">${p("rating")}</span>
            <span class="quick-label">Рейтинг</span>
          </button>
          <button class="quick-card glass" id="btn-results" aria-label="Результаты">
            <span class="quick-icon" aria-hidden="true">${p("results")}</span>
            <span class="quick-label">Результаты</span>
          </button>
          <button class="quick-card glass" id="btn-achievements" aria-label="Достижения">
            <span class="quick-icon" aria-hidden="true">${p("achievements")}</span>
            <span class="quick-label">Достижения</span>
          </button>
        </div>
      </section>

      <!-- SHOP -->
      <section id="screen-shop" class="screen" role="main" aria-label="Лавка">
        <h1 class="page-title">ЛАВКА</h1>
        <div class="glass shop-container">
          <div class="shop-empty">
            <div class="shop-soon-icon">${p("shop")}</div>
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
      ${ge("book","📖","Книга рыбака",`Здесь появится ваш
рыболовный журнал`)}

    </div>

    <!-- Tab bar injected by TabBar -->
    <div id="tabbar-mount"></div>

    <!-- Modal injected by TrophyModal -->
  `,a}function ge(a,e,t,s){return`
    <section id="screen-${a}" class="screen screen--empty" role="main" aria-label="${t}">
      <h1 class="page-title">${t.toUpperCase()}</h1>
      <div class="glass empty-content">
        <div class="empty-icon" aria-hidden="true">${p(a)}</div>
        <p class="empty-text">${s.replace(`
`,"<br>")}</p>
      </div>
    </section>
  `}function ye(){const a=document.createElement("div");return a.id="entry-overlay",a.className="entry-overlay",a.innerHTML=`
    <div class="entry-logo" aria-hidden="true">🌊</div>
    <p class="entry-title">ПОДВОДНЫЙ МИР</p>
    <p class="entry-subtitle">Загрузка…</p>
  `,document.body.appendChild(a),a}function be(a,e=1600){setTimeout(()=>{a.style.transition="opacity 0.6s ease",a.style.opacity="0",setTimeout(()=>a.remove(),700)},e)}function we(a,e){const t=document.getElementById("btn-achievements"),s=document.getElementById("btn-rating"),i=document.getElementById("btn-results");[t,s,i].forEach(n=>{n&&n.addEventListener("click",()=>{l.haptic("light"),n.classList.remove("bounce"),n.offsetWidth,n.classList.add("bounce"),n.addEventListener("animationend",()=>n.classList.remove("bounce"),{once:!0})})}),s&&a&&s.addEventListener("click",a),i&&e&&i.addEventListener("click",e)}function ke(a){const e=document.getElementById("select-trophy-btn");e&&(e.addEventListener("click",a),e.addEventListener("pointerdown",()=>{e.style.transform="scale(0.96)"}),e.addEventListener("pointerup",()=>{e.style.transform=""}),e.addEventListener("pointerleave",()=>{e.style.transform=""}))}const ae=[{id:"home",icon:"🧭",label:"ГЛАВНАЯ"},{id:"shop",icon:"🧺",label:"ЛАВКА"},{id:"friends",icon:"👤",label:"ДРУЗЬЯ"},{id:"guilds",icon:"🔱",label:"АРТЕЛИ"},{id:"book",icon:"📖",label:"КНИГА"}],T={name:"АКВАМАН_01",tag:"@aquaman01",level:15,xp:7200,maxXp:1e4,avatar:"🤿"},S={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"},xe=()=>{var a,e;return((e=(a=window.Telegram)==null?void 0:a.WebApp)==null?void 0:e.initData)||""};async function h(a,e={}){const s={"Content-Type":"application/json","X-Telegram-Init-Data":xe(),...e.headers||{}},i=await fetch(a,{...e,headers:s});if(!i.ok){const n=await i.json().catch(()=>({error:"Unknown error"}));throw new Error(n.error||`HTTP error! status: ${i.status}`)}return i.json()}const z=h;class Ee{constructor(){this.fillEl=null,this.wobbling=!1,this.profile={...T},this.el=this.build(),this.loadProfile()}async loadProfile(){try{const e=await h("/api/profile");e&&(this.profile.name=e.username||this.profile.name,this.profile.level=e.level||this.profile.level,this.profile.xp=e.xp||this.profile.xp,this.profile.maxXp=1e4,this.profile.tag=`@${e.user_id}`||this.profile.tag,this.updateUI())}catch(e){console.error("Failed to load profile:",e)}}updateUI(){const e=this.el.querySelector("#profile-name"),t=this.el.querySelector("#profile-tag"),s=this.el.querySelector(".level-label"),i=this.el.querySelector(".xp-label");e&&(e.textContent=this.profile.name.toUpperCase()),t&&(t.textContent=this.profile.tag),s&&(s.textContent=`Уровень ${this.profile.level}`),i&&(i.textContent=`${this.profile.xp.toLocaleString("ru")} XP`),this.animateProgress(0)}getElement(){return this.el}build(){const e=T,t=Math.round(e.xp/e.maxXp*100),s=document.createElement("div");s.id="profile-panel",s.className="profile-panel glass",s.innerHTML=`
      <div id="porthole-wrap" class="porthole" role="button" tabindex="0" aria-label="Аватар игрока">
        <div class="porthole__ring"></div>
        <div class="porthole__inner">${e.avatar}</div>
      </div>

      <div class="profile-info">
        <div class="profile-name" id="profile-name">${e.name}</div>
        <div class="profile-tag"  id="profile-tag">${e.tag}</div>

        <button class="edit-btn" id="edit-btn" aria-label="Редактировать профиль">
          ✏️ Редактировать
        </button>

        <div class="level-row">
          <span class="level-label">Уровень ${e.level}</span>
          <span class="xp-label">${e.xp.toLocaleString("ru")} / ${e.maxXp.toLocaleString("ru")} XP</span>
        </div>
        <div class="progress-track" role="progressbar" aria-valuenow="${t}" aria-valuemin="0" aria-valuemax="100">
          <div class="progress-fill" id="progress-fill"></div>
        </div>
      </div>
    `;const i=s.querySelector("#porthole-wrap");i.addEventListener("click",()=>this.wobble(i)),i.addEventListener("keydown",r=>{(r.key==="Enter"||r.key===" ")&&this.wobble(i)});const n=s.querySelector("#edit-btn");return n.addEventListener("click",()=>{l.haptic("light"),n.textContent="⏳ Загрузка...",setTimeout(()=>{n.innerHTML="✏️ Редактировать"},1800)}),n.addEventListener("pointerdown",()=>{n.style.transform="scale(0.96)"}),n.addEventListener("pointerup",()=>{n.style.transform=""}),this.fillEl=s.querySelector("#progress-fill"),s}animateProgress(e=200){if(!this.fillEl)return;const t=Math.round(T.xp/T.maxXp*100);this.fillEl.style.width="0%",setTimeout(()=>{this.fillEl.style.width=`${t}%`},e)}wobble(e){this.wobbling||(this.wobbling=!0,l.haptic("light"),e.classList.add("porthole--wobble"),e.addEventListener("animationend",()=>{e.classList.remove("porthole--wobble"),this.wobbling=!1},{once:!0}))}updateFromTelegram(){const e=l.getUserName(),t=l.getUserTag();if(e){const s=this.el.querySelector("#profile-name");s&&(s.textContent=e.toUpperCase())}if(t){const s=this.el.querySelector("#profile-tag");s&&(s.textContent=t)}}}class Se{constructor(e){this.targetX=0,this.targetY=0,this.currentX=0,this.currentY=0,this.rafId=0,this.el=e,this.bindEvents(),this.loop()}bindEvents(){window.addEventListener("mousemove",e=>{this.targetX=(e.clientX/window.innerWidth-.5)*14,this.targetY=(e.clientY/window.innerHeight-.5)*8}),window.addEventListener("deviceorientation",e=>{e.gamma===null||e.beta===null||(this.targetX=Math.max(-12,Math.min(12,e.gamma*.25)),this.targetY=Math.max(-7,Math.min(7,(e.beta-45)*.15)))})}loop(){this.currentX+=(this.targetX-this.currentX)*.06,this.currentY+=(this.targetY-this.currentY)*.06,this.el.style.transform=`scale(1.14) translate(${-this.currentX*.08}%, ${-this.currentY*.06}%)`,this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId)}}class Le{constructor(e){this.intervalId=0,this.container=e,this.start()}spawnOne(){if(document.hidden)return;const e=document.createElement("div");e.className="trophy-bubble";const t=4+Math.random()*9,s=20+Math.random()*60,i=2.8+Math.random()*2.8;e.style.cssText=`
      width:${t}px; height:${t}px;
      left:${s}%; bottom:${8+Math.random()*12}%;
      animation-duration:${i}s;
      animation-delay:${Math.random()*.3}s;
    `,this.container.appendChild(e),setTimeout(()=>e.remove(),(i+.5)*1e3)}start(){this.intervalId=window.setInterval(()=>this.spawnOne(),380)}stop(){clearInterval(this.intervalId),this.container.querySelectorAll(".trophy-bubble").forEach(e=>e.remove())}restart(){this.stop(),this.start()}}const A=class A{static transitionTo(e,t){this.pendingTimeout&&(clearTimeout(this.pendingTimeout),this.pendingTimeout=0);const s=++this.transitionToken;e.style.transition="opacity 0.35s ease, transform 0.35s ease",e.style.opacity="0",e.style.transform="scale(0.93)",e.style.pointerEvents="none",e.classList.remove("is-active"),t.style.display="flex",t.style.transition="none",t.style.opacity="0",t.style.transform="scale(1.06)",t.style.pointerEvents="all",t.classList.add("is-active"),this.pendingTimeout=window.setTimeout(()=>{s===this.transitionToken&&(e.style.display="none",e.style.opacity="",e.style.transform="",e.style.transition="",requestAnimationFrame(()=>{s===this.transitionToken&&(t.style.transition="opacity 0.38s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.38s cubic-bezier(0.25,0.46,0.45,0.94)",t.style.opacity="1",t.style.transform="scale(1)")}))},300)}};A.transitionToken=0,A.pendingTimeout=0;let j=A;const Ce={id:"no-trophy",emoji:"🐟",name:"Нет трофеев",latinName:"",rarity:"common",rarityLabel:"Обычная",rarityStars:"",weight:"0 кг",depth:"0 см"};class $e{constructor(e,t=2){this.cards=[],this.bubbleSpawner=null,this.fishData=[],this.startX=0,this.isDragging=!1,this.onChangeCallback=null,this.container=e,this.activeIndex=t,this.build(),this.bindSwipe(),this.update()}build(){this.container.innerHTML="",this.cards=[];const e=document.createElement("div");e.className="carousel__bubbles",this.container.appendChild(e),this.bubbleSpawner=new Le(e);const t=document.createElement("div");if(t.className="carousel__track",this.container.appendChild(t),this.fishData.length===0){t.innerHTML=`
        <div class="carousel__card is-active" style="opacity:1; transform:translateX(0) scale(1);">
          <div class="carousel__card-inner" style="--accent:${S.common}">
            <div class="carousel__fish-emoji">${p("trophy")}</div>
            <div class="carousel__rarity" style="color:${S.common}">ТРОФЕЕВ ПОКА НЕТ</div>
            <div class="carousel__fish-name">Поймай рыбу и создай трофей</div>
            <div class="carousel__fish-latin">Карточки появятся автоматически</div>
          </div>
        </div>
      `;return}this.fishData.forEach((s,i)=>{const n=document.createElement("div");n.className="carousel__card",n.dataset.index=String(i);const r=S[s.rarity];n.innerHTML=`
        <div class="carousel__card-inner" style="--accent:${r}">
          <div class="carousel__fish-emoji">${s.imageUrl?`<img src="${s.imageUrl}" alt="${s.name}" class="carousel__fish-image" loading="lazy">`:p(s.id)}</div>
          <div class="carousel__rarity" style="color:${r}">${s.rarityStars} ${s.rarityLabel}</div>
          <div class="carousel__fish-name">${s.name}</div>
          <div class="carousel__fish-latin">${s.latinName}</div>
          <div class="carousel__fish-stats">
            <span>⚖️ ${s.weight}</span>
            <span>📏 ${s.depth}</span>
          </div>
        </div>
      `,t.appendChild(n),this.cards.push(n)})}update(){var t;if(this.cards.length===0)return;this.cards.forEach((s,i)=>{const n=i-this.activeIndex,r=Math.abs(n);s.classList.remove("is-active","is-side","is-far");let o,c,d,v;switch(r){case 0:o=0,c=1,d=1,v=10,s.classList.add("is-active");break;case 1:o=n*148,c=.78,d=.6,v=5,s.classList.add("is-side");break;case 2:o=n*185,c=.62,d=.28,v=2,s.classList.add("is-far");break;default:o=n*200,c=.5,d=0,v=0}s.style.transform=`translateX(${o}px) scale(${c})`,s.style.opacity=String(d),s.style.zIndex=String(v)});const e=this.fishData[this.activeIndex];e&&((t=this.onChangeCallback)==null||t.call(this,e))}next(){this.fishData.length!==0&&this.activeIndex<this.fishData.length-1&&(this.activeIndex++,this.update(),l.haptic("light"))}prev(){this.fishData.length!==0&&this.activeIndex>0&&(this.activeIndex--,this.update(),l.haptic("light"))}goTo(e){this.fishData.length!==0&&(this.activeIndex=Math.max(0,Math.min(e,this.fishData.length-1)),this.update())}getActiveIndex(){return this.activeIndex}getActiveFish(){return this.fishData[this.activeIndex]||Ce}getItems(){return this.fishData}setFishData(e,t){if(this.fishData=[...e],t){const s=this.fishData.findIndex(i=>i.trophyId===t||i.id===t);this.activeIndex=s>=0?s:0}else this.activeIndex=this.fishData.length?Math.max(0,Math.min(this.activeIndex,this.fishData.length-1)):0;this.build(),this.update()}onChange(e){this.onChangeCallback=e}bindSwipe(){const e=this.container;e.addEventListener("touchstart",t=>{this.startX=t.touches[0].clientX,this.isDragging=!0},{passive:!0}),e.addEventListener("touchend",t=>{if(!this.isDragging)return;const s=t.changedTouches[0].clientX-this.startX;this.handleSwipeEnd(s),this.isDragging=!1},{passive:!0}),e.addEventListener("mousedown",t=>{this.startX=t.clientX,this.isDragging=!0,t.preventDefault()}),window.addEventListener("mouseup",t=>{if(!this.isDragging)return;const s=t.clientX-this.startX;this.handleSwipeEnd(s),this.isDragging=!1})}handleSwipeEnd(e){e<-42?this.next():e>42&&this.prev()}}const Me={обычная:"common",редкая:"rare",легендарная:"legendary",аквариумная:"aquarium",мифическая:"mythical",аномалия:"anomaly"},qe={common:"Обычная",rare:"Редкая",legendary:"Легендарная",aquarium:"Аквариумная",mythical:"Мифическая",anomaly:"Аномалия"},Te={common:"★★",rare:"★★★",legendary:"★★★★★",aquarium:"★★★★",mythical:"★★★★★",anomaly:"★★★★★★"},Ie={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"};function k(a){const e=String(a||"").trim().toLowerCase();return Me[e]||"common"}function U(a){return qe[k(a)]}function _e(a){return Te[k(a)]}function Ae(a){return Ie[k(a)]}let I=[],V="";function He(a){return`${(Number.isFinite(a)?Math.max(0,a):0).toLocaleString("ru-RU",{maximumFractionDigits:2})} кг`}function Be(a){return`${(Number.isFinite(a)?Math.max(0,a):0).toLocaleString("ru-RU",{maximumFractionDigits:1})} см`}function Fe(a){const e=a.rarity||"Обычная";return{id:a.id,emoji:"🐟",name:a.fish_name||a.name||"Неизвестная рыба",latinName:"",rarity:k(e),rarityLabel:U(e),rarityStars:_e(e),weight:He(Number(a.weight||0)),depth:Be(Number(a.length||0)),imageUrl:a.image_url||void 0,trophyId:a.id}}async function Pe(){var a;try{const e=await h("/api/trophies"),t=Array.isArray(e==null?void 0:e.items)?e.items:[];return V=((a=t.find(s=>!!s.is_active))==null?void 0:a.id)||"",I=t.filter(s=>s.id!=="none").map(Fe),I}catch(e){return console.error("Failed to load trophies:",e),I=[],V="",I}}async function Ne(a){if(!a)return!1;try{const e=await h("/api/trophy/select",{method:"POST",body:JSON.stringify({trophy_id:a})});return!!(e!=null&&e.ok)}catch(e){return console.error("Failed to select trophy:",e),!1}}class Oe{constructor(){this.isOpen=!1,this.bgBlurTarget=null,this.onSelectCallback=null,this.currentActiveIndex=0,this.items=[],this.sheetStartY=0,this.sheetDragging=!1,this.overlay=this.buildOverlay(),this.sheet=this.overlay.querySelector("#modal-sheet"),this.listEl=this.overlay.querySelector("#modal-fish-list"),document.body.appendChild(this.overlay),this.bindClose()}buildOverlay(){const e=document.createElement("div");return e.id="modal-overlay",e.className="modal-overlay",e.innerHTML=`
      <div id="modal-sheet" class="modal-sheet">
        <div class="modal-handle"></div>
        <p class="modal-title">🏆 Выбор трофея</p>
        <div id="modal-fish-list" class="modal-fish-list"></div>
      </div>
    `,e}buildList(){if(this.items.length===0){this.listEl.innerHTML='<div class="modal-empty">У вас пока нет трофеев</div>';return}this.listEl.innerHTML=this.items.map((e,t)=>{const s=S[e.rarity],i=t===this.currentActiveIndex;return`
        <div
          class="modal-fish-item ${i?"is-selected":""}"
          data-index="${t}"
          style="--accent:${s}"
          role="button"
          tabindex="0"
          aria-label="${e.name}"
        >
          <span class="modal-fish-emoji">${e.imageUrl?`<img src="${e.imageUrl}" alt="${e.name}" class="modal-fish-image" loading="lazy">`:p(e.id)}</span>
          <div class="modal-fish-info">
            <div class="modal-fish-name">${e.name}</div>
            <div class="modal-fish-rarity" style="color:${s}">${e.rarityStars} ${e.rarityLabel}</div>
            <div class="modal-fish-stats">⚖️ ${e.weight} · 📏 ${e.depth}</div>
          </div>
          ${i?'<span class="modal-check">✓</span>':""}
        </div>
      `}).join(""),this.listEl.querySelectorAll(".modal-fish-item").forEach(e=>{e.addEventListener("click",()=>{const t=parseInt(e.dataset.index??"0",10);this.select(t)})})}open(e,t){this.isOpen||(this.currentActiveIndex=e,this.bgBlurTarget=t??null,this.buildList(),this.overlay.style.display="flex",requestAnimationFrame(()=>{this.overlay.classList.add("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter="blur(4px)")}),this.isOpen=!0,l.haptic("medium"))}close(){this.isOpen&&(this.overlay.classList.remove("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter=""),setTimeout(()=>{this.overlay.style.display="none"},420),this.isOpen=!1)}onSelect(e){this.onSelectCallback=e}setItems(e){this.items=[...e],this.currentActiveIndex=Math.max(0,Math.min(this.currentActiveIndex,this.items.length-1))}async select(e){var i;this.currentActiveIndex=e;const t=this.items[e],s=t!=null&&t.trophyId?await Ne(t.trophyId):!0;if(l.haptic(s?"medium":"error"),!s){alert("Не удалось выбрать трофей. Попробуйте еще раз.");return}(i=this.onSelectCallback)==null||i.call(this,e),this.close()}bindClose(){this.overlay.addEventListener("click",t=>{t.target===this.overlay&&this.close()});const e=this.sheet;e.addEventListener("touchstart",t=>{this.sheetStartY=t.touches[0].clientY,this.sheetDragging=!0},{passive:!0}),e.addEventListener("touchmove",t=>{if(!this.sheetDragging)return;const s=t.touches[0].clientY-this.sheetStartY;s>0&&(e.style.transform=`translateY(${s*.55}px)`,e.style.transition="none")},{passive:!0}),e.addEventListener("touchend",t=>{if(!this.sheetDragging)return;const s=t.changedTouches[0].clientY-this.sheetStartY;e.style.transform="",e.style.transition="",s>80&&this.close(),this.sheetDragging=!1},{passive:!0})}get fish(){return this.items}}class De{constructor(e,t){this.activeId="home",this.buttons=new Map,this.screens=new Map,this.onChangeCallbacks=[],this.el=this.build(),e.appendChild(this.el),ae.forEach(s=>{const i=t.querySelector(`#screen-${s.id}`);i&&this.screens.set(s.id,i)}),this.screens.forEach((s,i)=>{i==="home"?(s.style.display="flex",s.style.opacity="1",s.style.transform="scale(1)",s.style.pointerEvents="all"):(s.style.display="none",s.style.opacity="0",s.style.transform="",s.style.pointerEvents="all")})}build(){const e=document.createElement("nav");return e.id="tab-bar",e.className="tab-bar",e.setAttribute("role","tablist"),ae.forEach(t=>{const s=document.createElement("button");s.id=`tab-${t.id}`,s.className=`tab-btn ${t.id==="home"?"is-active":""}`,s.setAttribute("role","tab"),s.setAttribute("aria-selected",t.id==="home"?"true":"false"),s.dataset.tab=t.id,s.innerHTML=`
        <span class="tab-icon" aria-hidden="true">${p(t.id)}</span>
        <span class="tab-label">${t.label}</span>
      `,s.addEventListener("click",()=>this.switchTo(t.id)),s.addEventListener("pointerdown",()=>{s.style.transform="scale(0.92)"}),s.addEventListener("pointerup",()=>{s.style.transform=""}),s.addEventListener("pointerleave",()=>{s.style.transform=""}),e.appendChild(s),this.buttons.set(t.id,s)}),e}switchTo(e){if(e===this.activeId)return;l.haptic("selection");const t=this.activeId;let s=this.screens.get(t);s||(s=document.getElementById(`screen-${t}`));let i=this.screens.get(e);if(i||(i=document.getElementById(`screen-${e}`)),!s||!i){console.warn(`Screen not found: from=${t} (${!!s}), to=${e} (${!!i})`);return}console.log(`Switching from ${t} to ${e}`),j.transitionTo(s,i),this.buttons.forEach((n,r)=>{const o=r===e;n.classList.toggle("is-active",o),n.setAttribute("aria-selected",String(o))}),this.activeId=e,this.onChangeCallbacks.forEach(n=>n(t,e))}onChange(e){this.onChangeCallbacks.push(e)}getActive(){return this.activeId}}let Y=[],oe=0;async function ce(){try{const a=await h("/api/book?limit=500");a&&a.ok&&(oe=Number(a.total_all||0),Y=a.items.map(e=>({id:e.image_file||"fishdef",emoji:"🐟",name:e.name,latinName:e.name,rarity:Re(e.rarity),glowColor:ze(e.rarity),depth:`${e.min_weight}-${e.max_weight} кг`,habitat:e.locations,length:`${e.min_length}-${e.max_length} см`,description:e.lore||`Рыба вида ${e.name}.`,funFact:e.baits?`Лучше ловится на: ${e.baits}.`:"Информации пока нет.",chapter:"Общий атлас",isCaught:e.is_caught,imageUrl:e.image_url||void 0})))}catch(a){console.error("Failed to load encyclopedia:",a)}}function Re(a){return k(a)}function ze(a){return Ae(a)}const je={common:"★★ Обычная",rare:"★★★ Редкая",legendary:"★★★★★ Легендарная",aquarium:"★★★★ Аквариумная",mythical:"★★★★★ Мифическая",anomaly:"★★★★★★ Аномалия"};class Ue{constructor(){this.entries=[],this.filtered=[],this.index=0,this.loading=!1,this.pageFlip=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-book",e.className="screen book-screen",e.setAttribute("role","main"),e.innerHTML=`
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
    `,e}async init(){this.bookContainer=this.el.querySelector(".book-wrap"),this.stBook=this.el.querySelector("#st-book"),this.searchInput=this.el.querySelector("#book-search-input"),this.prevBtn=this.el.querySelector("#book-prev-btn"),this.nextBtn=this.el.querySelector("#book-next-btn"),this.counterCur=this.el.querySelector("#counter-cur"),this.counterTot=this.el.querySelector("#counter-tot"),this.loading=!0,await ce(),this.entries=[...Y],this.filtered=[...Y],this.loading=!1,this.renderPages(),this.bindEvents()}buildPage(e){const t=e.isCaught??!1;return`
      <div class="my-page ${t?"":"not-caught"}">
        <div class="ph-content parchment">
          <div class="ph-chapter">${e.chapter}</div>
          <div class="ph-chapter-divider"><span class="ph-chapter-rule">✦ · ✦</span></div>

          <div class="ph-fish-block">
            <div class="ph-fish-emoji" style="--glow: ${t?e.glowColor:"#555"}; filter: ${t?"none":"grayscale(100%) contrast(50%) brightness(70%)"}">
              ${e.imageUrl?`<img src="${e.imageUrl}" alt="${e.name}" class="ph-fish-image" loading="lazy">`:p(e.id)}
            </div>
          </div>
          
          <div class="ph-fish-name">${e.name.toUpperCase()}</div>
          <div class="ph-fish-latin">${e.latinName}</div>
          
          <div class="ph-rarity-wrap">
            <div class="ph-rarity" style="color:${t?e.glowColor:"#777"}; border-color:${t?e.glowColor:"#777"}55">
              ${t?je[e.rarity]:'<span style="color: #ff4d4d; font-weight: bold;">НЕ СЛОВЛЕНА</span>'}
            </div>
          </div>

          <div class="ph-stats">
            <div class="ph-stat"><span>🌊 Глуб</span><strong>${e.depth}</strong></div>
            <div class="ph-stat"><span>📏 Длина</span><strong>${e.length}</strong></div>
            <div class="ph-stat"><span>📍 Среда</span><strong>${e.habitat}</strong></div>
          </div>

          <p class="ph-desc">${e.description}</p>
          
          ${t?`
          <div class="ph-funfact">
            <div class="ph-ff-head">💡 Факт</div>
            <div class="ph-ff-body">${e.funFact}</div>
          </div>
          `:""}
        </div>
      </div>
    `}renderPages(){this.pageFlip&&(this.pageFlip.destroy(),this.pageFlip=null);const e=this.el.querySelector("#st-book");e&&e.remove(),this.stBook=document.createElement("div"),this.stBook.id="st-book",this.stBook.className="st-book",this.bookContainer.appendChild(this.stBook),this.filtered.length!==0&&(this.stBook.innerHTML=this.filtered.map(t=>this.buildPage(t)).join(""),window.St&&window.St.PageFlip&&(this.pageFlip=new window.St.PageFlip(this.stBook,{width:320,height:480,size:"stretch",minWidth:280,maxWidth:600,minHeight:400,maxHeight:900,usePortrait:!0,showCover:!1,useMouseEvents:!1,maxShadowOpacity:.7,mobileScrollSupport:!1,flippingTime:600}),this.pageFlip.loadFromHTML(this.stBook.querySelectorAll(".my-page")),this.pageFlip.on("flip",t=>{this.index=t.data,this.syncUI()}),this.pageFlip.on("changeState",t=>{t.data==="flipping"&&l.haptic("light")})),this.index=0,this.syncUI())}syncUI(){this.counterCur.textContent=String(this.index+1),this.counterTot.textContent=String(Math.max(this.filtered.length,oe||0)),this.prevBtn.disabled=this.index===0,this.nextBtn.disabled=this.index===this.filtered.length-1}applySearch(e){const t=e.trim().toLowerCase();this.filtered=t?this.entries.filter(s=>s.name.toLowerCase().includes(t)||s.latinName.toLowerCase().includes(t)||s.description.toLowerCase().includes(t)):[...this.entries],this.filtered.length||(this.filtered=[...this.entries]),this.renderPages()}bindEvents(){this.prevBtn.addEventListener("click",()=>{this.pageFlip&&this.index>0&&this.pageFlip.flipPrev()}),this.nextBtn.addEventListener("click",()=>{this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext()});let e=0,t=0;this.bookContainer.addEventListener("pointerdown",i=>{e=i.clientX,t=i.clientY},{passive:!0}),this.bookContainer.addEventListener("pointerup",i=>{if(this.pageFlip&&this.pageFlip.getState()!=="read")return;const n=i.clientX,r=i.clientY,o=e-n,c=Math.abs(t-r);Math.abs(o)>40&&c<60&&(o>0?this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext():this.pageFlip&&this.index>0&&this.pageFlip.flipPrev())},{passive:!0}),this.searchInput.addEventListener("keydown",i=>{i.key==="Enter"&&(i.preventDefault(),this.applySearch(this.searchInput.value))});const s=this.el.querySelector("#book-search-btn");s&&s.addEventListener("click",()=>{this.applySearch(this.searchInput.value)})}}class Ve{constructor(){this.items=[],this.loading=!1,this.mode="view",this.selectedIds=new Set,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-shop",e.className="screen shop-screen",e.setAttribute("role","main"),e.innerHTML=`
      <div class="shop-header">
        <h1 class="page-title">ЛАВКА</h1>
        <button id="shop-sell-btn" class="glass-btn primary-btn" style="display:none;">${p("shop")} ПРОДАТЬ</button>
      </div>
      <div class="shop-container">
        <div id="shop-content" class="shop-content">
          <div class="loader-wrap"><div class="loader"></div></div>
        </div>
      </div>
      <div id="shop-select-actions" class="shop-select-actions" style="display:none;">
        <div class="select-info">Выбрано: <span id="select-count">0</span></div>
        <div class="select-buttons">
          <button id="cancel-select-btn" class="glass-btn">ОТМЕНА</button>
          <button id="confirm-sell-btn" class="glass-btn primary-btn">ПРОДАТЬ</button>
        </div>
      </div>
    `,e}async init(){await this.loadInventory(),this.bindEvents()}bindEvents(){const e=this.el.querySelector("#shop-sell-btn");e&&e.addEventListener("click",()=>{l.haptic("light"),this.showSellModal()});const t=this.el.querySelector("#cancel-select-btn");t&&t.addEventListener("click",()=>{l.haptic("light"),this.mode="view",this.selectedIds.clear(),this.renderInventory()});const s=this.el.querySelector("#confirm-sell-btn");s&&s.addEventListener("click",()=>{this.selectedIds.size!==0&&(l.haptic("medium"),this.sellBulk({ids:Array.from(this.selectedIds)}))})}showSellModal(){const e=`
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
    `,t=document.createElement("div");t.className="modal-overlay is-open",t.style.display="flex",t.innerHTML=`
      <div class="modal-sheet" style="transform:none; bottom:0;">
        <div class="modal-handle"></div>
        <p class="modal-title">ПРОДАЖА РЫБЫ</p>
        <div style="padding:10px;">${e}</div>
      </div>
    `,document.body.appendChild(t),t.addEventListener("click",s=>{s.target===t&&document.body.removeChild(t)}),t.querySelectorAll(".sell-opt-btn").forEach(s=>{s.addEventListener("click",()=>{const i=s.dataset.cat;l.haptic("light"),document.body.removeChild(t),i?this.sellBulk({category:i}):s.classList.contains("select-mode-btn")&&(this.mode="select",this.selectedIds.clear(),this.renderInventory())})})}async showFishDetailModal(e){var t,s,i;try{const n=await h("/api/inventory"),r=((n==null?void 0:n.items)||[]).filter(u=>e.ids.includes(u.id));if(r.length===0)return;const o=k(e.rarity),c=S[o]||"#ccc",d=document.createElement("div");d.className="modal-overlay is-open",d.style.display="flex";const v=`
        <div class="modal-sheet" style="transform:none; bottom:0; max-height: 80vh;">
          <div class="modal-handle"></div>
          <p class="modal-title">${e.name}</p>
          <p style="text-align:center; color:${c}; font-size:12px; margin-top:-10px;">${U(e.rarity)}</p>
          
          <div class="fish-action-buttons">
            <button class="glass-btn primary-btn" id="make-trophy-btn">🏆 Сделать трофеем</button>
            <button class="glass-btn" id="select-to-sell-btn">💰 Выбрать для продажи</button>
          </div>
          
          <div id="fish-detail-content" style="display:none;">
            <p style="text-align:center; font-size:14px; margin:10px 0;">Выберите рыбу:</p>
            <div class="fish-detail-grid">
              ${r.map(u=>`
                <div class="fish-detail-card" data-id="${u.id}">
                  <img src="${u.image_url}" alt="${u.name}">
                  <div class="fish-detail-weight">⚖️ ${u.weight.toFixed(2)} кг</div>
                  <div class="fish-detail-weight">📏 ${u.length.toFixed(1)} см</div>
                </div>
              `).join("")}
            </div>
            <div style="padding:10px; display:flex; gap:10px; justify-content:center;">
              <button class="glass-btn" id="cancel-detail-btn">ОТМЕНА</button>
              <button class="glass-btn primary-btn" id="confirm-detail-btn" style="display:none;">ПОДТВЕРДИТЬ</button>
            </div>
          </div>
        </div>
      `;d.innerHTML=v,document.body.appendChild(d);let m=new Set,b=null;const L=d.querySelector("#fish-detail-content"),C=d.querySelector(".fish-action-buttons"),g=d.querySelector("#confirm-detail-btn");(t=d.querySelector("#make-trophy-btn"))==null||t.addEventListener("click",()=>{l.haptic("light"),b="trophy",C.style.display="none",L.style.display="block",g.style.display="block",g.textContent="СДЕЛАТЬ ТРОФЕЕМ"}),(s=d.querySelector("#select-to-sell-btn"))==null||s.addEventListener("click",()=>{l.haptic("light"),b="sell",C.style.display="none",L.style.display="block",g.style.display="block",g.textContent="ПРОДАТЬ"}),d.querySelectorAll(".fish-detail-card").forEach(u=>{u.addEventListener("click",()=>{l.haptic("light");const E=parseInt(u.dataset.id||"0");m.has(E)?(m.delete(E),u.classList.remove("selected")):(m.add(E),u.classList.add("selected"))})}),(i=d.querySelector("#cancel-detail-btn"))==null||i.addEventListener("click",()=>{l.haptic("light"),document.body.removeChild(d)}),g==null||g.addEventListener("click",async()=>{if(m.size===0){alert("Выберите хотя бы одну рыбу");return}l.haptic("medium"),document.body.removeChild(d),b==="trophy"?await this.makeTrophies(Array.from(m)):b==="sell"&&await this.sellBulk({ids:Array.from(m)})}),d.addEventListener("click",u=>{u.target===d&&document.body.removeChild(d)})}catch(n){console.error("Failed to load fish details:",n),alert("Ошибка загрузки деталей рыбы")}}async makeTrophies(e){try{let t=0,s=!1,i=0,n=0;for(const r of e){const o=await h("/api/make-trophy",{method:"POST",body:JSON.stringify({id:r})});if(o!=null&&o.ok)t++;else if((o==null?void 0:o.error)==="insufficient_coins"){s=!0,i=o.required||1e4,n=o.current||0;break}}s?alert(`Недостаточно монет!
Требуется: ${i} 🪙
У вас: ${n} 🪙`):t>0&&(l.haptic("success"),alert(`Создано трофеев: ${t}
Списано: ${t*1e4} 🪙`),await this.loadInventory(),window.dispatchEvent(new CustomEvent("refresh-profile")))}catch{alert("Ошибка при создании трофеев")}}async sellBulk(e){try{const t=await h("/api/sell-bulk",{method:"POST",body:JSON.stringify(e)});t&&t.earned_coins!==void 0&&(l.haptic("success"),alert(`Успешно продано!
Получено: ${t.earned_coins} 🪙
Опыт: ${t.earned_xp} ✨`),this.mode="view",this.selectedIds.clear(),await this.loadInventory())}catch{alert("Ошибка при продаже")}}async loadInventory(){this.loading=!0;try{const e=await h("/api/inventory/grouped");this.items=(e==null?void 0:e.items)||[],this.renderInventory()}catch(e){console.error("Failed to load inventory:",e),this.renderError()}finally{this.loading=!1}}renderInventory(){const e=this.el.querySelector("#shop-content"),t=this.el.querySelector("#shop-sell-btn"),s=this.el.querySelector("#shop-select-actions");if(this.mode==="select"?(t.style.display="none",s.style.display="flex",this.updateSelectCount()):(t.style.display=this.items.length>0?"block":"none",s.style.display="none"),this.items.length===0){e.innerHTML=`
        <div class="shop-empty">
          <div class="shop-soon-icon">${p("shop")}</div>
          <h3>Садок пуст</h3>
          <p>Поймайте рыбу, чтобы она появилась здесь.</p>
        </div>
      `;return}e.innerHTML=`
      <div class="inventory-grid">
        ${this.items.map((i,n)=>{const r=k(i.rarity),o=S[r]||"#ccc",c=i.ids.every(m=>this.selectedIds.has(m)),d=i.ids.some(m=>this.selectedIds.has(m))&&!c;let v="";return this.mode==="select"&&(c?v="is-selected":d&&(v="is-partial")),`
            <div class="inv-card glass ${v}" style="--card-color: ${o}" data-idx="${n}">
              ${i.count>1?`<div class="inv-badge">${i.count}x</div>`:""}
              <div class="inv-img-wrap">
                <img src="${i.image_url}" alt="${i.name}" loading="lazy">
              </div>
              <div class="inv-details">
                <div class="inv-name">${i.name}</div>
                <div class="inv-rarity" style="color:${o}">${U(i.rarity)}</div>
                <div class="inv-weight">⚖️ ${i.total_weight.toFixed(2)} кг</div>
              </div>
              <div class="inv-price">
                <span>${i.price}</span> 🪙
              </div>
              ${this.mode==="select"?`<div class="select-indicator">${c?"✅":""}</div>`:""}
            </div>
          `}).join("")}
      </div>
    `,e.querySelectorAll(".inv-card").forEach(i=>{i.addEventListener("click",()=>{l.haptic("light");const n=parseInt(i.dataset.idx||"0"),r=this.items[n];this.mode==="select"?(r.ids.every(c=>this.selectedIds.has(c))?r.ids.forEach(c=>this.selectedIds.delete(c)):r.ids.forEach(c=>this.selectedIds.add(c)),this.renderInventory()):this.showFishDetailModal(r)})})}updateSelectCount(){const e=this.el.querySelector("#select-count");e&&(e.textContent=this.selectedIds.size.toString())}renderError(){const e=this.el.querySelector("#shop-content");e.innerHTML=`
      <div class="shop-empty">
        <div class="shop-soon-icon">❌</div>
        <h3>Ошибка загрузки</h3>
        <p>Не удалось загрузить инвентарь. Попробуйте позже.</p>
      </div>
    `}}const ne=["guild_beer","guild_rich","guild_cthulhu","guild_king"],re=["#00b4d8","#f4a82e","#9b5de5","#ff6b6b","#a5a5a5","#4d908e"];let w=[],x=null,G=!1;async function M(){try{const a=await h("/api/guilds");if(a&&a.ok){const e=a.my_clan;if(e&&e.id){const t=Array.isArray(e.requests)?e.requests:[],s={id:String(e.id),name:e.name,avatar:e.avatar_emoji||"🔱",borderColor:e.color_hex||"#00b4d8",type:e.access_type||"open",level:e.level||1,members:[],requests:t.map(i=>({requestId:String(i.request_id??i.id??""),userId:String(i.user_id??i.requester_user_id??""),name:String(i.username||"user"),level:Number(i.level||0),userAvatar:String(i.user_avatar||"👤")})),upgradeProgress:[],capacity:20,minLevel:e.min_level||0};w=[s],x=s.id,G=e.role==="leader"}else w=(a.items||[]).map(t=>({id:String(t.id),name:t.name,avatar:t.avatar_emoji||"🔱",borderColor:t.color_hex||"#00b4d8",type:t.access_type||"open",level:t.level||1,members:[],requests:[],upgradeProgress:[],capacity:20,minLevel:t.min_level||0})),x=null}}catch(a){console.error("Failed to load clans:",a)}}async function Ye(a){try{const e=await h("/api/guilds/create",{method:"POST",body:JSON.stringify({name:a.name,avatar:a.avatar,color:a.borderColor,type:a.type,min_level:a.minLevel})});if(e&&e.ok)return await M(),w.find(t=>t.id===String(e.clan_id))||null;e&&!e.ok&&(e.reason==="not_enough_coins"?alert(`Недостаточно монет для создания артели! Нужно ${e.cost.toLocaleString()} 🪙`):alert(`Ошибка создания: ${e.reason||"неизвестная ошибка"}`))}catch(e){console.error("Failed to create guild:",e)}return null}async function Xe(a){const e=w.find(t=>t.id===a);if(!e)return!1;try{const t=e.type==="open"?"/api/guilds/join":"/api/guilds/apply",s=await h(t,{method:"POST",body:JSON.stringify({guild_id:a})});if(s&&s.ok)return e.type==="open"&&(x=e.id),!0;s&&!s.ok&&(s.reason==="level_too_low"?alert(`Ваш уровень слишком низок! Требуется уровень ${s.required}`):s.reason==="not_enough_coins"?alert(`Недостаточно монет! Требуется ${s.cost} 🪙`):alert(`Ошибка: ${s.reason||s.error||"неизвестная ошибка"}`))}catch(t){console.error("Failed to join guild:",t)}return!1}async function le(a,e){try{const t=await h("/api/guilds/request/respond",{method:"POST",body:JSON.stringify({request_id:a,action:e})});if(t&&t.ok)return await M(),!0;t&&!t.ok&&alert(`Ошибка обработки заявки: ${t.error||"неизвестная ошибка"}`)}catch(t){console.error("Failed to respond to clan request:",t)}return!1}async function Ge(){if(x)try{const a=await h("/api/guilds/leave",{method:"POST"});a&&a.ok&&(x=null,G=!1,await M())}catch(a){console.error("Failed to leave guild:",a)}}class We{constructor(){this.view="list",this.loading=!1,this.newGuildName="",this.selectedAvatar=ne[0],this.selectedColor=re[0],this.selectedType="open",this.selectedMinLevel=0,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-guilds",e.className="screen guilds-screen",e.setAttribute("role","main"),e}async init(){this.loading=!0,this.render(),await M(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}x?this.renderManage():this.view==="create"?this.renderCreate():this.renderList()}renderList(){var e;this.el.innerHTML=`
      <h1 class="page-title">АРТЕЛИ</h1>
      <div class="guilds-header">
        <button class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>
      </div>
      <div class="guild-list">
        ${w.map(t=>`
          <div class="guild-card glass" data-id="${t.id}">
            <div class="guild-avatar" style="--border-color: ${t.borderColor}">${p(t.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${t.name}</div>
              <div class="guild-meta">
                <span>⭐ Ур. ${t.level}</span>
                <span>👤 ${t.members.length}/${t.capacity}</span>
                <span>${t.type==="open"?"🔓 Открыто":"🔒 По приглашению"}</span>
                ${t.type==="open"&&t.minLevel>0?`<span style="color: var(--gold)">⬆️ Ур. ${t.minLevel}+</span>`:""}
              </div>
            </div>
            <button class="adv-play-btn" style="padding: 8px 12px; font-size: 9px;">${t.type==="open"?"ВСТУПИТЬ":"ЗАЯВКА"}</button>
          </div>
        `).join("")}
      </div>
    `,(e=this.el.querySelector("#guild-create-trigger"))==null||e.addEventListener("click",()=>{this.view="create",this.render(),l.haptic("medium")}),this.el.querySelectorAll(".guild-card").forEach(t=>{var s;(s=t.querySelector("button"))==null||s.addEventListener("click",async i=>{i.stopPropagation();const n=t.getAttribute("data-id");if(await Xe(n)){l.haptic("heavy");const o=w.find(c=>c.id===n);(o==null?void 0:o.type)==="invite"?alert("Заявка отправлена!"):await this.init()}else l.haptic("error"),alert("Не удалось вступить в артель.")})})}renderCreate(){var s,i;this.el.innerHTML=`
      <h1 class="page-title">НОВАЯ АРТЕЛЬ</h1>
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14 симв.)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" placeholder="Введите название..." value="${this.newGuildName}">
        </div>

        <div class="form-group">
          <label class="form-label">Выберите герб</label>
          <div class="avatar-grid">
            ${ne.map(n=>`
              <div class="avatar-opt ${this.selectedAvatar===n?"is-selected":""}" data-val="${n}">${p(n)}</div>
            `).join("")}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Цвет каемки</label>
          <div class="color-row">
            ${re.map(n=>`
              <div class="color-opt ${this.selectedColor===n?"is-selected":""}" data-val="${n}" style="background:${n}"></div>
            `).join("")}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Тип входа</label>
          <div class="type-row">
            <div class="type-opt ${this.selectedType==="open"?"is-selected":""}" data-val="open">СВОБОДНЫЙ</div>
            <div class="type-opt ${this.selectedType==="invite"?"is-selected":""}" data-val="invite">ПО ПРИГЛАШЕНИЮ</div>
          </div>
        </div>

        ${this.selectedType==="open"?`
        <div class="form-group">
          <label class="form-label" id="min-level-label">Минимальный уровень: ${this.selectedMinLevel}</label>
          <input type="range" id="min-level-slider" min="0" max="100" value="${this.selectedMinLevel}" style="width:100%; accent-color:var(--gold);">
        </div>
        `:""}

        <div style="text-align:center; margin: 15px 0; color: var(--gold); font-weight: bold; font-size: 14px;">
           Стоимость: 100 000 🪙
        </div>

        <div style="display:flex; gap:10px; margin-top:10px;">
          <button class="guild-leave-btn" id="create-cancel" style="flex:1">ОТМЕНА</button>
          <button class="guild-create-btn" id="create-confirm" style="flex:2">СОЗДАТЬ</button>
        </div>
      </div>
    `;const e=this.el.querySelector("#guild-name-input");e.addEventListener("input",()=>{this.newGuildName=e.value}),this.el.querySelectorAll(".avatar-opt").forEach(n=>{n.addEventListener("click",()=>{this.selectedAvatar=n.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".color-opt").forEach(n=>{n.addEventListener("click",()=>{this.selectedColor=n.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".type-opt").forEach(n=>{n.addEventListener("click",()=>{this.selectedType=n.getAttribute("data-val"),this.render()})});const t=this.el.querySelector("#min-level-slider");t&&t.addEventListener("input",()=>{this.selectedMinLevel=parseInt(t.value);const n=this.el.querySelector("#min-level-label");n&&(n.textContent=`Минимальный уровень: ${this.selectedMinLevel}`)}),(s=this.el.querySelector("#create-cancel"))==null||s.addEventListener("click",()=>{this.view="list",this.render()}),(i=this.el.querySelector("#create-confirm"))==null||i.addEventListener("click",async()=>{if(this.newGuildName.trim().length<3){alert("Слишком короткое название!");return}await Ye({name:this.newGuildName,avatar:this.selectedAvatar,borderColor:this.selectedColor,type:this.selectedType,minLevel:this.selectedMinLevel})?(l.haptic("heavy"),await this.init()):(l.haptic("error"),alert("Ошибка при создании артели."))})}renderManage(){var s;const e=w.find(i=>i.id===x),t=G;this.el.innerHTML=`
      <h1 class="page-title">${e.name.toUpperCase()}</h1>
      
      <div class="glass" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
         <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${e.borderColor}">${p(e.avatar)}</div>
         <div class="guild-info">
           <div class="guild-name" style="font-size:17px;">Уровень ${e.level}</div>
           <div class="guild-meta" style="font-size:10px;">${e.members.length}/${e.capacity} участников</div>
         </div>
      </div>

      <div class="my-guild-stats">
        <div class="glass stat-box">
          <div class="stat-val">${e.type==="open"?"🔓":"🔒"}</div>
          <div class="stat-lab">Доступ</div>
        </div>
        <div class="glass stat-box">
          <div class="stat-val">⭐</div>
          <div class="stat-lab">Топ 100</div>
        </div>
      </div>

      <div class="glass" style="padding: 12px; margin-bottom: 12px;">
        <p class="form-label" style="margin-bottom: 10px; color: var(--gold); font-size: 10px;">Улучшение до ур. ${e.level+1}</p>
        <div class="upgrade-section">
          ${e.upgradeProgress.map((i,n)=>`
            <div class="upgrade-item">
              <div class="upgrade-main">
                <div class="upgrade-labels">
                  <span>${i.item}</span>
                  <span>${i.current}/${i.required}</span>
                </div>
                <div class="upgrade-bar">
                  <div class="upgrade-fill" style="width: ${i.current/i.required*100}%"></div>
                </div>
              </div>
              <button class="donate-btn" data-idx="${n}">ВКЛАД</button>
            </div>
          `).join("")}
        </div>
      </div>

      ${t&&e.requests.length>0?`
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки на вступление</p>
          <div class="requests-list">
            ${e.requests.map(i=>`
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${i.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${i.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${i.level}</div>
                </div>
                <div class="req-btns">
                  <button class="req-btn req-btn--no" data-id="${i.requestId}" style="width:28px; height:28px; font-size:12px;">✕</button>
                  <button class="req-btn req-btn--yes" data-id="${i.requestId}" style="width:28px; height:28px; font-size:12px;">✓</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `:""}

      <div class="guild-actions">
        <button class="guild-leave-btn" id="btn-leave" style="height:44px; font-size:11px;">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `,(s=this.el.querySelector("#btn-leave"))==null||s.addEventListener("click",()=>{confirm("Вы уверены, что хотите покинуть артель?")&&(Ge(),l.haptic("medium"),this.render())}),this.el.querySelectorAll(".donate-btn").forEach(i=>{i.addEventListener("click",()=>{const n=parseInt(i.getAttribute("data-idx"),10),r=e.upgradeProgress[n];r.current=Math.min(r.required,r.current+Math.floor(Math.random()*5)+1),l.haptic("selection"),this.render()})}),this.el.querySelectorAll(".req-btn--yes").forEach(i=>{i.addEventListener("click",async()=>{const n=i.getAttribute("data-id");if(!n)return;const r=await le(n,"accept");l.haptic(r?"heavy":"error"),r&&await this.init()})}),this.el.querySelectorAll(".req-btn--no").forEach(i=>{i.addEventListener("click",async()=>{const n=i.getAttribute("data-id");if(!n)return;const r=await le(n,"decline");l.haptic(r?"medium":"error"),r&&await this.init()})})}}let X=[],$=[];async function _(){try{const a=await h("/api/friends");if(a&&a.ok){const e=Array.isArray(a.items)?a.items:[],t=Array.isArray(a.incoming_requests)?a.incoming_requests:[];X=e.map(s=>({id:String(s.user_id),name:s.username,level:Number(s.level||0),avatar:"👤",online:!!s.is_online,xp:Number(s.xp||0)})),$=t.map(s=>({id:String(s.request_id||s.id),name:String(s.username||"user"),level:Number(s.level||0),avatar:"👤"}))}}catch(a){console.error("Failed to load friends:",a)}}async function Ze(a){try{const e=await h("/api/friends/add",{method:"POST",body:JSON.stringify({username:a})});return!!(e!=null&&e.ok)}catch(e){return console.error("Failed to send friend request:",e),!1}}async function Je(a){return de(a,"accept")}async function Ke(a){return de(a,"decline")}async function de(a,e){try{const t=await h("/api/friends/request/respond",{method:"POST",body:JSON.stringify({request_id:a,action:e})});if(t!=null&&t.ok)return await _(),!0}catch(t){console.error("Failed to respond friend request:",t)}return!1}class Qe{constructor(){this.currentView="list",this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-friends",e.className="screen friends-screen",e.setAttribute("role","main"),e}async init(){this.loading=!0,this.render(),await _(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}this.currentView==="requests"?this.renderRequests():this.renderList()}renderList(){var e,t;this.el.innerHTML=`
      <div class="friends-header-row">
        <h1 class="page-title" style="margin-bottom:0">ДРУЗЬЯ</h1>
        <div class="friends-notif-btn" id="btn-show-requests">
          <span>🔔</span>
          ${$.length>0?`<div class="notif-badge">${$.length}</div>`:""}
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
        ${X.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:20px;">У вас пока нет друзей</p>':""}
        ${X.map(s=>`
          <div class="friend-card glass">
            <div class="friend-avatar">${s.avatar}</div>
            <div class="friend-info">
              <div class="friend-name">${s.name}</div>
              <div class="friend-meta">Ур. ${s.level} · ${s.online?'<span style="color:#2ecc71">Online</span>':'<span style="opacity:0.5">Offline</span>'}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `,(e=this.el.querySelector("#btn-show-requests"))==null||e.addEventListener("click",()=>{this.currentView="requests",this.render(),l.haptic("medium")}),(t=this.el.querySelector("#btn-add-search"))==null||t.addEventListener("click",async()=>{const s=this.el.querySelector("#friend-search");s.value.trim()&&(await Ze(s.value.trim())?(alert("Запрос отправлен!"),s.value="",l.haptic("light"),await _(),this.render()):(l.haptic("error"),alert("Не удалось отправить заявку.")))})}renderRequests(){var e;this.el.innerHTML=`
      <div class="friends-header-row">
        <button class="back-btn" id="btn-back-list">←</button>
        <h1 class="page-title" style="margin:0; flex:1">ЗАЯВКИ</h1>
      </div>

      <div class="requests-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${$.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:40px;">Нет новых заявок</p>':""}
        ${$.map(t=>`
          <div class="request-card glass">
            <div class="req-avatar">${t.avatar}</div>
            <div class="req-info">
              <div class="req-name">${t.name}</div>
              <div class="req-lvl">Ур. ${t.level} хочет в друзья!</div>
            </div>
            <div class="req-btns">
               <button class="req-btn req-btn--no" data-id="${t.id}">✕</button>
               <button class="req-btn req-btn--yes" data-id="${t.id}">✓</button>
            </div>
          </div>
        `).join("")}
      </div>
    `,(e=this.el.querySelector("#btn-back-list"))==null||e.addEventListener("click",()=>{this.currentView="list",this.render(),l.haptic("light")}),this.el.querySelectorAll(".req-btn--yes").forEach(t=>{t.addEventListener("click",async()=>{const s=t.getAttribute("data-id"),i=await Je(s);l.haptic(i?"heavy":"error"),this.render()})}),this.el.querySelectorAll(".req-btn--no").forEach(t=>{t.addEventListener("click",async()=>{const s=t.getAttribute("data-id"),i=await Ke(s);l.haptic(i?"medium":"error"),this.render()})})}}class et{constructor(){this.currentType="normal",this.isLoading=!1,this.el=this.build()}build(){const e=document.createElement("section");return e.id="screen-rating",e.className="screen",e.setAttribute("role","main"),e.setAttribute("aria-label","Рейтинг"),e.innerHTML=`
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
    `,e}getElement(){return this.el}async init(){this.bindEvents(),await this.loadRating()}bindEvents(){setTimeout(()=>{const t=this.el.querySelector("#rating-back-btn");t&&t.addEventListener("click",s=>{s.preventDefault(),s.stopPropagation(),console.log("Rating back button clicked");const i=new CustomEvent("navigate-home");window.dispatchEvent(i)})},100);const e=this.el.querySelectorAll(".rating-tab");e.forEach(t=>{t.addEventListener("click",()=>{const s=t.dataset.type;s===this.currentType||this.isLoading||(l.haptic("selection"),e.forEach(i=>i.classList.remove("is-active")),t.classList.add("is-active"),this.currentType=s,this.loadRating())})})}async loadRating(){if(this.isLoading)return;this.isLoading=!0;const e=this.el.querySelector("#rating-list"),t=this.el.querySelector("#rating-my-rank");e.innerHTML='<div class="rating-loading">Загрузка...</div>',t.innerHTML='<div class="rating-loading">Загрузка...</div>';try{const s=await z(`/api/tickets/rating?ticket_type=${this.currentType}&limit=50`);if(!s.ok||!s.items)throw new Error("Failed to load rating");this.renderMyRank(t,s.my_rank,s.ticket_type),this.renderList(e,s.items)}catch(s){console.error("Failed to load rating:",s),e.innerHTML='<div class="rating-error">Ошибка загрузки рейтинга</div>',t.innerHTML='<div class="rating-error">Ошибка загрузки</div>'}finally{this.isLoading=!1}}renderMyRank(e,t,s){const i=s==="gold"?"🎫":"🎟️",n=s==="gold"?"золотых":"обычных";if(t===null||t===0)e.innerHTML=`
        <div class="my-rank-content">
          <div class="my-rank-icon">${i}</div>
          <div class="my-rank-text">
            <div class="my-rank-label">Ваше место</div>
            <div class="my-rank-value">Нет ${n} билетов</div>
          </div>
        </div>
      `;else{const r=t===1?"🥇":t===2?"🥈":t===3?"🥉":"";e.innerHTML=`
        <div class="my-rank-content">
          <div class="my-rank-icon">${r||i}</div>
          <div class="my-rank-text">
            <div class="my-rank-label">Ваше место в топе</div>
            <div class="my-rank-value">#${t}</div>
          </div>
        </div>
      `}}renderList(e,t){if(!t||t.length===0){e.innerHTML='<div class="rating-empty">Рейтинг пуст</div>';return}const s=t.map(i=>{const n=i.place===1?"🥇":i.place===2?"🥈":i.place===3?"🥉":"";return`
        <div class="rating-item ${i.place<=3?"rating-item-top":""}">
          <div class="rating-place">
            ${n?`<span class="rating-medal">${n}</span>`:`<span class="rating-number">#${i.place}</span>`}
          </div>
          <div class="rating-user">
            <div class="rating-username">${this.escapeHtml(i.username)}</div>
            <div class="rating-user-id">ID: ${i.user_id}</div>
          </div>
          <div class="rating-tickets">
            <div class="rating-tickets-value">${i.tickets}</div>
            <div class="rating-tickets-label">билетов</div>
          </div>
        </div>
      `}).join("");e.innerHTML=s}escapeHtml(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}}const tt=793216884;class st{constructor(){this.currentType="normal",this.isLoading=!1,this.isOwner=!1,this.el=this.build(),this.checkOwner()}checkOwner(){const e=l.getUser();this.isOwner=(e==null?void 0:e.id)===tt}build(){const e=document.createElement("section");return e.id="screen-results",e.className="screen",e.setAttribute("role","main"),e.setAttribute("aria-label","Результаты"),e.innerHTML=`
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
    `,e}getElement(){return this.el}async init(){if(this.isOwner){const e=this.el.querySelector("#results-owner-panel");e&&(e.style.display="block")}this.bindEvents(),await this.loadResults()}bindEvents(){setTimeout(()=>{const t=this.el.querySelector("#results-back-btn");t&&t.addEventListener("click",s=>{s.preventDefault(),s.stopPropagation(),console.log("Results back button clicked");const i=new CustomEvent("navigate-home");window.dispatchEvent(i)})},100);const e=this.el.querySelectorAll(".results-tab");if(e.forEach(t=>{t.addEventListener("click",()=>{const s=t.dataset.type;s===this.currentType||this.isLoading||(l.haptic("selection"),e.forEach(i=>i.classList.remove("is-active")),t.classList.add("is-active"),this.currentType=s,this.loadResults())})}),this.isOwner){const t=this.el.querySelector("#results-create-btn");t&&t.addEventListener("click",()=>this.createDraw())}}async loadResults(){if(this.isLoading)return;this.isLoading=!0;const e=this.el.querySelector("#results-list");e.innerHTML='<div class="results-loading">Загрузка...</div>';try{const t=await z(`/api/tickets/results?ticket_type=${this.currentType}`);if(!t.ok)throw new Error("Failed to load results");this.renderResults(e,t)}catch(t){console.error("Failed to load results:",t),e.innerHTML='<div class="results-error">Ошибка загрузки результатов</div>'}finally{this.isLoading=!1}}async createDraw(){var o;if(this.isLoading)return;const e=this.el.querySelector("#results-start-date"),t=this.el.querySelector("#results-end-date"),s=this.el.querySelector("#results-count"),i=e.value,n=t.value,r=parseInt(s.value)||3;if(!i||!n){l.showAlert("Укажите даты начала и окончания розыгрыша");return}if(new Date(i)>new Date(n)){l.showAlert("Дата начала не может быть позже даты окончания");return}this.isLoading=!0,l.haptic("medium");try{const c=await z("/api/tickets/draw",{method:"POST",body:JSON.stringify({ticket_type:this.currentType,start_date:i,end_date:n,count:r})});if(!c.ok)throw new Error("Failed to create draw");l.showAlert(`Розыгрыш проведен! Победителей: ${((o=c.items)==null?void 0:o.length)||0}`),await this.loadResults()}catch(c){console.error("Failed to create draw:",c),l.showAlert("Ошибка при проведении розыгрыша")}finally{this.isLoading=!1}}renderResults(e,t){if(!t.items||t.items.length===0){e.innerHTML=`
        <div class="results-empty">
          <div class="results-empty-icon">🎲</div>
          <div class="results-empty-text">Результатов розыгрышей пока нет</div>
        </div>
      `;return}const s=t.period,i=s?`
      <button class="results-period-btn" id="results-toggle-btn">
        <div class="results-period-btn-icon">📅</div>
        <div class="results-period-btn-text">
          <div class="results-period-btn-label">Результаты розыгрыша</div>
          <div class="results-period-btn-date">${this.formatDate(s.start_date)} — ${this.formatDate(s.end_date)}</div>
        </div>
        <div class="results-period-btn-arrow">▼</div>
      </button>
    `:"",n=t.items.map(d=>{const v=d.place===1?"🥇":d.place===2?"🥈":d.place===3?"🥉":"🎖️";return`
        <div class="results-winner ${d.place<=3?"results-winner-top":""}">
          <div class="results-winner-place">
            <span class="results-medal">${v}</span>
            <span class="results-place-number">#${d.place}</span>
          </div>
          <div class="results-winner-info">
            <div class="results-winner-username">${this.escapeHtml(d.username)}</div>
            <div class="results-winner-id">ID: ${d.user_id}</div>
            <div class="results-winner-ticket">Билет: <strong>${d.ticket_code}</strong></div>
          </div>
        </div>
      `}).join("");e.innerHTML=`
      ${i}
      <div class="results-winners" id="results-winners-list" style="display: none;">
        ${n}
      </div>
    `;const r=e.querySelector("#results-toggle-btn"),o=e.querySelector("#results-winners-list"),c=e.querySelector(".results-period-btn-arrow");r&&o&&r.addEventListener("click",()=>{const d=o.style.display!=="none";o.style.display=d?"none":"flex",c&&(c.textContent=d?"▼":"▲"),l.haptic("selection")})}formatDate(e){try{return new Date(e).toLocaleDateString("ru-RU",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}escapeHtml(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}}class it{constructor(){this.token="",this.challenge=null,this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-captcha",e.className="screen captcha-screen",e.setAttribute("role","main"),e.innerHTML=`
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
    `,e}async init(){const e=new URLSearchParams(window.location.search);if(this.token=e.get("captcha_token")||"",!this.token){this.showError("Токен капчи не найден. Откройте апку по ссылке из бота.");return}await this.loadChallenge(),this.bindEvents()}bindEvents(){const e=this.el.querySelector("#captcha-submit"),t=this.el.querySelector("#captcha-answer");e&&t&&(e.addEventListener("click",()=>{l.haptic("medium"),this.submitAnswer(t.value)}),t.addEventListener("keypress",s=>{s.key==="Enter"&&(l.haptic("medium"),this.submitAnswer(t.value))}))}async loadChallenge(){this.loading=!0,this.showStatus("loading","⏳ Загрузка капчи...");try{const e=await h(`/api/captcha/challenge?token=${this.token}`);if(!e||!e.ok){const t=(e==null?void 0:e.error)||"unknown_error";if(t==="penalty_active"){const s=(e==null?void 0:e.penalty_until)||"";this.showPenalty(s)}else t==="challenge_expired"?this.showError("⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте."):t==="challenge_not_found"?this.showError("❌ Капча не найдена. Запросите новую капчу в боте."):this.showError(`❌ Ошибка: ${t}`);return}if(e.penalty_active){const t=e.penalty_until||"";this.showPenalty(t);return}if(this.challenge=e.challenge||null,!this.challenge){this.showError("❌ Капча не найдена");return}this.renderChallenge(),this.startTimer()}catch(e){console.error("Failed to load captcha:",e),this.showError("❌ Ошибка загрузки капчи. Попробуйте позже.")}finally{this.loading=!1}}renderChallenge(){if(!this.challenge)return;const e=this.el.querySelector("#captcha-content"),t=this.el.querySelector("#captcha-map"),s=this.el.querySelector("#captcha-steps");e.style.display="block",this.showStatus("",""),t&&this.challenge.map&&(t.innerHTML=Object.entries(this.challenge.map).map(([i,n])=>`<li><strong>${i}</strong> = ${n}</li>`).join("")),s&&this.challenge.steps&&(s.innerHTML=this.challenge.steps.map(i=>`<li>${i}</li>`).join(""))}startTimer(){if(!this.challenge)return;const e=this.el.querySelector("#captcha-timer");if(!e)return;const t=()=>{if(!this.challenge)return;const s=new Date(this.challenge.expires_at),i=new Date,n=s.getTime()-i.getTime();if(n<=0){e.textContent="⏰ Время истекло",this.showError("⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте.");return}const r=Math.floor(n/6e4),o=Math.floor(n%6e4/1e3);e.textContent=`⏳ Осталось: ${r}:${o.toString().padStart(2,"0")}`,setTimeout(t,1e3)};t()}async submitAnswer(e){if(!e.trim()){alert("Введите ответ");return}if(!this.loading){this.loading=!0,this.showStatus("loading","⏳ Проверка ответа...");try{const t=await h("/api/captcha/solve",{method:"POST",body:JSON.stringify({token:this.token,answer:e.trim()})});if(t&&t.ok)l.haptic("success"),this.showStatus("success","✅ Капча пройдена! Ограничение снято."),setTimeout(()=>{var s,i,n;(s=window.Telegram)!=null&&s.WebApp&&((n=(i=window.Telegram.WebApp).close)==null||n.call(i))},2e3);else{const s=(t==null?void 0:t.error)||"wrong_answer";s==="wrong_answer"?(l.haptic("error"),this.showStatus("error","❌ Неверный ответ. Попробуйте еще раз.")):s==="challenge_expired"?this.showError("⏰ Время на прохождение капчи истекло. Запросите новую капчу в боте."):this.showError(`❌ Ошибка: ${s}`)}}catch(t){console.error("Failed to submit captcha:",t),l.haptic("error"),this.showStatus("error","❌ Ошибка отправки ответа. Попробуйте еще раз.")}finally{this.loading=!1}}}showStatus(e,t){const s=this.el.querySelector("#captcha-status");s&&(s.className=`captcha-status ${e}`,s.textContent=t,s.style.display=t?"block":"none")}showError(e){this.showStatus("error",e);const t=this.el.querySelector("#captcha-content");t&&(t.style.display="none")}showPenalty(e){const t=this.el.querySelector("#captcha-status");if(!t)return;const s=new Date(e),i=new Date,n=s.getTime()-i.getTime();if(n<=0){this.showError("⏰ Блокировка истекла. Обновите страницу.");return}const r=Math.floor(n/36e5),o=Math.floor(n%36e5/6e4);t.className="captcha-status penalty",t.textContent=`🚫 Вы заблокированы за подозрительную активность. Осталось: ${r}ч ${o}м`,t.style.display="block";const c=this.el.querySelector("#captcha-content");c&&(c.style.display="none")}}class at{constructor(e){this.particles=[],this.W=0,this.H=0,this.rafId=0,this.COUNT=60,this.canvas=e,this.ctx=e.getContext("2d"),this.resize(),window.addEventListener("resize",this.resize.bind(this));for(let t=0;t<this.COUNT;t++){const s=this.createParticle();s.y=Math.random()*this.H,s.life=Math.floor(Math.random()*s.maxLife*.5),this.particles.push(s)}this.loop()}resize(){this.W=this.canvas.width=this.canvas.offsetWidth,this.H=this.canvas.height=this.canvas.offsetHeight}createParticle(){const e=Math.random()<.28;return{x:Math.random()*this.W,y:this.H+12,r:e?1.5+Math.random()*2:1.2+Math.random()*3,vx:(Math.random()-.5)*.4,vy:-(.2+Math.random()*.55),alpha:0,alphaTarget:.12+Math.random()*.4,life:0,maxLife:180+Math.random()*420,isSediment:e,wobble:Math.random()*Math.PI*2,wobbleSpeed:.02+Math.random()*.03}}drawBubble(e){const t=this.ctx;e.wobble+=e.wobbleSpeed;const s=e.x+Math.sin(e.wobble)*1.8;t.save(),t.globalAlpha=e.alpha,t.strokeStyle="rgba(160,220,255,0.65)",t.lineWidth=.7,t.beginPath(),t.arc(s,e.y,e.r,0,Math.PI*2),t.stroke(),t.fillStyle="rgba(255,255,255,0.35)",t.beginPath(),t.arc(s-e.r*.28,e.y-e.r*.28,e.r*.38,0,Math.PI*2),t.fill(),t.restore()}drawSediment(e){const t=this.ctx;t.save(),t.globalAlpha=e.alpha,t.fillStyle="rgba(180,150,90,0.7)",t.beginPath(),t.ellipse(e.x,e.y,e.r*1.6,e.r*.55,e.wobble,0,Math.PI*2),t.fill(),t.restore()}updateParticle(e){e.x+=e.vx,e.y+=e.vy,e.life+=1;const t=40,s=50;return e.life<t?e.alpha=e.life/t*e.alphaTarget:e.life>e.maxLife-s?e.alpha=(e.maxLife-e.life)/s*e.alphaTarget:e.alpha=e.alphaTarget,e.life<e.maxLife&&e.y>-10}loop(){this.ctx.clearRect(0,0,this.W,this.H);for(let e=0;e<this.particles.length;e++){const t=this.particles[e];this.updateParticle(t)?t.isSediment?this.drawSediment(t):this.drawBubble(t):this.particles[e]=this.createParticle()}this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId),window.removeEventListener("resize",this.resize.bind(this))}}const nt=new URLSearchParams(window.location.search),rt=nt.get("captcha_mode");if(rt==="antibot"){const a=new it,e=a.getElement();document.body.innerHTML="",document.body.appendChild(e),a.init()}else lt();function lt(){const a=ye();fe();const e=document.getElementById("particles-canvas");new at(e);const t=document.getElementById("bg-parallax");new Se(t);const s=new Ee;s.updateFromTelegram(),document.getElementById("profile-mount").appendChild(s.getElement());async function n(){try{await Promise.all([_(),M(),ce()]),console.log("Initial data loaded")}catch(y){console.error("Failed to load initial data:",y)}}n();const r=document.getElementById("carousel-mount"),o=new $e(r,2),c=document.getElementById("screens-wrap"),d=new Oe;async function v(){const y=await Pe();o.setFishData(y,V),d.setItems(o.getItems())}v(),d.onSelect(y=>{o.goTo(y)}),ke(()=>{d.open(o.getActiveIndex(),c)});const m=new Ue,b=m.getElement(),L=document.getElementById("screen-book");L?L.replaceWith(b):c.appendChild(b);const C=new Ve,g=C.getElement(),u=document.getElementById("screen-shop");u?u.replaceWith(g):c.appendChild(g);const E=new We,W=E.getElement(),Z=document.getElementById("screen-guilds");Z?Z.replaceWith(W):c.appendChild(W);const H=new Qe,J=H.getElement(),K=document.getElementById("screen-friends");K?K.replaceWith(J):c.appendChild(J);const B=new et,he=B.getElement();c.appendChild(he);const F=new st,ue=F.getElement();c.appendChild(ue);let Q=!1,ee=!1,te=!1,P=!1,N=!1,O=!1;const pe=document.getElementById("tabbar-mount"),q=new De(pe,c);q.onChange((y,f)=>{console.log(`Screen transition: ${y} -> ${f}`);const D=document.getElementById("tab-bar");if(D&&(f==="rating"||f==="results"?D.classList.add("hide-tabbar"):D.classList.remove("hide-tabbar")),f==="book"&&!Q&&(m.init(),Q=!0),f==="shop"&&!ee&&(C.init(),ee=!0),f==="guilds"&&!te&&(E.init(),te=!0),f==="friends"&&!P?(H.init(),P=!0):f==="friends"&&P&&H.init(),f==="rating"&&!N?(B.init(),N=!0):f==="rating"&&N&&B.init(),f==="results"&&!O?(F.init(),O=!0):f==="results"&&O&&F.init(),f==="home"){const se=document.getElementById("screen-home");se&&se.querySelectorAll(".slide-up").forEach(ve=>{const R=ve;R.style.animation="none",R.style.opacity="1",R.style.transform="translateY(0)"})}}),we(()=>q.switchTo("rating"),()=>q.switchTo("results")),window.addEventListener("navigate-home",()=>{console.log("Navigate home event received");const y=document.getElementById("tab-bar");y&&y.classList.remove("hide-tabbar"),q.switchTo("home")}),setTimeout(()=>s.animateProgress(0),2e3),be(a,1600)}
