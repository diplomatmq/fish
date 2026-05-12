(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))i(a);new MutationObserver(a=>{for(const r of a)if(r.type==="childList")for(const n of r.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&i(n)}).observe(document,{childList:!0,subtree:!0});function t(a){const r={};return a.integrity&&(r.integrity=a.integrity),a.referrerPolicy&&(r.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?r.credentials="include":a.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function i(a){if(a.ep)return;a.ep=!0;const r=t(a);fetch(a.href,r)}})();class re{constructor(){var e;this.tg=((e=window.Telegram)==null?void 0:e.WebApp)??null,this.tg&&(this.tg.ready(),this.tg.expand(),this.tg.setHeaderColor("#0a1628"),this.tg.setBackgroundColor("#0a1628"))}haptic(e){var t;(t=this.tg)!=null&&t.HapticFeedback&&(e==="selection"?this.tg.HapticFeedback.selectionChanged():e==="success"||e==="error"?this.tg.HapticFeedback.notificationOccurred(e):e==="impact"?this.tg.HapticFeedback.impactOccurred("medium"):["light","medium","heavy"].includes(e)&&this.tg.HapticFeedback.impactOccurred(e))}getUserName(){var e,t,i;return((i=(t=(e=this.tg)==null?void 0:e.initDataUnsafe)==null?void 0:t.user)==null?void 0:i.first_name)??null}getUserTag(){var t,i,a;const e=(a=(i=(t=this.tg)==null?void 0:t.initDataUnsafe)==null?void 0:i.user)==null?void 0:a.username;return e?`@${e}`:null}}const l=new re,F={home:`
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
  `,trophy:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 9C6 9 6 3 12 3C18 3 18 9 18 9M6 9C6 14 10 17 12 17C14 17 18 14 18 9M6 9H3V11C3 13 5 13 5 13M18 9H21V11C21 13 19 13 19 13M12 17V21M9 21H15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `};function d(s,e=""){const t=F[s]||F.home;return e?t.replace("<svg",`<svg class="${e}"`):t}function ne(){const s=document.getElementById("app");return s.innerHTML=`
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
            ${d("trophy")} &nbsp;ВЫБРАТЬ ТРОФЕЙ
          </button>
        </div>

        <!-- Quick actions -->
        <div class="quick-actions slide-up" style="animation-delay:2.1s">
          <button class="quick-card glass" id="btn-achievements" aria-label="Достижения">
            <span class="quick-icon" aria-hidden="true">${d("achievements")}</span>
            <span class="quick-label">Достижения</span>
          </button>
          <button class="quick-card glass" id="btn-rating" aria-label="Рейтинг">
            <span class="quick-icon" aria-hidden="true">${d("rating")}</span>
            <span class="quick-label">Рейтинг</span>
          </button>
        </div>
      </section>

      <!-- SHOP -->
      <section id="screen-shop" class="screen" role="main" aria-label="Лавка">
        <h1 class="page-title">ЛАВКА</h1>
        <div class="glass shop-container">
          <div class="shop-empty">
            <div class="shop-soon-icon">${d("shop")}</div>
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
      ${le("book","📖","Книга рыбака",`Здесь появится ваш
рыболовный журнал`)}

    </div>

    <!-- Tab bar injected by TabBar -->
    <div id="tabbar-mount"></div>

    <!-- Modal injected by TrophyModal -->
  `,s}function le(s,e,t,i){return`
    <section id="screen-${s}" class="screen screen--empty" role="main" aria-label="${t}">
      <h1 class="page-title">${t.toUpperCase()}</h1>
      <div class="glass empty-content">
        <div class="empty-icon" aria-hidden="true">${d(s)}</div>
        <p class="empty-text">${i.replace(`
`,"<br>")}</p>
      </div>
    </section>
  `}function oe(){const s=document.createElement("div");return s.id="entry-overlay",s.className="entry-overlay",s.innerHTML=`
    <div class="entry-logo" aria-hidden="true">🌊</div>
    <p class="entry-title">ПОДВОДНЫЙ МИР</p>
    <p class="entry-subtitle">Загрузка…</p>
  `,document.body.appendChild(s),s}function ce(s,e=1600){setTimeout(()=>{s.style.transition="opacity 0.6s ease",s.style.opacity="0",setTimeout(()=>s.remove(),700)},e)}function de(){const s=document.getElementById("btn-achievements"),e=document.getElementById("btn-rating");[s,e].forEach(t=>{t&&t.addEventListener("click",()=>{l.haptic("light"),t.classList.remove("bounce"),t.offsetWidth,t.classList.add("bounce"),t.addEventListener("animationend",()=>t.classList.remove("bounce"),{once:!0})})})}function he(s){const e=document.getElementById("select-trophy-btn");e&&(e.addEventListener("click",s),e.addEventListener("pointerdown",()=>{e.style.transform="scale(0.96)"}),e.addEventListener("pointerup",()=>{e.style.transform=""}),e.addEventListener("pointerleave",()=>{e.style.transform=""}))}const P=[{id:"home",icon:"🧭",label:"ГЛАВНАЯ"},{id:"shop",icon:"🧺",label:"ЛАВКА"},{id:"friends",icon:"👤",label:"ДРУЗЬЯ"},{id:"guilds",icon:"🔱",label:"АРТЕЛИ"},{id:"book",icon:"📖",label:"КНИГА"}],k={name:"АКВАМАН_01",tag:"@aquaman01",level:15,xp:7200,maxXp:1e4,avatar:"🤿"},b={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"},pe=()=>{var s,e;return((e=(s=window.Telegram)==null?void 0:s.WebApp)==null?void 0:e.initData)||""};async function h(s,e={}){const i={"Content-Type":"application/json","X-Telegram-Init-Data":pe(),...e.headers||{}},a=await fetch(s,{...e,headers:i});if(!a.ok){const r=await a.json().catch(()=>({error:"Unknown error"}));throw new Error(r.error||`HTTP error! status: ${a.status}`)}return a.json()}class ue{constructor(){this.fillEl=null,this.wobbling=!1,this.profile={...k},this.el=this.build(),this.loadProfile()}async loadProfile(){try{const e=await h("/api/profile");e&&(this.profile.name=e.username||this.profile.name,this.profile.level=e.level||this.profile.level,this.profile.xp=e.xp||this.profile.xp,this.profile.maxXp=1e4,this.profile.tag=`@${e.user_id}`||this.profile.tag,this.updateUI())}catch(e){console.error("Failed to load profile:",e)}}updateUI(){const e=this.el.querySelector("#profile-name"),t=this.el.querySelector("#profile-tag"),i=this.el.querySelector(".level-label"),a=this.el.querySelector(".xp-label");e&&(e.textContent=this.profile.name.toUpperCase()),t&&(t.textContent=this.profile.tag),i&&(i.textContent=`Уровень ${this.profile.level}`),a&&(a.textContent=`${this.profile.xp.toLocaleString("ru")} XP`),this.animateProgress(0)}getElement(){return this.el}build(){const e=k,t=Math.round(e.xp/e.maxXp*100),i=document.createElement("div");i.id="profile-panel",i.className="profile-panel glass",i.innerHTML=`
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
    `;const a=i.querySelector("#porthole-wrap");a.addEventListener("click",()=>this.wobble(a)),a.addEventListener("keydown",n=>{(n.key==="Enter"||n.key===" ")&&this.wobble(a)});const r=i.querySelector("#edit-btn");return r.addEventListener("click",()=>{l.haptic("light"),r.textContent="⏳ Загрузка...",setTimeout(()=>{r.innerHTML="✏️ Редактировать"},1800)}),r.addEventListener("pointerdown",()=>{r.style.transform="scale(0.96)"}),r.addEventListener("pointerup",()=>{r.style.transform=""}),this.fillEl=i.querySelector("#progress-fill"),i}animateProgress(e=200){if(!this.fillEl)return;const t=Math.round(k.xp/k.maxXp*100);this.fillEl.style.width="0%",setTimeout(()=>{this.fillEl.style.width=`${t}%`},e)}wobble(e){this.wobbling||(this.wobbling=!0,l.haptic("light"),e.classList.add("porthole--wobble"),e.addEventListener("animationend",()=>{e.classList.remove("porthole--wobble"),this.wobbling=!1},{once:!0}))}updateFromTelegram(){const e=l.getUserName(),t=l.getUserTag();if(e){const i=this.el.querySelector("#profile-name");i&&(i.textContent=e.toUpperCase())}if(t){const i=this.el.querySelector("#profile-tag");i&&(i.textContent=t)}}}class ve{constructor(e){this.targetX=0,this.targetY=0,this.currentX=0,this.currentY=0,this.rafId=0,this.el=e,this.bindEvents(),this.loop()}bindEvents(){window.addEventListener("mousemove",e=>{this.targetX=(e.clientX/window.innerWidth-.5)*14,this.targetY=(e.clientY/window.innerHeight-.5)*8}),window.addEventListener("deviceorientation",e=>{e.gamma===null||e.beta===null||(this.targetX=Math.max(-12,Math.min(12,e.gamma*.25)),this.targetY=Math.max(-7,Math.min(7,(e.beta-45)*.15)))})}loop(){this.currentX+=(this.targetX-this.currentX)*.06,this.currentY+=(this.targetY-this.currentY)*.06,this.el.style.transform=`scale(1.14) translate(${-this.currentX*.08}%, ${-this.currentY*.06}%)`,this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId)}}class fe{constructor(e){this.intervalId=0,this.container=e,this.start()}spawnOne(){if(document.hidden)return;const e=document.createElement("div");e.className="trophy-bubble";const t=4+Math.random()*9,i=20+Math.random()*60,a=2.8+Math.random()*2.8;e.style.cssText=`
      width:${t}px; height:${t}px;
      left:${i}%; bottom:${8+Math.random()*12}%;
      animation-duration:${a}s;
      animation-delay:${Math.random()*.3}s;
    `,this.container.appendChild(e),setTimeout(()=>e.remove(),(a+.5)*1e3)}start(){this.intervalId=window.setInterval(()=>this.spawnOne(),380)}stop(){clearInterval(this.intervalId),this.container.querySelectorAll(".trophy-bubble").forEach(e=>e.remove())}restart(){this.stop(),this.start()}}const L=class L{static transitionTo(e,t){this.pendingTimeout&&(clearTimeout(this.pendingTimeout),this.pendingTimeout=0);const i=++this.transitionToken;e.style.transition="opacity 0.35s ease, transform 0.35s ease",e.style.opacity="0",e.style.transform="scale(0.93)",e.style.pointerEvents="none",t.style.transition="none",t.style.opacity="0",t.style.transform="scale(1.06)",t.style.display="flex",t.style.pointerEvents="none",this.pendingTimeout=window.setTimeout(()=>{i===this.transitionToken&&(e.style.display="none",e.style.opacity="",e.style.transform="",e.style.transition="",requestAnimationFrame(()=>{i===this.transitionToken&&(t.style.transition="opacity 0.38s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.38s cubic-bezier(0.25,0.46,0.45,0.94)",t.style.opacity="1",t.style.transform="scale(1)",t.style.pointerEvents="all")}))},300)}};L.transitionToken=0,L.pendingTimeout=0;let M=L;const me={id:"no-trophy",emoji:"🐟",name:"Нет трофеев",latinName:"",rarity:"common",rarityLabel:"Обычная",rarityStars:"",weight:"0 кг",depth:"0 см"};class ge{constructor(e,t=2){this.cards=[],this.bubbleSpawner=null,this.fishData=[],this.startX=0,this.isDragging=!1,this.onChangeCallback=null,this.container=e,this.activeIndex=t,this.build(),this.bindSwipe(),this.update()}build(){this.container.innerHTML="",this.cards=[];const e=document.createElement("div");e.className="carousel__bubbles",this.container.appendChild(e),this.bubbleSpawner=new fe(e);const t=document.createElement("div");if(t.className="carousel__track",this.container.appendChild(t),this.fishData.length===0){t.innerHTML=`
        <div class="carousel__card is-active" style="opacity:1; transform:translateX(0) scale(1);">
          <div class="carousel__card-inner" style="--accent:${b.common}">
            <div class="carousel__fish-emoji">${d("trophy")}</div>
            <div class="carousel__rarity" style="color:${b.common}">ТРОФЕЕВ ПОКА НЕТ</div>
            <div class="carousel__fish-name">Поймай рыбу и создай трофей</div>
            <div class="carousel__fish-latin">Карточки появятся автоматически</div>
          </div>
        </div>
      `;return}this.fishData.forEach((i,a)=>{const r=document.createElement("div");r.className="carousel__card",r.dataset.index=String(a);const n=b[i.rarity];r.innerHTML=`
        <div class="carousel__card-inner" style="--accent:${n}">
          <div class="carousel__fish-emoji">${i.imageUrl?`<img src="${i.imageUrl}" alt="${i.name}" class="carousel__fish-image" loading="lazy">`:d(i.id)}</div>
          <div class="carousel__rarity" style="color:${n}">${i.rarityStars} ${i.rarityLabel}</div>
          <div class="carousel__fish-name">${i.name}</div>
          <div class="carousel__fish-latin">${i.latinName}</div>
          <div class="carousel__fish-stats">
            <span>⚖️ ${i.weight}</span>
            <span>📏 ${i.depth}</span>
          </div>
        </div>
      `,t.appendChild(r),this.cards.push(r)})}update(){var t;if(this.cards.length===0)return;this.cards.forEach((i,a)=>{const r=a-this.activeIndex,n=Math.abs(r);i.classList.remove("is-active","is-side","is-far");let o,c,u,p;switch(n){case 0:o=0,c=1,u=1,p=10,i.classList.add("is-active");break;case 1:o=r*148,c=.78,u=.6,p=5,i.classList.add("is-side");break;case 2:o=r*185,c=.62,u=.28,p=2,i.classList.add("is-far");break;default:o=r*200,c=.5,u=0,p=0}i.style.transform=`translateX(${o}px) scale(${c})`,i.style.opacity=String(u),i.style.zIndex=String(p)});const e=this.fishData[this.activeIndex];e&&((t=this.onChangeCallback)==null||t.call(this,e))}next(){this.fishData.length!==0&&this.activeIndex<this.fishData.length-1&&(this.activeIndex++,this.update(),l.haptic("light"))}prev(){this.fishData.length!==0&&this.activeIndex>0&&(this.activeIndex--,this.update(),l.haptic("light"))}goTo(e){this.fishData.length!==0&&(this.activeIndex=Math.max(0,Math.min(e,this.fishData.length-1)),this.update())}getActiveIndex(){return this.activeIndex}getActiveFish(){return this.fishData[this.activeIndex]||me}getItems(){return this.fishData}setFishData(e,t){if(this.fishData=[...e],t){const i=this.fishData.findIndex(a=>a.trophyId===t||a.id===t);this.activeIndex=i>=0?i:0}else this.activeIndex=this.fishData.length?Math.max(0,Math.min(this.activeIndex,this.fishData.length-1)):0;this.build(),this.update()}onChange(e){this.onChangeCallback=e}bindSwipe(){const e=this.container;e.addEventListener("touchstart",t=>{this.startX=t.touches[0].clientX,this.isDragging=!0},{passive:!0}),e.addEventListener("touchend",t=>{if(!this.isDragging)return;const i=t.changedTouches[0].clientX-this.startX;this.handleSwipeEnd(i),this.isDragging=!1},{passive:!0}),e.addEventListener("mousedown",t=>{this.startX=t.clientX,this.isDragging=!0,t.preventDefault()}),window.addEventListener("mouseup",t=>{if(!this.isDragging)return;const i=t.clientX-this.startX;this.handleSwipeEnd(i),this.isDragging=!1})}handleSwipeEnd(e){e<-42?this.next():e>42&&this.prev()}}const ye={обычная:"common",редкая:"rare",легендарная:"legendary",аквариумная:"aquarium",мифическая:"mythical",аномалия:"anomaly"},be={common:"Обычная",rare:"Редкая",legendary:"Легендарная",aquarium:"Аквариумная",mythical:"Мифическая",anomaly:"Аномалия"},we={common:"★★",rare:"★★★",legendary:"★★★★★",aquarium:"★★★★",mythical:"★★★★★",anomaly:"★★★★★★"},ke={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"};function m(s){const e=String(s||"").trim().toLowerCase();return ye[e]||"common"}function K(s){return be[m(s)]}function xe(s){return we[m(s)]}function Ce(s){return ke[m(s)]}let x=[],q="";function Se(s){return`${(Number.isFinite(s)?Math.max(0,s):0).toLocaleString("ru-RU",{maximumFractionDigits:2})} кг`}function Le(s){return`${(Number.isFinite(s)?Math.max(0,s):0).toLocaleString("ru-RU",{maximumFractionDigits:1})} см`}function $e(s){const e=s.rarity||"Обычная";return{id:s.id,emoji:"🐟",name:s.fish_name||s.name||"Неизвестная рыба",latinName:"",rarity:m(e),rarityLabel:K(e),rarityStars:xe(e),weight:Se(Number(s.weight||0)),depth:Le(Number(s.length||0)),imageUrl:s.image_url||void 0,trophyId:s.id}}async function Ee(){var s;try{const e=await h("/api/trophies"),t=Array.isArray(e==null?void 0:e.items)?e.items:[];return q=((s=t.find(i=>!!i.is_active))==null?void 0:s.id)||"",x=t.filter(i=>i.id!=="none").map($e),x}catch(e){return console.error("Failed to load trophies:",e),x=[],q="",x}}async function Me(s){if(!s)return!1;try{const e=await h("/api/trophy/select",{method:"POST",body:JSON.stringify({trophy_id:s})});return!!(e!=null&&e.ok)}catch(e){return console.error("Failed to select trophy:",e),!1}}class qe{constructor(){this.isOpen=!1,this.bgBlurTarget=null,this.onSelectCallback=null,this.currentActiveIndex=0,this.items=[],this.sheetStartY=0,this.sheetDragging=!1,this.overlay=this.buildOverlay(),this.sheet=this.overlay.querySelector("#modal-sheet"),this.listEl=this.overlay.querySelector("#modal-fish-list"),document.body.appendChild(this.overlay),this.bindClose()}buildOverlay(){const e=document.createElement("div");return e.id="modal-overlay",e.className="modal-overlay",e.innerHTML=`
      <div id="modal-sheet" class="modal-sheet">
        <div class="modal-handle"></div>
        <p class="modal-title">🏆 Выбор трофея</p>
        <div id="modal-fish-list" class="modal-fish-list"></div>
      </div>
    `,e}buildList(){if(this.items.length===0){this.listEl.innerHTML='<div class="modal-empty">У вас пока нет трофеев</div>';return}this.listEl.innerHTML=this.items.map((e,t)=>{const i=b[e.rarity],a=t===this.currentActiveIndex;return`
        <div
          class="modal-fish-item ${a?"is-selected":""}"
          data-index="${t}"
          style="--accent:${i}"
          role="button"
          tabindex="0"
          aria-label="${e.name}"
        >
          <span class="modal-fish-emoji">${e.imageUrl?`<img src="${e.imageUrl}" alt="${e.name}" class="modal-fish-image" loading="lazy">`:d(e.id)}</span>
          <div class="modal-fish-info">
            <div class="modal-fish-name">${e.name}</div>
            <div class="modal-fish-rarity" style="color:${i}">${e.rarityStars} ${e.rarityLabel}</div>
            <div class="modal-fish-stats">⚖️ ${e.weight} · 📏 ${e.depth}</div>
          </div>
          ${a?'<span class="modal-check">✓</span>':""}
        </div>
      `}).join(""),this.listEl.querySelectorAll(".modal-fish-item").forEach(e=>{e.addEventListener("click",()=>{const t=parseInt(e.dataset.index??"0",10);this.select(t)})})}open(e,t){this.isOpen||(this.currentActiveIndex=e,this.bgBlurTarget=t??null,this.buildList(),this.overlay.style.display="flex",requestAnimationFrame(()=>{this.overlay.classList.add("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter="blur(4px)")}),this.isOpen=!0,l.haptic("medium"))}close(){this.isOpen&&(this.overlay.classList.remove("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter=""),setTimeout(()=>{this.overlay.style.display="none"},420),this.isOpen=!1)}onSelect(e){this.onSelectCallback=e}setItems(e){this.items=[...e],this.currentActiveIndex=Math.max(0,Math.min(this.currentActiveIndex,this.items.length-1))}async select(e){var a;this.currentActiveIndex=e;const t=this.items[e],i=t!=null&&t.trophyId?await Me(t.trophyId):!0;if(l.haptic(i?"medium":"error"),!i){alert("Не удалось выбрать трофей. Попробуйте еще раз.");return}(a=this.onSelectCallback)==null||a.call(this,e),this.close()}bindClose(){this.overlay.addEventListener("click",t=>{t.target===this.overlay&&this.close()});const e=this.sheet;e.addEventListener("touchstart",t=>{this.sheetStartY=t.touches[0].clientY,this.sheetDragging=!0},{passive:!0}),e.addEventListener("touchmove",t=>{if(!this.sheetDragging)return;const i=t.touches[0].clientY-this.sheetStartY;i>0&&(e.style.transform=`translateY(${i*.55}px)`,e.style.transition="none")},{passive:!0}),e.addEventListener("touchend",t=>{if(!this.sheetDragging)return;const i=t.changedTouches[0].clientY-this.sheetStartY;e.style.transform="",e.style.transition="",i>80&&this.close(),this.sheetDragging=!1},{passive:!0})}get fish(){return this.items}}class Ie{constructor(e,t){this.activeId="home",this.buttons=new Map,this.screens=new Map,this.onChangeCallbacks=[],this.el=this.build(),e.appendChild(this.el),P.forEach(i=>{const a=t.querySelector(`#screen-${i.id}`);a&&this.screens.set(i.id,a)}),this.screens.forEach((i,a)=>{a==="home"?(i.style.display="flex",i.style.opacity="1",i.style.pointerEvents="all"):(i.style.display="none",i.style.opacity="0")})}build(){const e=document.createElement("nav");return e.id="tab-bar",e.className="tab-bar",e.setAttribute("role","tablist"),P.forEach(t=>{const i=document.createElement("button");i.id=`tab-${t.id}`,i.className=`tab-btn ${t.id==="home"?"is-active":""}`,i.setAttribute("role","tab"),i.setAttribute("aria-selected",t.id==="home"?"true":"false"),i.dataset.tab=t.id,i.innerHTML=`
        <span class="tab-icon" aria-hidden="true">${d(t.id)}</span>
        <span class="tab-label">${t.label}</span>
      `,i.addEventListener("click",()=>this.switchTo(t.id)),i.addEventListener("pointerdown",()=>{i.style.transform="scale(0.92)"}),i.addEventListener("pointerup",()=>{i.style.transform=""}),i.addEventListener("pointerleave",()=>{i.style.transform=""}),e.appendChild(i),this.buttons.set(t.id,i)}),e}switchTo(e){if(e===this.activeId)return;l.haptic("selection");const t=this.activeId,i=this.screens.get(t),a=this.screens.get(e);!i||!a||(M.transitionTo(i,a),this.buttons.forEach((r,n)=>{const o=n===e;r.classList.toggle("is-active",o),r.setAttribute("aria-selected",String(o))}),this.activeId=e,this.onChangeCallbacks.forEach(r=>r(t,e)))}onChange(e){this.onChangeCallbacks.push(e)}getActive(){return this.activeId}}let I=[],Q=0;async function ee(){try{const s=await h("/api/book?limit=500");s&&s.ok&&(Q=Number(s.total_all||0),I=s.items.map(e=>({id:e.image_file||"fishdef",emoji:"🐟",name:e.name,latinName:e.name,rarity:Te(e.rarity),glowColor:_e(e.rarity),depth:`${e.min_weight}-${e.max_weight} кг`,habitat:e.locations,length:`${e.min_length}-${e.max_length} см`,description:e.lore||`Рыба вида ${e.name}.`,funFact:e.baits?`Лучше ловится на: ${e.baits}.`:"Информации пока нет.",chapter:"Общий атлас",isCaught:e.is_caught,imageUrl:e.image_url||void 0})))}catch(s){console.error("Failed to load encyclopedia:",s)}}function Te(s){return m(s)}function _e(s){return Ce(s)}const Ae={common:"★★ Обычная",rare:"★★★ Редкая",legendary:"★★★★★ Легендарная",aquarium:"★★★★ Аквариумная",mythical:"★★★★★ Мифическая",anomaly:"★★★★★★ Аномалия"};class Be{constructor(){this.entries=[],this.filtered=[],this.index=0,this.loading=!1,this.pageFlip=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-book",e.className="screen book-screen",e.setAttribute("role","main"),e.innerHTML=`
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
    `,e}async init(){this.bookContainer=this.el.querySelector(".book-wrap"),this.stBook=this.el.querySelector("#st-book"),this.searchInput=this.el.querySelector("#book-search-input"),this.prevBtn=this.el.querySelector("#book-prev-btn"),this.nextBtn=this.el.querySelector("#book-next-btn"),this.counterCur=this.el.querySelector("#counter-cur"),this.counterTot=this.el.querySelector("#counter-tot"),this.loading=!0,await ee(),this.entries=[...I],this.filtered=[...I],this.loading=!1,this.renderPages(),this.bindEvents()}buildPage(e){const t=e.isCaught??!1;return`
      <div class="my-page ${t?"":"not-caught"}">
        <div class="ph-content parchment">
          <div class="ph-chapter">${e.chapter}</div>
          <div class="ph-chapter-divider"><span class="ph-chapter-rule">✦ · ✦</span></div>

          <div class="ph-fish-block">
            <div class="ph-fish-emoji" style="--glow: ${t?e.glowColor:"#555"}; filter: ${t?"none":"grayscale(100%) contrast(50%) brightness(70%)"}">
              ${e.imageUrl?`<img src="${e.imageUrl}" alt="${e.name}" class="ph-fish-image" loading="lazy">`:d(e.id)}
            </div>
          </div>
          
          <div class="ph-fish-name">${e.name.toUpperCase()}</div>
          <div class="ph-fish-latin">${e.latinName}</div>
          
          <div class="ph-rarity-wrap">
            <div class="ph-rarity" style="color:${t?e.glowColor:"#777"}; border-color:${t?e.glowColor:"#777"}55">
              ${t?Ae[e.rarity]:'<span style="color: #ff4d4d; font-weight: bold;">НЕ СЛОВЛЕНА</span>'}
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
    `}renderPages(){this.pageFlip&&(this.pageFlip.destroy(),this.pageFlip=null);const e=this.el.querySelector("#st-book");e&&e.remove(),this.stBook=document.createElement("div"),this.stBook.id="st-book",this.stBook.className="st-book",this.bookContainer.appendChild(this.stBook),this.filtered.length!==0&&(this.stBook.innerHTML=this.filtered.map(t=>this.buildPage(t)).join(""),window.St&&window.St.PageFlip&&(this.pageFlip=new window.St.PageFlip(this.stBook,{width:320,height:480,size:"stretch",minWidth:280,maxWidth:600,minHeight:400,maxHeight:900,usePortrait:!0,showCover:!1,useMouseEvents:!1,maxShadowOpacity:.7,mobileScrollSupport:!1,flippingTime:600}),this.pageFlip.loadFromHTML(this.stBook.querySelectorAll(".my-page")),this.pageFlip.on("flip",t=>{this.index=t.data,this.syncUI()}),this.pageFlip.on("changeState",t=>{t.data==="flipping"&&l.haptic("light")})),this.index=0,this.syncUI())}syncUI(){this.counterCur.textContent=String(this.index+1),this.counterTot.textContent=String(Math.max(this.filtered.length,Q||0)),this.prevBtn.disabled=this.index===0,this.nextBtn.disabled=this.index===this.filtered.length-1}applySearch(e){const t=e.trim().toLowerCase();this.filtered=t?this.entries.filter(i=>i.name.toLowerCase().includes(t)||i.latinName.toLowerCase().includes(t)||i.description.toLowerCase().includes(t)):[...this.entries],this.filtered.length||(this.filtered=[...this.entries]),this.renderPages()}bindEvents(){this.prevBtn.addEventListener("click",()=>{this.pageFlip&&this.index>0&&this.pageFlip.flipPrev()}),this.nextBtn.addEventListener("click",()=>{this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext()});let e=0,t=0;this.bookContainer.addEventListener("pointerdown",a=>{e=a.clientX,t=a.clientY},{passive:!0}),this.bookContainer.addEventListener("pointerup",a=>{if(this.pageFlip&&this.pageFlip.getState()!=="read")return;const r=a.clientX,n=a.clientY,o=e-r,c=Math.abs(t-n);Math.abs(o)>40&&c<60&&(o>0?this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext():this.pageFlip&&this.index>0&&this.pageFlip.flipPrev())},{passive:!0}),this.searchInput.addEventListener("keydown",a=>{a.key==="Enter"&&(a.preventDefault(),this.applySearch(this.searchInput.value))});const i=this.el.querySelector("#book-search-btn");i&&i.addEventListener("click",()=>{this.applySearch(this.searchInput.value)})}}class He{constructor(){this.items=[],this.loading=!1,this.mode="view",this.selectedIds=new Set,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-shop",e.className="screen shop-screen",e.setAttribute("role","main"),e.innerHTML=`
      <div class="shop-header">
        <h1 class="page-title">ЛАВКА</h1>
        <button id="shop-sell-btn" class="glass-btn primary-btn" style="display:none;">${d("shop")} ПРОДАТЬ</button>
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
    `,e}async init(){await this.loadInventory(),this.bindEvents()}bindEvents(){const e=this.el.querySelector("#shop-sell-btn");e&&e.addEventListener("click",()=>{l.haptic("light"),this.showSellModal()});const t=this.el.querySelector("#cancel-select-btn");t&&t.addEventListener("click",()=>{l.haptic("light"),this.mode="view",this.selectedIds.clear(),this.renderInventory()});const i=this.el.querySelector("#confirm-sell-btn");i&&i.addEventListener("click",()=>{this.selectedIds.size!==0&&(l.haptic("medium"),this.sellBulk({ids:Array.from(this.selectedIds)}))})}showSellModal(){const e=`
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
    `,document.body.appendChild(t),t.addEventListener("click",i=>{i.target===t&&document.body.removeChild(t)}),t.querySelectorAll(".sell-opt-btn").forEach(i=>{i.addEventListener("click",()=>{const a=i.dataset.cat;l.haptic("light"),document.body.removeChild(t),a?this.sellBulk({category:a}):i.classList.contains("select-mode-btn")&&(this.mode="select",this.selectedIds.clear(),this.renderInventory())})})}async sellBulk(e){try{const t=await h("/api/sell-bulk",{method:"POST",body:JSON.stringify(e)});t&&t.earned_coins!==void 0&&(l.haptic("success"),alert(`Успешно продано!
Получено: ${t.earned_coins} 🪙
Опыт: ${t.earned_xp} ✨`),this.mode="view",this.selectedIds.clear(),await this.loadInventory())}catch{alert("Ошибка при продаже")}}async loadInventory(){this.loading=!0;try{const e=await h("/api/inventory/grouped");this.items=(e==null?void 0:e.items)||[],this.renderInventory()}catch(e){console.error("Failed to load inventory:",e),this.renderError()}finally{this.loading=!1}}renderInventory(){const e=this.el.querySelector("#shop-content"),t=this.el.querySelector("#shop-sell-btn"),i=this.el.querySelector("#shop-select-actions");if(this.mode==="select"?(t.style.display="none",i.style.display="flex",this.updateSelectCount()):(t.style.display=this.items.length>0?"block":"none",i.style.display="none"),this.items.length===0){e.innerHTML=`
        <div class="shop-empty">
          <div class="shop-soon-icon">${d("shop")}</div>
          <h3>Садок пуст</h3>
          <p>Поймайте рыбу, чтобы она появилась здесь.</p>
        </div>
      `;return}e.innerHTML=`
      <div class="inventory-grid">
        ${this.items.map((a,r)=>{const n=m(a.rarity),o=b[n]||"#ccc",c=a.ids.every($=>this.selectedIds.has($)),u=a.ids.some($=>this.selectedIds.has($))&&!c;let p="";return this.mode==="select"&&(c?p="is-selected":u&&(p="is-partial")),`
            <div class="inv-card glass ${p}" style="--card-color: ${o}" data-idx="${r}">
              ${a.count>1?`<div class="inv-badge">${a.count}x</div>`:""}
              <div class="inv-img-wrap">
                <img src="${a.image_url}" alt="${a.name}" loading="lazy">
              </div>
              <div class="inv-details">
                <div class="inv-name">${a.name}</div>
                <div class="inv-rarity" style="color:${o}">${K(a.rarity)}</div>
                <div class="inv-weight">⚖️ ${a.total_weight.toFixed(2)} кг</div>
              </div>
              <div class="inv-price">
                <span>${a.price}</span> 🪙
              </div>
              ${this.mode==="select"?`<div class="select-indicator">${c?"✅":""}</div>`:""}
            </div>
          `}).join("")}
      </div>
    `,e.querySelectorAll(".inv-card").forEach(a=>{a.addEventListener("click",()=>{if(this.mode!=="select")return;l.haptic("light");const r=parseInt(a.dataset.idx||"0"),n=this.items[r];n.ids.every(c=>this.selectedIds.has(c))?n.ids.forEach(c=>this.selectedIds.delete(c)):n.ids.forEach(c=>this.selectedIds.add(c)),this.renderInventory()})})}updateSelectCount(){const e=this.el.querySelector("#select-count");e&&(e.textContent=this.selectedIds.size.toString())}renderError(){const e=this.el.querySelector("#shop-content");e.innerHTML=`
      <div class="shop-empty">
        <div class="shop-soon-icon">❌</div>
        <h3>Ошибка загрузки</h3>
        <p>Не удалось загрузить инвентарь. Попробуйте позже.</p>
      </div>
    `}}const N=["guild_beer","guild_rich","guild_cthulhu","guild_king"],O=["#00b4d8","#f4a82e","#9b5de5","#ff6b6b","#a5a5a5","#4d908e"];let v=[],f=null,A=!1;async function w(){try{const s=await h("/api/guilds");if(s&&s.ok){const e=s.my_clan;if(e&&e.id){const t=Array.isArray(e.requests)?e.requests:[],i={id:String(e.id),name:e.name,avatar:e.avatar_emoji||"🔱",borderColor:e.color_hex||"#00b4d8",type:e.access_type||"open",level:e.level||1,members:[],requests:t.map(a=>({requestId:String(a.request_id??a.id??""),userId:String(a.user_id??a.requester_user_id??""),name:String(a.username||"user"),level:Number(a.level||0),userAvatar:String(a.user_avatar||"👤")})),upgradeProgress:[],capacity:20,minLevel:e.min_level||0};v=[i],f=i.id,A=e.role==="leader"}else v=(s.items||[]).map(t=>({id:String(t.id),name:t.name,avatar:t.avatar_emoji||"🔱",borderColor:t.color_hex||"#00b4d8",type:t.access_type||"open",level:t.level||1,members:[],requests:[],upgradeProgress:[],capacity:20,minLevel:t.min_level||0})),f=null}}catch(s){console.error("Failed to load clans:",s)}}async function Fe(s){try{const e=await h("/api/guilds/create",{method:"POST",body:JSON.stringify({name:s.name,avatar:s.avatar,color:s.borderColor,type:s.type,min_level:s.minLevel})});if(e&&e.ok)return await w(),v.find(t=>t.id===String(e.clan_id))||null;e&&!e.ok&&(e.reason==="not_enough_coins"?alert(`Недостаточно монет для создания артели! Нужно ${e.cost.toLocaleString()} 🪙`):alert(`Ошибка создания: ${e.reason||"неизвестная ошибка"}`))}catch(e){console.error("Failed to create guild:",e)}return null}async function Pe(s){const e=v.find(t=>t.id===s);if(!e)return!1;try{const t=e.type==="open"?"/api/guilds/join":"/api/guilds/apply",i=await h(t,{method:"POST",body:JSON.stringify({guild_id:s})});if(i&&i.ok)return e.type==="open"&&(f=e.id),!0;i&&!i.ok&&(i.reason==="level_too_low"?alert(`Ваш уровень слишком низок! Требуется уровень ${i.required}`):i.reason==="not_enough_coins"?alert(`Недостаточно монет! Требуется ${i.cost} 🪙`):alert(`Ошибка: ${i.reason||i.error||"неизвестная ошибка"}`))}catch(t){console.error("Failed to join guild:",t)}return!1}async function D(s,e){try{const t=await h("/api/guilds/request/respond",{method:"POST",body:JSON.stringify({request_id:s,action:e})});if(t&&t.ok)return await w(),!0;t&&!t.ok&&alert(`Ошибка обработки заявки: ${t.error||"неизвестная ошибка"}`)}catch(t){console.error("Failed to respond to clan request:",t)}return!1}async function Ne(){if(f)try{const s=await h("/api/guilds/leave",{method:"POST"});s&&s.ok&&(f=null,A=!1,await w())}catch(s){console.error("Failed to leave guild:",s)}}class Oe{constructor(){this.view="list",this.loading=!1,this.newGuildName="",this.selectedAvatar=N[0],this.selectedColor=O[0],this.selectedType="open",this.selectedMinLevel=0,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-guilds",e.className="screen guilds-screen",e.setAttribute("role","main"),e}async init(){this.loading=!0,this.render(),await w(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}f?this.renderManage():this.view==="create"?this.renderCreate():this.renderList()}renderList(){var e;this.el.innerHTML=`
      <h1 class="page-title">АРТЕЛИ</h1>
      <div class="guilds-header">
        <button class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>
      </div>
      <div class="guild-list">
        ${v.map(t=>`
          <div class="guild-card glass" data-id="${t.id}">
            <div class="guild-avatar" style="--border-color: ${t.borderColor}">${d(t.avatar)}</div>
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
    `,(e=this.el.querySelector("#guild-create-trigger"))==null||e.addEventListener("click",()=>{this.view="create",this.render(),l.haptic("medium")}),this.el.querySelectorAll(".guild-card").forEach(t=>{var i;(i=t.querySelector("button"))==null||i.addEventListener("click",async a=>{a.stopPropagation();const r=t.getAttribute("data-id");if(await Pe(r)){l.haptic("heavy");const o=v.find(c=>c.id===r);(o==null?void 0:o.type)==="invite"?alert("Заявка отправлена!"):await this.init()}else l.haptic("error"),alert("Не удалось вступить в артель.")})})}renderCreate(){var i,a;this.el.innerHTML=`
      <h1 class="page-title">НОВАЯ АРТЕЛЬ</h1>
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14 симв.)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" placeholder="Введите название..." value="${this.newGuildName}">
        </div>

        <div class="form-group">
          <label class="form-label">Выберите герб</label>
          <div class="avatar-grid">
            ${N.map(r=>`
              <div class="avatar-opt ${this.selectedAvatar===r?"is-selected":""}" data-val="${r}">${d(r)}</div>
            `).join("")}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Цвет каемки</label>
          <div class="color-row">
            ${O.map(r=>`
              <div class="color-opt ${this.selectedColor===r?"is-selected":""}" data-val="${r}" style="background:${r}"></div>
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
    `;const e=this.el.querySelector("#guild-name-input");e.addEventListener("input",()=>{this.newGuildName=e.value}),this.el.querySelectorAll(".avatar-opt").forEach(r=>{r.addEventListener("click",()=>{this.selectedAvatar=r.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".color-opt").forEach(r=>{r.addEventListener("click",()=>{this.selectedColor=r.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".type-opt").forEach(r=>{r.addEventListener("click",()=>{this.selectedType=r.getAttribute("data-val"),this.render()})});const t=this.el.querySelector("#min-level-slider");t&&t.addEventListener("input",()=>{this.selectedMinLevel=parseInt(t.value);const r=this.el.querySelector("#min-level-label");r&&(r.textContent=`Минимальный уровень: ${this.selectedMinLevel}`)}),(i=this.el.querySelector("#create-cancel"))==null||i.addEventListener("click",()=>{this.view="list",this.render()}),(a=this.el.querySelector("#create-confirm"))==null||a.addEventListener("click",async()=>{if(this.newGuildName.trim().length<3){alert("Слишком короткое название!");return}await Fe({name:this.newGuildName,avatar:this.selectedAvatar,borderColor:this.selectedColor,type:this.selectedType,minLevel:this.selectedMinLevel})?(l.haptic("heavy"),await this.init()):(l.haptic("error"),alert("Ошибка при создании артели."))})}renderManage(){var i;const e=v.find(a=>a.id===f),t=A;this.el.innerHTML=`
      <h1 class="page-title">${e.name.toUpperCase()}</h1>
      
      <div class="glass" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
         <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${e.borderColor}">${d(e.avatar)}</div>
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
          ${e.upgradeProgress.map((a,r)=>`
            <div class="upgrade-item">
              <div class="upgrade-main">
                <div class="upgrade-labels">
                  <span>${a.item}</span>
                  <span>${a.current}/${a.required}</span>
                </div>
                <div class="upgrade-bar">
                  <div class="upgrade-fill" style="width: ${a.current/a.required*100}%"></div>
                </div>
              </div>
              <button class="donate-btn" data-idx="${r}">ВКЛАД</button>
            </div>
          `).join("")}
        </div>
      </div>

      ${t&&e.requests.length>0?`
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки на вступление</p>
          <div class="requests-list">
            ${e.requests.map(a=>`
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${a.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${a.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${a.level}</div>
                </div>
                <div class="req-btns">
                  <button class="req-btn req-btn--no" data-id="${a.requestId}" style="width:28px; height:28px; font-size:12px;">✕</button>
                  <button class="req-btn req-btn--yes" data-id="${a.requestId}" style="width:28px; height:28px; font-size:12px;">✓</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `:""}

      <div class="guild-actions">
        <button class="guild-leave-btn" id="btn-leave" style="height:44px; font-size:11px;">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `,(i=this.el.querySelector("#btn-leave"))==null||i.addEventListener("click",()=>{confirm("Вы уверены, что хотите покинуть артель?")&&(Ne(),l.haptic("medium"),this.render())}),this.el.querySelectorAll(".donate-btn").forEach(a=>{a.addEventListener("click",()=>{const r=parseInt(a.getAttribute("data-idx"),10),n=e.upgradeProgress[r];n.current=Math.min(n.required,n.current+Math.floor(Math.random()*5)+1),l.haptic("selection"),this.render()})}),this.el.querySelectorAll(".req-btn--yes").forEach(a=>{a.addEventListener("click",async()=>{const r=a.getAttribute("data-id");if(!r)return;const n=await D(r,"accept");l.haptic(n?"heavy":"error"),n&&await this.init()})}),this.el.querySelectorAll(".req-btn--no").forEach(a=>{a.addEventListener("click",async()=>{const r=a.getAttribute("data-id");if(!r)return;const n=await D(r,"decline");l.haptic(n?"medium":"error"),n&&await this.init()})})}}let T=[],y=[];async function C(){try{const s=await h("/api/friends");if(s&&s.ok){const e=Array.isArray(s.items)?s.items:[],t=Array.isArray(s.incoming_requests)?s.incoming_requests:[];T=e.map(i=>({id:String(i.user_id),name:i.username,level:Number(i.level||0),avatar:"👤",online:!!i.is_online,xp:Number(i.xp||0)})),y=t.map(i=>({id:String(i.request_id||i.id),name:String(i.username||"user"),level:Number(i.level||0),avatar:"👤"}))}}catch(s){console.error("Failed to load friends:",s)}}async function De(s){try{const e=await h("/api/friends/add",{method:"POST",body:JSON.stringify({username:s})});return!!(e!=null&&e.ok)}catch(e){return console.error("Failed to send friend request:",e),!1}}async function ze(s){return te(s,"accept")}async function Ve(s){return te(s,"decline")}async function te(s,e){try{const t=await h("/api/friends/request/respond",{method:"POST",body:JSON.stringify({request_id:s,action:e})});if(t!=null&&t.ok)return await C(),!0}catch(t){console.error("Failed to respond friend request:",t)}return!1}class Re{constructor(){this.currentView="list",this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-friends",e.className="screen friends-screen",e.setAttribute("role","main"),e}async init(){this.loading=!0,this.render(),await C(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}this.currentView==="requests"?this.renderRequests():this.renderList()}renderList(){var e,t;this.el.innerHTML=`
      <div class="friends-header-row">
        <h1 class="page-title" style="margin-bottom:0">ДРУЗЬЯ</h1>
        <div class="friends-notif-btn" id="btn-show-requests">
          <span>🔔</span>
          ${y.length>0?`<div class="notif-badge">${y.length}</div>`:""}
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
        ${T.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:20px;">У вас пока нет друзей</p>':""}
        ${T.map(i=>`
          <div class="friend-card glass">
            <div class="friend-avatar">${i.avatar}</div>
            <div class="friend-info">
              <div class="friend-name">${i.name}</div>
              <div class="friend-meta">Ур. ${i.level} · ${i.online?'<span style="color:#2ecc71">Online</span>':'<span style="opacity:0.5">Offline</span>'}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `,(e=this.el.querySelector("#btn-show-requests"))==null||e.addEventListener("click",()=>{this.currentView="requests",this.render(),l.haptic("medium")}),(t=this.el.querySelector("#btn-add-search"))==null||t.addEventListener("click",async()=>{const i=this.el.querySelector("#friend-search");i.value.trim()&&(await De(i.value.trim())?(alert("Запрос отправлен!"),i.value="",l.haptic("light"),await C(),this.render()):(l.haptic("error"),alert("Не удалось отправить заявку.")))})}renderRequests(){var e;this.el.innerHTML=`
      <div class="friends-header-row">
        <button class="back-btn" id="btn-back-list">←</button>
        <h1 class="page-title" style="margin:0; flex:1">ЗАЯВКИ</h1>
      </div>

      <div class="requests-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${y.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:40px;">Нет новых заявок</p>':""}
        ${y.map(t=>`
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
    `,(e=this.el.querySelector("#btn-back-list"))==null||e.addEventListener("click",()=>{this.currentView="list",this.render(),l.haptic("light")}),this.el.querySelectorAll(".req-btn--yes").forEach(t=>{t.addEventListener("click",async()=>{const i=t.getAttribute("data-id"),a=await ze(i);l.haptic(a?"heavy":"error"),this.render()})}),this.el.querySelectorAll(".req-btn--no").forEach(t=>{t.addEventListener("click",async()=>{const i=t.getAttribute("data-id"),a=await Ve(i);l.haptic(a?"medium":"error"),this.render()})})}}class je{constructor(e){this.particles=[],this.W=0,this.H=0,this.rafId=0,this.COUNT=60,this.canvas=e,this.ctx=e.getContext("2d"),this.resize(),window.addEventListener("resize",this.resize.bind(this));for(let t=0;t<this.COUNT;t++){const i=this.createParticle();i.y=Math.random()*this.H,i.life=Math.floor(Math.random()*i.maxLife*.5),this.particles.push(i)}this.loop()}resize(){this.W=this.canvas.width=this.canvas.offsetWidth,this.H=this.canvas.height=this.canvas.offsetHeight}createParticle(){const e=Math.random()<.28;return{x:Math.random()*this.W,y:this.H+12,r:e?1.5+Math.random()*2:1.2+Math.random()*3,vx:(Math.random()-.5)*.4,vy:-(.2+Math.random()*.55),alpha:0,alphaTarget:.12+Math.random()*.4,life:0,maxLife:180+Math.random()*420,isSediment:e,wobble:Math.random()*Math.PI*2,wobbleSpeed:.02+Math.random()*.03}}drawBubble(e){const t=this.ctx;e.wobble+=e.wobbleSpeed;const i=e.x+Math.sin(e.wobble)*1.8;t.save(),t.globalAlpha=e.alpha,t.strokeStyle="rgba(160,220,255,0.65)",t.lineWidth=.7,t.beginPath(),t.arc(i,e.y,e.r,0,Math.PI*2),t.stroke(),t.fillStyle="rgba(255,255,255,0.35)",t.beginPath(),t.arc(i-e.r*.28,e.y-e.r*.28,e.r*.38,0,Math.PI*2),t.fill(),t.restore()}drawSediment(e){const t=this.ctx;t.save(),t.globalAlpha=e.alpha,t.fillStyle="rgba(180,150,90,0.7)",t.beginPath(),t.ellipse(e.x,e.y,e.r*1.6,e.r*.55,e.wobble,0,Math.PI*2),t.fill(),t.restore()}updateParticle(e){e.x+=e.vx,e.y+=e.vy,e.life+=1;const t=40,i=50;return e.life<t?e.alpha=e.life/t*e.alphaTarget:e.life>e.maxLife-i?e.alpha=(e.maxLife-e.life)/i*e.alphaTarget:e.alpha=e.alphaTarget,e.life<e.maxLife&&e.y>-10}loop(){this.ctx.clearRect(0,0,this.W,this.H);for(let e=0;e<this.particles.length;e++){const t=this.particles[e];this.updateParticle(t)?t.isSediment?this.drawSediment(t):this.drawBubble(t):this.particles[e]=this.createParticle()}this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId),window.removeEventListener("resize",this.resize.bind(this))}}const Ue=oe();ne();const Xe=document.getElementById("particles-canvas");new je(Xe);const Ye=document.getElementById("bg-parallax");new ve(Ye);const B=new ue;B.updateFromTelegram();const Ge=document.getElementById("profile-mount");Ge.appendChild(B.getElement());async function We(){try{await Promise.all([C(),w(),ee()]),console.log("Initial data loaded")}catch(s){console.error("Failed to load initial data:",s)}}We();const Ze=document.getElementById("carousel-mount"),S=new ge(Ze,2),g=document.getElementById("screens-wrap"),H=new qe;async function Je(){const s=await Ee();S.setFishData(s,q),H.setItems(S.getItems())}Je();H.onSelect(s=>{S.goTo(s)});he(()=>{H.open(S.getActiveIndex(),g)});const ie=new Be,z=ie.getElement(),V=document.getElementById("screen-book");V?V.replaceWith(z):g.appendChild(z);const se=new He,R=se.getElement(),j=document.getElementById("screen-shop");j?j.replaceWith(R):g.appendChild(R);const ae=new Oe,U=ae.getElement(),X=document.getElementById("screen-guilds");X?X.replaceWith(U):g.appendChild(U);const _=new Re,Y=_.getElement(),G=document.getElementById("screen-friends");G?G.replaceWith(Y):g.appendChild(Y);let W=!1,Z=!1,J=!1,E=!1;const Ke=document.getElementById("tabbar-mount"),Qe=new Ie(Ke,g);Qe.onChange((s,e)=>{e==="book"&&!W&&(ie.init(),W=!0),e==="shop"&&!Z&&(se.init(),Z=!0),e==="guilds"&&!J&&(ae.init(),J=!0),e==="friends"&&!E?(_.init(),E=!0):e==="friends"&&E&&_.init()});de();setTimeout(()=>B.animateProgress(0),2e3);ce(Ue,1600);
