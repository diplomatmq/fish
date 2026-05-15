// ─────────────────────────────────────────────────────────────────────────────
// main.ts — Application entry point
// Wires together: layout → particles → parallax → profilePanel →
//                 carousel → modal → tabBar → bookScreen → entry animation
// ─────────────────────────────────────────────────────────────────────────────
import './style.css';
import './book.css';
import './adventures.css';
import './guilds.css';
import './friends.css';
import './rating.css';
import './captcha.css';

import { buildLayout, buildEntryOverlay, hideEntryOverlay, bindQuickActions, bindTrophyButton } from './ui/layout';
import { ProfilePanel }   from './ui/profile';
import { FishCarousel }   from './ui/carousel';
import { TrophyModal }    from './ui/modal';
import { TabBar }         from './ui/tabbar';
import { BookScreen }     from './ui/bookScreen';
import { ShopScreen }     from './ui/shopScreen';
import { GuildsScreen } from './ui/guildsScreen';
import { FriendsScreen } from './ui/friendsScreen';
import { RatingScreen } from './ui/ratingScreen';
import { ResultsScreen } from './ui/resultsScreen';
import { CaptchaScreen } from './ui/captchaScreen';
import { ParticleSystem } from './animations/particles';
import { ParallaxController } from './animations/effects';

import { loadFriends } from './modules/friendsData';
import { loadClans } from './modules/guildsData';
import { loadEncyclopedia } from './modules/encyclopediaData';
import { loadTrophies, ACTIVE_TROPHY_ID } from './modules/trophiesData';

// ── Check if captcha mode ──────────────────────────────────────────────────
const urlParams = new URLSearchParams(window.location.search);
const captchaMode = urlParams.get('captcha_mode');

if (captchaMode === 'antibot') {
  // Captcha mode - show only captcha screen
  const captchaScreen = new CaptchaScreen();
  const captchaEl = captchaScreen.getElement();
  document.body.innerHTML = '';
  document.body.appendChild(captchaEl);
  captchaScreen.init();
} else {
  // Normal mode - show full app
  initNormalMode();
}

function initNormalMode() {
// ── Entry overlay (shown during boot) ──────────────────────────────────────
const entryOverlay = buildEntryOverlay();

// ── Build DOM ────────────────────────────────────────────────────────────────
const app = buildLayout();

// ── Particles ────────────────────────────────────────────────────────────────
const canvas = document.getElementById('particles-canvas') as HTMLCanvasElement;
new ParticleSystem(canvas);

// ── Parallax background ───────────────────────────────────────────────────────
const bgEl = document.getElementById('bg-parallax') as HTMLElement;
new ParallaxController(bgEl);

// ── Profile panel ─────────────────────────────────────────────────────────────
const profilePanel = new ProfilePanel();
profilePanel.updateFromTelegram();
const profileMount = document.getElementById('profile-mount')!;
profileMount.appendChild(profilePanel.getElement());

// ── Initial Data Loading ──────────────────────────────────────────────────────
async function initAppData() {
  try {
    await Promise.all([
      loadFriends(),
      loadClans(),
      loadEncyclopedia()
    ]);
    console.log('Initial data loaded');
  } catch (e) {
    console.error('Failed to load initial data:', e);
  }
}

initAppData();

// ── Fish carousel ──────────────────────────────────────────────────────────────
const carouselMount = document.getElementById('carousel-mount')!;
const carousel = new FishCarousel(carouselMount, 2);

// ── Trophy modal ───────────────────────────────────────────────────────────────
const screensWrap  = document.getElementById('screens-wrap') as HTMLElement;
const trophyModal  = new TrophyModal();

async function refreshTrophies(): Promise<void> {
  const items = await loadTrophies();
  carousel.setFishData(items, ACTIVE_TROPHY_ID);
  trophyModal.setItems(carousel.getItems());
}

void refreshTrophies();

trophyModal.onSelect((index) => {
  carousel.goTo(index);
});

bindTrophyButton(() => {
  trophyModal.open(carousel.getActiveIndex(), screensWrap);
});

// ── Book screen ───────────────────────────────────────────────────────────────
const bookScreen = new BookScreen();
const bookScreenEl = bookScreen.getElement();
const oldBookPlaceholder = document.getElementById('screen-book');
if (oldBookPlaceholder) oldBookPlaceholder.replaceWith(bookScreenEl);
else screensWrap.appendChild(bookScreenEl);

// ── Shop screen ───────────────────────────────────────────────────────────────
const shopScreen = new ShopScreen();
const shopScreenEl = shopScreen.getElement();
const oldShopPlaceholder = document.getElementById('screen-shop');
if (oldShopPlaceholder) oldShopPlaceholder.replaceWith(shopScreenEl);
else screensWrap.appendChild(shopScreenEl);

// ── Guilds screen ─────────────────────────────────────────────────────────────
const guildsScreen = new GuildsScreen();
const guildsScreenEl = guildsScreen.getElement();
const oldGuildsPlaceholder = document.getElementById('screen-guilds');
if (oldGuildsPlaceholder) oldGuildsPlaceholder.replaceWith(guildsScreenEl);
else screensWrap.appendChild(guildsScreenEl);

// ── Friends screen ─────────────────────────────────────────────────────────────
const friendsScreen = new FriendsScreen();
const friendsScreenEl = friendsScreen.getElement();
const oldFriendsPlaceholder = document.getElementById('screen-friends');
if (oldFriendsPlaceholder) oldFriendsPlaceholder.replaceWith(friendsScreenEl);
else screensWrap.appendChild(friendsScreenEl);

// ── Rating screen ──────────────────────────────────────────────────────────────
const ratingScreen = new RatingScreen();
const ratingScreenEl = ratingScreen.getElement();
screensWrap.appendChild(ratingScreenEl);

// ── Results screen ─────────────────────────────────────────────────────────────
const resultsScreen = new ResultsScreen();
const resultsScreenEl = resultsScreen.getElement();
screensWrap.appendChild(resultsScreenEl);

let bookInitialized = false;
let shopInitialized = false;
let guildsInitialized = false;
let friendsInitialized = false;
let ratingInitialized = false;
let resultsInitialized = false;

// ── Shop screen ────────────────────────────────────────────────────────────────────
const tabbarMount = document.getElementById('tabbar-mount')!;
const tabBar   = new TabBar(tabbarMount, screensWrap);

// Lazy-init screens on first visit
tabBar.onChange((_prev, next) => {
  console.log(`Screen transition: ${_prev} -> ${next}`);
  
  // Hide/show TabBar based on screen
  const tabBarEl = document.getElementById('tab-bar');
  if (tabBarEl) {
    if (next === 'rating' || next === 'results') {
      tabBarEl.classList.add('hide-tabbar');
    } else {
      tabBarEl.classList.remove('hide-tabbar');
    }
  }
  
  if (next === 'book' && !bookInitialized) {
    bookScreen.init();
    bookInitialized = true;
  }
  if (next === 'shop' && !shopInitialized) {
    shopScreen.init();
    shopInitialized = true;
  }
  if (next === 'guilds' && !guildsInitialized) {
    guildsScreen.init();
    guildsInitialized = true;
  }
  if (next === 'friends' && !friendsInitialized) {
    friendsScreen.init();
    friendsInitialized = true;
  } else if (next === 'friends' && friendsInitialized) {
    friendsScreen.init();
  }
  if (next === 'rating' && !ratingInitialized) {
    ratingScreen.init();
    ratingInitialized = true;
  } else if (next === 'rating' && ratingInitialized) {
    ratingScreen.init();
  }
  if (next === 'results' && !resultsInitialized) {
    resultsScreen.init();
    resultsInitialized = true;
  } else if (next === 'results' && resultsInitialized) {
    resultsScreen.init();
  }
  
  // ИСПРАВЛЕНИЕ: При возврате на home - сбрасываем анимации и показываем контент
  if (next === 'home') {
    const homeScreen = document.getElementById('screen-home');
    if (homeScreen) {
      // Находим все элементы с анимацией slide-up
      const animatedElements = homeScreen.querySelectorAll('.slide-up');
      
      animatedElements.forEach((el) => {
        const element = el as HTMLElement;
        // Сбрасываем анимацию и принудительно показываем элемент
        element.style.animation = 'none';
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
      });
    }
  }
});

// ── Quick action buttons ────────────────────────────────────────────────────
bindQuickActions(
  () => tabBar.switchTo('rating'),
  () => tabBar.switchTo('results')
);

// ── Navigate home event listener ───────────────────────────────────────────
window.addEventListener('navigate-home', () => {
  console.log('Navigate home event received');
  
  // Показываем TabBar
  const tabBarEl = document.getElementById('tab-bar');
  if (tabBarEl) {
    tabBarEl.classList.remove('hide-tabbar');
  }
  
  // Переключаемся на главный экран
  tabBar.switchTo('home');
});

// ── Animate progress bar after boot sequence ──────────────────────────────────
setTimeout(() => profilePanel.animateProgress(0), 2000);

// ── Hide entry overlay ────────────────────────────────────────────────────────
hideEntryOverlay(entryOverlay, 1600);

// Unused variable lint guard
void tabBar;
void app;
}
