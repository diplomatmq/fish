(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))i(a);new MutationObserver(a=>{for(const s of a)if(s.type==="childList")for(const l of s.addedNodes)l.tagName==="LINK"&&l.rel==="modulepreload"&&i(l)}).observe(document,{childList:!0,subtree:!0});function t(a){const s={};return a.integrity&&(s.integrity=a.integrity),a.referrerPolicy&&(s.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?s.credentials="include":a.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function i(a){if(a.ep)return;a.ep=!0;const s=t(a);fetch(a.href,s)}})();class K{constructor(){var e;this.tg=((e=window.Telegram)==null?void 0:e.WebApp)??null,this.tg&&(this.tg.ready(),this.tg.expand(),this.tg.setHeaderColor("#0a1628"),this.tg.setBackgroundColor("#0a1628"))}haptic(e){var t;(t=this.tg)!=null&&t.HapticFeedback&&(e==="selection"?this.tg.HapticFeedback.selectionChanged():e==="success"||e==="error"?this.tg.HapticFeedback.notificationOccurred(e):e==="impact"?this.tg.HapticFeedback.impactOccurred("medium"):["light","medium","heavy"].includes(e)&&this.tg.HapticFeedback.impactOccurred(e))}getUserName(){var e,t,i;return((i=(t=(e=this.tg)==null?void 0:e.initDataUnsafe)==null?void 0:t.user)==null?void 0:i.first_name)??null}getUserTag(){var t,i,a;const e=(a=(i=(t=this.tg)==null?void 0:t.initDataUnsafe)==null?void 0:i.user)==null?void 0:a.username;return e?`@${e}`:null}}const o=new K,S={home:`
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
  `};function d(r,e=""){const t=S[r]||S.home;return e?t.replace("<svg",`<svg class="${e}"`):t}function J(){const r=document.getElementById("app");return r.innerHTML=`
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
      ${M("adventures","🗺️","Приключения",`Мини-игры и приключения
скоро появятся!`)}

      <!-- FRIENDS -->
      <section id="screen-friends" class="screen" role="main" aria-label="Друзья"></section>

      <!-- GUILDS (ARTELS) -->
      <section id="screen-guilds" class="screen" role="main" aria-label="Артели"></section>

      <!-- BOOK -->
      ${M("book","📖","Книга рыбака",`Здесь появится ваш
рыболовный журнал`)}

    </div>

    <!-- Tab bar injected by TabBar -->
    <div id="tabbar-mount"></div>

    <!-- Modal injected by TrophyModal -->
  `,r}function M(r,e,t,i){return`
    <section id="screen-${r}" class="screen screen--empty" role="main" aria-label="${t}">
      <h1 class="page-title">${t.toUpperCase()}</h1>
      <div class="glass empty-content">
        <div class="empty-icon" aria-hidden="true">${d(r)}</div>
        <p class="empty-text">${i.replace(`
`,"<br>")}</p>
      </div>
    </section>
  `}function Q(){const r=document.createElement("div");return r.id="entry-overlay",r.className="entry-overlay",r.innerHTML=`
    <div class="entry-logo" aria-hidden="true">🌊</div>
    <p class="entry-title">ПОДВОДНЫЙ МИР</p>
    <p class="entry-subtitle">Загрузка…</p>
  `,document.body.appendChild(r),r}function ee(r,e=1600){setTimeout(()=>{r.style.transition="opacity 0.6s ease",r.style.opacity="0",setTimeout(()=>r.remove(),700)},e)}function te(){const r=document.getElementById("btn-achievements"),e=document.getElementById("btn-rating");[r,e].forEach(t=>{t&&t.addEventListener("click",()=>{o.haptic("light"),t.classList.remove("bounce"),t.offsetWidth,t.classList.add("bounce"),t.addEventListener("animationend",()=>t.classList.remove("bounce"),{once:!0})})})}function ie(r){const e=document.getElementById("select-trophy-btn");e&&(e.addEventListener("click",r),e.addEventListener("pointerdown",()=>{e.style.transform="scale(0.96)"}),e.addEventListener("pointerup",()=>{e.style.transform=""}),e.addEventListener("pointerleave",()=>{e.style.transform=""}))}const u=[{id:"lionfish",emoji:"🦁",name:"Рыба-лев",latinName:"Pterois volitans",rarity:"rare",rarityLabel:"Редкая",rarityStars:"★★★",weight:"1.2 кг",depth:"50–80 м"},{id:"clownfish",emoji:"🐠",name:"Рыба-клоун",latinName:"Amphiprioninae",rarity:"common",rarityLabel:"Обычная",rarityStars:"★★",weight:"0.18 кг",depth:"1–15 м"},{id:"anglerfish",emoji:"👾",name:"Чёрный удильщик",latinName:"Melanocetus johnsonii",rarity:"legendary",rarityLabel:"Легендарная",rarityStars:"★★★★★",weight:"5.4 кг",depth:"200–2000 м"},{id:"barracuda",emoji:"🐟",name:"Барракуда",latinName:"Sphyraena barracuda",rarity:"common",rarityLabel:"Обычная",rarityStars:"★★",weight:"0.9 кг",depth:"0–30 м"},{id:"seahorse",emoji:"🦑",name:"Морской конёк",latinName:"Hippocampus",rarity:"rare",rarityLabel:"Редкая",rarityStars:"★★★",weight:"0.08 кг",depth:"1–30 м"},{id:"pufferfish",emoji:"🐡",name:"Рыба-шар",latinName:"Tetraodontidae",rarity:"rare",rarityLabel:"Редкая",rarityStars:"★★★",weight:"0.7 кг",depth:"5–25 м"},{id:"shark",emoji:"🦈",name:"Белая акула",latinName:"Carcharodon carcharias",rarity:"epic",rarityLabel:"Эпическая",rarityStars:"★★★★",weight:"120 кг",depth:"0–250 м"}],E=[{id:"home",icon:"🧭",label:"Главная"},{id:"adventures",icon:"📦",label:"Мини-игры"},{id:"friends",icon:"👤",label:"Друзья"},{id:"guilds",icon:"🔱",label:"Артели"},{id:"book",icon:"📖",label:"Книга"}],y={name:"АКВАМАН_01",tag:"@aquaman01",level:15,xp:7200,maxXp:1e4,avatar:"🤿"},N={common:"#90e0ef",rare:"#00b4d8",epic:"#9b5de5",legendary:"#f4a82e"},se=()=>{var r,e;return((e=(r=window.Telegram)==null?void 0:r.WebApp)==null?void 0:e.initData)||""};async function m(r,e={}){const i={"Content-Type":"application/json","X-Telegram-Init-Data":se(),...e.headers||{}},a=await fetch(r,{...e,headers:i});if(!a.ok){const s=await a.json().catch(()=>({error:"Unknown error"}));throw new Error(s.error||`HTTP error! status: ${a.status}`)}return a.json()}class ae{constructor(){this.fillEl=null,this.wobbling=!1,this.profile={...y},this.el=this.build(),this.loadProfile()}async loadProfile(){try{const e=await m("/api/profile");e&&(this.profile.name=e.username||this.profile.name,this.profile.level=e.level||this.profile.level,this.profile.xp=e.xp||this.profile.xp,this.profile.maxXp=1e4,this.profile.tag=`@${e.user_id}`||this.profile.tag,this.updateUI())}catch(e){console.error("Failed to load profile:",e)}}updateUI(){const e=this.el.querySelector("#profile-name"),t=this.el.querySelector("#profile-tag"),i=this.el.querySelector(".level-label"),a=this.el.querySelector(".xp-label");e&&(e.textContent=this.profile.name.toUpperCase()),t&&(t.textContent=this.profile.tag),i&&(i.textContent=`Уровень ${this.profile.level}`),a&&(a.textContent=`${this.profile.xp.toLocaleString("ru")} XP`),this.animateProgress(0)}getElement(){return this.el}build(){const e=y,t=Math.round(e.xp/e.maxXp*100),i=document.createElement("div");i.id="profile-panel",i.className="profile-panel glass",i.innerHTML=`
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
    `;const a=i.querySelector("#porthole-wrap");a.addEventListener("click",()=>this.wobble(a)),a.addEventListener("keydown",l=>{(l.key==="Enter"||l.key===" ")&&this.wobble(a)});const s=i.querySelector("#edit-btn");return s.addEventListener("click",()=>{o.haptic("light"),s.textContent="⏳ Загрузка...",setTimeout(()=>{s.innerHTML="✏️ Редактировать"},1800)}),s.addEventListener("pointerdown",()=>{s.style.transform="scale(0.96)"}),s.addEventListener("pointerup",()=>{s.style.transform=""}),this.fillEl=i.querySelector("#progress-fill"),i}animateProgress(e=200){if(!this.fillEl)return;const t=Math.round(y.xp/y.maxXp*100);this.fillEl.style.width="0%",setTimeout(()=>{this.fillEl.style.width=`${t}%`},e)}wobble(e){this.wobbling||(this.wobbling=!0,o.haptic("light"),e.classList.add("porthole--wobble"),e.addEventListener("animationend",()=>{e.classList.remove("porthole--wobble"),this.wobbling=!1},{once:!0}))}updateFromTelegram(){const e=o.getUserName(),t=o.getUserTag();if(e){const i=this.el.querySelector("#profile-name");i&&(i.textContent=e.toUpperCase())}if(t){const i=this.el.querySelector("#profile-tag");i&&(i.textContent=t)}}}class re{constructor(e){this.targetX=0,this.targetY=0,this.currentX=0,this.currentY=0,this.rafId=0,this.el=e,this.bindEvents(),this.loop()}bindEvents(){window.addEventListener("mousemove",e=>{this.targetX=(e.clientX/window.innerWidth-.5)*14,this.targetY=(e.clientY/window.innerHeight-.5)*8}),window.addEventListener("deviceorientation",e=>{e.gamma===null||e.beta===null||(this.targetX=Math.max(-12,Math.min(12,e.gamma*.25)),this.targetY=Math.max(-7,Math.min(7,(e.beta-45)*.15)))})}loop(){this.currentX+=(this.targetX-this.currentX)*.06,this.currentY+=(this.targetY-this.currentY)*.06,this.el.style.transform=`scale(1.14) translate(${-this.currentX*.08}%, ${-this.currentY*.06}%)`,this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId)}}class le{constructor(e){this.intervalId=0,this.container=e,this.start()}spawnOne(){if(document.hidden)return;const e=document.createElement("div");e.className="trophy-bubble";const t=4+Math.random()*9,i=20+Math.random()*60,a=2.8+Math.random()*2.8;e.style.cssText=`
      width:${t}px; height:${t}px;
      left:${i}%; bottom:${8+Math.random()*12}%;
      animation-duration:${a}s;
      animation-delay:${Math.random()*.3}s;
    `,this.container.appendChild(e),setTimeout(()=>e.remove(),(a+.5)*1e3)}start(){this.intervalId=window.setInterval(()=>this.spawnOne(),380)}stop(){clearInterval(this.intervalId),this.container.querySelectorAll(".trophy-bubble").forEach(e=>e.remove())}restart(){this.stop(),this.start()}}class ne{static transitionTo(e,t){e.style.transition="opacity 0.35s ease, transform 0.35s ease",e.style.opacity="0",e.style.transform="scale(0.93)",e.style.pointerEvents="none",t.style.transition="none",t.style.opacity="0",t.style.transform="scale(1.06)",t.style.display="flex",setTimeout(()=>{e.style.display="none",e.style.opacity="",e.style.transform="",requestAnimationFrame(()=>{t.style.transition="opacity 0.38s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.38s cubic-bezier(0.25,0.46,0.45,0.94)",t.style.opacity="1",t.style.transform="scale(1)",t.style.pointerEvents="all"})},300)}}class oe{constructor(e,t=2){this.cards=[],this.bubbleSpawner=null,this.startX=0,this.isDragging=!1,this.onChangeCallback=null,this.container=e,this.activeIndex=t,this.build(),this.bindSwipe(),this.update()}build(){this.container.innerHTML="",this.cards=[];const e=document.createElement("div");e.className="carousel__bubbles",this.container.appendChild(e),this.bubbleSpawner=new le(e);const t=document.createElement("div");t.className="carousel__track",this.container.appendChild(t),u.forEach((i,a)=>{const s=document.createElement("div");s.className="carousel__card",s.dataset.index=String(a);const l=N[i.rarity];s.innerHTML=`
        <div class="carousel__card-inner" style="--accent:${l}">
          <div class="carousel__fish-emoji">${d(i.id)}</div>
          <div class="carousel__rarity" style="color:${l}">${i.rarityStars} ${i.rarityLabel}</div>
          <div class="carousel__fish-name">${i.name}</div>
          <div class="carousel__fish-latin">${i.latinName}</div>
          <div class="carousel__fish-stats">
            <span>⚖️ ${i.weight}</span>
            <span>🌊 ${i.depth}</span>
          </div>
        </div>
      `,t.appendChild(s),this.cards.push(s)})}update(){var e;this.cards.forEach((t,i)=>{const a=i-this.activeIndex,s=Math.abs(a);t.classList.remove("is-active","is-side","is-far");let l,n,c,h;switch(s){case 0:l=0,n=1,c=1,h=10,t.classList.add("is-active");break;case 1:l=a*148,n=.78,c=.6,h=5,t.classList.add("is-side");break;case 2:l=a*185,n=.62,c=.28,h=2,t.classList.add("is-far");break;default:l=a*200,n=.5,c=0,h=0}t.style.transform=`translateX(${l}px) scale(${n})`,t.style.opacity=String(c),t.style.zIndex=String(h)}),(e=this.onChangeCallback)==null||e.call(this,u[this.activeIndex])}next(){this.activeIndex<u.length-1&&(this.activeIndex++,this.update(),o.haptic("light"))}prev(){this.activeIndex>0&&(this.activeIndex--,this.update(),o.haptic("light"))}goTo(e){this.activeIndex=Math.max(0,Math.min(e,u.length-1)),this.update()}getActiveIndex(){return this.activeIndex}getActiveFish(){return u[this.activeIndex]}onChange(e){this.onChangeCallback=e}bindSwipe(){const e=this.container;e.addEventListener("touchstart",t=>{this.startX=t.touches[0].clientX,this.isDragging=!0},{passive:!0}),e.addEventListener("touchend",t=>{if(!this.isDragging)return;const i=t.changedTouches[0].clientX-this.startX;this.handleSwipeEnd(i),this.isDragging=!1},{passive:!0}),e.addEventListener("mousedown",t=>{this.startX=t.clientX,this.isDragging=!0,t.preventDefault()}),window.addEventListener("mouseup",t=>{if(!this.isDragging)return;const i=t.clientX-this.startX;this.handleSwipeEnd(i),this.isDragging=!1})}handleSwipeEnd(e){e<-42?this.next():e>42&&this.prev()}}class ce{constructor(){this.isOpen=!1,this.bgBlurTarget=null,this.onSelectCallback=null,this.currentActiveIndex=0,this.sheetStartY=0,this.sheetDragging=!1,this.overlay=this.buildOverlay(),this.sheet=this.overlay.querySelector("#modal-sheet"),this.listEl=this.overlay.querySelector("#modal-fish-list"),document.body.appendChild(this.overlay),this.bindClose()}buildOverlay(){const e=document.createElement("div");return e.id="modal-overlay",e.className="modal-overlay",e.innerHTML=`
      <div id="modal-sheet" class="modal-sheet">
        <div class="modal-handle"></div>
        <p class="modal-title">🏆 Выбор трофея</p>
        <div id="modal-fish-list" class="modal-fish-list"></div>
      </div>
    `,e}buildList(){this.listEl.innerHTML=u.map((e,t)=>{const i=N[e.rarity],a=t===this.currentActiveIndex;return`
        <div
          class="modal-fish-item ${a?"is-selected":""}"
          data-index="${t}"
          style="--accent:${i}"
          role="button"
          tabindex="0"
          aria-label="${e.name}"
        >
          <span class="modal-fish-emoji">${d(e.id)}</span>
          <div class="modal-fish-info">
            <div class="modal-fish-name">${e.name}</div>
            <div class="modal-fish-rarity" style="color:${i}">${e.rarityStars} ${e.rarityLabel}</div>
            <div class="modal-fish-stats">⚖️ ${e.weight} · 🌊 ${e.depth}</div>
          </div>
          ${a?'<span class="modal-check">✓</span>':""}
        </div>
      `}).join(""),this.listEl.querySelectorAll(".modal-fish-item").forEach(e=>{e.addEventListener("click",()=>{const t=parseInt(e.dataset.index??"0",10);this.select(t)})})}open(e,t){this.isOpen||(this.currentActiveIndex=e,this.bgBlurTarget=t??null,this.buildList(),this.overlay.style.display="flex",requestAnimationFrame(()=>{this.overlay.classList.add("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter="blur(4px)")}),this.isOpen=!0,o.haptic("medium"))}close(){this.isOpen&&(this.overlay.classList.remove("is-open"),this.bgBlurTarget&&(this.bgBlurTarget.style.filter=""),setTimeout(()=>{this.overlay.style.display="none"},420),this.isOpen=!1)}onSelect(e){this.onSelectCallback=e}select(e){var t;this.currentActiveIndex=e,o.haptic("medium"),(t=this.onSelectCallback)==null||t.call(this,e),this.close()}bindClose(){this.overlay.addEventListener("click",t=>{t.target===this.overlay&&this.close()});const e=this.sheet;e.addEventListener("touchstart",t=>{this.sheetStartY=t.touches[0].clientY,this.sheetDragging=!0},{passive:!0}),e.addEventListener("touchmove",t=>{if(!this.sheetDragging)return;const i=t.touches[0].clientY-this.sheetStartY;i>0&&(e.style.transform=`translateY(${i*.55}px)`,e.style.transition="none")},{passive:!0}),e.addEventListener("touchend",t=>{if(!this.sheetDragging)return;const i=t.changedTouches[0].clientY-this.sheetStartY;e.style.transform="",e.style.transition="",i>80&&this.close(),this.sheetDragging=!1},{passive:!0})}get fish(){return u}}class de{constructor(e,t){this.activeId="home",this.buttons=new Map,this.screens=new Map,this.onChangeCallbacks=[],this.el=this.build(),e.appendChild(this.el),E.forEach(i=>{const a=t.querySelector(`#screen-${i.id}`);a&&this.screens.set(i.id,a)}),this.screens.forEach((i,a)=>{a==="home"?(i.style.display="flex",i.style.opacity="1",i.style.pointerEvents="all"):(i.style.display="none",i.style.opacity="0")})}build(){const e=document.createElement("nav");return e.id="tab-bar",e.className="tab-bar",e.setAttribute("role","tablist"),E.forEach(t=>{const i=document.createElement("button");i.id=`tab-${t.id}`,i.className=`tab-btn ${t.id==="home"?"is-active":""}`,i.setAttribute("role","tab"),i.setAttribute("aria-selected",t.id==="home"?"true":"false"),i.dataset.tab=t.id,i.innerHTML=`
        <span class="tab-icon" aria-hidden="true">${d(t.id)}</span>
        <span class="tab-label">${t.label}</span>
      `,i.addEventListener("click",()=>this.switchTo(t.id)),i.addEventListener("pointerdown",()=>{i.style.transform="scale(0.92)"}),i.addEventListener("pointerup",()=>{i.style.transform=""}),i.addEventListener("pointerleave",()=>{i.style.transform=""}),e.appendChild(i),this.buttons.set(t.id,i)}),e}switchTo(e){if(e===this.activeId)return;o.haptic("selection");const t=this.activeId,i=this.screens.get(t),a=this.screens.get(e);ne.transitionTo(i,a),this.buttons.forEach((s,l)=>{const n=l===e;s.classList.toggle("is-active",n),s.setAttribute("aria-selected",String(n))}),this.activeId=e,this.onChangeCallbacks.forEach(s=>s(t,e))}onChange(e){this.onChangeCallbacks.push(e)}getActive(){return this.activeId}}let k=[];async function Y(){try{const r=await m("/api/book");r&&r.ok&&(k=r.items.map(e=>({id:e.image_file||"fishdef",emoji:"🐟",name:e.name,latinName:e.name,rarity:he(e.rarity),glowColor:pe(e.rarity),depth:"1-100 м",habitat:e.locations,length:`${e.min_length}-${e.max_length} см`,description:e.lore||`Рыба вида ${e.name}.`,funFact:"Информации пока нет.",chapter:"Общий атлас",isCaught:e.is_caught})))}catch(r){console.error("Failed to load encyclopedia:",r)}}function he(r){return{Обычная:"common",Редкая:"rare",Легендарная:"legendary",Мифическая:"epic"}[r]||"common"}function pe(r){return{Обычная:"#90e0ef",Редкая:"#00b4d8",Легендарная:"#f4a82e",Мифическая:"#9b5de5"}[r]||"#90e0ef"}const ue={common:"★★ Обычная",rare:"★★★ Редкая",epic:"★★★★ Эпическая",legendary:"★★★★★ Легендарная"};class ve{constructor(){this.entries=[],this.filtered=[],this.index=0,this.loading=!1,this.pageFlip=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-book",e.className="screen book-screen",e.setAttribute("role","main"),e.innerHTML=`
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
    `,e}async init(){this.bookContainer=this.el.querySelector(".book-wrap"),this.stBook=this.el.querySelector("#st-book"),this.searchInput=this.el.querySelector("#book-search-input"),this.prevBtn=this.el.querySelector("#book-prev-btn"),this.nextBtn=this.el.querySelector("#book-next-btn"),this.counterCur=this.el.querySelector("#counter-cur"),this.counterTot=this.el.querySelector("#counter-tot"),this.loading=!0,await Y(),this.entries=[...k],this.filtered=[...k],this.loading=!1,this.renderPages(),this.bindEvents()}buildPage(e){const t=e.isCaught??!1;return`
      <div class="my-page ${t?"":"not-caught"}">
        <div class="ph-content parchment">
          <div class="ph-chapter">${e.chapter}</div>
          <div class="ph-chapter-divider"><span class="ph-chapter-rule">✦ · ✦</span></div>

          <div class="ph-fish-block">
            <div class="ph-fish-emoji" style="--glow: ${t?e.glowColor:"#555"}; filter: ${t?"none":"grayscale(100%) contrast(50%) brightness(70%)"}">
              ${d(e.id)}
            </div>
          </div>
          
          <div class="ph-fish-name">${e.name.toUpperCase()}</div>
          <div class="ph-fish-latin">${e.latinName}</div>
          
          <div class="ph-rarity-wrap">
            <div class="ph-rarity" style="color:${t?e.glowColor:"#777"}; border-color:${t?e.glowColor:"#777"}55">
              ${t?ue[e.rarity]:'<span style="color: #ff4d4d; font-weight: bold;">НЕ СЛОВЛЕНА</span>'}
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
    `}renderPages(){this.pageFlip&&(this.pageFlip.destroy(),this.pageFlip=null);const e=this.el.querySelector("#st-book");e&&e.remove(),this.stBook=document.createElement("div"),this.stBook.id="st-book",this.stBook.className="st-book",this.bookContainer.appendChild(this.stBook),this.filtered.length!==0&&(this.stBook.innerHTML=this.filtered.map(t=>this.buildPage(t)).join(""),window.St&&window.St.PageFlip&&(this.pageFlip=new window.St.PageFlip(this.stBook,{width:320,height:480,size:"stretch",minWidth:280,maxWidth:600,minHeight:400,maxHeight:900,usePortrait:!0,showCover:!1,useMouseEvents:!1,maxShadowOpacity:.7,mobileScrollSupport:!1,flippingTime:600}),this.pageFlip.loadFromHTML(this.stBook.querySelectorAll(".my-page")),this.pageFlip.on("flip",t=>{this.index=t.data,this.syncUI()}),this.pageFlip.on("changeState",t=>{t.data==="flipping"&&o.haptic("light")})),this.index=0,this.syncUI())}syncUI(){this.counterCur.textContent=String(this.index+1),this.counterTot.textContent=String(this.filtered.length),this.prevBtn.disabled=this.index===0,this.nextBtn.disabled=this.index===this.filtered.length-1}applySearch(e){const t=e.trim().toLowerCase();this.filtered=t?this.entries.filter(i=>i.name.toLowerCase().includes(t)||i.latinName.toLowerCase().includes(t)||i.description.toLowerCase().includes(t)):[...this.entries],this.filtered.length||(this.filtered=[...this.entries]),this.renderPages()}bindEvents(){this.prevBtn.addEventListener("click",()=>{this.pageFlip&&this.index>0&&this.pageFlip.flipPrev()}),this.nextBtn.addEventListener("click",()=>{this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext()});let e=0,t=0;this.bookContainer.addEventListener("pointerdown",a=>{e=a.clientX,t=a.clientY},{passive:!0}),this.bookContainer.addEventListener("pointerup",a=>{if(this.pageFlip&&this.pageFlip.getState()!=="read")return;const s=a.clientX,l=a.clientY,n=e-s,c=Math.abs(t-l);Math.abs(n)>40&&c<60&&(n>0?this.pageFlip&&this.index<this.filtered.length-1&&this.pageFlip.flipNext():this.pageFlip&&this.index>0&&this.pageFlip.flipPrev())},{passive:!0}),this.searchInput.addEventListener("keydown",a=>{a.key==="Enter"&&(a.preventDefault(),this.applySearch(this.searchInput.value))});const i=this.el.querySelector("#book-search-btn");i&&i.addEventListener("click",()=>{this.applySearch(this.searchInput.value)})}}class fe{constructor(e,t){this.isPlaying=!1,this.isGameOver=!1,this.distance=0,this.coins=0,this.speed=3,this.animationId=0,this.player={x:80,y:0,targetY:0,size:40},this.angler={x:-20,y:0,size:80,baseY:0,time:0},this.obstacles=[],this.collectibles=[],this.particles=[],this.lastTime=0,this.spawnTimer=0,this.onExit=t,this.el=document.createElement("div"),this.el.className="game-container",this.el.innerHTML=`
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
    `,e.appendChild(this.el),this.init()}destroy(){this.isPlaying=!1,cancelAnimationFrame(this.animationId),this.el.remove()}init(){const e=this.el;this.canvas=e.querySelector("#runner-canvas"),this.ctx=this.canvas.getContext("2d"),this.menuOverlay=e.querySelector("#adv-menu"),this.gameOverOverlay=e.querySelector("#adv-gameover"),this.distanceEl=e.querySelector("#adv-dist"),this.coinsEl=e.querySelector("#adv-coins"),e.querySelector("#adv-start-btn").addEventListener("click",()=>this.startGame()),e.querySelector("#adv-restart-btn").addEventListener("click",()=>this.startGame()),e.querySelector("#adv-exit-btn").addEventListener("click",()=>this.onExit()),e.querySelector("#adv-exit-btn2").addEventListener("click",()=>this.onExit());const t=()=>{this.canvas.width=window.innerWidth,this.canvas.height=e.clientHeight||window.innerHeight,this.isPlaying||this.drawStaticBackground()};window.addEventListener("resize",t),setTimeout(t,100);let i=0;this.canvas.addEventListener("touchstart",s=>{i=s.touches[0].clientY}),this.canvas.addEventListener("touchmove",s=>{s.preventDefault();const l=s.touches[0].clientY,n=l-i;this.player.targetY+=n*1.5,this.player.targetY<50&&(this.player.targetY=50),this.player.targetY>this.canvas.height-50&&(this.player.targetY=this.canvas.height-50),i=l},{passive:!1});let a=!1;this.canvas.addEventListener("mousedown",s=>{a=!0,i=s.clientY}),window.addEventListener("mouseup",()=>a=!1),this.canvas.addEventListener("mousemove",s=>{if(!a)return;const l=s.clientY-i;this.player.targetY+=l*1.5,this.player.targetY<50&&(this.player.targetY=50),this.player.targetY>this.canvas.height-50&&(this.player.targetY=this.canvas.height-50),i=s.clientY})}startGame(){o.haptic("impact"),this.isPlaying=!0,this.isGameOver=!1,this.distance=0,this.coins=0,this.speed=3,this.obstacles=[],this.collectibles=[],this.particles=[],this.player.y=this.canvas.height/2,this.player.targetY=this.player.y,this.angler.y=this.canvas.height/2,this.menuOverlay.style.display="none",this.gameOverOverlay.style.display="none",cancelAnimationFrame(this.animationId),this.lastTime=performance.now(),this.gameLoop(this.lastTime)}spawnObstacle(){const e=Math.random()>.5?"🪨":"🦑",t=50+Math.random()*30;this.obstacles.push({x:this.canvas.width+50,y:50+Math.random()*(this.canvas.height-100),size:t,type:e,wobble:Math.random()*Math.PI*2})}spawnCollectible(){this.collectibles.push({x:this.canvas.width+50,y:50+Math.random()*(this.canvas.height-100),size:30,type:"💎"})}spawnParticles(e,t,i){for(let a=0;a<10;a++)this.particles.push({x:e,y:t,vx:(Math.random()-.5)*10,vy:(Math.random()-.5)*10,life:1,color:i})}endGame(){this.isPlaying=!1,this.isGameOver=!0,o.haptic("heavy"),this.ctx.fillStyle="rgba(0, 0, 0, 0.5)",this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height),this.el.querySelector("#adv-final-dist").textContent=Math.floor(this.distance).toString(),this.el.querySelector("#adv-final-coins").textContent=this.coins.toString(),this.gameOverOverlay.style.display="flex"}gameLoop(e){if(!this.isPlaying)return;const t=(e-this.lastTime)/1e3;this.lastTime=e,this.distance+=this.speed*t*10,this.speed+=t*.05,this.distanceEl.textContent=Math.floor(this.distance).toString(),this.spawnTimer+=t,this.spawnTimer>1.2*(3/this.speed)&&(this.spawnTimer=0,this.spawnObstacle(),Math.random()>.4&&this.spawnCollectible()),this.player.y+=(this.player.targetY-this.player.y)*.1,this.angler.time+=t*5,this.angler.baseY+=(this.player.y-this.angler.baseY)*.02,this.angler.y=this.angler.baseY+Math.sin(this.angler.time)*20,this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height),Math.random()>.9&&this.particles.push({x:this.canvas.width+10,y:Math.random()*this.canvas.height,vx:-this.speed*.5,vy:-1-Math.random()*2,life:2,color:"rgba(255, 255, 255, 0.2)",isBubble:!0});for(let a=this.particles.length-1;a>=0;a--){const s=this.particles[a];if(s.x+=s.vx,s.y+=s.vy,s.isBubble?s.life-=t*.2:s.life-=t*1.5,s.life<=0){this.particles.splice(a,1);continue}this.ctx.globalAlpha=s.life,this.ctx.fillStyle=s.color,this.ctx.beginPath(),this.ctx.arc(s.x,s.y,s.isBubble?4:3,0,Math.PI*2),this.ctx.fill(),this.ctx.globalAlpha=1}this.ctx.font="30px Arial",this.ctx.textAlign="center",this.ctx.textBaseline="middle";for(let a=this.collectibles.length-1;a>=0;a--){const s=this.collectibles[a];if(s.x-=this.speed,Math.hypot(s.x-this.player.x,s.y-this.player.y)<this.player.size/2+s.size/2){this.coins++,this.coinsEl.textContent=this.coins.toString(),this.spawnParticles(s.x,s.y,"#00b4d8"),this.collectibles.splice(a,1),o.haptic("light");continue}if(s.x<-50){this.collectibles.splice(a,1);continue}this.ctx.shadowColor="#00b4d8",this.ctx.shadowBlur=10,this.ctx.fillText(s.type,s.x,s.y+Math.sin(e/200+s.x)*5),this.ctx.shadowBlur=0}for(let a=this.obstacles.length-1;a>=0;a--){const s=this.obstacles[a];s.x-=this.speed,s.wobble+=t*3;const l=s.type==="🦑"?s.y+Math.sin(s.wobble)*15:s.y;if(Math.hypot(s.x-this.player.x,l-this.player.y)<this.player.size/2+s.size*.35){this.endGame();return}if(s.x<-100){this.obstacles.splice(a,1);continue}this.ctx.font=`${s.size}px Arial`,this.ctx.fillText(s.type,s.x,l)}this.ctx.font=`${this.player.size}px Arial`,this.ctx.shadowColor="#00b4d8",this.ctx.shadowBlur=15;const i=(this.player.targetY-this.player.y)*.05;this.ctx.save(),this.ctx.translate(this.player.x,this.player.y),this.ctx.rotate(i),this.ctx.fillText("🦁",0,0),this.ctx.restore(),this.ctx.shadowBlur=0,this.ctx.font=`${this.angler.size}px Arial`,this.ctx.shadowColor="#ff0055",this.ctx.shadowBlur=20,this.ctx.fillText("👾",this.angler.x,this.angler.y),this.ctx.shadowBlur=0,this.ctx.beginPath(),this.ctx.moveTo(this.angler.x+10,this.angler.y-30),this.ctx.lineTo(this.angler.x+30,this.angler.y-40),this.ctx.strokeStyle="#00ffcc",this.ctx.lineWidth=2,this.ctx.stroke(),this.ctx.beginPath(),this.ctx.fillStyle="#00ffcc",this.ctx.arc(this.angler.x+30,this.angler.y-40,4,0,Math.PI*2),this.ctx.fill(),this.animationId=requestAnimationFrame(a=>this.gameLoop(a))}drawStaticBackground(){this.ctx.fillStyle="rgba(0,10,30,0.5)",this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height),this.ctx.font="50px Arial",this.ctx.textAlign="center",this.ctx.fillText("👾",50,this.canvas.height/2),this.ctx.fillText("🦁",150,this.canvas.height/2)}}class me{constructor(e,t){this.animationId=0,this.isPlaying=!1,this.grid=[],this.cols=6,this.rows=8,this.player={gx:0,gy:0},this.pearls=0,this.moves=15,this.tileW=60,this.tileH=30,this.onExit=t,this.el=document.createElement("div"),this.el.className="game-container",this.el.innerHTML=`
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
    `,e.appendChild(this.el),this.init()}destroy(){this.isPlaying=!1,cancelAnimationFrame(this.animationId),this.el.remove()}init(){const e=this.el;this.canvas=e.querySelector("#maze-canvas"),this.ctx=this.canvas.getContext("2d"),this.overlay=e.querySelector("#maze-gameover"),e.querySelector("#maze-start-btn").addEventListener("click",()=>this.startGame()),e.querySelector("#maze-restart-btn").addEventListener("click",()=>this.startGame()),e.querySelector("#maze-exit-btn").addEventListener("click",()=>this.onExit()),e.querySelector("#maze-exit-btn2").addEventListener("click",()=>this.onExit());const t=()=>{this.canvas.width=window.innerWidth,this.canvas.height=e.clientHeight||window.innerHeight,this.tileW=Math.min(60,this.canvas.width/(this.cols+2)),this.tileH=this.tileW*.55};window.addEventListener("resize",t),setTimeout(t,100);const i=(n,c)=>{this.isPlaying&&(Math.abs(n)>Math.abs(c)&&Math.abs(n)>30?n>0?this.tryMove(1,0):this.tryMove(-1,0):Math.abs(c)>30&&(c>0?this.tryMove(0,1):this.tryMove(0,-1)))};let a=0,s=0;this.canvas.addEventListener("touchstart",n=>{a=n.touches[0].clientX,s=n.touches[0].clientY},{passive:!0}),this.canvas.addEventListener("touchend",n=>{const c=n.changedTouches[0].clientX,h=n.changedTouches[0].clientY;i(c-a,h-s)});let l=!1;this.canvas.addEventListener("mousedown",n=>{l=!0,a=n.clientX,s=n.clientY}),window.addEventListener("mouseup",n=>{l&&(l=!1,i(n.clientX-a,n.clientY-s))}),window.addEventListener("keydown",n=>{if(this.isPlaying)switch(n.key){case"ArrowUp":case"w":case"W":case"Ц":case"ц":this.tryMove(0,-1);break;case"ArrowDown":case"s":case"S":case"Ы":case"ы":this.tryMove(0,1);break;case"ArrowLeft":case"a":case"A":case"Ф":case"ф":this.tryMove(-1,0);break;case"ArrowRight":case"d":case"D":case"В":case"в":this.tryMove(1,0);break}})}generateMaze(){const e=[["start","floor","wall","floor","pearl","floor"],["wall","floor","wall","floor","wall","floor"],["floor","floor","floor","floor","wall","floor"],["floor","wall","wall","floor","eel","floor"],["pearl","floor","wall","floor","floor","floor"],["wall","floor","floor","eel","wall","wall"],["floor","floor","wall","floor","floor","pearl"],["floor","eel","floor","floor","wall","chest"]];this.grid=e}startGame(){o.haptic("impact"),this.generateMaze(),this.player={gx:0,gy:0},this.moves=20,this.pearls=0,this.isPlaying=!0,this.el.querySelector("#maze-menu").style.display="none",this.el.querySelector("#maze-gameover").style.display="none",this.updateUI(),cancelAnimationFrame(this.animationId),this.renderLoop(performance.now())}tryMove(e,t){if(this.moves<=0)return;const i=this.player.gx+e,a=this.player.gy+t;if(i>=0&&i<this.cols&&a>=0&&a<this.rows){const s=this.grid[a][i];if(s==="wall"){o.haptic("error");return}if(this.player.gx=i,this.player.gy=a,this.moves--,o.haptic("light"),s==="pearl")this.pearls++,this.grid[a][i]="floor",o.haptic("success");else if(s==="eel"){this.endGame(!1,"СЪЕДЕН УГРЕМ!");return}else if(s==="chest"){this.endGame(!0,"СОКРОВИЩЕ НАЙДЕНО!");return}this.updateUI(),this.moves<=0&&this.endGame(!1,"ЗАКОНЧИЛИСЬ ХОДЫ!")}}updateUI(){this.el.querySelector("#maze-moves").textContent=this.moves.toString(),this.el.querySelector("#maze-pearls").textContent=this.pearls.toString()}endGame(e,t){this.isPlaying=!1,o.haptic(e?"success":"heavy"),this.el.querySelector("#maze-result-title").textContent=t,this.el.querySelector("#maze-final-pearls").textContent=this.pearls.toString(),this.el.querySelector("#maze-gameover").style.display="flex"}renderLoop(e){if(!this.isPlaying)return;this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height),this.ctx.fillStyle="rgba(0,10,25,0.8)",this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height);const t=this.canvas.width/2,i=100;for(let a=0;a<this.rows;a++)for(let s=0;s<this.cols;s++){const l=this.grid[a][s],n=t+(s-a)*this.tileW,c=i+(s+a)*this.tileH;if(this.drawTile(n,c,l,e),this.player.gx===s&&this.player.gy===a){this.ctx.font="34px Arial",this.ctx.textAlign="center",this.ctx.shadowColor="#00f0ff",this.ctx.shadowBlur=15;const h=Math.abs(Math.sin(e/200))*10;this.ctx.fillText("🦑",n,c-15-h),this.ctx.shadowBlur=0,this.ctx.beginPath(),this.ctx.ellipse(n,c,this.tileW,this.tileH,0,0,Math.PI*2);const w=this.ctx.createRadialGradient(n,c,0,n,c,this.tileW);w.addColorStop(0,"rgba(0, 240, 255, 0.4)"),w.addColorStop(1,"rgba(0, 240, 255, 0)"),this.ctx.fillStyle=w,this.ctx.fill()}}this.animationId=requestAnimationFrame(a=>this.renderLoop(a))}drawTile(e,t,i,a){const s=this.tileW,l=this.tileH;this.ctx.beginPath(),this.ctx.moveTo(e,t-l),this.ctx.lineTo(e+s,t),this.ctx.lineTo(e,t+l),this.ctx.lineTo(e-s,t),this.ctx.closePath(),this.ctx.fillStyle=i==="wall"?"#14314c":"#081f33",this.ctx.fill(),this.ctx.strokeStyle="rgba(0,180,216,0.3)",this.ctx.lineWidth=1,this.ctx.stroke(),this.ctx.font="24px Arial",this.ctx.textAlign="center",i==="wall"?(this.ctx.beginPath(),this.ctx.moveTo(e-s,t),this.ctx.lineTo(e,t+l),this.ctx.lineTo(e,t+l-20),this.ctx.lineTo(e-s,t-20),this.ctx.fillStyle="#104d7d",this.ctx.fill(),this.ctx.beginPath(),this.ctx.moveTo(e,t+l),this.ctx.lineTo(e+s,t),this.ctx.lineTo(e+s,t-20),this.ctx.lineTo(e,t+l-20),this.ctx.fillStyle="#0b3558",this.ctx.fill(),this.ctx.beginPath(),this.ctx.moveTo(e,t-l-20),this.ctx.lineTo(e+s,t-20),this.ctx.lineTo(e,t+l-20),this.ctx.lineTo(e-s,t-20),this.ctx.fillStyle="#18649e",this.ctx.fill(),this.ctx.fillText("🪸",e,t-5)):i==="chest"?(this.ctx.shadowColor="#ffe259",this.ctx.shadowBlur=20,this.ctx.fillText("🧰",e,t),this.ctx.shadowBlur=0):i==="pearl"?this.ctx.fillText("⚪",e,t+Math.sin(a/300+e)*5):i==="eel"&&(this.ctx.shadowColor="#ff6b6b",this.ctx.shadowBlur=10,this.ctx.fillText("🐍",e,t),this.ctx.shadowBlur=0)}}class ge{constructor(){this.currentGame=null,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-adventures",e.className="screen adventures-main-screen",e.setAttribute("role","main"),e.innerHTML=`
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
    `,e}init(){const e=this.el.querySelector("#adv-main-menu");this.el.querySelector("#card-runner button").addEventListener("click",()=>{o.haptic("impact"),e.style.display="none",this.currentGame&&this.currentGame.destroy(),this.currentGame=new fe(this.el,()=>{this.currentGame.destroy(),this.currentGame=null,e.style.display="flex"})}),this.el.querySelector("#card-maze button").addEventListener("click",()=>{o.haptic("impact"),e.style.display="none",this.currentGame&&this.currentGame.destroy(),this.currentGame=new me(this.el,()=>{this.currentGame.destroy(),this.currentGame=null,e.style.display="flex"})})}}const L=["guild_beer","guild_rich","guild_cthulhu","guild_king"],$=["#00b4d8","#f4a82e","#9b5de5","#ff6b6b","#a5a5a5","#4d908e"];let v=[],f=null,D=!1;async function x(){try{const r=await m("/api/guilds");if(r&&r.ok){const e=r.my_clan;if(e){const t={id:String(e.id),name:e.name,avatar:e.avatar_emoji||"🔱",borderColor:e.color_hex||"#00b4d8",type:e.access_type||"open",level:e.level||1,members:[],requests:[],upgradeProgress:[],capacity:20,minLevel:e.min_level||0};v=[t],f=t.id,D=e.role==="leader"}else v=(r.items||[]).map(t=>({id:String(t.id),name:t.name,avatar:t.avatar_emoji||"🔱",borderColor:t.color_hex||"#00b4d8",type:t.access_type||"open",level:t.level||1,members:[],requests:[],upgradeProgress:[],capacity:20,minLevel:t.min_level||0})),f=null}}catch(r){console.error("Failed to load clans:",r)}}async function ye(r){try{const e=await m("/api/guilds/create",{method:"POST",body:JSON.stringify({name:r.name,avatar:r.avatar,color:r.borderColor,type:r.type,min_level:r.minLevel})});if(e&&e.ok)return await x(),v.find(t=>t.id===String(e.clan_id))||null;e&&!e.ok&&(e.reason==="not_enough_coins"?alert(`Недостаточно монет для создания артели! Нужно ${e.cost.toLocaleString()} 🪙`):alert(`Ошибка создания: ${e.reason||"неизвестная ошибка"}`))}catch(e){console.error("Failed to create guild:",e)}return null}async function be(r){const e=v.find(t=>t.id===r);if(!e)return!1;try{const t=e.type==="open"?"/api/guilds/join":"/api/guilds/apply",i=await m(t,{method:"POST",body:JSON.stringify({guild_id:r})});if(i&&i.ok)return e.type==="open"&&(f=e.id),!0;i&&!i.ok&&(i.reason==="level_too_low"?alert(`Ваш уровень слишком низок! Требуется уровень ${i.required}`):i.reason==="not_enough_coins"?alert(`Недостаточно монет! Требуется ${i.cost} 🪙`):alert(`Ошибка: ${i.reason||i.error||"неизвестная ошибка"}`))}catch(t){console.error("Failed to join guild:",t)}return!1}async function xe(){if(f)try{const r=await m("/api/guilds/leave",{method:"POST"});r&&r.ok&&(f=null,D=!1,await x())}catch(r){console.error("Failed to leave guild:",r)}}class we{constructor(){this.view="list",this.loading=!1,this.newGuildName="",this.selectedAvatar=L[0],this.selectedColor=$[0],this.selectedType="open",this.selectedMinLevel=0,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-guilds",e.className="screen guilds-screen",e.setAttribute("role","main"),e}async init(){this.loading=!0,this.render(),await x(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}f?this.renderManage():this.view==="create"?this.renderCreate():this.renderList()}renderList(){var e;this.el.innerHTML=`
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
    `,(e=this.el.querySelector("#guild-create-trigger"))==null||e.addEventListener("click",()=>{this.view="create",this.render(),o.haptic("medium")}),this.el.querySelectorAll(".guild-card").forEach(t=>{var i;(i=t.querySelector("button"))==null||i.addEventListener("click",async a=>{a.stopPropagation();const s=t.getAttribute("data-id");if(await be(s)){o.haptic("heavy");const n=v.find(c=>c.id===s);(n==null?void 0:n.type)==="invite"?alert("Заявка отправлена!"):await this.init()}else o.haptic("error"),alert("Не удалось вступить в артель.")})})}renderCreate(){var i,a;this.el.innerHTML=`
      <h1 class="page-title">НОВАЯ АРТЕЛЬ</h1>
      <div class="glass artel-form" style="padding: 20px;">
        <div class="form-group">
          <label class="form-label">Название (макс. 14 симв.)</label>
          <input type="text" id="guild-name-input" class="form-input" maxlength="14" placeholder="Введите название..." value="${this.newGuildName}">
        </div>

        <div class="form-group">
          <label class="form-label">Выберите герб</label>
          <div class="avatar-grid">
            ${L.map(s=>`
              <div class="avatar-opt ${this.selectedAvatar===s?"is-selected":""}" data-val="${s}">${d(s)}</div>
            `).join("")}
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Цвет каемки</label>
          <div class="color-row">
            ${$.map(s=>`
              <div class="color-opt ${this.selectedColor===s?"is-selected":""}" data-val="${s}" style="background:${s}"></div>
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
          <label class="form-label">Минимальный уровень: ${this.selectedMinLevel}</label>
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
    `;const e=this.el.querySelector("#guild-name-input");e.addEventListener("input",()=>{this.newGuildName=e.value}),this.el.querySelectorAll(".avatar-opt").forEach(s=>{s.addEventListener("click",()=>{this.selectedAvatar=s.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".color-opt").forEach(s=>{s.addEventListener("click",()=>{this.selectedColor=s.getAttribute("data-val"),this.render()})}),this.el.querySelectorAll(".type-opt").forEach(s=>{s.addEventListener("click",()=>{this.selectedType=s.getAttribute("data-val"),this.render()})});const t=this.el.querySelector("#min-level-slider");t&&t.addEventListener("input",()=>{this.selectedMinLevel=parseInt(t.value);const s=this.el.querySelector(".form-label:nth-of-type(4)");s&&(s.textContent=`Минимальный уровень: ${this.selectedMinLevel}`)}),(i=this.el.querySelector("#create-cancel"))==null||i.addEventListener("click",()=>{this.view="list",this.render()}),(a=this.el.querySelector("#create-confirm"))==null||a.addEventListener("click",async()=>{if(this.newGuildName.trim().length<3){alert("Слишком короткое название!");return}await ye({name:this.newGuildName,avatar:this.selectedAvatar,borderColor:this.selectedColor,type:this.selectedType,minLevel:this.selectedMinLevel})?(o.haptic("heavy"),await this.init()):(o.haptic("error"),alert("Ошибка при создании артели."))})}renderManage(){var i,a;const e=v.find(s=>s.id===f),t=((i=e.members.find(s=>s.userId==="current-user"))==null?void 0:i.role)==="owner";this.el.innerHTML=`
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
          ${e.upgradeProgress.map((s,l)=>`
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
              <button class="donate-btn" data-idx="${l}">ВКЛАД</button>
            </div>
          `).join("")}
        </div>
      </div>

      ${t&&e.requests.length>0?`
        <div class="glass" style="padding: 12px; margin-bottom: 12px;">
          <p class="form-label" style="margin-bottom: 10px; font-size: 10px;">Заявки на вступление</p>
          <div class="requests-list">
            ${e.requests.map(s=>`
              <div class="request-card glass" style="padding: 8px;">
                <div class="req-avatar" style="font-size:20px;">${s.userAvatar}</div>
                <div class="req-info">
                  <div class="req-name" style="font-size:12px;">${s.name}</div>
                  <div class="req-lvl" style="font-size:9px;">Ур. ${s.level}</div>
                </div>
                <div class="req-btns">
                  <button class="req-btn req-btn--no" data-id="${s.userId}" style="width:28px; height:28px; font-size:12px;">✕</button>
                  <button class="req-btn req-btn--yes" data-id="${s.userId}" style="width:28px; height:28px; font-size:12px;">✓</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `:""}

      <div class="guild-actions">
        <button class="guild-leave-btn" id="btn-leave" style="height:44px; font-size:11px;">ПОКИНУТЬ АРТЕЛЬ</button>
      </div>
    `,(a=this.el.querySelector("#btn-leave"))==null||a.addEventListener("click",()=>{confirm("Вы уверены, что хотите покинуть артель?")&&(xe(),o.haptic("medium"),this.render())}),this.el.querySelectorAll(".donate-btn").forEach(s=>{s.addEventListener("click",()=>{const l=parseInt(s.getAttribute("data-idx"),10),n=e.upgradeProgress[l];n.current=Math.min(n.required,n.current+Math.floor(Math.random()*5)+1),o.haptic("selection"),this.render()})}),this.el.querySelectorAll(".req-btn--yes").forEach(s=>{s.addEventListener("click",()=>{const l=s.getAttribute("data-id"),n=e.requests.findIndex(c=>c.userId===l);if(n!==-1){const c=e.requests.splice(n,1)[0];e.members.push({userId:c.userId,name:c.name,level:c.level,role:"member"}),o.haptic("heavy"),this.render()}})}),this.el.querySelectorAll(".req-btn--no").forEach(s=>{s.addEventListener("click",()=>{const l=s.getAttribute("data-id");e.requests=e.requests.filter(n=>n.userId!==l),o.haptic("medium"),this.render()})})}}let b=[],p=[];async function j(){try{const r=await m("/api/friends");r&&r.ok&&(b=r.friends.map(e=>({id:String(e.user_id),name:e.username,level:e.level,avatar:"👤",online:!0,xp:e.xp})))}catch(r){console.error("Failed to load friends:",r)}}function ke(r){return console.log(`Friend request sent to: ${r}`),!0}function Ce(r){const e=p.find(t=>t.id===r);e&&(b.push({...e,online:Math.random()>.5}),p=p.filter(t=>t.id!==r))}function Se(r){p=p.filter(e=>e.id!==r)}class Me{constructor(){this.currentView="list",this.loading=!1,this.el=this.buildShell()}getElement(){return this.el}buildShell(){const e=document.createElement("section");return e.id="screen-friends",e.className="screen friends-screen",e.setAttribute("role","main"),e}async init(){this.loading=!0,this.render(),await j(),this.loading=!1,this.render()}render(){if(this.loading){this.el.innerHTML='<div style="display:flex; justify-content:center; align-items:center; height:100%; color:white;">Загрузка...</div>';return}this.currentView==="requests"?this.renderRequests():this.renderList()}renderList(){var e,t;this.el.innerHTML=`
      <div class="friends-header-row">
        <h1 class="page-title" style="margin-bottom:0">ДРУЗЬЯ</h1>
        <div class="friends-notif-btn" id="btn-show-requests">
          <span>🔔</span>
          ${p.length>0?`<div class="notif-badge">${p.length}</div>`:""}
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
        ${b.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:20px;">У вас пока нет друзей</p>':""}
        ${b.map(i=>`
          <div class="friend-card glass">
            <div class="friend-avatar">${i.avatar}</div>
            <div class="friend-info">
              <div class="friend-name">${i.name}</div>
              <div class="friend-meta">Ур. ${i.level} · ${i.online?'<span style="color:#2ecc71">Online</span>':'<span style="opacity:0.5">Offline</span>'}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `,(e=this.el.querySelector("#btn-show-requests"))==null||e.addEventListener("click",()=>{this.currentView="requests",this.render(),o.haptic("medium")}),(t=this.el.querySelector("#btn-add-search"))==null||t.addEventListener("click",()=>{const i=this.el.querySelector("#friend-search");i.value.trim()&&(ke(i.value),alert("Запрос отправлен!"),i.value="",o.haptic("light"))})}renderRequests(){var e;this.el.innerHTML=`
      <div class="friends-header-row">
        <button class="back-btn" id="btn-back-list">←</button>
        <h1 class="page-title" style="margin:0; flex:1">ЗАЯВКИ</h1>
      </div>

      <div class="requests-list" style="margin-top: 20px; display:flex; flex-direction:column; gap:10px;">
        ${p.length===0?'<p style="text-align:center; opacity:0.5; font-size:12px; margin-top:40px;">Нет новых заявок</p>':""}
        ${p.map(t=>`
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
    `,(e=this.el.querySelector("#btn-back-list"))==null||e.addEventListener("click",()=>{this.currentView="list",this.render(),o.haptic("light")}),this.el.querySelectorAll(".req-btn--yes").forEach(t=>{t.addEventListener("click",()=>{const i=t.getAttribute("data-id");Ce(i),o.haptic("heavy"),this.render()})}),this.el.querySelectorAll(".req-btn--no").forEach(t=>{t.addEventListener("click",()=>{const i=t.getAttribute("data-id");Se(i),o.haptic("medium"),this.render()})})}}class Ee{constructor(e){this.particles=[],this.W=0,this.H=0,this.rafId=0,this.COUNT=60,this.canvas=e,this.ctx=e.getContext("2d"),this.resize(),window.addEventListener("resize",this.resize.bind(this));for(let t=0;t<this.COUNT;t++){const i=this.createParticle();i.y=Math.random()*this.H,i.life=Math.floor(Math.random()*i.maxLife*.5),this.particles.push(i)}this.loop()}resize(){this.W=this.canvas.width=this.canvas.offsetWidth,this.H=this.canvas.height=this.canvas.offsetHeight}createParticle(){const e=Math.random()<.28;return{x:Math.random()*this.W,y:this.H+12,r:e?1.5+Math.random()*2:1.2+Math.random()*3,vx:(Math.random()-.5)*.4,vy:-(.2+Math.random()*.55),alpha:0,alphaTarget:.12+Math.random()*.4,life:0,maxLife:180+Math.random()*420,isSediment:e,wobble:Math.random()*Math.PI*2,wobbleSpeed:.02+Math.random()*.03}}drawBubble(e){const t=this.ctx;e.wobble+=e.wobbleSpeed;const i=e.x+Math.sin(e.wobble)*1.8;t.save(),t.globalAlpha=e.alpha,t.strokeStyle="rgba(160,220,255,0.65)",t.lineWidth=.7,t.beginPath(),t.arc(i,e.y,e.r,0,Math.PI*2),t.stroke(),t.fillStyle="rgba(255,255,255,0.35)",t.beginPath(),t.arc(i-e.r*.28,e.y-e.r*.28,e.r*.38,0,Math.PI*2),t.fill(),t.restore()}drawSediment(e){const t=this.ctx;t.save(),t.globalAlpha=e.alpha,t.fillStyle="rgba(180,150,90,0.7)",t.beginPath(),t.ellipse(e.x,e.y,e.r*1.6,e.r*.55,e.wobble,0,Math.PI*2),t.fill(),t.restore()}updateParticle(e){e.x+=e.vx,e.y+=e.vy,e.life+=1;const t=40,i=50;return e.life<t?e.alpha=e.life/t*e.alphaTarget:e.life>e.maxLife-i?e.alpha=(e.maxLife-e.life)/i*e.alphaTarget:e.alpha=e.alphaTarget,e.life<e.maxLife&&e.y>-10}loop(){this.ctx.clearRect(0,0,this.W,this.H);for(let e=0;e<this.particles.length;e++){const t=this.particles[e];this.updateParticle(t)?t.isSediment?this.drawSediment(t):this.drawBubble(t):this.particles[e]=this.createParticle()}this.rafId=requestAnimationFrame(this.loop.bind(this))}destroy(){cancelAnimationFrame(this.rafId),window.removeEventListener("resize",this.resize.bind(this))}}const Le=Q();J();const $e=document.getElementById("particles-canvas");new Ee($e);const qe=document.getElementById("bg-parallax");new re(qe);const C=new ae;C.updateFromTelegram();const Te=document.getElementById("profile-mount");Te.appendChild(C.getElement());async function Ie(){try{await Promise.all([j(),x(),Y()]),console.log("Initial data loaded")}catch(r){console.error("Failed to load initial data:",r)}}Ie();const Ae=document.getElementById("carousel-mount"),V=new oe(Ae,2),g=document.getElementById("screens-wrap"),X=new ce;X.onSelect(r=>{V.goTo(r)});ie(()=>{X.open(V.getActiveIndex(),g)});const U=new ve,q=U.getElement(),T=document.getElementById("screen-book");T?T.replaceWith(q):g.appendChild(q);const R=new ge,I=R.getElement(),A=document.getElementById("screen-adventures");A?A.replaceWith(I):g.appendChild(I);const W=new we,B=W.getElement(),P=document.getElementById("screen-guilds");P?P.replaceWith(B):g.appendChild(B);const Z=new Me,z=Z.getElement(),H=document.getElementById("screen-friends");H?H.replaceWith(z):g.appendChild(z);let _=!1,F=!1,G=!1,O=!1;const Be=document.getElementById("tabbar-mount"),Pe=new de(Be,g);Pe.onChange((r,e)=>{e==="book"&&!_&&(U.init(),_=!0),e==="adventures"&&!F&&(R.init(),F=!0),e==="guilds"&&!G&&(W.init(),G=!0),e==="friends"&&!O&&(Z.init(),O=!0)});te();setTimeout(()=>C.animateProgress(0),2e3);ee(Le,1600);
