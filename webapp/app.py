from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl

from flask import Flask, jsonify, render_template, request

try:
	from database import db as fish_db
except Exception:
	fish_db = None


logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent

app = Flask(
	__name__,
	template_folder=str(BASE_DIR / "templates"),
	static_folder=str(BASE_DIR / "static"),
)


DEFAULT_TROPHIES = [
	{"id": "none", "name": "Без трофея"},
	{"id": "shark_tooth", "name": "Зуб акулы"},
	{"id": "gold_hook", "name": "Золотой крюк"},
	{"id": "deep_pearl", "name": "Жемчужина глубин"},
]


def _normalize_username(value: str | None) -> str:
	safe_username = (value or "angler").strip() or "angler"
	if not safe_username.startswith("@"):
		safe_username = f"@{safe_username}"
	return safe_username


def _safe_int(value: str | None) -> Optional[int]:
	if value is None:
		return None
	try:
		return int(str(value).strip())
	except (TypeError, ValueError):
		return None


def _build_title(level: int) -> str:
	if level >= 30:
		return "Легенда глубин"
	if level >= 20:
		return "Грозa штормов"
	if level >= 10:
		return "Морской охотник"
	return "Молодой рыбак"


def _auth_error_status(error_code: str) -> int:
	if error_code == "server_misconfigured":
		return 500
	return 401


def _verify_telegram_init_data(init_data: str) -> tuple[Optional[dict], Optional[str]]:
	bot_token = (os.getenv("BOT_TOKEN") or "").strip()
	if not bot_token:
		return None, "server_misconfigured"

	try:
		payload = dict(parse_qsl(init_data, keep_blank_values=True))
	except Exception:
		return None, "auth_invalid"

	received_hash = str(payload.pop("hash", "")).strip()
	if not received_hash:
		return None, "auth_invalid"

	data_check_string = "\n".join(
		f"{key}={value}" for key, value in sorted(payload.items(), key=lambda item: item[0])
	)
	secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
	expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

	if not hmac.compare_digest(expected_hash, received_hash):
		return None, "auth_invalid"

	auth_date = _safe_int(payload.get("auth_date"))
	max_age_seconds = _safe_int(os.getenv("WEBAPP_AUTH_MAX_AGE_SEC")) or 86400
	if auth_date is None:
		return None, "auth_invalid"
	if max_age_seconds > 0 and int(time.time()) - auth_date > max_age_seconds:
		return None, "auth_expired"

	raw_user = payload.get("user")
	if not raw_user:
		return None, "auth_invalid"

	try:
		user_payload = json.loads(raw_user)
	except (TypeError, ValueError, json.JSONDecodeError):
		return None, "auth_invalid"

	user_id = _safe_int(user_payload.get("id"))
	if not user_id:
		return None, "auth_invalid"

	username = user_payload.get("username") or user_payload.get("first_name") or user_payload.get("last_name")
	return {"id": user_id, "username": username}, None


def _get_verified_user_from_request() -> tuple[Optional[dict], Optional[str]]:
	init_data = (request.headers.get("X-Telegram-Init-Data") or request.args.get("init_data") or "").strip()
	if not init_data:
		return None, "auth_required"
	return _verify_telegram_init_data(init_data)


@app.get("/")
def index():
	return render_template("index.html")


@app.get("/health")
def health():
	return jsonify({"ok": True})


@app.get("/api/profile")
def profile():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	fallback_username = auth_user.get("username")
	logger.info("WebApp verified access user_id=%s username=%s", user_id, fallback_username or "")

	if fish_db is None:
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		player = fish_db.get_player(user_id, -1)
	except Exception:
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

	if not player:
		default_username = str(fallback_username or f"user_{user_id}")
		try:
			player = fish_db.create_player(user_id, default_username, -1)
		except Exception:
			return jsonify({"ok": False, "error": "profile_create_failed"}), 500

	if not player:
		return jsonify({"ok": False, "error": "profile_not_found"}), 404

	level = int(player.get("level") or 0)
	payload = {
		"username": _normalize_username(player.get("username") or fallback_username),
		"level": level,
		"xp": int(player.get("xp") or 0),
		"coins": int(player.get("coins") or 0),
		"title": _build_title(level),
		"selected_trophy": "none",
	}
	return jsonify(payload)


@app.get("/api/trophies")
def trophies():
	_, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	return jsonify({"items": DEFAULT_TROPHIES})


@app.post("/api/trophy/select")
def select_trophy():
	_, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	data = request.get_json(silent=True) or {}
	trophy_id = str(data.get("trophy_id") or "").strip()
	known_ids = {item["id"] for item in DEFAULT_TROPHIES}

	if trophy_id not in known_ids:
		return jsonify({"ok": False, "error": "invalid_trophy"}), 400

	# This is intentionally non-persistent for now.
	# Later it can be wired to DB by telegram user id.
	return jsonify({"ok": True, "selected_trophy": trophy_id})


if __name__ == "__main__":
	# Railway sets PORT dynamically for public HTTP services.
	port = int(os.getenv("PORT") or os.getenv("APP_PORT", "8008"))
	app.run(
		host=os.getenv("APP_HOST", "0.0.0.0"),
		port=port,
		debug=os.getenv("APP_DEBUG", "0") == "1",
	)
