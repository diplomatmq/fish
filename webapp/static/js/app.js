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
const characterStatusEl = document.getElementById("characterStatus");

let currentProfile = null;
let characterScene = null;
let characterModulePromise = null;

function getTelegramUserInfo() {
  const tg = window.Telegram?.WebApp;
  const fallback = {
    userId: null,
    username: "angler",
  };

  if (!tg) {
    return fallback;
  }

  tg.ready();
  tg.expand();

  const user = tg.initDataUnsafe?.user;
  if (!user) {
    return fallback;
  }

  return {
    userId: typeof user.id === "number" ? user.id : null,
    username: user.username || user.first_name || user.last_name || "angler",
  };
}

function setCharacterStatus(text, isError = false) {
  if (!characterStatusEl) {
    return;
  }
  characterStatusEl.textContent = text;
  characterStatusEl.classList.toggle("error", Boolean(isError));
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
  const tgUser = getTelegramUserInfo();
  if (!tgUser.userId) {
    throw new Error("telegram_user_missing");
  }

  const params = new URLSearchParams({
    user_id: String(tgUser.userId),
    username: tgUser.username,
  });
  const response = await fetch(`/api/profile?${params.toString()}`);

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `profile_http_${response.status}`);
  }

  updateProfile(payload);
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
    trophyStatus.textContent = "Трофей сохранен";
  } else {
    trophyStatus.textContent = "Ошибка сохранения";
  }
}

async function ensureCharacterScene() {
  if (!characterHost) {
    return;
  }

  if (characterScene) {
    characterScene.resize();
    return;
  }

  characterHost.classList.add("loading");
  setCharacterStatus("Загрузка 3D...", false);

  try {
    if (!characterModulePromise) {
      characterModulePromise = import("/static/js/character3d.js");
    }

    const module = await characterModulePromise;
    characterScene = module.initCharacterScene(characterHost);
    if (characterScene && typeof characterScene.resize === "function") {
      characterScene.resize();
    }
    setCharacterStatus("3D готово", false);
  } catch (error) {
    console.error(error);
    setCharacterStatus("Не удалось загрузить 3D. Проверьте интернет и перезапустите апку.", true);
  } finally {
    characterHost.classList.remove("loading");
  }
}

function switchView(viewName) {
  Object.entries(views).forEach(([name, node]) => {
    if (!node) {
      return;
    }
    node.classList.toggle("active", name === viewName);
  });

  tabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });

  if (viewName === "character") {
    ensureCharacterScene().catch((error) => {
      console.error(error);
      setCharacterStatus("Ошибка загрузки 3D", true);
    });
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

    const messageByCode = {
      telegram_user_missing: "Не удалось получить Telegram user_id",
      missing_user_id: "Не передан user_id",
      profile_not_found: "Профиль не найден. Напишите /start боту и попробуйте снова.",
      db_unavailable: "База временно недоступна",
      db_read_failed: "Ошибка чтения профиля",
    };

    trophyStatus.textContent = messageByCode[error.message] || "Ошибка загрузки профиля";
  }
}

bootstrap();
