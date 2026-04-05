import { initCharacterScene } from "/static/js/character3d.js";

const usernameEl = document.getElementById("username");
const titleEl = document.getElementById("title");
const levelEl = document.getElementById("level");
const xpEl = document.getElementById("xp");
const coinsEl = document.getElementById("coins");
const xpFillEl = document.getElementById("xpFill");
const xpInfoEl = document.getElementById("xpInfo");
const trophySelect = document.getElementById("trophySelect");
const saveTrophyButton = document.getElementById("saveTrophy");
const trophyStatus = document.getElementById("trophyStatus");
const tabs = document.querySelectorAll(".tab");
const views = {
  profile: document.getElementById("view-profile"),
  character: document.getElementById("view-character"),
};
const characterHost = document.getElementById("characterCanvas");

let currentProfile = null;
let characterScene = null;

function getTelegramUserIdentity() {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    return "angler";
  }

  tg.ready();
  tg.expand();

  const user = tg.initDataUnsafe?.user;
  if (!user) {
    return "angler";
  }

  return user.username || user.first_name || user.last_name || "angler";
}

function updateProfile(profile) {
  currentProfile = profile;

  usernameEl.textContent = profile.username || "@angler";
  titleEl.textContent = profile.title || "Рыбак";
  levelEl.textContent = String(profile.level || 1);
  xpEl.textContent = String(profile.xp || 0);
  coinsEl.textContent = String(profile.coins || 0);

  const xp = Number(profile.xp || 0);
  const nextLevelTarget = 2000;
  const percent = Math.max(0, Math.min(100, Math.round((xp / nextLevelTarget) * 100)));
  xpFillEl.style.width = `${percent}%`;
  xpInfoEl.textContent = `До следующего уровня: ${Math.max(0, nextLevelTarget - xp)} XP`;
}

async function loadProfile() {
  const identity = getTelegramUserIdentity();
  const response = await fetch(`/api/profile?username=${encodeURIComponent(identity)}`);
  if (!response.ok) {
    throw new Error(`Profile load failed: ${response.status}`);
  }

  const profile = await response.json();
  updateProfile(profile);
}

async function loadTrophies() {
  const response = await fetch("/api/trophies");
  if (!response.ok) {
    throw new Error(`Trophies load failed: ${response.status}`);
  }

  const payload = await response.json();
  const items = Array.isArray(payload.items) ? payload.items : [];

  trophySelect.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    trophySelect.appendChild(option);
  });

  const selected = currentProfile?.selected_trophy || "none";
  if (items.some((item) => item.id === selected)) {
    trophySelect.value = selected;
  }
}

async function saveTrophySelection() {
  const trophyId = trophySelect.value;
  trophyStatus.textContent = "Сохранение...";

  const response = await fetch("/api/trophy/select", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ trophy_id: trophyId }),
  });

  if (!response.ok) {
    trophyStatus.textContent = "Не удалось сохранить выбор";
    return;
  }

  const payload = await response.json();
  if (payload.ok) {
    trophyStatus.textContent = "Трофей выбран. Полную синхронизацию подключим в следующем этапе.";
  } else {
    trophyStatus.textContent = "Ошибка сохранения";
  }
}

function switchView(viewName) {
  Object.entries(views).forEach(([name, node]) => {
    node.classList.toggle("active", name === viewName);
  });

  tabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });

  if (viewName === "character") {
    if (!characterScene) {
      characterScene = initCharacterScene(characterHost);
    }
    characterScene.resize();
  }
}

function bindUi() {
  tabs.forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });

  saveTrophyButton.addEventListener("click", () => {
    saveTrophySelection().catch((error) => {
      console.error(error);
      trophyStatus.textContent = "Ошибка запроса";
    });
  });

  window.addEventListener("resize", () => {
    if (characterScene) {
      characterScene.resize();
    }
  });
}

async function bootstrap() {
  bindUi();

  try {
    await loadProfile();
    await loadTrophies();
    trophyStatus.textContent = "Можно выбрать трофей";
  } catch (error) {
    console.error(error);
    trophyStatus.textContent = "Ошибка загрузки профиля";
  }
}

bootstrap();
