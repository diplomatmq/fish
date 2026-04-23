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

import { buildLayout, buildEntryOverlay, hideEntryOverlay, bindQuickActions, bindTrophyButton } from './ui/layout';
import { ProfilePanel }   from './ui/profile';
import { FishCarousel }   from './ui/carousel';
import { TrophyModal }    from './ui/modal';
import { TabBar }         from './ui/tabbar';
import { BookScreen }     from './ui/bookScreen';
import { AdventuresScreen } from './ui/adventuresScreen';
import { GuildsScreen } from './ui/guildsScreen';
import { FriendsScreen } from './ui/friendsScreen';
import { ParticleSystem } from './animations/particles';
import { ParallaxController } from './animations/effects';

import { loadFriends } from './modules/friendsData';
import { loadClans } from './modules/guildsData';
import { loadEncyclopedia } from './modules/encyclopediaData';

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

// ── Adventures screen ─────────────────────────────────────────────────────────
const advScreen = new AdventuresScreen();
const advScreenEl = advScreen.getElement();
const oldAdvPlaceholder = document.getElementById('screen-adventures');
if (oldAdvPlaceholder) oldAdvPlaceholder.replaceWith(advScreenEl);
else screensWrap.appendChild(advScreenEl);

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

let bookInitialized = false;
let advInitialized = false;
let guildsInitialized = false;
let friendsInitialized = false;

// ── Tab bar ────────────────────────────────────────────────────────────────────
const tabbarMount = document.getElementById('tabbar-mount')!;
const tabBar   = new TabBar(tabbarMount, screensWrap);

// Lazy-init screens on first visit
tabBar.onChange((_prev, next) => {
  if (next === 'book' && !bookInitialized) {
    bookScreen.init();
    bookInitialized = true;
  }
  if (next === 'adventures' && !advInitialized) {
    advScreen.init();
    advInitialized = true;
  }
  if (next === 'guilds' && !guildsInitialized) {
    guildsScreen.init();
    guildsInitialized = true;
  }
  if (next === 'friends' && !friendsInitialized) {
    friendsScreen.init();
    friendsInitialized = true;
  }
});

// ── Quick action buttons ────────────────────────────────────────────────────
bindQuickActions();

// ── Animate progress bar after boot sequence ──────────────────────────────────
setTimeout(() => profilePanel.animateProgress(0), 2000);

// ── Hide entry overlay ────────────────────────────────────────────────────────
hideEntryOverlay(entryOverlay, 1600);

// Unused variable lint guard
void tabBar;
void app;
