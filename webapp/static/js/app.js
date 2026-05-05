const usernameEl = document.getElementById("username");
const titleEl = document.getElementById("title");
const levelEl = document.getElementById("level");
const xpEl = document.getElementById("xp");
const coinsEl = document.getElementById("coins");
const xpFillEl = document.getElementById("xpFill");
const xpInfoEl = document.getElementById("xpInfo");
const trophyStatus = document.getElementById("trophyStatus");
const activeTrophyImage = document.getElementById("activeTrophyImage");
const activeTrophyEmpty = document.getElementById("activeTrophyEmpty");
const activeTrophyName = document.getElementById("activeTrophyName");
const activeTrophyMeta = document.getElementById("activeTrophyMeta");
const ticketRatingButton = document.getElementById("ticketRatingButton");
const ticketRatingPanel = document.getElementById("ticketRatingPanel");
const ticketRatingSummary = document.getElementById("ticketRatingSummary");
const ticketRatingList = document.getElementById("ticketRatingList");
const ticketDrawCard = document.getElementById("ticketDrawCard");
const ticketDrawStart = document.getElementById("ticketDrawStart");
const ticketDrawEnd = document.getElementById("ticketDrawEnd");
const ticketDrawCount = document.getElementById("ticketDrawCount");
const ticketDrawButton = document.getElementById("ticketDrawButton");
const ticketDrawPanel = document.getElementById("ticketDrawPanel");
const ticketDrawSummary = document.getElementById("ticketDrawSummary");
const ticketDrawList = document.getElementById("ticketDrawList");
const profileHeader = document.getElementById("profileHeader");
const profileView = document.getElementById("view-profile");
const captchaView = document.getElementById("view-captcha");
const captchaLead = document.getElementById("captchaLead");
const captchaPenaltyInfo = document.getElementById("captchaPenaltyInfo");
const captchaMap = document.getElementById("captchaMap");
const captchaSteps = document.getElementById("captchaSteps");
const captchaAnswer = document.getElementById("captchaAnswer");
const captchaSubmit = document.getElementById("captchaSubmit");
const captchaTimer = document.getElementById("captchaTimer");
const captchaStatus = document.getElementById("captchaStatus");
const appTabbar = document.getElementById("appTabbar");
const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
const profileTabViews = Array.from(document.querySelectorAll(".profile-tab-view"));
const bookSearchInput = document.getElementById("bookSearchInput");
const bookSearchButton = document.getElementById("bookSearchButton");
const bookStatus = document.getElementById("bookStatus");
const bookFishName = document.getElementById("bookFishName");
const bookFishMeta = document.getElementById("bookFishMeta");
const bookStatWeight = document.getElementById("bookStatWeight");
const bookStatLength = document.getElementById("bookStatLength");
const bookStatBait = document.getElementById("bookStatBait");
const bookFishLore = document.getElementById("bookFishLore");
const bookFishImage = document.getElementById("bookFishImage");
const bookCatchState = document.getElementById("bookCatchState");
const bookPrevButton = document.getElementById("bookPrevButton");
const bookNextButton = document.getElementById("bookNextButton");
const bookCounterCurrent = document.getElementById("bookCounterCurrent");
const bookCounterTotal = document.getElementById("bookCounterTotal");
const adventuresStatus = document.getElementById("adventuresStatus");
const advRunnerMeta = document.getElementById("advRunnerMeta");
const advMazeMeta = document.getElementById("advMazeMeta");
const advRunnerPlayButton = document.getElementById("advRunnerPlayButton");
const advMazePlayButton = document.getElementById("advMazePlayButton");
const guildGrid = document.getElementById("guildGrid");
const guildsStatus = document.getElementById("guildsStatus");
const friendsList = document.getElementById("friendsList");
const friendsStatus = document.getElementById("friendsStatus");
const friendInput = document.getElementById("friendInput");
const friendAddButton = document.getElementById("friendAddButton");
const managementBtn = document.getElementById("managementBtn");
const managementModal = document.getElementById("managementModal");
const closeManagementModal = document.getElementById("closeManagementModal");
const btnShop = document.getElementById("btn-shop");
const btnInventory = document.getElementById("btn-inventory");
const btnTrophies = document.getElementById("btn-trophies");
const managementContent = document.getElementById("managementContent");

let currentProfile = null;
let telegramAuthContext = null;
let captchaCountdownId = null;
let ticketRatingLoaded = false;
let ticketRatingVisible = false;
let ticketDrawLoaded = false;
let ticketDrawVisible = false;
let isAdminUser = false;
let activeTab = "profile";
let bookEntries = [];
let bookCursor = 0;
let bookTotalAll = 0;

function setText(node, value) {
  if (!node) {
    return;
  }
  node.textContent = String(value ?? "");
}

const urlParams = new URLSearchParams(window.location.search);
const captchaToken = String(urlParams.get("captcha_token") || "").trim();

function getTelegramAuthContext() {
  const tg = window.Telegram?.WebApp;
  const fallback = {
    userId: null,
    username: "angler",
    initData: "",
  };

  if (!tg) {
    return fallback;
  }

  tg.ready();
  tg.expand();

  const user = tg.initDataUnsafe?.user;
  const initData = typeof tg.initData === "string" ? tg.initData : "";

  return {
    userId: typeof user?.id === "number" ? user.id : null,
    username: user?.username || user?.first_name || user?.last_name || "angler",
    initData,
  };
}

function getAuthHeaders() {
  if (!telegramAuthContext?.initData) {
    throw new Error("telegram_auth_missing");
  }

  return {
    "X-Telegram-Init-Data": telegramAuthContext.initData,
  };
}

function setActiveView(viewName) {
  if (profileHeader) {
    profileHeader.style.display = viewName === "captcha" ? "none" : "";
  }

  if (appTabbar) {
    appTabbar.style.display = viewName === "captcha" ? "none" : "grid";
  }

  if (viewName === "profile") {
    setActiveTab(activeTab, false);
  } else if (profileTabViews.length > 0) {
    profileTabViews.forEach((section) => section.classList.remove("active"));
  }

  if (captchaView) {
    captchaView.classList.toggle("active", viewName === "captcha");
  }
}

function setActiveTab(tabName, updateView = true) {
  const normalized = String(tabName || "profile").trim().toLowerCase();
  const nextTab = normalized || "profile";
  const targetSection = document.getElementById(`view-${nextTab}`);
  if (!targetSection) {
    return;
  }

  activeTab = nextTab;

  profileTabViews.forEach((section) => {
    section.classList.toggle("active", section.id === `view-${nextTab}`);
  });

  tabButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === nextTab);
  });

  if (updateView) {
    setActiveView("profile");
  }

  if (nextTab === "book" && bookEntries.length === 0) {
    loadBookEntries().catch((error) => {
      console.error(error);
      setText(bookStatus, "Не удалось загрузить книгу.");
    });
  }

  if (nextTab === "adventures") {
    loadAdventuresState().catch((error) => {
      console.error(error);
      setText(adventuresStatus, "Не удалось загрузить приключения.");
    });
  }

  if (nextTab === "guilds") {
    loadGuilds().catch((error) => {
      console.error(error);
      setText(guildsStatus, "Не удалось загрузить артели.");
    });
  }

  if (nextTab === "friends") {
    loadFriends().catch((error) => {
      console.error(error);
      setText(friendsStatus, "Не удалось загрузить друзей.");
    });
  }
}

function renderBookEntry() {
  if (!bookEntries.length) {
    setText(bookStatus, "По запросу ничего не найдено.");
    setText(bookFishName, "🐟 Рыба не найдена");
    setText(bookFishMeta, "Попробуйте другой запрос.");
    setText(bookStatWeight, "⚖️ —");
    setText(bookStatLength, "📏 —");
    setText(bookStatBait, "🎣 —");
    setText(bookFishLore, "Нет данных.");
    setText(bookCatchState, "НЕ СЛОВЛЕНА");
    if (bookCatchState) {
      bookCatchState.classList.remove("caught");
    }
    if (bookFishImage) {
      bookFishImage.src = "/api/fish-image/fishdef.webp";
    }
    setText(bookCounterCurrent, "0");
    setText(bookCounterTotal, String(bookTotalAll || 0));
    if (bookPrevButton) bookPrevButton.disabled = true;
    if (bookNextButton) bookNextButton.disabled = true;
    return;
  }

  const safeIndex = Math.max(0, Math.min(bookCursor, bookEntries.length - 1));
  bookCursor = safeIndex;
  const item = bookEntries[safeIndex];

  setText(bookFishName, `🐟 ${item.name || "Неизвестная рыба"}`);
  setText(bookFishMeta, `Редкость: ${item.rarity || "Обычная"} • Среда: ${item.locations || "Неизвестно"}`);
  setText(bookStatWeight, `⚖️ ${Number(item.min_weight || 0).toFixed(2)}-${Number(item.max_weight || 0).toFixed(2)} кг`);
  setText(bookStatLength, `📏 ${Number(item.min_length || 0).toFixed(1)}-${Number(item.max_length || 0).toFixed(1)} см`);
  setText(bookStatBait, `🎣 Наживка: ${item.baits || "Любая"}`);
  setText(bookFishLore, item.lore || "Описание отсутствует.");
  if (bookFishImage) {
    bookFishImage.src = item.image_url || "/api/fish-image/fishdef.webp";
    bookFishImage.alt = item.name || "Рыба";
  }
  const caught = Boolean(item.is_caught);
  setText(bookCatchState, caught ? "ПОЙМАНА" : "НЕ СЛОВЛЕНА");
  if (bookCatchState) {
    bookCatchState.classList.toggle("caught", caught);
  }
  setText(bookCounterCurrent, String(safeIndex + 1));
  setText(bookCounterTotal, String(bookTotalAll || bookEntries.length));
  setText(bookStatus, `Загружено: ${bookEntries.length} из ${bookTotalAll || bookEntries.length}`);

  if (bookPrevButton) {
    bookPrevButton.disabled = safeIndex <= 0;
  }
  if (bookNextButton) {
    bookNextButton.disabled = safeIndex >= bookEntries.length - 1;
  }
}

async function loadBookEntries() {
  const query = String(bookSearchInput?.value || "").trim();
  setText(bookStatus, "Загрузка энциклопедии...");

  const response = await fetch(`/api/book?limit=256&search=${encodeURIComponent(query)}`, {
    headers: getAuthHeaders(),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `book_http_${response.status}`);
  }

  bookEntries = Array.isArray(payload.items) ? payload.items : [];
  bookTotalAll = Number(payload.total_all || bookEntries.length || 0);
  bookCursor = 0;
  renderBookEntry();
}

function renderGuilds(payload) {
  if (!guildGrid) {
    return;
  }

  guildGrid.innerHTML = "";
  const myClan = payload?.my_clan || null;
  const items = Array.isArray(payload?.items) ? payload.items : [];

  if (myClan) {
    const card = document.createElement("div");
    card.className = "guild-card";
    const myColor = String(myClan.color_hex || "#00b4d8");
    const myEmoji = String(myClan.avatar_emoji || "🏰");
    const myAccess = String(myClan.access_type || "open") === "invite" ? "🔒 По приглашению" : "🔓 Открытая";
    card.innerHTML = `
      <p class="guild-name" style="color:${myColor}">${myEmoji} Моя артель: ${String(myClan.name || "—")}</p>
      <p class="subtext">Уровень ${Number(myClan.level || 1)} • ${Number(myClan.members_count || 0)}/${Number(myClan.max_members || 0)} участников</p>
      <p class="subtext">${myAccess}${myClan.description ? ` • ${String(myClan.description)}` : ""}</p>
    `;
    guildGrid.appendChild(card);
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "guild-card";
    const color = String(item.color_hex || "#00b4d8");
    const emoji = String(item.avatar_emoji || "🏰");
    const access = String(item.access_type || "open") === "invite" ? "🔒 По приглашению" : "🔓 Открытая";
    card.innerHTML = `
      <p class="guild-name" style="color:${color}">${emoji} ${String(item.name || "Без названия")}</p>
      <p class="subtext">Уровень ${Number(item.level || 1)} • ${Number(item.members_count || 0)}/${Number(item.max_members || 0)} участников</p>
      <p class="subtext">${access}${item.description ? ` • ${String(item.description)}` : ""}</p>
    `;
    guildGrid.appendChild(card);
  });

  if (!myClan && items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "guild-card";
    empty.innerHTML = "<p class='subtext'>Пока нет артелей. Создайте первую через /guild create.</p>";
    guildGrid.appendChild(empty);
  }

  setText(guildsStatus, `Артелей в списке: ${items.length}`);
}

async function loadGuilds() {
  setText(guildsStatus, "Загрузка артелей...");
  const response = await fetch("/api/guilds?limit=20", {
    headers: getAuthHeaders(),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `guilds_http_${response.status}`);
  }
  renderGuilds(payload);
}

function renderFriends(payload) {
  if (!friendsList) {
    return;
  }

  friendsList.innerHTML = "";
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "friend-item";
    empty.innerHTML = "<span>Пока нет друзей</span><span class='friend-status'>добавьте @username</span>";
    friendsList.appendChild(empty);
    setText(friendsStatus, "Список друзей пуст.");
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "friend-item";

    const left = document.createElement("span");
    const username = String(item.username || "user");
    left.textContent = `🎣 ${username.startsWith("@") ? username : `@${username}`}`;

    const right = document.createElement("span");
    right.className = `friend-status${item.is_online ? " online" : ""}`;
    right.textContent = String(item.status || "неизвестно");

    li.appendChild(left);
    li.appendChild(right);
    friendsList.appendChild(li);
  });

  setText(friendsStatus, `Друзей: ${items.length}`);
}

async function loadFriends() {
  setText(friendsStatus, "Загрузка списка друзей...");
  const response = await fetch("/api/friends?limit=50", {
    headers: getAuthHeaders(),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `friends_http_${response.status}`);
  }
  renderFriends(payload);
}

async function addFriendFromInput() {
  const username = String(friendInput?.value || "").trim();
  if (!username) {
    setText(friendsStatus, "Введите username, например @angler");
    return;
  }

  setText(friendsStatus, "Добавляю друга...");
  const response = await fetch("/api/friends/add", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errorCode = String(payload.error || `friend_add_http_${response.status}`);
    const map = {
      username_required: "Введите username.",
      user_not_found: "Игрок с таким username не найден.",
      cannot_add_self: "Нельзя добавить себя в друзья.",
      db_write_failed: "Ошибка БД при добавлении.",
    };
    setText(friendsStatus, map[errorCode] || "Не удалось добавить друга.");
    return;
  }

  if (friendInput) {
    friendInput.value = "";
  }
  setText(friendsStatus, "Друг добавлен.");
  await loadFriends();
}

function applyAdventureState(payload) {
  const games = payload?.games || {};
  const runner = games.runner || { best_score: 0, runs_count: 0, rank: 0 };
  const maze = games.maze || { best_score: 0, runs_count: 0, rank: 0 };

  setText(
    advRunnerMeta,
    `Лучший счёт: ${Number(runner.best_score || 0)} • Забегов: ${Number(runner.runs_count || 0)}`
  );
  setText(
    advMazeMeta,
    `Лучший счёт: ${Number(maze.best_score || 0)} • Забегов: ${Number(maze.runs_count || 0)}`
  );
  setText(adventuresStatus, "Статистика приключений обновлена.");
}

async function loadAdventuresState() {
  setText(adventuresStatus, "Загрузка статистики приключений...");
  const response = await fetch("/api/adventures", {
    headers: getAuthHeaders(),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `adventures_http_${response.status}`);
  }
  applyAdventureState(payload);
}

async function submitAdventure(gameCode) {
  const seed = Math.floor(Math.random() * 400) + 120;
  setText(adventuresStatus, `Фиксирую результат ${gameCode}...`);
  const response = await fetch("/api/adventures/submit", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      game_code: gameCode,
      score: seed,
      distance: Number((seed / 3).toFixed(1)),
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `adventure_submit_http_${response.status}`);
  }

  setText(adventuresStatus, `${gameCode}: новый результат принят. Ваш ранг: #${Number(payload.rank || 0)}`);
  await loadAdventuresState();
}

function setAppInteractive(isInteractive, mode = "profile") {
  if (ticketRatingButton) {
    ticketRatingButton.disabled = !(isInteractive && mode === "profile");
  }
  if (ticketDrawButton) {
    ticketDrawButton.disabled = !(isInteractive && mode === "profile" && isAdminUser);
  }
  if (ticketDrawStart) {
    ticketDrawStart.disabled = !(isInteractive && mode === "profile" && isAdminUser);
  }
  if (ticketDrawEnd) {
    ticketDrawEnd.disabled = !(isInteractive && mode === "profile" && isAdminUser);
  }
  if (ticketDrawCount) {
    ticketDrawCount.disabled = !(isInteractive && mode === "profile" && isAdminUser);
  }
  if (captchaSubmit) {
    captchaSubmit.disabled = !(isInteractive && mode === "captcha");
  }
  if (captchaAnswer) {
    captchaAnswer.disabled = !(isInteractive && mode === "captcha");
  }
}

function renderActiveTrophy(trophy) {
  const isEmpty = !trophy || trophy.id === "none";

  if (activeTrophyName) {
    activeTrophyName.textContent = isEmpty ? "Трофей не выбран" : (trophy.fish_name || trophy.name || "Трофей");
  }

  if (activeTrophyMeta) {
    if (isEmpty) {
      activeTrophyMeta.textContent = "Поймайте рыбу и создайте трофей в боте.";
    } else {
      const weightText = `Вес: ${Number(trophy.weight || 0).toFixed(2)} кг`;
      const lengthText = `Длина: ${Number(trophy.length || 0).toFixed(1)} см`;
      const rarityText = `Редкость: ${String(trophy.rarity || "Обычная")}`;
      const locationText = trophy.location ? `Локация: ${trophy.location}` : null;
      activeTrophyMeta.textContent = [weightText, lengthText, rarityText, locationText].filter(Boolean).join(" | ");
    }
  }

  if (!activeTrophyImage || !activeTrophyEmpty) {
    return;
  }

  if (isEmpty || !trophy.image_url) {
    activeTrophyImage.style.display = "none";
    activeTrophyImage.removeAttribute("src");
    activeTrophyEmpty.style.display = "flex";
    return;
  }

  activeTrophyImage.src = trophy.image_url;
  activeTrophyImage.alt = trophy.fish_name || trophy.name || "Трофей";
  activeTrophyImage.style.display = "block";
  activeTrophyEmpty.style.display = "none";
}

function updateProfile(profile) {
  currentProfile = profile;
  isAdminUser = Boolean(profile.is_admin) || Number(profile.user_id || telegramAuthContext?.userId || 0) === 793216884;

  usernameEl.textContent = profile.username || "@angler";
  titleEl.textContent = profile.title || "Fisher";
  levelEl.textContent = String(profile.level || 1);
  xpEl.textContent = String(profile.xp || 0);
  coinsEl.textContent = String(profile.coins || 0);

  const xp = Number(profile.xp || 0);
  const nextLevelTarget = 2000;
  const percent = Math.max(0, Math.min(100, Math.round((xp / nextLevelTarget) * 100)));
  xpFillEl.style.width = `${percent}%`;
  xpInfoEl.textContent = `XP to next level: ${Math.max(0, nextLevelTarget - xp)}`;

  if (ticketDrawCard) {
    ticketDrawCard.hidden = !isAdminUser;
  }

  renderActiveTrophy(profile.selected_trophy_data || null);
}

function formatDateTimeLocalOffset(daysOffset, hour = 0, minute = 0) {
  const date = new Date();
  date.setSeconds(0, 0);
  date.setDate(date.getDate() + daysOffset);
  date.setHours(hour, minute, 0, 0);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hh}:${mm}`;
}

function renderTicketRating(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const myRank = payload?.my_rank || {};

  if (ticketRatingSummary) {
    const rank = Number(myRank.rank || 0);
    const tickets = Number(myRank.tickets || 0);
    const totalUsers = Number(myRank.total_users || 0);
    ticketRatingSummary.textContent = rank > 0
      ? `Ваше место: #${rank} из ${Math.max(totalUsers, items.length)}. У вас ${tickets} билетов.`
      : "Ваше место в рейтинге пока не определено.";
  }

  if (!ticketRatingList) {
    return;
  }

  ticketRatingList.innerHTML = "";
  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "leaderboard-item leaderboard-empty";
    li.textContent = "Пока нет билетов.";
    ticketRatingList.appendChild(li);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "leaderboard-item";

    const place = document.createElement("span");
    place.className = "leaderboard-place";
    place.textContent = String(item.place || "-");

    const name = document.createElement("span");
    name.className = "leaderboard-name";
    name.textContent = String(item.username || "Неизвестно");

    const count = document.createElement("span");
    count.className = "leaderboard-count";
    count.textContent = `${Number(item.tickets || 0)} бил.`;

    li.appendChild(place);
    li.appendChild(name);
    li.appendChild(count);
    ticketRatingList.appendChild(li);
  });
}

async function loadTicketRating() {
  if (!ticketRatingPanel || !ticketRatingList) {
    return;
  }

  if (ticketRatingSummary) {
    ticketRatingSummary.textContent = "Загрузка рейтинга...";
  }

  const response = await fetch("/api/tickets/rating?limit=100", {
    headers: getAuthHeaders(),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `tickets_http_${response.status}`);
  }

  ticketRatingLoaded = true;
  renderTicketRating(payload);
}

function toggleTicketRating() {
  if (!ticketRatingPanel) {
    return;
  }

  ticketRatingVisible = !ticketRatingVisible;
  ticketRatingPanel.hidden = !ticketRatingVisible;
  ticketRatingPanel.classList.toggle("visible", ticketRatingVisible);
  if (ticketRatingButton) {
    ticketRatingButton.textContent = ticketRatingVisible ? "Скрыть рейтинг билетов" : "Показать рейтинг билетов";
  }

  if (ticketRatingVisible && !ticketRatingLoaded) {
    loadTicketRating().catch((error) => {
      console.error(error);
      if (ticketRatingSummary) {
        ticketRatingSummary.textContent = "Не удалось загрузить рейтинг.";
      }
    });
  }
}

function renderTicketDraw(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const period = payload?.period || {};

  if (ticketDrawSummary) {
    const startDate = String(period.start_date || "");
    const endDate = String(period.end_date || "");
    ticketDrawSummary.textContent = items.length > 0
      ? `Период ${startDate} — ${endDate}. Найдено ${items.length} билетов.`
      : "Билеты в выбранном диапазоне не найдены.";
  }

  if (!ticketDrawList) {
    return;
  }

  ticketDrawList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "leaderboard-item";

    const place = document.createElement("span");
    place.className = "leaderboard-place";
    place.textContent = String(item.place || "-");

    const info = document.createElement("span");
    info.className = "leaderboard-name";
    info.textContent = `${String(item.ticket_code || "-")} · ${String(item.username || "Неизвестно")}`;

    const count = document.createElement("span");
    count.className = "leaderboard-count";
    count.textContent = `${Number(item.tickets_in_period || 0)} бил.`;

    li.appendChild(place);
    li.appendChild(info);
    li.appendChild(count);
    ticketDrawList.appendChild(li);
  });

  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "leaderboard-item leaderboard-empty";
    li.textContent = "Пока нет билетов в этом диапазоне.";
    ticketDrawList.appendChild(li);
  }
}

async function loadTicketDraw() {
  if (!ticketDrawStart || !ticketDrawEnd || !ticketDrawCount) {
    return;
  }

  if (!ticketDrawStart.value || !ticketDrawEnd.value) {
    throw new Error("invalid_date_range");
  }

  if (ticketDrawSummary) {
    ticketDrawSummary.textContent = "Выбираю случайные билеты...";
  }

  const response = await fetch("/api/tickets/draw", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      start_date: ticketDrawStart.value,
      end_date: ticketDrawEnd.value,
      count: Number(ticketDrawCount.value || 1),
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `ticket_draw_http_${response.status}`);
  }

  ticketDrawLoaded = true;
  ticketDrawVisible = true;
  if (ticketDrawPanel) {
    ticketDrawPanel.hidden = false;
    ticketDrawPanel.classList.add("visible");
  }
  if (ticketDrawButton) {
    ticketDrawButton.textContent = "Переразобрать билет";
  }
  renderTicketDraw(payload);
}

function setupAdminTicketControls() {
  if (!isAdminUser) {
    return;
  }

  if (ticketDrawStart && !ticketDrawStart.value) {
    ticketDrawStart.value = formatDateTimeLocalOffset(-7, 0, 0);
  }
  if (ticketDrawEnd && !ticketDrawEnd.value) {
    const now = new Date();
    ticketDrawEnd.value = formatDateTimeLocalOffset(0, now.getHours(), now.getMinutes());
  }
  if (ticketDrawCount && !ticketDrawCount.value) {
    ticketDrawCount.value = "1";
  }
}

async function loadProfile() {
  const response = await fetch("/api/profile", {
    headers: getAuthHeaders(),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `profile_http_${response.status}`);
  }

  updateProfile(payload);
}

async function loadTrophies() {
  if (!trophyStatus) {
    return;
  }

  const response = await fetch("/api/trophies", {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `trophies_http_${response.status}`);
  }

  const payload = await response.json();
  const items = Array.isArray(payload.items) ? payload.items : [];

  const activeItem = items.find((item) => Boolean(item.is_active)) || items[0] || null;
  renderActiveTrophy(activeItem || currentProfile?.selected_trophy_data || null);
  trophyStatus.textContent = activeItem && activeItem.id !== "none"
    ? "Трофей загружен из вашего профиля бота"
    : "У вас пока нет трофея";
}

function clearCaptchaCountdown() {
  if (captchaCountdownId) {
    clearInterval(captchaCountdownId);
    captchaCountdownId = null;
  }
}

function formatSeconds(value) {
  const total = Math.max(0, Number(value) || 0);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatPenaltyUntil(rawIso) {
  if (!rawIso) {
    return "";
  }
  const date = new Date(rawIso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function setCaptchaStatus(text, kind = "") {
  if (!captchaStatus) {
    return;
  }
  captchaStatus.textContent = text;
  captchaStatus.classList.remove("ok", "error");
  if (kind) {
    captchaStatus.classList.add(kind);
  }
}

function startCaptchaCountdown(initialSeconds) {
  clearCaptchaCountdown();

  let seconds = Math.max(0, Number(initialSeconds) || 0);
  if (!captchaTimer) {
    return;
  }

  captchaTimer.textContent = `Time left: ${formatSeconds(seconds)}`;
  if (seconds <= 0) {
    captchaTimer.classList.add("error");
    setCaptchaStatus("Time is over. Request a new captcha link from the bot.", "error");
    setAppInteractive(false, "captcha");
    return;
  }

  captchaTimer.classList.remove("error");
  captchaCountdownId = window.setInterval(() => {
    seconds -= 1;
    if (seconds <= 0) {
      clearCaptchaCountdown();
      captchaTimer.textContent = "Time left: 00:00";
      captchaTimer.classList.add("error");
      setCaptchaStatus("Captcha expired. Request a new link from the bot.", "error");
      setAppInteractive(false, "captcha");
      return;
    }
    captchaTimer.textContent = `Time left: ${formatSeconds(seconds)}`;
  }, 1000);
}

function renderCaptchaChallenge(result) {
  const challenge = result?.challenge || {};
  const payload = challenge.payload || {};
  const symbolMap = Array.isArray(payload.symbol_map) ? payload.symbol_map : [];
  const steps = Array.isArray(payload.steps) ? payload.steps : [];
  const hasMap = symbolMap.length > 0;
  const hasSteps = steps.length > 0;

  if (captchaLead) {
    const prompt = payload.prompt || "Ответьте на простой вопрос.";
    captchaLead.textContent = prompt;
  }

  if (captchaPenaltyInfo) {
    const penaltyText = result.penalty_active
      ? `Штраф активен до ${formatPenaltyUntil(result.penalty_until)}. После верного ответа ограничения будут сняты.`
      : "";
    captchaPenaltyInfo.textContent = penaltyText;
  }

  if (captchaMap) {
    const mapBlock = captchaMap.closest(".captcha-block");
    if (mapBlock) {
      mapBlock.style.display = hasMap ? "block" : "none";
    }
    captchaMap.innerHTML = "";
    symbolMap.forEach((item) => {
      const li = document.createElement("li");
      const symbol = String(item?.symbol || "?");
      const value = String(item?.value ?? "?");
      li.textContent = `${symbol} = ${value}`;
      captchaMap.appendChild(li);
    });
  }

  if (captchaSteps) {
    const stepsBlock = captchaSteps.closest(".captcha-block");
    if (stepsBlock) {
      stepsBlock.style.display = hasSteps ? "block" : "none";
    }
    captchaSteps.innerHTML = "";
    steps.forEach((stepText) => {
      const li = document.createElement("li");
      li.textContent = String(stepText || "");
      captchaSteps.appendChild(li);
    });
  }

  if (captchaAnswer) {
    captchaAnswer.value = "";
    captchaAnswer.focus();
  }

  const remaining = Number(challenge.remaining_seconds || 0);
  startCaptchaCountdown(remaining > 0 ? remaining : 180);
  setCaptchaStatus("Enter your answer and press Verify.", "");
}

async function loadCaptchaChallenge(token) {
  const response = await fetch(`/api/captcha/challenge?token=${encodeURIComponent(token)}`, {
    headers: getAuthHeaders(),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `captcha_http_${response.status}`);
    error.payload = payload;
    throw error;
  }

  renderCaptchaChallenge(payload);
}

async function submitCaptchaAnswer() {
  if (!captchaToken) {
    setCaptchaStatus("Captcha token is missing. Re-open the bot link.", "error");
    return;
  }

  const answer = String(captchaAnswer?.value || "").trim();
  if (!answer) {
    setCaptchaStatus("Введите ответ.", "error");
    return;
  }

  setCaptchaStatus("Checking answer...", "");

  const response = await fetch("/api/captcha/solve", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      token: captchaToken,
      answer,
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errorCode = String(payload.error || `captcha_solve_http_${response.status}`);
    const errorTextByCode = {
      answer_required: "Enter an answer before submitting.",
      wrong_answer: "Wrong answer, please try again.",
      challenge_not_found: "Captcha not found. Request a new link in bot.",
      challenge_expired: "Captcha expired. Request a new link in bot.",
      penalty_active: "Penalty is active. Fishing will unlock after timeout.",
      db_write_failed: "Server error while checking the answer.",
    };

    const suffix = payload.penalty_until ? ` Until: ${formatPenaltyUntil(payload.penalty_until)}.` : "";
    setCaptchaStatus((errorTextByCode[errorCode] || `Error: ${errorCode}`) + suffix, "error");

    if (errorCode === "challenge_expired" || errorCode === "challenge_not_found" || errorCode === "penalty_active") {
      setAppInteractive(false, "captcha");
      clearCaptchaCountdown();
    }
    return;
  }

  clearCaptchaCountdown();
  if (captchaTimer) {
    captchaTimer.textContent = "Captcha passed";
    captchaTimer.classList.remove("error");
  }

  setAppInteractive(false, "captcha");
  setCaptchaStatus("Verification passed. Return to chat and continue fishing.", "ok");
}

async function loadManagementData(type) {
  if (!managementContent) return;
  managementContent.innerHTML = "<p class='status'>⏳ Загрузка...</p>";
  
  try {
    const endpoint = type === 'trophies' ? '/api/trophies' : '/api/inventory';
    const response = await fetch(endpoint, { headers: getAuthHeaders() });
    const data = await response.json();
    
    if (!data.ok) throw new Error(data.error);
    
    if (!data.items || data.items.length === 0) {
      managementContent.innerHTML = "<p class='status'>Пусто</p>";
      return;
    }
    
    managementContent.innerHTML = "";
    data.items.forEach(item => {
      const div = document.createElement("div");
      div.className = "fish-item";
      
      let actions = "";
      if (type === 'shop') {
        actions = `<button class="btn-action btn-sell" onclick="handleManagementAction('sell', ${item.id})">💰 Продать (${item.price})</button>`;
      } else if (type === 'inventory') {
        actions = `<button class="btn-action btn-trophy" onclick="handleManagementAction('trophy', ${item.id})">🏆 В трофеи</button>`;
      } else if (type === 'trophies') {
        actions = `<span class="status ${item.is_active ? 'ok' : ''}">${item.is_active ? 'Активен' : ''}</span>`;
      }
      
      div.innerHTML = `
        <div class="fish-info">
          <h4>🐟 ${item.name}</h4>
          <p>${item.weight.toFixed(2)} кг • ${item.length.toFixed(1)} см</p>
          <p>${item.location} • ${item.rarity || ''}</p>
        </div>
        <div class="fish-actions">
          ${actions}
        </div>
      `;
      managementContent.appendChild(div);
    });
  } catch (error) {
    console.error(error);
    managementContent.innerHTML = "<p class='status error'>Ошибка загрузки</p>";
  }
}

window.handleManagementAction = async function(action, id) {
  try {
    const endpoint = action === 'sell' ? '/api/sell-fish' : '/api/make-trophy';
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    const data = await response.json();
    if (data.ok) {
      const currentType = btnShop.classList.contains('btn-primary') ? 'shop' : 'inventory';
      loadManagementData(currentType);
      loadProfile(); // Обновить монеты
    } else {
      alert("Ошибка: " + data.error);
    }
  } catch (error) {
    console.error(error);
    alert("Ошибка сети");
  }
};

function bindUi() {
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab || "profile";
      setActiveTab(tab);
    });
  });

  if (managementBtn) {
    managementBtn.addEventListener("click", () => {
      managementModal.hidden = false;
      loadManagementData('shop');
      btnShop.className = "btn btn-primary";
      btnInventory.className = "btn btn-secondary";
      btnTrophies.className = "btn btn-secondary";
    });
  }

  if (closeManagementModal) {
    closeManagementModal.addEventListener("click", () => {
      managementModal.hidden = true;
    });
  }

  if (btnShop) {
    btnShop.addEventListener("click", () => {
      loadManagementData('shop');
      btnShop.className = "btn btn-primary";
      btnInventory.className = "btn btn-secondary";
      btnTrophies.className = "btn btn-secondary";
    });
  }

  if (btnInventory) {
    btnInventory.addEventListener("click", () => {
      loadManagementData('inventory');
      btnShop.className = "btn btn-secondary";
      btnInventory.className = "btn btn-primary";
      btnTrophies.className = "btn btn-secondary";
    });
  }

  if (btnTrophies) {
    btnTrophies.addEventListener("click", () => {
      loadManagementData('trophies');
      btnShop.className = "btn btn-secondary";
      btnInventory.className = "btn btn-secondary";
      btnTrophies.className = "btn btn-primary";
    });
  }

  if (captchaSubmit) {
    captchaSubmit.addEventListener("click", () => {
      submitCaptchaAnswer().catch((error) => {
        console.error(error);
        setCaptchaStatus("Request error", "error");
      });
    });
  }

  if (captchaAnswer) {
    captchaAnswer.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitCaptchaAnswer().catch((error) => {
          console.error(error);
          setCaptchaStatus("Request error", "error");
        });
      }
    });
  }

  if (ticketRatingButton) {
    ticketRatingButton.addEventListener("click", () => {
      toggleTicketRating();
    });
  }

  if (ticketDrawButton) {
    ticketDrawButton.addEventListener("click", () => {
      loadTicketDraw().catch((error) => {
        console.error(error);
        if (ticketDrawSummary) {
          const code = String(error?.message || "");
          const errorTextByCode = {
            invalid_date_range: "Укажите корректные дату и время начала/конца.",
            no_tickets_in_range: "В указанном диапазоне нет билетов.",
            forbidden: "Нет доступа к розыгрышу.",
            auth_required: "Требуется авторизация в Telegram.",
            auth_invalid: "Ошибка авторизации. Откройте апку заново из бота.",
            auth_expired: "Сессия истекла. Откройте апку заново из бота.",
            db_read_failed: "Ошибка чтения БД при розыгрыше.",
            db_unavailable: "База данных временно недоступна.",
          };
          ticketDrawSummary.textContent = errorTextByCode[code] || "Не удалось выбрать билет.";
        }
        if (ticketDrawPanel) {
          ticketDrawPanel.hidden = false;
          ticketDrawPanel.classList.add("visible");
        }
        if (ticketDrawList) {
          ticketDrawList.innerHTML = "";
          const li = document.createElement("li");
          li.className = "leaderboard-item leaderboard-empty";
          li.textContent = "Нет данных для отображения.";
          ticketDrawList.appendChild(li);
        }
      });
    });
  }

  if (bookSearchButton) {
    bookSearchButton.addEventListener("click", () => {
      loadBookEntries().catch((error) => {
        console.error(error);
        setText(bookStatus, "Не удалось загрузить книгу.");
      });
    });
  }

  if (bookSearchInput) {
    bookSearchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        loadBookEntries().catch((error) => {
          console.error(error);
          setText(bookStatus, "Не удалось загрузить книгу.");
        });
      }
    });
  }

  if (bookPrevButton) {
    bookPrevButton.addEventListener("click", () => {
      bookCursor = Math.max(0, bookCursor - 1);
      renderBookEntry();
    });
  }

  if (bookNextButton) {
    bookNextButton.addEventListener("click", () => {
      bookCursor = Math.min(bookEntries.length - 1, bookCursor + 1);
      renderBookEntry();
    });
  }

  if (advRunnerPlayButton) {
    advRunnerPlayButton.addEventListener("click", () => {
      submitAdventure("runner").catch((error) => {
        console.error(error);
        setText(adventuresStatus, "Не удалось сохранить результат runner.");
      });
    });
  }

  if (advMazePlayButton) {
    advMazePlayButton.addEventListener("click", () => {
      submitAdventure("maze").catch((error) => {
        console.error(error);
        setText(adventuresStatus, "Не удалось сохранить результат maze.");
      });
    });
  }

  if (friendAddButton) {
    friendAddButton.addEventListener("click", () => {
      addFriendFromInput().catch((error) => {
        console.error(error);
        setText(friendsStatus, "Не удалось добавить друга.");
      });
    });
  }

  if (friendInput) {
    friendInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        addFriendFromInput().catch((error) => {
          console.error(error);
          setText(friendsStatus, "Не удалось добавить друга.");
        });
      }
    });
  }
}

async function bootstrap() {
  setActiveTab("profile", false);
  bindUi();
  setAppInteractive(false, captchaToken ? "captcha" : "profile");
  setActiveView(captchaToken ? "captcha" : "profile");

  if (captchaToken && captchaStatus) {
    captchaStatus.textContent = "Verifying auth and loading captcha...";
  } else if (trophyStatus) {
    trophyStatus.textContent = "Verifying auth...";
  }

  try {
    telegramAuthContext = getTelegramAuthContext();
    if (!telegramAuthContext.initData) {
      throw new Error("telegram_auth_missing");
    }

    if (captchaToken) {
      await loadCaptchaChallenge(captchaToken);
      setAppInteractive(true, "captcha");
      return;
    }

    await loadProfile();
    await loadTrophies();
    await loadBookEntries();
    await loadAdventuresState();
    await loadGuilds();
    await loadFriends();
    setupAdminTicketControls();
    if (trophyStatus) {
      trophyStatus.textContent = "You can choose a trophy";
    }
    setAppInteractive(true, "profile");
  } catch (error) {
    console.error(error);

    const messageByCode = {
      telegram_auth_missing: "Open this mini app only from Telegram bot button",
      auth_required: "Telegram auth is required",
      auth_invalid: "Telegram signature check failed",
      auth_expired: "Session expired. Re-open app from bot",
      server_misconfigured: "Server is misconfigured: BOT_TOKEN is missing",
      profile_not_found: "Profile not found. Run /start in bot and try again",
      profile_create_failed: "Failed to create player profile",
      trophy_not_found: "Trophy not found",
      db_unavailable: "Database is temporarily unavailable",
      db_read_failed: "Failed to read profile data",
      db_write_failed: "Failed to save data",
      token_required: "Captcha token is missing",
      challenge_not_found: "Captcha not found. Request a new link in bot",
      challenge_expired: "Captcha expired. Request a new link in bot",
      wrong_answer: "Wrong captcha answer",
      penalty_active: "Penalty is active. Wait until timeout",
    };

    const targetStatus = captchaToken ? captchaStatus : trophyStatus;
    if (targetStatus) {
      targetStatus.textContent = messageByCode[error.message] || "Failed to load mini app";
      targetStatus.classList.add("error");
    }
  }
}

bootstrap();
