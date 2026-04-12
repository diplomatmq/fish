from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl

from flask import Flask, jsonify, render_template, request, send_from_directory


logger = logging.getLogger(__name__)
fish_db = None
fish_db_import_error: Exception | None = None


def _get_fish_db():
	global fish_db, fish_db_import_error
	if fish_db is not None:
		return fish_db

	try:
		project_root = Path(__file__).resolve().parent.parent
		project_root_str = str(project_root)
		if project_root_str not in sys.path:
			sys.path.insert(0, project_root_str)

		from database import db as imported_db
		fish_db = imported_db
		fish_db_import_error = None
	except Exception as exc:
		fish_db = None
		fish_db_import_error = exc
		logger.exception("WebApp DB import failed")

	return fish_db


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
TROPHY_ID_PREFIX = "trophy_"

app = Flask(
	__name__,
	template_folder=str(BASE_DIR / "templates"),
	static_folder=str(BASE_DIR / "static"),
)


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


def _parse_date_input(value: str | None, end_of_day: bool = False) -> Optional[datetime]:
	raw = str(value or "").strip()
	if not raw:
		return None
	for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
		try:
			parsed = datetime.strptime(raw, fmt)
			if fmt == "%Y-%m-%d" and end_of_day:
				return parsed.replace(hour=23, minute=59, second=59)
			if fmt == "%Y-%m-%d" and not end_of_day:
				return parsed.replace(hour=0, minute=0, second=0)
			return parsed
		except Exception:
			continue
	return None


def _build_title(level: int) -> str:
	if level >= 30:
		return "Легенда глубин"
	if level >= 20:
		return "Грозa штормов"
	if level >= 10:
		return "Морской охотник"
	return "Молодой рыбак"


def _safe_image_file_name(filename: str | None) -> str:
	raw = str(filename or "").strip()
	if not raw:
		return "fishdef.webp"

	name = Path(raw).name
	if name != raw:
		return "fishdef.webp"
	if Path(name).suffix.lower() not in {".webp", ".png", ".jpg", ".jpeg"}:
		return "fishdef.webp"
	return name


def _format_trophy_id(trophy: dict | None) -> str:
	if not trophy:
		return "none"
	try:
		return f"{TROPHY_ID_PREFIX}{int(trophy.get('id') or 0)}"
	except (TypeError, ValueError):
		return "none"


def _parse_trophy_id(value: str | None) -> Optional[int]:
	raw = str(value or "").strip()
	if not raw or raw == "none":
		return None
	if raw.startswith(TROPHY_ID_PREFIX):
		raw = raw[len(TROPHY_ID_PREFIX):]
	return _safe_int(raw)


def _build_trophy_payload(trophy: dict | None) -> Optional[dict]:
	if not trophy:
		return None

	image_file = _safe_image_file_name(trophy.get("image_file"))
	try:
		weight = float(trophy.get("weight") or 0)
	except (TypeError, ValueError):
		weight = 0.0
	try:
		length = float(trophy.get("length") or 0)
	except (TypeError, ValueError):
		length = 0.0

	name = str(trophy.get("fish_name") or "Неизвестная рыба")
	return {
		"id": _format_trophy_id(trophy),
		"name": name,
		"fish_name": name,
		"weight": round(weight, 2),
		"length": round(length, 1),
		"location": trophy.get("location"),
		"image_url": f"/api/fish-image/{image_file}",
		"is_active": bool(int(trophy.get("is_active") or 0)),
	}


def _auth_error_status(error_code: str) -> int:
	if error_code == "server_misconfigured":
		return 500
	return 401


def _captcha_error_status(error_code: str) -> int:
	if error_code in {"token_required", "answer_required", "wrong_answer"}:
		return 400
	if error_code == "challenge_not_found":
		return 404
	if error_code == "challenge_expired":
		return 410
	if error_code == "penalty_active":
		return 423
	return 400


def _verify_telegram_init_data(init_data: str) -> tuple[Optional[dict], Optional[str]]:
	bot_token = (os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
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
	captcha_mode = bool(str(request.args.get("captcha_token") or "").strip())
	return render_template("index.html", captcha_mode=captcha_mode)


@app.get("/health")
def health():
	return jsonify({"ok": True})


@app.get("/api/fish-image/<path:filename>")
def fish_image(filename: str):
	safe_name = _safe_image_file_name(filename)
	target = PROJECT_ROOT / safe_name
	if not target.exists() or not target.is_file():
		fallback = PROJECT_ROOT / "fishdef.webp"
		if fallback.exists() and fallback.is_file():
			return send_from_directory(str(PROJECT_ROOT), "fishdef.webp")
		return jsonify({"ok": False, "error": "image_not_found"}), 404

	return send_from_directory(str(PROJECT_ROOT), safe_name)


@app.get("/api/profile")
def profile():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	fallback_username = auth_user.get("username")
	logger.info("WebApp verified access user_id=%s username=%s", user_id, fallback_username or "")

	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	player = None
	for chat_id in (-1, 0):
		try:
			player = db.get_player(user_id, chat_id)
		except Exception:
			logger.exception("WebApp profile read failed for user_id=%s chat_id=%s", user_id, chat_id)
			continue
		if player:
			break

	if not player:
		default_username = str(fallback_username or f"user_{user_id}")
		try:
			player = db.create_player(user_id, default_username, -1)
		except Exception:
			logger.exception("WebApp profile create failed for user_id=%s", user_id)
			return jsonify({"ok": False, "error": "profile_create_failed"}), 500

	if not player:
		for chat_id in (-1, 0):
			try:
				player = db.get_player(user_id, chat_id)
			except Exception:
				continue
			if player:
				break

	if not player:
		return jsonify({"ok": False, "error": "profile_not_found"}), 404

	try:
		trophy_items = db.get_player_trophies(user_id)
	except Exception:
		logger.exception("WebApp trophy read failed for user_id=%s", user_id)
		trophy_items = []

	active_trophy = next((item for item in trophy_items if int(item.get("is_active") or 0) == 1), None)
	if not active_trophy and trophy_items:
		active_trophy = trophy_items[0]

	level = int(player.get("level") or 0)
	payload = {
		"user_id": user_id,
		"is_admin": user_id == 793216884,
		"username": _normalize_username(player.get("username") or fallback_username),
		"level": level,
		"xp": int(player.get("xp") or 0),
		"coins": int(player.get("coins") or 0),
		"title": _build_title(level),
		"selected_trophy": _format_trophy_id(active_trophy),
		"selected_trophy_data": _build_trophy_payload(active_trophy),
	}
	return jsonify(payload)


@app.get("/api/trophies")
def trophies():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		trophies = db.get_player_trophies(user_id)
	except Exception:
		logger.exception("WebApp trophies read failed for user_id=%s", user_id)
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

	items = []
	for trophy in trophies:
		payload = _build_trophy_payload(trophy)
		if payload:
			items.append(payload)

	if not items:
		items = [{
			"id": "none",
			"name": "Без трофея",
			"fish_name": "Без трофея",
			"weight": 0,
			"length": 0,
			"location": None,
			"image_url": None,
			"is_active": True,
		}]

	return jsonify({"items": items})


@app.post("/api/trophy/select")
def select_trophy():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	data = request.get_json(silent=True) or {}
	trophy_id_raw = str(data.get("trophy_id") or "").strip()
	if trophy_id_raw == "none":
		return jsonify({"ok": True, "selected_trophy": "none"})

	trophy_id = _parse_trophy_id(trophy_id_raw)
	if not trophy_id:
		return jsonify({"ok": False, "error": "invalid_trophy"}), 400

	try:
		updated = db.set_active_trophy(user_id, trophy_id)
	except Exception:
		logger.exception("WebApp set trophy failed for user_id=%s trophy_id=%s", user_id, trophy_id)
		return jsonify({"ok": False, "error": "db_write_failed"}), 500

	if not updated:
		return jsonify({"ok": False, "error": "trophy_not_found"}), 404

	return jsonify({"ok": True, "selected_trophy": _format_trophy_id({"id": trophy_id})})


@app.get("/api/tickets/rating")
def tickets_rating():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	limit = _safe_int(request.args.get("limit")) or 100
	limit = max(1, min(limit, 100))

	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		rows = db.get_tickets_leaderboard(limit=limit)
		my_rank = db.get_user_tickets_rank(user_id)
	except Exception:
		logger.exception("WebApp ticket rating read failed for user_id=%s", user_id)
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

	items = []
	for idx, row in enumerate(rows, start=1):
		items.append({
			"place": idx,
			"user_id": int(row.get("user_id") or 0),
			"username": str(row.get("username") or "Неизвестно"),
			"tickets": int(row.get("tickets") or 0),
		})

	return jsonify({
		"ok": True,
		"items": items,
		"my_rank": my_rank,
		"limit": limit,
	})


@app.post("/api/tickets/draw")
def tickets_draw():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	if user_id != 793216884:
		return jsonify({"ok": False, "error": "forbidden"}), 403

	data = request.get_json(silent=True) or {}
	start_date = _parse_date_input(data.get("start_date"), end_of_day=False)
	end_date = _parse_date_input(data.get("end_date"), end_of_day=True)
	count = _safe_int(data.get("count")) or 1
	count = max(1, min(count, 100))

	if not start_date or not end_date:
		return jsonify({"ok": False, "error": "invalid_date_range"}), 400
	if start_date > end_date:
		return jsonify({"ok": False, "error": "invalid_date_range"}), 400

	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		draws = db.get_random_tickets_in_period(start_date, end_date, limit=count)
		user_counts = db.get_ticket_counts_for_users_in_period(
			[user_id for user_id in {int(row.get("user_id") or 0) for row in draws}],
			start_date,
			end_date,
		)
	except Exception:
		logger.exception("WebApp ticket draw failed for user_id=%s", user_id)
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

	if not draws:
		return jsonify({
			"ok": True,
			"items": [],
			"period": {
				"start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
				"end_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),
				"count": 0,
			},
		})

	items = []
	for idx, row in enumerate(draws, start=1):
		row_user_id = int(row.get("user_id") or 0)
		items.append({
			"place": idx,
			"ticket_code": row.get("ticket_code"),
			"user_id": row_user_id,
			"username": str(row.get("username") or "Неизвестно"),
			"tickets_in_period": int(user_counts.get(row_user_id, 0)),
			"created_at": row.get("created_at"),
			"source_type": row.get("source_type"),
			"source_ref": row.get("source_ref"),
		})

	return jsonify({
		"ok": True,
		"items": items,
		"period": {
			"start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
			"end_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),
			"count": len(items),
		},
	})


@app.get("/api/tickets/random")
def tickets_random():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		row = db.get_random_ticket()
	except Exception:
		logger.exception("WebApp random ticket draw failed for user_id=%s", auth_user.get("id"))
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

	if not row:
		return jsonify({"ok": False, "error": "no_tickets"}), 404

	return jsonify({
		"ok": True,
		"ticket": {
			"ticket_code": row.get("ticket_code"),
			"award_id": row.get("award_id"),
			"user_id": row.get("user_id"),
			"username": row.get("username"),
			"source_type": row.get("source_type"),
			"source_ref": row.get("source_ref"),
			"created_at": row.get("created_at"),
		},
	})


@app.get("/api/captcha/challenge")
def captcha_challenge():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	token = str(request.args.get("token") or request.args.get("captcha_token") or "").strip()

	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		result = db.get_antibot_challenge_for_user(user_id, token)
	except Exception:
		logger.exception("WebApp captcha challenge read failed for user_id=%s", user_id)
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

	if not result.get("ok"):
		error_code = str(result.get("error") or "challenge_not_found")
		response_payload = {
			"ok": False,
			"error": error_code,
			"penalty_until": result.get("penalty_until"),
		}
		return jsonify(response_payload), _captcha_error_status(error_code)

	challenge = result.get("challenge") or {}
	return jsonify({
		"ok": True,
		"challenge": challenge,
		"penalty_active": bool(result.get("penalty_active")),
		"penalty_until": result.get("penalty_until"),
		"first_link_at": result.get("first_link_at"),
	})


@app.post("/api/captcha/solve")
def captcha_solve():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)

	user_id = int(auth_user["id"])
	data = request.get_json(silent=True) or {}
	token = str(data.get("token") or request.args.get("token") or "").strip()
	answer = str(data.get("answer") or "").strip()

	db = _get_fish_db()
	if db is None:
		if fish_db_import_error is not None:
			logger.error("WebApp DB unavailable: %s", fish_db_import_error)
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		result = db.solve_antibot_challenge(user_id, token, answer)
	except Exception:
		logger.exception("WebApp captcha solve failed for user_id=%s", user_id)
		return jsonify({"ok": False, "error": "db_write_failed"}), 500

	if not result.get("ok"):
		error_code = str(result.get("error") or "wrong_answer")
		response_payload = {
			"ok": False,
			"error": error_code,
			"penalty_until": result.get("penalty_until"),
		}
		return jsonify(response_payload), _captcha_error_status(error_code)

	return jsonify({"ok": True})


if __name__ == "__main__":
	# Railway sets PORT dynamically for public HTTP services.
	port = int(os.getenv("PORT") or os.getenv("APP_PORT", "8008"))
	app.run(
		host=os.getenv("APP_HOST", "0.0.0.0"),
		port=port,
		debug=os.getenv("APP_DEBUG", "0") == "1",
	)
