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
const activeTrophyImage = document.getElementById("activeTrophyImage");
const activeTrophyEmpty = document.getElementById("activeTrophyEmpty");
const activeTrophyName = document.getElementById("activeTrophyName");
const activeTrophyMeta = document.getElementById("activeTrophyMeta");
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

let currentProfile = null;
let telegramAuthContext = null;
let trophyById = {};
let captchaCountdownId = null;

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

  if (profileView) {
    profileView.classList.toggle("active", viewName === "profile");
  }
  if (captchaView) {
    captchaView.classList.toggle("active", viewName === "captcha");
  }
}

function setAppInteractive(isInteractive, mode = "profile") {
  if (saveTrophyButton) {
    saveTrophyButton.disabled = !(isInteractive && mode === "profile");
  }
  if (trophySelect) {
    trophySelect.disabled = !(isInteractive && mode === "profile");
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
    activeTrophyName.textContent = isEmpty ? "No trophy selected" : (trophy.fish_name || trophy.name || "Trophy");
  }

  if (activeTrophyMeta) {
    if (isEmpty) {
      activeTrophyMeta.textContent = "Choose a trophy from the list above.";
    } else {
      const weightText = `Weight: ${Number(trophy.weight || 0).toFixed(2)} kg`;
      const lengthText = `Length: ${Number(trophy.length || 0).toFixed(1)} cm`;
      const locationText = trophy.location ? `Location: ${trophy.location}` : null;
      activeTrophyMeta.textContent = [weightText, lengthText, locationText].filter(Boolean).join(" | ");
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
  activeTrophyImage.alt = trophy.fish_name || trophy.name || "Trophy";
  activeTrophyImage.style.display = "block";
  activeTrophyEmpty.style.display = "none";
}

function updateProfile(profile) {
  currentProfile = profile;

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

  renderActiveTrophy(profile.selected_trophy_data || null);
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
  const response = await fetch("/api/trophies", {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `trophies_http_${response.status}`);
  }

  const payload = await response.json();
  const items = Array.isArray(payload.items) ? payload.items : [];
  trophyById = {};

  trophySelect.innerHTML = "";
  items.forEach((item) => {
    trophyById[item.id] = item;

    const option = document.createElement("option");
    option.value = item.id;
    if (item.id === "none") {
      option.textContent = item.name;
    } else {
      const weightText = Number(item.weight || 0).toFixed(2);
      const lengthText = Number(item.length || 0).toFixed(1);
      option.textContent = `${item.name} (${weightText} kg, ${lengthText} cm)`;
    }
    trophySelect.appendChild(option);
  });

  const selected = currentProfile?.selected_trophy || "none";
  if (items.some((item) => item.id === selected)) {
    trophySelect.value = selected;
  }

  const selectedItem = trophyById[trophySelect.value] || null;
  renderActiveTrophy(selectedItem || currentProfile?.selected_trophy_data || null);
}

async function saveTrophySelection() {
  const trophyId = trophySelect.value;
  trophyStatus.textContent = "Saving...";

  const response = await fetch("/api/trophy/select", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ trophy_id: trophyId }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    trophyStatus.textContent = payload.error ? `Error: ${payload.error}` : "Failed to save selection";
    return;
  }

  const payload = await response.json();
  if (payload.ok) {
    const selectedId = payload.selected_trophy || trophyId;
    if (currentProfile) {
      currentProfile.selected_trophy = selectedId;
      currentProfile.selected_trophy_data = trophyById[selectedId] || null;
    }
    renderActiveTrophy(trophyById[selectedId] || null);
    trophyStatus.textContent = "Trophy saved";
  } else {
    trophyStatus.textContent = "Save error";
  }
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

function bindUi() {
  if (saveTrophyButton) {
    saveTrophyButton.addEventListener("click", () => {
      saveTrophySelection().catch((error) => {
        console.error(error);
        if (trophyStatus) {
          trophyStatus.textContent = "Request error";
        }
      });
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
}

async function bootstrap() {
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
