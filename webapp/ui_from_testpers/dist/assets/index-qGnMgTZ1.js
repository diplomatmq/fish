(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))i(s);new MutationObserver(s=>{for(const a of s)if(a.type==="childList")for(const n of a.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&i(n)}).observe(document,{childList:!0,subtree:!0});function e(s){const a={};return s.integrity&&(a.integrity=s.integrity),s.referrerPolicy&&(a.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?a.credentials="include":s.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function i(s){if(s.ep)return;s.ep=!0;const a=e(s);fetch(s.href,a)}})();class at{constructor(){var t;this.tg=((t=window.Telegram)==null?void 0:t.WebApp)??null,this.tg&&(this.tg.ready(),this.tg.expand(),this.tg.setHeaderColor("#0a1628"),this.tg.setBackgroundColor("#0a1628"))}haptic(t){var e;(e=this.tg)!=null&&e.HapticFeedback&&(t==="selection"?this.tg.HapticFeedback.selectionChanged():t==="success"||t==="error"?this.tg.HapticFeedback.notificationOccurred(t):t==="impact"?this.tg.HapticFeedback.impactOccurred("medium"):["light","medium","heavy"].includes(t)&&this.tg.HapticFeedback.impactOccurred(t))}getUserName(){var t,e,i;return((i=(e=(t=this.tg)==null?void 0:t.initDataUnsafe)==null?void 0:e.user)==null?void 0:i.first_name)??null}getUserTag(){var e,i,s;const t=(s=(i=(e=this.tg)==null?void 0:e.initDataUnsafe)==null?void 0:i.user)==null?void 0:s.username;return t?`@${t}`:null}}const o=new at,B={home:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="currentColor" stroke-width="2" />
      <path d="M12 3V9" stroke="#ff6b6b" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="12" cy="12" r="3" fill="#ff6b6b" stroke="currentColor" stroke-width="1"/>
      <path d="M12 15L12 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `,adventures:`
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M16 7C16 7 15 3 12 3C9 3 8 7 8 7C8 10 11 12 11 15C11 17 9 18 7 18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="7" cy="19" r="1" fill="currentColor"/>
      <path d="M16 7L18 9L21 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
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
      <path d="M12 15C15.3137 15 18 12.3137 18 9C18 5.68629 15.3137 3 12 3C8.68629 3 6 5.68629 6 9C6 12.3137 8.68629 15 12 15Z" stroke="currentColor" stroke-width="2"/>
      <path d="M8 9H16M12 15V21M9 21H15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `};function d(r,t=""){const e=B[r]||B.home;return t?e.replace("<svg",`<svg class="${t}"`):e}function rt(){const r=document.getElementById("app");return r.innerHTML=`
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

      <!-- ADVENTURES -->
      ${z("adventures","🗺️","Приключения",`Мини-игры и приключения
скоро появятся!`)}

      <!-- FRIENDS -->
      <section id="screen-friends" class="screen" role="main" aria-label="Друзья"></section>

      <!-- GUILDS (ARTELS) -->
      <section id="screen-guilds" class="screen" role="main" aria-label="Артели"></section>

      <!-- BOOK -->
      ${z("book","📖","Книга рыбака",`Здесь появится ваш
рыболовный журнал`)}

    </div>

    <!-- Tab bar injected by TabBar -->
    <div id="tabbar-mount"></div>

    <!-- Modal injected by TrophyModal -->
  `,r}function z(r,t,e,i){return`
    <section id="screen-${r}" class="screen screen--empty" role="main" aria-label="${e}">
      <h1 class="page-title">${e.toUpperCase()}</h1>
      <div class="glass empty-content">
        <div class="empty-icon" aria-hidden="true">${d(r)}</div>
        <p class="empty-text">${i.replace(`
`,"<br>")}</p>
      </div>
    </section>
  `}function nt(){const r=document.createElement("div");return r.id="entry-overlay",r.className="entry-overlay",r.innerHTML=`
    <div class="entry-logo" aria-hidden="true">🌊</div>
    <p class="entry-title">ПОДВОДНЫЙ МИР</p>
    <p class="entry-subtitle">Загрузка…</p>
  `,document.body.appendChild(r),r}function lt(r,t=1600){setTimeout(()=>{r.style.transition="opacity 0.6s ease",r.style.opacity="0",setTimeout(()=>r.remove(),700)},t)}function ot(){const r=document.getElementById("btn-achievements"),t=document.getElementById("btn-rating");[r,t].forEach(e=>{e&&e.addEventListener("click",()=>{o.haptic("light"),e.classList.remove("bounce"),e.offsetWidth,e.classList.add("bounce"),e.addEventListener("animationend",()=>e.classList.remove("bounce"),{once:!0})})})}function ct(r){const t=document.getElementById("select-trophy-btn");t&&(t.addEventListener("click",r),t.addEventListener("pointerdown",()=>{t.style.transform="scale(0.96)"}),t.addEventListener("pointerup",()=>{t.style.transform=""}),t.addEventListener("pointerleave",()=>{t.style.transform=""}))}const O=[{id:"home",icon:"🧭",label:"Главная"},{id:"adventures",icon:"📦",label:"Мини-игры"},{id:"friends",icon:"👤",label:"Друзья"},{id:"guilds",icon:"🔱",label:"Артели"},{id:"book",icon:"📖",label:"Книга"}],w={name:"АКВАМАН_01",tag:"@aquaman01",level:15,xp:7200,maxXp:1e4,avatar:"🤿"},k={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"},dt=()=>{var r,t;return((t=(r=window.Telegram)==null?void 0:r.WebApp)==null?void 0:t.initData)||""};async function h(r,t={}){const i={"Content-Type":"application/json","X-Telegram-Init-Data":dt(),...t.headers||{}},s=await fetch(r,{...t,headers:i});if(!s.ok){const a=await s.json().catch(()=>({error:"Unknown error"}));throw new Error(a.error||`HTTP error! status: ${s.status}`)}return s.json()}class ht{constructor(){this.fillEl=null,this.wobbling=!1,this.profile={...w},this.el=this.build(),this.loadProfile()}async loadProfile(){try{const t=await h("/api/profile");t&&(this.profile.name=t.username||this.profile.name,this.profile.level=t.level||this.profile.level,this.profile.xp=t.xp||this.profile.xp,this.profile.maxXp=1e4,this.profile.tag=`@${t.user_id}`||this.profile.tag,this.updateUI())}catch(t){console.error("Failed to load profile:",t)}}updateUI(){const t=this.el.querySelector("#profile-name"),e=this.el.querySelector("#profile-tag"),i=this.el.querySelector(".level-label"),s=this.el.querySelector(".xp-label");t&&(t.textContent=this.profile.name.toUpperCase()),e&&(e.textContent=this.profile.tag),i&&(i.textContent=`Уровень ${this.profile.level}`),s&&(s.textContent=`${this.profile.xp.toLocaleString("ru")} XP`),this.animateProgress(0)}getElement(){return this.el}build(){const t=w,e=Math.round(t.xp/t.maxXp*100),i=document.createElement("div");i.id="profile-panel",i.className="profile-panel glass",i.innerHTML=`
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
    `;const s=i.querySelector("#porthole-wrap");s.addEventListener("click",()=>this.wobble(s)),s.addEventListener("keydown",n=>{(n.key==="Enter"||n.key===" ")&&this.wobble(s)});const a=i.querySelector("#edit-btn");return a.addEventListener("click",()=>{o.haptic("light"),a.textContent="⏳ Загрузка...",setTimeout(()=>{a.innerHTML="✏️ Редактировать"},1800)}),a.addEventListener("pointerdown",()=>{a.style.transform="scale(0.96)"}),a.addEventListener("pointerup",()=>{a.style.transform=""}),this.fillEl=i.querySelector("#progress-fill"),i}animateProgress(t=200){if(!this.fillEl)return;const e=Math.round(w.xp/w.maxXp*100);this.fillEl.style.width="0%",setTimeout(()=>{this.fillEl.style.width=`${e}%`},t)}wobble(t){this.wobbling||(this.wobbling=!0,o.haptic("light"),t.classList.add("porthole--wobble"),t.addEventListener("animationend",()=>{t.classList.remove("porthole--wobble"),this.wobbling=!1},{once:!0}))}updateFromTelegram(){const t=o.getUserName(),e=o.getUserTag();if(t){const i=this.el.querySelector("#profile-name");i&&(i.textContent=t.toUpperCase())}if(e){const i=this.el.querySelector("#profile-tag");i&&(i.textContent=e)}}}class pt{constructor(t){this.targetX=0,this.targetY=0,this.currentX=0,this.currentY=0,this.rafId=0,this.el=t,this.bindEvents(),this.loop()}bindEvents(){window.addEventListener("mousemove",t=>{this.targetX=(t.clientX/window.innerWidth-.5)*14,this.targetY=(t.clientY/window.innerHeight-.5)*8}),window.addEventListener("deviceorientation",t=>{t.gamma===null||t.beta===null||(this.targetX=Math.max(-12,Math.min(12,t.gamma*.25)),this.targetY=Math.max(-7,Math.min(7,(t.beta-45)*.15)))})}loop(){this.currentX+=(this.targetX-this.currentX)*.06,this.currentY+=(this.targetY-this.currentY)*.06,this.el.style.transform=`scale(1.14) translate(${-this.currentX*.08}%, ${-this.currentY*.06}%)`,this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId)}}class ut{constructor(t){this.intervalId=0,this.container=t,this.start()}spawnOne(){if(document.hidden)return;const t=document.createElement("div");t.className="trophy-bubble";const e=4+Math.random()*9,i=20+Math.random()*60,s=2.8+Math.random()*2.8;t.style.cssText=`
      width:${e}px; height:${e}px;
      left:${i}%; bottom:${8+Math.random()*12}%;
      animation-duration:${s}s;
      animation-delay:${Math.random()*.3}s;
    `,this.container.appendChild(t),setTimeout(()=>t.remove(),(s+.5)*1e3)}start(){this.intervalId=window.setInterval(()=>this.spawnOne(),380)}stop(){clearInterval(this.intervalId),this.container.querySelectorAll(".trophy-bubble").forEach(t=>t.remove())}restart(){this.stop(),this.start()}}const M=class M{static transitionTo(t,e){this.pendingTimeout&&(clearTimeout(this.pendingTimeout),this.pendingTimeout=0);const i=++this.transitionToken;t.style.transition="opacity 0.35s ease, transform 0.35s ease",t.style.opacity="0",t.style.transform="scale(0.93)",t.style.pointerEvents="none",e.style.transition="none",e.style.opacity="0",e.style.transform="scale(1.06)",e.style.display="flex",e.style.pointerEvents="none",this.pendingTimeout=window.setTimeout(()=>{i===this.transitionToken&&(t.style.display="none",t.style.opacity="",t.style.transform="",t.style.transition="",requestAnimationFrame(()=>{i===this.transitionToken&&(e.style.transition="opacity 0.38s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.38s cubic-bezier(0.25,0.46,0.45,0.94)",e.style.opacity="1",e.style.transform="scale(1)",e.style.pointerEvents="all")}))},300)}};M.transitionToken=0,M.pendingTimeout=0;let E=M;const vt={id:"no-trophy",emoji:"🐟",name:"Нет трофеев",latinName:"",rarity:"common",rarityLabel:"Обычная",rarityStars:"",weight:"0 кг",depth:"0 см"};class ft{constructor(t,e=2){this.cards=[],this.bubbleSpawner=null,this.fishData=[],this.startX=0,this.isDragging=!1,this.onChangeCallback=null,this.container=t,this.activeIndex=e,this.build(),this.bindSwipe(),this.update()}build(){this.container.innerHTML="",this.cards=[];const t=document.createElement("div");t.className="carousel__bubbles",this.container.appendChild(t),this.bubbleSpawner=new ut(t);const e=document.createElement("div");if(e.className="carousel__track",this.container.appendChild(e),this.fishData.length===0){e.innerHTML=`
        <div class="carousel__card is-active" style="opacity:1; transform:translateX(0) scale(1);">
          <div class="carousel__card-inner" style="--accent:${k.common}">
            <div class="carousel__fish-emoji">${d("trophy")}</div>
            <div class="carousel__rarity" style="color:${k.common}">ТРОФЕЕВ ПОКА НЕТ</div>
            <div class="carousel__fish-name">Поймай рыбу и создай трофей</div>
            <div class="carousel__fish-latin">Карточки появятся автоматически</div>
          </div>
        </div>
      `;return}this.fishData.forEach((i,s)=>{const a=document.createElement("div");a.className="carousel__card",a.dataset.index=String(s);const n=k[i.rarity];a.innerHTML=`
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
      `,e.appendChild(a),this.cards.push(a)})}update(){var e;if(this.cards.length===0)return;this.cards.forEach((i,s)=>{const a=s-this.activeIndex,n=Math.abs(a);i.classList.remove("is-active","is-side","is-far");let l,c,p,u;switch(n){case 0:l=0,c=1,p=1,u=10,i.classList.add("is-active");break;case 1:l=a*148,c=.78,p=.6,u=5,i.classList.add("is-side");break;case 2:l=a*185,c=.62,p=.28,u=2,i.classList.add("is-far");break;default:l=a*200,c=.5,p=0,u=0}i.style.transform=`translateX(${l}px) scale(${c})`,i.style.opacity=String(p),i.style.zIndex=String(u)});const t=this.fishData[this.activeIndex];t&&((e=this.onChangeCallback)==null||e.call(this,t))}next(){this.fishData.length!==0&&this.activeIndex<this.fishData.length-1&&(this.activeIndex++,this.update(),o.haptic("light"))}prev(){this.fishData.length!==0&&this.activeIndex>0&&(this.activeIndex--,this.update(),o.haptic("light"))}goTo(t){this.fishData.length!==0&&(this.activeIndex=Math.max(0,Math.min(t,this.fishData.length-1)),this.update())}getActiveIndex(){return this.activeIndex}getActiveFish(){return this.fishData[this.activeIndex]||vt}getItems(){return this.fishData}setFishData(t,e){if(this.fishData=[...t],e){const i=this.fishData.findIndex(s=>s.trophyId===e||s.id===e);this.activeIndex=i>=0?i:0}else this.activeIndex=this.fishData.length?Math.max(0,Math.min(this.activeIndex,this.fishData.length-1)):0;this.build(),this.update()}onChange(t){this.onChangeCallback=t}bindSwipe(){const t=this.container;t.addEventListener("touchstart",e=>{this.startX=e.touches[0].clientX,this.isDragging=!0},{passive:!0}),t.addEventListener("touchend",e=>{if(!this.isDragging)return;const i=e.changedTouches[0].clientX-this.startX;this.handleSwipeEnd(i),this.isDragging=!1},{passive:!0}),t.addEventListener("mousedown",e=>{this.startX=e.clientX,this.isDragging=!0,e.preventDefault()}),window.addEventListener("mouseup",e=>{if(!this.isDragging)return;const i=e.clientX-this.startX;this.handleSwipeEnd(i),this.isDragging=!1})}handleSwipeEnd(t){t<-42?this.next():t>42&&this.prev()}}const mt={обычная:"common",редкая:"rare",легендарная:"legendary",аквариумная:"aquarium",мифическая:"mythical",аномалия:"anomaly"},gt={common:"Обычная",rare:"Редкая",legendary:"Легендарная",aquarium:"Аквариумная",mythical:"Мифическая",anomaly:"Аномалия"},yt={common:"★★",rare:"★★★",legendary:"★★★★★",aquarium:"★★★★",mythical:"★★★★★",anomaly:"★★★★★★"},bt={common:"#90e0ef",rare:"#00b4d8",legendary:"#f4a82e",aquarium:"#4cc9f0",mythical:"#ef476f",anomaly:"#7b2cbf"};function y(r){const t=String(r||"").trim().toLowerCase();return mt[t]||"common"}function wt(r){return gt[y(r)]}function xt(r){return yt[y(r)]}function kt(r){return bt[y(r)]}let x=[],$="";function Ct(r){return`${(Number.isFinite(r)?Math.max(0,r):0).toLocaleString("ru-RU",{maximumFractionDigits:2})} кг`}function St(r){return`${(Number.isFinite(r)?Math.max(0,r):0).toLocaleString("ru-RU",{maximumFractionDigits:1})} см`}function Mt(r){const t=r.rarity||"Обычная";return{id:r.id,emoji:"🐟",name:r.fish_name||r.name||"Неизвестная рыба",latinName:"",rarity:y(t),rarityLabel:wt(t),rarityStars:xt(t),weight:Ct(Number(r.weight||0)),depth:St(Number(r.length||0)),imageUrl:r.image_url||void 0,trophyId:r.id}}async function Lt(){var r;try{const t=await h("/api/trophies"),e=Array.isArray(t==null?void 0:t.items)?t.items:[];return $=((r=e.find(i=>!!i.is_active))==null?void 0:r.id)||"",x=e.filter(i=>i.id!=="none").map(Mt),x}catch(t){return console.error("Failed to load trophies:",t),x=[],$="",x}}async function Et(r){if(!r)return!1;try{const t=await h("/api/trophy/select",{method:"POST",body:JSON.stringify({trophy_id:r})});return!!(t!=null&&t.ok)}catch(t){return console.error("Failed to select trophy:",t),!1}}class $t{constructor(){this.isOpen=!1,this.bgBlurTarget=null,this.onSelectCallback=null,this.currentActiveIndex=0,this.items=[],this.sheetStartY=0,this.sheetDragging=!1,this.overlay=this.buildOverlay(),this.sheet=this.overlay.querySelector("#modal-sheet"),this.listEl=this.overlay.querySelector("#modal-fish-list"),document.body.appendChild(this.overlay),this.bindClose()}buildOverlay(){const t=document.createElement("div");return t.id="modal-overlay",t.className="modal-overlay",t.innerHTML=`
      <div id="modal-sheet" class="modal-sheet">
        <div class="modal-handle"></div>
        <p class="modal-title">🏆 Выбор трофея</p>
        <div id="modal-fish-list" class="modal-fish-list"></div>
      </div>
    `,t}buildList(){if(this.items.length===0){this.listEl.innerHTML='<div class="modal-empty">У вас пока нет трофеев</div>';return}this.listEl.innerHTML=this.items.map((t,e)=>{const i=k[t.rarity],s=e===this.currentActiveIndex;return`
        <div
          class="modal-fish-item ${s?"is-selected":""}"
          data-index="${e}"
          style="--accent:${i}"
          role="button"
          tabindex="0"
          aria-label="${t.name}"
        >
          <span class="modal-fish-emoji">${t.imageUrl?`<img src="${t.imageUrl}" alt="${t.name}" class="modal-fish-image" loading="lazy">`:d(t.id)}</span>
          <div class="modal-fish-info">
            <div class="modal-fish-name">${t.name}</div>
            <div class="modal-fish-rarity" style="color:${i}">${t.rarityStars} ${t.rarityLabel}</div>
            <div class="modal-fish-stats">⚖️ ${t.weight} · 📏 ${t.depth}</div>
          </div>
          ${s?'<span class="modal-check">✓</span>':""}
        </div>
      `}).join(""),this.listEl.querySelectorAll(".modal-fish-item").forEach(t=>{t.addEventListener("click",()=>{const e=parseInt(t.dataset.index??"0",10);this.select(e)})})}open(t,e){this.isOpen||(this.currentActiveIndex=t,this.bgBlurTarget=e??null,this.buildList(),this.overlay.style.display="flex",requestAnimationFrame(()=>{this.overlay.classList.add("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter="blur(4px)")}),this.isOpen=!0,o.haptic("medium"))}close(){this.isOpen&&(this.overlay.classList.remove("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter=""),setTimeout(()=>{this.overlay.style.display="none"},420),this.isOpen=!1)}onSelect(t){this.onSelectCallback=t}setItems(t){this.items=[...t],this.currentActiveIndex=Math.max(0,Math.min(this.currentActiveIndex,this.items.length-1))}async select(t){var s;this.currentActiveIndex=t;const e=this.items[t],i=e!=null&&e.trophyId?await Et(e.trophyId):!0;if(o.haptic(i?"medium":"error"),!i){alert("Не удалось выбрать трофей. Попробуйте еще раз.");return}(s=this.onSelectCallback)==null||s.call(this,t),this.close()}bindClose(){this.overlay.addEventListener("click",e=>{e.target===this.overlay&&this.close()});const t=this.sheet;t.addEventListener("touchstart",e=>{this.sheetStartY=e.touches[0].clientY,this.sheetDragging=!0},{passive:!0}),t.addEventListener("touchmove",e=>{if(!this.sheetDragging)return;const i=e.touches[0].clientY-this.sheetStartY;i>0&&(t.style.transform=`translateY(${i*.55}px)`,t.style.transition="none")},{passive:!0}),t.addEventListener("touchend",e=>{if(!this.sheetDragging)return;const i=e.changedTouches[0].clientY-this.sheetStartY;t.style.transform="",t.style.transition="",i>80&&this.close(),this.sheetDragging=!1},{passive:!0})}get fish(){return this.items}}class Tt{constructor(t,e){this.activeId="home",this.buttons=new Map,this.screens=new Map,this.onChangeCallbacks=[],this.el=this.build(),t.appendChild(this.el),O.forEach(i=>{const s=e.querySelector(`#screen-${i.id}`);s&&this.screens.set(i.id,s)}),this.screens.forEach((i,s)=>{s==="home"?(i.style.display="flex",i.style.opacity="1",i.style.pointerEvents="all"):(i.style.display="none",i.style.opacity="0")})}build(){const t=document.createElement("nav");return t.id="tab-bar",t.className="tab-bar",t.setAttribute("role","tablist"),O.forEach(e=>{const i=document.createElement("button");i.id=`tab-${e.id}`,i.className=`tab-btn ${e.id==="home"?"is-active":""}`,i.setAttribute("role","tab"),i.setAttribute("aria-selected",e.id==="home"?"true":"false"),i.dataset.tab=e.id,i.innerHTML=`
        <span class="tab-icon" aria-hidden="true">${d(e.id)}</span>
        <span class="tab-label">${e.label}</span>
      `,i.addEventListener("click",()=>this.switchTo(e.id)),i.addEventListener("pointerdown",()=>{i.style.transform="scale(0.92)"}),i.addEventListener("pointerup",()=>{i.style.transform=""}),i.addEventListener("pointerleave",()=>{i.style.transform=""}),t.appendChild(i),this.buttons.set(e.id,i)}),t}switchTo(t){if(t===this.activeId)return;o.haptic("selection");const e=this.activeId,i=this.screens.get(e),s=this.screens.get(t);!i||!s||(E.transitionTo(i,s),this.buttons.forEach((a,n)=>{const l=n===t;a.classList.toggle("is-active",l),a.setAttribute("aria-selected",String(l))}),this.activeId=t,this.onChangeCallbacks.forEach(a=>a(e,t)))}onChange(t){this.onChangeCallbacks.push(t)}getActive(){return this.activeId}}let T=[],K=0;async function Q(){try{const r=await h("/api/book?limit=500");r&&r.ok&&(K=Number(r.total_all||0),T=r.items.map(t=>({id:t.image_file||"fishdef",emoji:"🐟",name:t.name,latinName:t.name,rarity:qt(t.rarity),glowColor:It(t.rarity),depth:`${t.min_weight}-${t.max_weight} кг`,habitat:t.locations,length:`${t.min_length}-${t.max_length} см`,description:t.lore||`Рыба вида ${t.name}.`,funFact:t.baits?`Лучше ловится на: ${t.baits}.`:"Информации пока нет.",chapter:"Общий атлас",isCaught:t.is_caught,imageUrl:t.image_url||void 0})))}catch(r){console.error("Failed to load encyclopedia:",r)}}function qt(r){return y(r)}function It(r){return kt(r)}const At={common:"★★ Обычная",rare:"★★★ Редкая",legendary:"★★★★★ Легендарная",aquarium:"★★★★ Аквариумная",mythical:"★★★★★ Мифическая",anomaly:"★★★★★★ Аномалия"};class _t{constructor(){this.entries=[],this.filtered=[],this.index=0,this.loading=!1,this.pageFlip=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-book",t.className="screen book-screen",t.setAttribute("role","main"),t.innerHTML=`
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
    `,t}async init(){this.bookContainer=this.el.querySelector(".book-wrap"),this.stBook=this.el.querySelector("#st-book"),this.searchInput=this.el.querySelector("#book-search-input"),this.prevBtn=this.el.querySelector("#book-prev-btn"),this.nextBtn=this.el.querySelector("#book-next-btn"),this.counterCur=this.el.querySelector("#counter-cur"),this.counterTot=this.el.querySelector("#counter-tot"),this.loading=!0,await Q(),this.entries=[...T],this.filtered=[...T],this.loading=!1,this.renderPages(),this.bindEvents()}buildPage(t){const e=t.isCaught??!1;return`
      <div class="my-page ${e?"":"not-caught"}">
        <div class="ph-content parchment">
          <div class="ph-chapter">${t.chapter}</div>
          <div class="ph-chapter-divider"><span class="ph-chapter-rule">✦ · ✦</span></div>

          <div class="ph-fish-block">
            <div class="ph-fish-emoji" style="--glow: ${e?t.glowColor:"#555"}; filter: ${e?"none":"grayscale(100%) contrast(50%) brightness(70%)"}">
              ${t.imageUrl?`<img src="${t.imageUrl}" alt="${t.name}" class="ph-fish-image" loading="lazy">`:d(t.id)}
            </div>
          </div>
          
          <div class="ph-fish-name">${t.name.toUpperCase()}</div>
          <div class="ph-fish-latin">${t.latinName}</div>
          
          <div class="ph-rarity-wrap">
            <div class="ph-rarity" style="color:${e?t.glowColor:"#777"}; border-color:${e?t.glowColor:"#777"}55">
              ${e?At[t.rarity]:'<span style="color: #ff4d4d; font-weight: bold;">НЕ СЛОВЛЕНА</span>'}
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
    `}renderPages(){this.pageFlip&&(this.pageFlip.destroy(),this.pageFlip=null);const t=this.el.querySelector("#st-book");t&&t.remove(),this.stBook=document.createElement("div"),this.stBook.id="st-book",this.stBook.className="st-book",this.bookContainer.appendChild(this.stBook),this.filtered.length!==0&&(this.stBook.innerHTML=this.filtered.map(e=>this.buildPage(e)).join(""),window.St&&window.St.PageFlip&&(this.pageFlip=new window.St.PageFlip(this.stBook,{width:320,height:480,size:"stretch",minWidth:280,maxWidth:600,minHeight:400,maxHeight:900,usePortrait:!0,showCover:!1,useMouseEvents:!1,maxShadowOpacity:.7,mobileScrollSupport:!1,flippingTime:600}),this.pageFlip.loadFromHTML(this.stBook.querySelectorAll(".my-page")),this.pageFlip.on("flip",e=>{this.index=e.data,this.syncUI()}),this.pageFlip.on("changeState",e=>{e.data==="flipping"&&o.haptic("light")})),this.index=0,this.syncUI())}syncUI(){this.counterCur.textContent=String(this.index+1),this.counterTot.textContent=String(Math.max(this.filtered.length,K||0)),this.prevBtn.disabled=this.index===0,this.nextBtn.disabled=this.index===this.filtered.length-1}applySearch(t){const e=t.trim().toLowerCase();this.filtered=e?this.entries.filter(i=>i.name.toLowerCase().includes(e)||i.latinName.toLowerCase().includes(e)||i.description.toLowerCase().includes(e)):[...this.entries],this.filtered.length||(this.filtered=[...this.entries]),this.renderPages()}bindEvents(){this.prevBtn.addEventListener("click",()=>{this.pageFlip&&this.index>0&&this.pageFlip.flipPrev()}),this.nextBtn.addEventListener("click",()=>{this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext()});let t=0,e=0;this.bookContainer.addEventListener("pointerdown",s=>{t=s.clientX,e=s.clientY},{passive:!0}),this.bookContainer.addEventListener("pointerup",s=>{if(this.pageFlip&&this.pageFlip.getState()!=="read")return;const a=s.clientX,n=s.clientY,l=t-a,c=Math.abs(e-n);Math.abs(l)>40&&c<60&&(l>0?this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext():this.pageFlip&&this.index>0&&this.pageFlip.flipPrev())},{passive:!0}),this.searchInput.addEventListener("keydown",s=>{s.key==="Enter"&&(s.preventDefault(),this.applySearch(this.searchInput.value))});const i=this.el.querySelector("#book-search-btn");i&&i.addEventListener("click",()=>{this.applySearch(this.searchInput.value)})}}class Pt{constructor(t,e){this.isPlaying=!1,this.isGameOver=!1,this.distance=0,this.coins=0,this.speed=3,this.animationId=0,this.player={x:80,y:0,targetY:0,size:40},this.angler={x:-20,y:0,size:80,baseY:0,time:0},this.obstacles=[],this.collectibles=[],this.particles=[],this.lastTime=0,this.spawnTimer=0,this.onExit=e,this.el=document.createElement("div"),this.el.className="game-container",this.el.innerHTML=`
      <div class="adv-hud">
        <div class="adv-stat">ДИСТАНЦИЯ: <span id="adv-dist">0</span> м</div>
        <div class="adv-title">УКЛОНЯЙСЯ ОТ УДИЛЬЩИКА!</div>
        <div class="adv-stat">МОНЕТЫ: <span id="adv-coins">0</span></div>
      </div>
      
      <canvas id="runner-canvas" class="runner-canvas"></canvas>
      
      <div id="adv-menu" class="adv-overlay">
        <h2>ПОБЕГ ОТ УДИЛЬЩИКА</h2>
        <p>Свайпай вверх и вниз, чтобы уклоняться от препятствий и собирать монеты!</p>
        <button id="adv-start-btn" class="adv-btn">ИГРАТЬ</button>
        <button id="adv-exit-btn" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>

      <div id="adv-gameover" class="adv-overlay" style="display:none;">
        <h2>СЪЕДЕН!</h2>
        <p>Дистанция: <span id="adv-final-dist">0</span> м</p>
        <p>Собрано монет: <span id="adv-final-coins">0</span></p>
        <button id="adv-restart-btn" class="adv-btn">ПОВТОРИТЬ</button>
        <button id="adv-exit-btn2" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>
    `,t.appendChild(this.el),this.init()}destroy(){this.isPlaying=!1,cancelAnimationFrame(this.animationId),this.el.remove()}init(){const t=this.el;this.canvas=t.querySelector("#runner-canvas"),this.ctx=this.canvas.getContext("2d"),this.menuOverlay=t.querySelector("#adv-menu"),this.gameOverOverlay=t.querySelector("#adv-gameover"),this.distanceEl=t.querySelector("#adv-dist"),this.coinsEl=t.querySelector("#adv-coins"),t.querySelector("#adv-start-btn").addEventListener("click",()=>this.startGame()),t.querySelector("#adv-restart-btn").addEventListener("click",()=>this.startGame()),t.querySelector("#adv-exit-btn").addEventListener("click",()=>this.onExit()),t.querySelector("#adv-exit-btn2").addEventListener("click",()=>this.onExit());const e=()=>{this.canvas.width=window.innerWidth,this.canvas.height=t.clientHeight||window.innerHeight,this.isPlaying||this.drawStaticBackground()};window.addEventListener("resize",e),setTimeout(e,100);let i=0;this.canvas.addEventListener("touchstart",a=>{i=a.touches[0].clientY}),this.canvas.addEventListener("touchmove",a=>{a.preventDefault();const n=a.touches[0].clientY,l=n-i;this.player.targetY+=l*1.5,this.player.targetY<50&&(this.player.targetY=50),this.player.targetY>this.canvas.height-50&&(this.player.targetY=this.canvas.height-50),i=n},{passive:!1});let s=!1;this.canvas.addEventListener("mousedown",a=>{s=!0,i=a.clientY}),window.addEventListener("mouseup",()=>s=!1),this.canvas.addEventListener("mousemove",a=>{if(!s)return;const n=a.clientY-i;this.player.targetY+=n*1.5,this.player.targetY<50&&(this.player.targetY=50),this.player.targetY>this.canvas.height-50&&(this.player.targetY=this.canvas.height-50),i=a.clientY})}startGame(){o.haptic("impact"),this.isPlaying=!0,this.isGameOver=!1,this.distance=0,this.coins=0,this.speed=3,this.obstacles=[],this.collectibles=[],this.particles=[],this.player.y=this.canvas.height/2,this.player.targetY=this.player.y,this.angler.y=this.canvas.height/2,this.menuOverlay.style.display="none",this.gameOverOverlay.style.display="none",cancelAnimationFrame(this.animationId),this.lastTime=performance.now(),this.gameLoop(this.lastTime)}spawnObstacle(){const t=Math.random()>.5?"🪨":"🦑",e=50+Math.random()*30;this.obstacles.push({x:this.canvas.width+50,y:50+Math.random()*(this.canvas.height-100),size:e,type:t,wobble:Math.random()*Math.PI*2})}spawnCollectible(){this.collectibles.push({x:this.canvas.width+50,y:50+Math.random()*(this.canvas.height-100),size:30,type:"💎"})}spawnParticles(t,e,i){for(let s=0;s<10;s++)this.particles.push({x:t,y:e,vx:(Math.random()-.5)*10,vy:(Math.random()-.5)*10,life:1,color:i})}endGame(){this.isPlaying=!1,this.isGameOver=!0,o.haptic("heavy"),this.ctx.fillStyle="rgba(0, 0, 0, 0.5)",this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height),this.el.querySelector("#adv-final-dist").textContent=Math.floor(this.distance).toString(),this.el.querySelector("#adv-final-coins").textContent=this.coins.toString(),this.gameOverOverlay.style.display="flex"}gameLoop(t){if(!this.isPlaying)return;const e=(t-this.lastTime)/1e3;this.lastTime=t,this.distance+=this.speed*e*10,this.speed+=e*.05,this.distanceEl.textContent=Math.floor(this.distance).toString(),this.spawnTimer+=e,this.spawnTimer>1.2*(3/this.speed)&&(this.spawnTimer=0,this.spawnObstacle(),Math.random()>.4&&this.spawnCollectible()),this.player.y+=(this.player.targetY-this.player.y)*.1,this.angler.time+=e*5,this.angler.baseY+=(this.player.y-this.angler.baseY)*.02,this.angler.y=this.angler.baseY+Math.sin(this.angler.time)*20,this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height),Math.random()>.9&&this.particles.push({x:this.canvas.width+10,y:Math.random()*this.canvas.height,vx:-this.speed*.5,vy:-1-Math.random()*2,life:2,color:"rgba(255, 255, 255, 0.2)",isBubble:!0});for(let s=this.particles.length-1;s>=0;s--){const a=this.particles[s];if(a.x+=a.vx,a.y+=a.vy,a.isBubble?a.life-=e*.2:a.life-=e*1.5,a.life<=0){this.particles.splice(s,1);continue}this.ctx.globalAlpha=a.life,this.ctx.fillStyle=a.color,this.ctx.beginPath(),this.ctx.arc(a.x,a.y,a.isBubble?4:3,0,Math.PI*2),this.ctx.fill(),this.ctx.globalAlpha=1}this.ctx.font="30px Arial",this.ctx.textAlign="center",this.ctx.textBaseline="middle";for(let s=this.collectibles.length-1;s>=0;s--){const a=this.collectibles[s];if(a.x-=this.speed,Math.hypot(a.x-this.player.x,a.y-this.player.y)<this.player.size/2+a.size/2){this.coins++,this.coinsEl.textContent=this.coins.toString(),this.spawnParticles(a.x,a.y,"#00b4d8"),this.collectibles.splice(s,1),o.haptic("light");continue}if(a.x<-50){this.collectibles.splice(s,1);continue}this.ctx.shadowColor="#00b4d8",this.ctx.shadowBlur=10,this.ctx.fillText(a.type,a.x,a.y+Math.sin(t/200+a.x)*5),this.ctx.shadowBlur=0}for(let s=this.obstacles.length-1;s>=0;s--){const a=this.obstacles[s];a.x-=this.speed,a.wobble+=e*3;const n=a.type==="🦑"?a.y+Math.sin(a.wobble)*15:a.y;if(Math.hypot(a.x-this.player.x,n-this.player.y)<this.player.size/2+a.size*.35){this.endGame();return}if(a.x<-100){this.obstacles.splice(s,1);continue}this.ctx.font=`${a.size}px Arial`,this.ctx.fillText(a.type,a.x,n)}this.ctx.font=`${this.player.size}px Arial`,this.ctx.shadowColor="#00b4d8",this.ctx.shadowBlur=15;const i=(this.player.targetY-this.player.y)*.05;this.ctx.save(),this.ctx.translate(this.player.x,this.player.y),this.ctx.rotate(i),this.ctx.fillText("🦁",0,0),this.ctx.restore(),this.ctx.shadowBlur=0,this.ctx.font=`${this.angler.size}px Arial`,this.ctx.shadowColor="#ff0055",this.ctx.shadowBlur=20,this.ctx.fillText("👾",this.angler.x,this.angler.y),this.ctx.shadowBlur=0,this.ctx.beginPath(),this.ctx.moveTo(this.angler.x+10,this.angler.y-30),this.ctx.lineTo(this.angler.x+30,this.angler.y-40),this.ctx.strokeStyle="#00ffcc",this.ctx.lineWidth=2,this.ctx.stroke(),this.ctx.beginPath(),this.ctx.fillStyle="#00ffcc",this.ctx.arc(this.angler.x+30,this.angler.y-40,4,0,Math.PI*2),this.ctx.fill(),this.animationId=requestAnimationFrame(s=>this.gameLoop(s))}drawStaticBackground(){this.ctx.fillStyle="rgba(0,10,30,0.5)",this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height),this.ctx.font="50px Arial",this.ctx.textAlign="center",this.ctx.fillText("👾",50,this.canvas.height/2),this.ctx.fillText("🦁",150,this.canvas.height/2)}}class Bt{constructor(t,e){this.animationId=0,this.isPlaying=!1,this.grid=[],this.cols=6,this.rows=8,this.player={gx:0,gy:0},this.pearls=0,this.moves=15,this.tileW=60,this.tileH=30,this.onExit=e,this.el=document.createElement("div"),this.el.className="game-container",this.el.innerHTML=`
      <div class="adv-hud">
        <div class="adv-stat">ХОДОВ: <span id="maze-moves">15</span></div>
        <div class="adv-title">НАЙДИ ПУТЬ К СОКРОВИЩУ</div>
        <div class="adv-stat">ЖЕМЧУГ: <span id="maze-pearls">0</span></div>
      </div>
      
      <canvas id="maze-canvas" class="runner-canvas"></canvas>
      
      <div id="maze-menu" class="adv-overlay">
        <h2>МОРСКОЙ НАВИГАТОР</h2>
        <p>Свайпай (Вверх, Вниз, Влево, Вправо) чтобы довести Конька до сундука.</p>
        <p>Опасайся угрей 🐍 и планируй ходы!</p>
        <button id="maze-start-btn" class="adv-btn">ИГРАТЬ</button>
        <button id="maze-exit-btn" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>

      <div id="maze-gameover" class="adv-overlay" style="display:none;">
        <h2 id="maze-result-title">ПОБЕДА!</h2>
        <p>Собрано жемчуга: <span id="maze-final-pearls">0</span></p>
        <button id="maze-restart-btn" class="adv-btn">СЫГРАТЬ ЕЩЕ</button>
        <button id="maze-exit-btn2" class="adv-btn adv-btn-secondary" style="margin-top: 10px;">ВЫХОД</button>
      </div>
    `,t.appendChild(this.el),this.init()}destroy(){this.isPlaying=!1,cancelAnimationFrame(this.animationId),this.el.remove()}init(){const t=this.el;this.canvas=t.querySelector("#maze-canvas"),this.ctx=this.canvas.getContext("2d"),this.overlay=t.querySelector("#maze-gameover"),t.querySelector("#maze-start-btn").addEventListener("click",()=>this.startGame()),t.querySelector("#maze-restart-btn").addEventListener("click",()=>this.startGame()),t.querySelector("#maze-exit-btn").addEventListener("click",()=>this.onExit()),t.querySelector("#maze-exit-btn2").addEventListener("click",()=>this.onExit());const e=()=>{this.canvas.width=window.innerWidth,this.canvas.height=t.clientHeight||window.innerHeight,this.tileW=Math.min(60,this.canvas.width/(this.cols+2)),this.tileH=this.tileW*.55};window.addEventListener("resize",e),setTimeout(e,100);const i=(l,c)=>{this.isPlaying&&(Math.abs(l)>Math.abs(c)&&Math.abs(l)>30?l>0?this.tryMove(1,0):this.tryMove(-1,0):Math.abs(c)>30&&(c>0?this.tryMove(0,1):this.tryMove(0,-1)))};let s=0,a=0;this.canvas.addEventListener("touchstart",l=>{s=l.touches[0].clientX,a=l.touches[0].clientY},{passive:!0}),this.canvas.addEventListener("touchend",l=>{const c=l.changedTouches[0].clientX,p=l.changedTouches[0].clientY;i(c-s,p-a)});let n=!1;this.canvas.addEventListener("mousedown",l=>{n=!0,s=l.clientX,a=l.clientY}),window.addEventListener("mouseup",l=>{n&&(n=!1,i(l.clientX-s,l.clientY-a))}),window.addEventListener("keydown",l=>{if(this.isPlaying)switch(l.key){case"ArrowUp":case"w":case"W":case"Ц":case"ц":this.tryMove(0,-1);break;case"ArrowDown":case"s":case"S":case"Ы":case"ы":this.tryMove(0,1);break;case"ArrowLeft":case"a":case"A":case"Ф":case"ф":this.tryMove(-1,0);break;case"ArrowRight":case"d":case"D":case"В":case"в":this.tryMove(1,0);break}})}generateMaze(){const t=[["start","floor","wall","floor","pearl","floor"],["wall","floor","wall","floor","wall","floor"],["floor","floor","floor","floor","wall","floor"],["floor","wall","wall","floor","eel","floor"],["pearl","floor","wall","floor","floor","floor"],["wall","floor","floor","eel","wall","wall"],["floor","floor","wall","floor","floor","pearl"],["floor","eel","floor","floor","wall","chest"]];this.grid=t}startGame(){o.haptic("impact"),this.generateMaze(),this.player={gx:0,gy:0},this.moves=20,this.pearls=0,this.isPlaying=!0,this.el.querySelector("#maze-menu").style.display="none",this.el.querySelector("#maze-gameover").style.display="none",this.updateUI(),cancelAnimationFrame(this.animationId),this.renderLoop(performance.now())}tryMove(t,e){if(this.moves<=0)return;const i=this.player.gx+t,s=this.player.gy+e;if(i>=0&&i<this.cols&&s>=0&&s<this.rows){const a=this.grid[s][i];if(a==="wall"){o.haptic("error");return}if(this.player.gx=i,this.player.gy=s,this.moves--,o.haptic("light"),a==="pearl")this.pearls++,this.grid[s][i]="floor",o.haptic("success");else if(a==="eel"){this.endGame(!1,"СЪЕДЕН УГРЕМ!");return}else if(a==="chest"){this.endGame(!0,"СОКРОВИЩЕ НАЙДЕНО!");return}this.updateUI(),this.moves<=0&&this.endGame(!1,"ЗАКОНЧИЛИСЬ ХОДЫ!")}}updateUI(){this.el.querySelector("#maze-moves").textContent=this.moves.toString(),this.el.querySelector("#maze-pearls").textContent=this.pearls.toString()}endGame(t,e){this.isPlaying=!1,o.haptic(t?"success":"heavy"),this.el.querySelector("#maze-result-title").textContent=e,this.el.querySelector("#maze-final-pearls").textContent=this.pearls.toString(),this.el.querySelector("#maze-gameover").style.display="flex"}renderLoop(t){if(!this.isPlaying)return;this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height),this.ctx.fillStyle="rgba(0,10,25,0.8)",this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height);const e=this.canvas.width/2,i=100;for(let s=0;s<this.rows;s++)for(let a=0;a<this.cols;a++){const n=this.grid[s][a],l=e+(a-s)*this.tileW,c=i+(a+s)*this.tileH;if(this.drawTile(l,c,n,t),this.player.gx===a&&this.player.gy===s){this.ctx.font="34px Arial",this.ctx.textAlign="center",this.ctx.shadowColor="#00f0ff",this.ctx.shadowBlur=15;const p=Math.abs(Math.sin(t/200))*10;this.ctx.fillText("🦑",l,c-15-p),this.ctx.shadowBlur=0,this.ctx.beginPath(),this.ctx.ellipse(l,c,this.tileW,this.tileH,0,0,Math.PI*2);const u=this.ctx.createRadialGradient(l,c,0,l,c,this.tileW);u.addColorStop(0,"rgba(0, 240, 255, 0.4)"),u.addColorStop(1,"rgba(0, 240, 255, 0)"),this.ctx.fillStyle=u,this.ctx.fill()}}this.animationId=requestAnimationFrame(s=>this.renderLoop(s))}drawTile(t,e,i,s){const a=this.tileW,n=this.tileH;this.ctx.beginPath(),this.ctx.moveTo(t,e-n),this.ctx.lineTo(t+a,e),this.ctx.lineTo(t,e+n),this.ctx.lineTo(t-a,e),this.ctx.closePath(),this.ctx.fillStyle=i==="wall"?"#14314c":"#081f33",this.ctx.fill(),this.ctx.strokeStyle="rgba(0,180,216,0.3)",this.ctx.lineWidth=1,this.ctx.stroke(),this.ctx.font="24px Arial",this.ctx.textAlign="center",i==="wall"?(this.ctx.beginPath(),this.ctx.moveTo(t-a,e),this.ctx.lineTo(t,e+n),this.ctx.lineTo(t,e+n-20),this.ctx.lineTo(t-a,e-20),this.ctx.fillStyle="#104d7d",this.ctx.fill(),this.ctx.beginPath(),this.ctx.moveTo(t,e+n),this.ctx.lineTo(t+a,e),this.ctx.lineTo(t+a,e-20),this.ctx.lineTo(t,e+n-20),this.ctx.fillStyle="#0b3558",this.ctx.fill(),this.ctx.beginPath(),this.ctx.moveTo(t,e-n-20),this.ctx.lineTo(t+a,e-20),this.ctx.lineTo(t,e+n-20),this.ctx.lineTo(t-a,e-20),this.ctx.fillStyle="#18649e",this.ctx.fill(),this.ctx.fillText("🪸",t,e-5)):i==="chest"?(this.ctx.shadowColor="#ffe259",this.ctx.shadowBlur=20,this.ctx.fillText("🧰",t,e),this.ctx.shadowBlur=0):i==="pearl"?this.ctx.fillText("⚪",t,e+Math.sin(s/300+t)*5):i==="eel"&&(this.ctx.shadowColor="#ff6b6b",this.ctx.shadowBlur=10,this.ctx.fillText("🐍",t,e),this.ctx.shadowBlur=0)}}class zt{constructor(){this.currentGame=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-adventures",t.className="screen adventures-main-screen",t.setAttribute("role","main"),t.innerHTML=`
      <div class="adv-main-menu" id="adv-main-menu">
        <h1 class="page-title">ПРИКЛЮЧЕНИЯ</h1>
        <div class="adv-cards-wrap">
          
          <div class="adv-game-card" id="card-runner">
            <div class="adv-card-icon">${d("anglerfish")}</div>
            <div class="adv-card-info">
              <h3>Бег от Удильщика</h3>
              <p>Ритмичный 2D раннер на выживание</p>
            </div>
            <div class="adv-soon-label">SOON</div>
          </div>

          <div class="adv-game-card" id="card-maze">
            <div class="adv-card-icon">${d("seahorse")}</div>
            <div class="adv-card-info">
              <h3>Морской Навигатор</h3>
              <p>3D Головоломка-лабиринт</p>
            </div>
            <div class="adv-soon-label">SOON</div>
          </div>

        </div>
      </div>
    `,t}init(){const t=this.el.querySelector("#adv-main-menu");this.el.querySelector("#card-runner button").addEventListener("click",()=>{o.haptic("impact"),t.style.display="none",this.currentGame&&this.currentGame.destroy(),this.currentGame=new Pt(this.el,()=>{this.currentGame.destroy(),this.currentGame=null,t.style.display="flex"})}),this.el.querySelector("#card-maze button").addEventListener("click",()=>{o.haptic("impact"),t.style.display="none",this.currentGame&&this.currentGame.destroy(),this.currentGame=new Bt(this.el,()=>{this.currentGame.destroy(),this.currentGame=null,t.style.display="flex"})})}}const H=["guild_beer","guild_rich","guild_cthulhu","guild_king"],F=["#00b4d8","#f4a82e","#9b5de5","#ff6b6b","#a5a5a5","#4d908e"];let v=[],f=null,A=!1;async function b(){try{const r=await h("/api/guilds");if(r&&r.ok){const t=r.my_clan;if(t&&t.id){const e=Array.isArray(t.requests)?t.requests:[],i={id:String(t.id),name:t.name,avatar:t.avatar_emoji||"🔱",borderColor:t.color_hex||"#00b4d8",type:t.access_type||"open",level:t.level||1,members:[],requests:e.map(s=>({requestId:String(s.request_id??s.id??""),userId:String(s.user_id??s.requester_user_id??""),name:String(s.username||"user"),level:Number(s.level||0),userAvatar:String(s.user_avatar||"👤")})),upgradeProgress:[],capacity:20,minLevel:t.min_level||0};v=[i],f=i.id,A=t.role==="leader"}else v=(r.items||[]).map(e=>({id:String(e.id),name:e.name,avatar:e.avatar_emoji||"🔱",borderColor:e.color_hex||"#00b4d8",type:e.access_type||"open",level:e.level||1,members:[],requests:[],upgradeProgress:[],capacity:20,minLevel:e.min_level||0})),f=null}}catch(r){console.error("Failed to load clans:",r)}}async function Ot(r){try{const t=await h("/api/guilds/create",{method:"POST",body:JSON.stringify({name:r.name,avatar:r.avatar,color:r.borderColor,type:r.type,min_level:r.minLevel})});if(t&&t.ok)return await b(),v.find(e=>e.id===String(t.clan_id))||null;t&&!t.ok&&(t.reason==="not_enough_coins"?alert(`Недостаточно монет для создания артели! Нужно ${t.cost.toLocaleString()} 🪙`):alert(`Ошибка создания: ${t.reason||"неизвестная ошибка"}`))}catch(t){console.error("Failed to create guild:",t)}return null}async function Ht(r){const t=v.find(e=>e.id===r);if(!t)return!1;try{const e=t.type==="open"?"/api/guilds/join":"/api/guilds/apply",i=await h(e,{method:"POST",body:JSON.stringify({guild_id:r})});if(i&&i.ok)return t.type==="open"&&(f=t.id),!0;i&&!i.ok&&(i.reason==="level_too_low"?alert(`Ваш уровень слишком низок! Требуется уровень ${i.required}`):i.reason==="not_enough_coins"?alert(`Недостаточно монет! Требуется ${i.cost} 🪙`):alert(`Ошибка: ${i.reason||i.error||"неизвестная ошибка"}`))}catch(e){console.error("Failed to join guild:",e)}return!1}async function N(r,t){try{const e=await h("/api/guilds/request/respond",{method:"POST",body:JSON.stringify({request_id:r,action:t})});if(e&&e.ok)return await b(),!0;e&&!e.ok&&alert(`Ошибка обработки заявки: ${e.error||"неизвестная ошибка"}`)}catch(e){console.error("Failed to respond to clan request:",e)}return!1}async function Ft(){if(f)try{const r=await h("/api/guilds/leave",{method:"POST"});r&&r.ok&&(f=null,A=!1,await b())}catch(r){console.error("Failed to leave guild:",r)}}class Nt{constructor(){this.view="list",this.loading=!1,this.newGuildName="",this.selectedAvatar=H[0],this.selectedColor=F[0],this.selectedType="open",this.selectedMinLevel=0,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-guilds",t.className="screen guilds-screen",t.setAttribute("role","main"),t}async init(){this.loading=!0,this.render(),await b(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}f?this.renderManage():this.view==="create"?this.renderCreate():this.renderList()}renderList(){var t;this.el.innerHTML=`
      <h1 class="page-title">АРТЕЛИ</h1>
      <div class="guilds-header">
        <button class="guild-create-btn" id="guild-create-trigger">СОЗДАТЬ АРТЕЛЬ</button>
      </div>
      <div class="guild-list">
        ${v.map(e=>`
          <div class="guild-card glass" data-id="${e.id}">
            <div class="guild-avatar" style="--border-color: ${e.borderColor}">${d(e.avatar)}</div>
            <div class="guild-info">
              <div class="guild-name">${e.name}</div>
              <div class="guild-meta">
                <span>⭐ Ур. ${e.level}</span>
                <span>👤 ${e.members.length}/${e.capacity}</span>
                <span>${e.type==="open"?"🔓 Открыто":"🔒 По приглашению"}</span>
                ${e.type==="open"&&e.minLevel>0?`<span style="color: var(--gold)">⬆️ Ур. ${e.minLevel}+</span>`:""}
              </div>
            </div>
            <button class="adv-play-btn" style="padding: 8px 12px; font-size: 9px;">${e.type==="open"?"ВСТУПИТЬ":"ЗАЯВКА"}</button>
          </div>
        `).join("")}
      </div>
    `,(t=this.el.querySelector("#guild-create-trigger"))==null||t.addEventListener("click",()=>{this.view="create",this.render(),o.haptic("medium")}),this.el.querySelectorAll(".guild-card").forEach(e=>{var i;(i=e.querySelector("button"))==null||i.addEventListener("click",async s=>{s.stopPropagation();const a=e.getAttribute("data-id");if(await Ht(a)){o.haptic("heavy");const l=v.find(c=>c.id===a);(l==null?void 0:l.type)==="invite"?alert("Заявка отправлена!"):await this.init()}else o.haptic("error"),alert("Не удалось вступить в артель.")})})}renderCreate(){var i,s;this.el.innerHTML=`
      <h1 class="page-title">НОВАЯ АРТЕЛЬ</h1>
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14 симв.)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" placeholder="Введите название..." value="${this.newGuildName}">
        </div>

        <div class="form-group">
          <label class="form-label">Выберите герб</label>
          <div class="avatar-grid">
            ${H.map(a=>`
              <div class="avatar-opt ${this.selectedAvatar===a?"is-selected":""}" data-val="${a}">${d(a)}</div>
            `).join("")}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Цвет каемки</label>
          <div class="color-row">
            ${F.map(a=>`
              <div class="color-opt ${this.selectedColor===a?"is-selected":""}" data-val="${a}" style="background:${a}"></div>
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
    `;const t=this.el.querySelector("#guild-name-input");t.addEventListener("input",()=>{this.newGuildName=t.value}),this.el.querySelectorAll(".avatar-opt").forEach(a=>{a.addEventListener("click",()=>{this.selectedAvatar=a.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".color-opt").forEach(a=>{a.addEventListener("click",()=>{this.selectedColor=a.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".type-opt").forEach(a=>{a.addEventListener("click",()=>{this.selectedType=a.getAttribute("data-val"),this.render()})});const e=this.el.querySelector("#min-level-slider");e&&e.addEventListener("input",()=>{this.selectedMinLevel=parseInt(e.value);const a=this.el.querySelector("#min-level-label");a&&(a.textContent=`Минимальный уровень: ${this.selectedMinLevel}`)}),(i=this.el.querySelector("#create-cancel"))==null||i.addEventListener("click",()=>{this.view="list",this.render()}),(s=this.el.querySelector("#create-confirm"))==null||s.addEventListener("click",async()=>{if(this.newGuildName.trim().length<3){alert("Слишком короткое название!");return}await Ot({name:this.newGuildName,avatar:this.selectedAvatar,borderColor:this.selectedColor,type:this.selectedType,minLevel:this.selectedMinLevel})?(o.haptic("heavy"),await this.init()):(o.haptic("error"),alert("Ошибка при создании артели."))})}renderManage(){var i;const t=v.find(s=>s.id===f),e=A;this.el.innerHTML=`
      <h1 class="page-title">${t.name.toUpperCase()}</h1>
      
      <div class="glass" style="padding: 12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
         <div class="guild-avatar" style="width:64px; height:64px; font-size:32px; --border-color:${t.borderColor}">${d(t.avatar)}</div>
         <div class="guild-info">
           <div class="guild-name" style="font-size:17px;">Уровень ${t.level}</div>
           <div class="guild-meta" style="font-size:10px;">${t.members.length}/${t.capacity} участников</div>
         </div>
      </div>

      <div class="my-guild-stats">
        <div class="glass stat-box">
          <div class="stat-val">${t.type==="open"?"🔓":"🔒"}</div>
          <div class="stat-lab">Доступ</div>
        </div>
        <div class="glass stat-box">
          <div class="stat-val">⭐</div>
          <div class="stat-lab">Топ 100</div>
        </div>
      </div>

      <div class="glass" style="padding: 12px; margin-bottom: 12px;">
        <p class="form-label" style="margin-bottom: 10px; color: var(--gold); font-size: 10px;">Улучшение до ур. ${t.level+1}</p>
        <div class="upgrade-section">
          ${t.upgradeProgress.map((s,a)=>`
            <div class="upgrade-item">
              <div class="upgrade-main">
                <div class="upgrade-labels">
                  <span>${s.item}</span>
                  <span>${s.current}/${s.required}</span>
                </div>
                <div class="upgrade-bar">
                  <div class="upgrade-fill" style="width: ${s.current/s.required*100}%"></div>
                </div>
              </div>
              <button class="donate-btn" data-idx="${a}">ВКЛАД</button>
            </div>
          `).join("")}
        </div>
      </div>

      ${e&&t.requests.length>0?`
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки на вступление</p>
          <div class="requests-list">
            ${t.requests.map(s=>`
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${s.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${s.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${s.level}</div>
                </div>
                <div class="req-btns">
                  <button class="req-btn req-btn--no" data-id="${s.requestId}" style="width:28px; height:28px; font-size:12px;">✕</button>
                  <button class="req-btn req-btn--yes" data-id="${s.requestId}" style="width:28px; height:28px; font-size:12px;">✓</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `:""}

      <div class="guild-actions">
        <button class="guild-leave-btn" id="btn-leave" style="height:44px; font-size:11px;">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `,(i=this.el.querySelector("#btn-leave"))==null||i.addEventListener("click",()=>{confirm("Вы уверены, что хотите покинуть артель?")&&(Ft(),o.haptic("medium"),this.render())}),this.el.querySelectorAll(".donate-btn").forEach(s=>{s.addEventListener("click",()=>{const a=parseInt(s.getAttribute("data-idx"),10),n=t.upgradeProgress[a];n.current=Math.min(n.required,n.current+Math.floor(Math.random()*5)+1),o.haptic("selection"),this.render()})}),this.el.querySelectorAll(".req-btn--yes").forEach(s=>{s.addEventListener("click",async()=>{const a=s.getAttribute("data-id");if(!a)return;const n=await N(a,"accept");o.haptic(n?"heavy":"error"),n&&await this.init()})}),this.el.querySelectorAll(".req-btn--no").forEach(s=>{s.addEventListener("click",async()=>{const a=s.getAttribute("data-id");if(!a)return;const n=await N(a,"decline");o.haptic(n?"medium":"error"),n&&await this.init()})})}}let q=[],g=[];async function C(){try{const r=await h("/api/friends");if(r&&r.ok){const t=Array.isArray(r.items)?r.items:[],e=Array.isArray(r.incoming_requests)?r.incoming_requests:[];q=t.map(i=>({id:String(i.user_id),name:i.username,level:Number(i.level||0),avatar:"👤",online:!!i.is_online,xp:Number(i.xp||0)})),g=e.map(i=>({id:String(i.request_id||i.id),name:String(i.username||"user"),level:Number(i.level||0),avatar:"👤"}))}}catch(r){console.error("Failed to load friends:",r)}}async function Yt(r){try{const t=await h("/api/friends/add",{method:"POST",body:JSON.stringify({username:r})});return!!(t!=null&&t.ok)}catch(t){return console.error("Failed to send friend request:",t),!1}}async function Gt(r){return tt(r,"accept")}async function Dt(r){return tt(r,"decline")}async function tt(r,t){try{const e=await h("/api/friends/request/respond",{method:"POST",body:JSON.stringify({request_id:r,action:t})});if(e!=null&&e.ok)return await C(),!0}catch(e){console.error("Failed to respond friend request:",e)}return!1}class Rt{constructor(){this.currentView="list",this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const t=document.createElement("section");return t.id="screen-friends",t.className="screen friends-screen",t.setAttribute("role","main"),t}async init(){this.loading=!0,this.render(),await C(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}this.currentView==="requests"?this.renderRequests():this.renderList()}renderList(){var t,e;this.el.innerHTML=`
      <div class="friends-header-row">
        <h1 class="page-title" style="margin-bottom:0">ДРУЗЬЯ</h1>
        <div class="friends-notif-btn" id="btn-show-requests">
          <span>🔔</span>
          ${g.length>0?`<div class="notif-badge">${g.length}</div>`:""}
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
        ${q.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:20px;">У вас пока нет друзей</p>':""}
        ${q.map(i=>`
          <div class="friend-card glass">
            <div class="friend-avatar">${i.avatar}</div>
            <div class="friend-info">
              <div class="friend-name">${i.name}</div>
              <div class="friend-meta">Ур. ${i.level} · ${i.online?'<span style="color:#2ecc71">Online</span>':'<span style="opacity:0.5">Offline</span>'}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `,(t=this.el.querySelector("#btn-show-requests"))==null||t.addEventListener("click",()=>{this.currentView="requests",this.render(),o.haptic("medium")}),(e=this.el.querySelector("#btn-add-search"))==null||e.addEventListener("click",async()=>{const i=this.el.querySelector("#friend-search");i.value.trim()&&(await Yt(i.value.trim())?(alert("Запрос отправлен!"),i.value="",o.haptic("light"),await C(),this.render()):(o.haptic("error"),alert("Не удалось отправить заявку.")))})}renderRequests(){var t;this.el.innerHTML=`
      <div class="friends-header-row">
        <button class="back-btn" id="btn-back-list">←</button>
        <h1 class="page-title" style="margin:0; flex:1">ЗАЯВКИ</h1>
      </div>

      <div class="requests-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${g.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:40px;">Нет новых заявок</p>':""}
        ${g.map(e=>`
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
    `,(t=this.el.querySelector("#btn-back-list"))==null||t.addEventListener("click",()=>{this.currentView="list",this.render(),o.haptic("light")}),this.el.querySelectorAll(".req-btn--yes").forEach(e=>{e.addEventListener("click",async()=>{const i=e.getAttribute("data-id"),s=await Gt(i);o.haptic(s?"heavy":"error"),this.render()})}),this.el.querySelectorAll(".req-btn--no").forEach(e=>{e.addEventListener("click",async()=>{const i=e.getAttribute("data-id"),s=await Dt(i);o.haptic(s?"medium":"error"),this.render()})})}}class Ut{constructor(t){this.particles=[],this.W=0,this.H=0,this.rafId=0,this.COUNT=60,this.canvas=t,this.ctx=t.getContext("2d"),this.resize(),window.addEventListener("resize",this.resize.bind(this));for(let e=0;e<this.COUNT;e++){const i=this.createParticle();i.y=Math.random()*this.H,i.life=Math.floor(Math.random()*i.maxLife*.5),this.particles.push(i)}this.loop()}resize(){this.W=this.canvas.width=this.canvas.offsetWidth,this.H=this.canvas.height=this.canvas.offsetHeight}createParticle(){const t=Math.random()<.28;return{x:Math.random()*this.W,y:this.H+12,r:t?1.5+Math.random()*2:1.2+Math.random()*3,vx:(Math.random()-.5)*.4,vy:-(.2+Math.random()*.55),alpha:0,alphaTarget:.12+Math.random()*.4,life:0,maxLife:180+Math.random()*420,isSediment:t,wobble:Math.random()*Math.PI*2,wobbleSpeed:.02+Math.random()*.03}}drawBubble(t){const e=this.ctx;t.wobble+=t.wobbleSpeed;const i=t.x+Math.sin(t.wobble)*1.8;e.save(),e.globalAlpha=t.alpha,e.strokeStyle="rgba(160,220,255,0.65)",e.lineWidth=.7,e.beginPath(),e.arc(i,t.y,t.r,0,Math.PI*2),e.stroke(),e.fillStyle="rgba(255,255,255,0.35)",e.beginPath(),e.arc(i-t.r*.28,t.y-t.r*.28,t.r*.38,0,Math.PI*2),e.fill(),e.restore()}drawSediment(t){const e=this.ctx;e.save(),e.globalAlpha=t.alpha,e.fillStyle="rgba(180,150,90,0.7)",e.beginPath(),e.ellipse(t.x,t.y,t.r*1.6,t.r*.55,t.wobble,0,Math.PI*2),e.fill(),e.restore()}updateParticle(t){t.x+=t.vx,t.y+=t.vy,t.life+=1;const e=40,i=50;return t.life<e?t.alpha=t.life/e*t.alphaTarget:t.life>t.maxLife-i?t.alpha=(t.maxLife-t.life)/i*t.alphaTarget:t.alpha=t.alphaTarget,t.life<t.maxLife&&t.y>-10}loop(){this.ctx.clearRect(0,0,this.W,this.H);for(let t=0;t<this.particles.length;t++){const e=this.particles[t];this.updateParticle(e)?e.isSediment?this.drawSediment(e):this.drawBubble(e):this.particles[t]=this.createParticle()}this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId),window.removeEventListener("resize",this.resize.bind(this))}}const Vt=nt();rt();const Xt=document.getElementById("particles-canvas");new Ut(Xt);const jt=document.getElementById("bg-parallax");new pt(jt);const _=new ht;_.updateFromTelegram();const Wt=document.getElementById("profile-mount");Wt.appendChild(_.getElement());async function Zt(){try{await Promise.all([C(),b(),Q()]),console.log("Initial data loaded")}catch(r){console.error("Failed to load initial data:",r)}}Zt();const Jt=document.getElementById("carousel-mount"),S=new ft(Jt,2),m=document.getElementById("screens-wrap"),P=new $t;async function Kt(){const r=await Lt();S.setFishData(r,$),P.setItems(S.getItems())}Kt();P.onSelect(r=>{S.goTo(r)});ct(()=>{P.open(S.getActiveIndex(),m)});const et=new _t,Y=et.getElement(),G=document.getElementById("screen-book");G?G.replaceWith(Y):m.appendChild(Y);const it=new zt,D=it.getElement(),R=document.getElementById("screen-adventures");R?R.replaceWith(D):m.appendChild(D);const st=new Nt,U=st.getElement(),V=document.getElementById("screen-guilds");V?V.replaceWith(U):m.appendChild(U);const I=new Rt,X=I.getElement(),j=document.getElementById("screen-friends");j?j.replaceWith(X):m.appendChild(X);let W=!1,Z=!1,J=!1,L=!1;const Qt=document.getElementById("tabbar-mount"),te=new Tt(Qt,m);te.onChange((r,t)=>{t==="book"&&!W&&(et.init(),W=!0),t==="adventures"&&!Z&&(it.init(),Z=!0),t==="guilds"&&!J&&(st.init(),J=!0),t==="friends"&&!L?(I.init(),L=!0):t==="friends"&&L&&I.init()});ot();setTimeout(()=>_.animateProgress(0),2e3);lt(Vt,1600);
