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
import { ShopScreen }     from './ui/shopScreen';
import { GuildsScreen } from './ui/guildsScreen';
import { FriendsScreen } from './ui/friendsScreen';
import { ParticleSystem } from './animations/particles';
import { ParallaxController } from './animations/effects';

import { loadFriends } from './modules/friendsData';
import { loadClans } from './modules/guildsData';
import { loadEncyclopedia } from './modules/encyclopediaData';
import { fetchApi } from './modules/api';
import type { FishData } from './types';

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
    const [profileData] = await Promise.all([
      fetchApi<any>('/api/profile'),
      loadFriends(),
      loadClans(),
      loadEncyclopedia()
    ]);
    console.log('Initial data loaded');

    // Load trophies
    const trophiesResponse = await fetchApi<any>('/api/trophies');
    if (trophiesResponse && trophiesResponse.items) {
      const trophies: FishData[] = trophiesResponse.items
        .filter((t: any) => t.id !== 'none')
        .map((t: any) => ({
          id: t.image_url ? t.image_url.split('/').pop() : 'fishdef.webp',
          emoji: '🐟',
          name: t.fish_name,
          latinName: t.rarity || 'Обычная',
          rarity: mapRarity(t.rarity),
          rarityLabel: t.rarity || 'Обычная',
          rarityStars: mapStars(t.rarity),
          weight: `${t.weight} кг`,
          depth: `${t.length} см`
        }));
      
      let activeIdx = trophies.findIndex((t: any, i: number) => {
          const apiTrophy = trophiesResponse.items.filter((x: any) => x.id !== 'none')[i];
          return apiTrophy && apiTrophy.is_active;
      });
      if (activeIdx === -1) activeIdx = 0;

      carousel.setTrophies(trophies, activeIdx);
      trophyModal.setTrophies(trophies);
    }

  } catch (e) {
    console.error('Failed to load initial data:', e);
  }
}

function mapRarity(r: string): any {
  const m: any = { 'Обычная': 'common', 'Редкая': 'rare', 'Эпическая': 'epic', 'Легендарная': 'legendary' };
  return m[r] || 'common';
}
function mapStars(r: string): string {
  const m: any = { 'Обычная': '★★', 'Редкая': '★★★', 'Эпическая': '★★★★', 'Легендарная': '★★★★★' };
  return m[r] || '★★';
}

initAppData();

// ── Fish carousel ──────────────────────────────────────────────────────────────
const carouselMount = document.getElementById('carousel-mount')!;
const carousel = new FishCarousel(carouselMount, 0);

// ── Trophy modal ───────────────────────────────────────────────────────────────
const screensWrap  = document.getElementById('screens-wrap') as HTMLElement;
const trophyModal  = new TrophyModal();

trophyModal.onSelect(async (index) => {
  const fish = trophyModal.fish[index];
  if (fish) {
    // We need the original API ID here, but our mapped FishData uses filename as ID.
    // Let's refetch or store IDs. For now, we'll just update local carousel.
    carousel.goTo(index);
    
    // Attempt to sync with server
    try {
        const trophiesResponse = await fetchApi<any>('/api/trophies');
        const apiTrophies = trophiesResponse.items.filter((x: any) => x.id !== 'none');
        const selectedId = apiTrophies[index]?.id;
        if (selectedId) {
            await fetchApi('/api/trophy/select', {
                method: 'POST',
                body: JSON.stringify({ trophy_id: selectedId })
            });
        }
    } catch (e) {
        console.error('Failed to sync trophy selection:', e);
    }
  }
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

let bookInitialized = false;
let shopInitialized = false;
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
