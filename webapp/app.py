from __future__ import annotations



import hashlib

import hmac

import json

import logging

import os

import sys

import time
from concurrent.futures import ThreadPoolExecutor

from datetime import datetime, timedelta

from pathlib import Path

from typing import Optional

from urllib.parse import parse_qsl
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen



from flask import Flask, jsonify, render_template, request, send_from_directory

import fish_stickers
from fish_stickers import FISH_STICKERS as fish_stickers_dict





logger = logging.getLogger(__name__)
WEBHOOK_PROXY_EXECUTOR = ThreadPoolExecutor(
	max_workers=int(os.getenv("WEBHOOK_PROXY_WORKERS", "128")),
	thread_name_prefix="telegram_webhook_proxy",
)

fish_db = None

fish_db_import_error: Exception | None = None

_fish_db_initialized = False




def _get_fish_db():

	global fish_db, fish_db_import_error, _fish_db_initialized

	if fish_db is not None:

		if not _fish_db_initialized:

			try:

				fish_db.init_db()

				_fish_db_initialized = True

			except Exception:

				logger.exception("WebApp DB init failed")

		return fish_db



	try:

		project_root = Path(__file__).resolve().parent.parent

		project_root_str = str(project_root)

		if project_root_str not in sys.path:

			sys.path.insert(0, project_root_str)



		from database import db as imported_db

		fish_db = imported_db

		fish_db_import_error = None

		try:

			fish_db.init_db()

			_fish_db_initialized = True

		except Exception:

			logger.exception("WebApp DB init failed")

	except Exception as exc:

		fish_db = None

		fish_db_import_error = exc

		logger.exception("WebApp DB import failed")



	return fish_db





BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = BASE_DIR.parent

TRANSFERRED_UI_DIST = BASE_DIR / "ui_from_testpers" / "dist"

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





def _build_trophy_payload(trophy: dict | None, fish_rarity: str | None = None) -> Optional[dict]:

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

		"rarity": str(fish_rarity or "Обычная"),

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
	# Serve built Vite application from ui_from_testpers/dist
	if (TRANSFERRED_UI_DIST / "index.html").exists():
		return send_from_directory(str(TRANSFERRED_UI_DIST), "index.html")
		
	# Fallback to template
	return render_template("index.html")


@app.get("/src/<path:filename>")
def transferred_src(filename: str):
	if filename.lower().endswith('.ts'):
		return send_from_directory(str(BASE_DIR / "ui_from_testpers" / "src"), filename, mimetype='application/javascript')
	return send_from_directory(str(BASE_DIR / "ui_from_testpers" / "src"), filename)


@app.get("/<path:filename>.css")
def transferred_css(filename: str):
	return send_from_directory(str(BASE_DIR / "ui_from_testpers" / "src"), filename if filename.endswith(".css") else f"{filename}.css")


@app.get("/assets/<path:filename>")

def transferred_assets(filename: str):

	return send_from_directory(str(TRANSFERRED_UI_DIST / "assets"), filename)





@app.get("/background.jpg")

def transferred_background():

	return send_from_directory(str(TRANSFERRED_UI_DIST), "background.jpg")





@app.get("/health")

def health():

	return jsonify({"ok": True})



@app.get("/ping")

def ping():

	return jsonify({"ok": True, "service": "fishbot-webapp", "ts": int(time.time())})





@app.post(f"/{os.getenv('WEBHOOK_PATH', 'telegram-webhook').strip('/') or 'telegram-webhook'}")
def telegram_webhook_proxy():
	target_url = os.getenv("BOT_INTERNAL_WEBHOOK_URL", "http://127.0.0.1:9000/telegram-webhook")
	payload = request.get_data(cache=False)
	headers = {
		"Content-Type": request.headers.get("Content-Type", "application/json"),
		"X-Telegram-Bot-Api-Secret-Token": request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""),
	}
	if os.getenv("WEBHOOK_PROXY_LOG_UPDATES", "1") == "1":
		logger.info("Telegram webhook proxy accepted update: bytes=%s target=%s", len(payload), target_url)
	WEBHOOK_PROXY_EXECUTOR.submit(_forward_telegram_update, target_url, payload, headers)
	return "", 200


def _forward_telegram_update(target_url: str, payload: bytes, headers: dict) -> None:
	try:
		proxy_request = UrlRequest(target_url, data=payload, headers=headers, method="POST")
		with urlopen(proxy_request, timeout=float(os.getenv("WEBHOOK_PROXY_TIMEOUT", "30"))) as response:
			response.read(1024)
		if os.getenv("WEBHOOK_PROXY_LOG_UPDATES", "1") == "1":
			logger.info("Telegram webhook proxy forwarded update to bot: status=%s", getattr(response, "status", "?"))
	except HTTPError as exc:
		logger.warning("Telegram webhook proxy got HTTP %s from bot", exc.code)
	except (TimeoutError, URLError) as exc:
		logger.warning("Telegram webhook proxy could not forward update to bot: %s", exc)
	except Exception:
		logger.exception("Telegram webhook proxy background forward failed")


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





@app.get("/api/inventory")
def inventory():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
	
	user_id = int(auth_user["id"])
	db = _get_fish_db()
	if db is None:
		return jsonify({"ok": False, "error": "db_unavailable"}), 500
	
	try:
		# Получаем список непроданной рыбы с лимитом для производительности
		with db._connect() as conn:
			cursor = conn.cursor()
			cursor.execute('''
				SELECT cf.id, cf.fish_name, cf.weight, cf.length, cf.location, f.rarity, f.price, f.sticker_id
				FROM caught_fish cf
				JOIN fish f ON cf.fish_name = f.name
				WHERE cf.user_id = ? AND cf.sold = 0
				ORDER BY cf.caught_at DESC
				LIMIT 1000
			''', (user_id,))
			rows = cursor.fetchall()
			
			items = []
			for r in rows:
				fish_name = r[1]
				image_file = r[7] or fish_stickers_dict.get(fish_name) or 'fishdef.webp'
				items.append({
					"id": r[0],
					"name": fish_name,
					"weight": r[2],
					"length": r[3],
					"location": r[4],
					"rarity": r[5],
					"price": r[6],
					"image_url": f"/api/fish-image/{image_file}"
				})
			return jsonify({"ok": True, "items": items})
	except Exception as e:
		logger.exception("API inventory failed")
		return jsonify({"ok": False, "error": "internal_error"}), 500

@app.post("/api/sell-fish")
def sell_fish():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
	
	user_id = int(auth_user["id"])
	data = request.json or {}
	fish_id = data.get("id")
	
	db = _get_fish_db()
	if db is None:
		return jsonify({"ok": False, "error": "db_unavailable"}), 500
	
	try:
		with db._connect() as conn:
			cursor = conn.cursor()
			# Проверяем владельца, цену и вес
			cursor.execute('''
				SELECT f.price, cf.weight, cf.fish_name FROM caught_fish cf
				JOIN fish f ON cf.fish_name = f.name
				WHERE cf.id = ? AND cf.user_id = ? AND cf.sold = 0
			''', (fish_id, user_id))
			row = cursor.fetchone()
			if not row:
				return jsonify({"ok": False, "error": "fish_not_found"}), 404
			
			price = row[0]
			weight = row[1]
			fish_name = row[2]
			
			# Обновляем статистику продажи
			db.update_player_sale_stats(user_id, weight, price)
			
			# УДАЛЯЕМ рыбу вместо пометки sold=1
			cursor.execute('DELETE FROM caught_fish WHERE id = ?', (fish_id,))
			cursor.execute('UPDATE players SET coins = coins + ? WHERE user_id = ?', (price, user_id))
			conn.commit()
			
			return jsonify({"ok": True, "earned": price})
	except Exception as e:
		logger.exception("API sell-fish failed")
		return jsonify({"ok": False, "error": "internal_error"}), 500

@app.get("/api/inventory/grouped")
def inventory_grouped():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error: return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
	user_id = int(auth_user["id"])
	db = _get_fish_db()
	if not db: return jsonify({"ok": False, "error": "db_unavailable"}), 500
	try:
		with db._connect() as conn:
			cursor = conn.cursor()
			# Оптимизированный запрос с использованием STRING_AGG и LIMIT
			cursor.execute('''
				SELECT cf.fish_name, f.rarity, f.price, f.sticker_id, COUNT(cf.id), SUM(cf.weight), STRING_AGG(CAST(cf.id AS TEXT), ',')
				FROM caught_fish cf
				LEFT JOIN fish f ON cf.fish_name = f.name
				WHERE cf.user_id = ? AND cf.sold = 0
				GROUP BY cf.fish_name, f.rarity, f.price, f.sticker_id
				ORDER BY f.rarity IS NOT NULL DESC, COUNT(cf.id) DESC
				LIMIT 500
			''', (user_id,))
			rows = cursor.fetchall()
			items = []
			for r in rows:
				fish_name, rarity, price, sticker_id, count, tw, ids_str = r
				price = price or 0
				ids = [int(i) for i in ids_str.split(',') if i]
				if not rarity:
					cursor.execute('SELECT price, sticker_id FROM trash WHERE name = ?', (fish_name,))
					tr = cursor.fetchone()
					if tr:
						price, sticker_id = tr
					rarity = "Мусор"
				im = sticker_id or fish_stickers_dict.get(fish_name) or 'fishdef.webp'
				items.append({"ids": ids, "name": fish_name, "count": count, "total_weight": tw, "rarity": rarity, "price": price * count, "unit_price": price, "image_url": f"/api/fish-image/{im}"})
			return jsonify({"ok": True, "items": items})
	except Exception as e:
		logger.exception("Grouped API error")
		return jsonify({"ok": False, "error": "internal_error"}), 500

@app.post("/api/sell-bulk")
def sell_bulk():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error: return jsonify({"ok": False}), 401
	user_id = int(auth_user["id"])
	data = request.json or {}
	ids = data.get("ids", [])
	category = data.get("category")
	db = _get_fish_db()
	try:
		with db._connect() as conn:
			cursor = conn.cursor()
			if category:
				if category == "all": cursor.execute('SELECT id, fish_name, weight FROM caught_fish WHERE user_id = ? AND sold = 0', (user_id,))
				elif category == "trash": cursor.execute('SELECT cf.id, cf.fish_name, cf.weight FROM caught_fish cf LEFT JOIN fish f ON cf.fish_name = f.name WHERE cf.user_id = ? AND cf.sold = 0 AND f.name IS NULL', (user_id,))
				else:
					rmap = {"common": "Обычная", "rare": "Редкая", "legendary": "Легендарная", "anomaly": "Аномалия", "aquarium": "Аквариумная", "mythic": "Мифическая"}
					cursor.execute('SELECT cf.id, cf.fish_name, cf.weight FROM caught_fish cf JOIN fish f ON cf.fish_name = f.name WHERE cf.user_id = ? AND cf.sold = 0 AND f.rarity = ?', (user_id, rmap.get(category)))
			elif ids:
				p = ",".join("?" for _ in ids)
				cursor.execute(f'SELECT id, fish_name, weight FROM caught_fish WHERE id IN ({p}) AND user_id = ? AND sold = 0', (*ids, user_id))
			else: return jsonify({"ok": False}), 400
			
			rows = cursor.fetchall()
			if not rows: return jsonify({"ok": True, "earned_coins": 0, "earned_xp": 0})
			actual_ids = [r[0] for r in rows]
			names = list(set(r[1] for r in rows))
			p_names = ",".join("?" for _ in names)
			cursor.execute(f'SELECT name, rarity, price FROM fish WHERE name IN ({p_names})', names)
			fdict = {r[0]: {"r": r[1], "p": r[2]} for r in cursor.fetchall()}
			cursor.execute(f'SELECT name, price FROM trash WHERE name IN ({p_names})', names)
			tdict = {r[0]: r[1] for r in cursor.fetchall()}
			
			tot_price = 0
			tot_xp = 0
			fish_items = []
			for r in rows:
				nm = r[1]
				if nm in fdict:
					tot_price += fdict[nm]["p"]
					fish_items.append({"name": nm, "weight": r[2], "rarity": fdict[nm]["r"]})
				elif nm in tdict:
					tot_price += tdict[nm]
					tot_xp += 1
			
			if fish_items:
				try:
					from bot import calculate_sale_summary
					xp, _, _, _, total_weight = calculate_sale_summary(fish_items)
					tot_xp += xp
					# Обновляем статистику продажи
					db.update_player_sale_stats(user_id, total_weight, tot_price)
				except:
					pass
				
			pid = ",".join("?" for _ in actual_ids)
			# УДАЛЯЕМ рыбу вместо пометки sold=1
			cursor.execute(f'DELETE FROM caught_fish WHERE id IN ({pid})', actual_ids)
			cursor.execute('UPDATE players SET coins = coins + ?, xp = xp + ? WHERE user_id = ?', (tot_price, tot_xp, user_id))
			conn.commit()
			return jsonify({"ok": True, "earned_coins": tot_price, "earned_xp": tot_xp})
	except Exception as e:
		logger.exception("Sell bulk err")
		return jsonify({"ok": False}), 500

@app.get("/api/ratings")
def api_ratings():
	db = _get_fish_db()
	if not db: return jsonify({"ok": False}), 500
	t = request.args.get("type", "normal")
	try:
		with db._connect() as conn:
			cursor = conn.cursor()
			field = "gold_tickets" if t == "gold" else "tickets"
			cursor.execute(f'SELECT username, {field}, user_id FROM players WHERE {field} > 0 ORDER BY {field} DESC LIMIT 100')
			return jsonify({"ok": True, "top": [{"username": r[0], "score": r[1], "user_id": r[2]} for r in cursor.fetchall()]})
	except Exception: return jsonify({"ok": False}), 500

@app.get("/api/results")
def api_results():
	return jsonify({"ok": True, "results": []})


@app.post("/api/make-trophy")
def make_trophy():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
	
	user_id = int(auth_user["id"])
	data = request.json or {}
	fish_id = data.get("id")
	
	db = _get_fish_db()
	if db is None:
		return jsonify({"ok": False, "error": "db_unavailable"}), 500
	
	TROPHY_COST = 10000
	
	try:
		with db._connect() as conn:
			cursor = conn.cursor()
			
			# Проверяем баланс игрока
			cursor.execute('SELECT coins FROM players WHERE user_id = ?', (user_id,))
			player_row = cursor.fetchone()
			if not player_row:
				return jsonify({"ok": False, "error": "player_not_found"}), 404
			
			current_coins = int(player_row[0] or 0)
			if current_coins < TROPHY_COST:
				return jsonify({"ok": False, "error": "insufficient_coins", "required": TROPHY_COST, "current": current_coins}), 400
			
			# Проверяем рыбу
			cursor.execute('SELECT fish_name, weight, length, location FROM caught_fish WHERE id = ? AND user_id = ? AND sold = 0', (fish_id, user_id))
			row = cursor.fetchone()
			if not row:
				return jsonify({"ok": False, "error": "fish_not_found"}), 404
			
			fish_name, weight, length, location = row
			
			# Создаем трофей (по логике бота это перенос из caught_fish в player_trophies)
			cursor.execute('''
				INSERT INTO player_trophies (user_id, fish_name, weight, length, location)
				VALUES (?, ?, ?, ?, ?)
			''', (user_id, fish_name, weight, length, location))
			
			# Списываем монеты
			cursor.execute('UPDATE players SET coins = coins - ? WHERE user_id = ?', (TROPHY_COST, user_id))
			
			# Удаляем из инвентаря
			cursor.execute('DELETE FROM caught_fish WHERE id = ?', (fish_id,))
			conn.commit()
			
			return jsonify({"ok": True, "coins_spent": TROPHY_COST})
	except Exception as e:
		logger.exception("API make-trophy failed")
		return jsonify({"ok": False, "error": "internal_error"}), 500

@app.get("/api/trophies")
def trophies_list():
	auth_user, auth_error = _get_verified_user_from_request()
	if auth_error:
		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
	
	user_id = int(auth_user["id"])
	db = _get_fish_db()
	if db is None:
		return jsonify({"ok": False, "error": "db_unavailable"}), 500
	
	try:
		with db._connect() as conn:
			cursor = conn.cursor()
			cursor.execute('''
				SELECT pt.id, pt.fish_name, pt.weight, pt.length, pt.location, pt.is_active, f.rarity, f.sticker_id, pt.image_file
				FROM player_trophies pt
				LEFT JOIN fish f ON pt.fish_name = f.name
				WHERE pt.user_id = ?
				ORDER BY pt.created_at DESC
			''', (user_id,))
			rows = cursor.fetchall()
			
			items = []
			for r in rows:
				fish_name = r[1]
				# Приоритет: pt.image_file -> f.sticker_id -> dictionary -> default
				image_file = r[8] or r[7] or fish_stickers_dict.get(fish_name) or 'fishdef.webp'
				
				items.append({
					"id": r[0],
					"name": fish_name,
					"weight": r[2],
					"length": r[3],
					"location": r[4],
					"is_active": bool(r[5]),
					"rarity": r[6] or "Обычная",
					"image_url": f"/api/fish-image/{image_file}"
				})
			return jsonify({"ok": True, "items": items})
	except Exception as e:
		logger.exception("API trophies failed")
		return jsonify({"ok": False, "error": "internal_error"}), 500


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



	active_rarity = "Обычная"

	if active_trophy:

		try:

			fish = db.get_fish_by_name(str(active_trophy.get("fish_name") or ""))

			active_rarity = str((fish or {}).get("rarity") or "Обычная")

		except Exception:

			active_rarity = "Обычная"



	level = int(player.get("level") or 0)
	try:
		tickets_total = db.get_user_tickets(user_id, ticket_type='normal')
		gold_tickets_total = db.get_user_tickets(user_id, ticket_type='gold')
	except Exception:
		tickets_total = int(player.get('tickets') or 0)
		gold_tickets_total = int(player.get('gold_tickets') or 0)

	payload = {

		"user_id": user_id,

		"is_admin": user_id == 793216884,

		"username": _normalize_username(player.get("username") or fallback_username),

		"level": level,

		"xp": int(player.get("xp") or 0),

		"coins": int(player.get("coins") or 0),

		"stars": int(player.get("stars") or 0),

		"tickets": int(tickets_total or 0),

		"gold_tickets": int(gold_tickets_total or 0),

		"title": _build_title(level),

		"selected_trophy": _format_trophy_id(active_trophy),

		"selected_trophy_data": _build_trophy_payload(active_trophy, fish_rarity=active_rarity),

	}

	return jsonify(payload)





@app.get("/api/guilds")

def get_guilds():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	db = _get_fish_db()

	if not db:

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		snapshot = db.get_webapp_guilds_snapshot(user_id=user_id)

		return jsonify({"ok": True, **snapshot})

	except Exception:

		logger.exception("WebApp guilds snapshot failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500





@app.post("/api/guilds/join")

def join_guild():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.json or {}

	guild_id = data.get("guild_id")

	if not guild_id:

		return jsonify({"ok": False, "error": "missing_guild_id"}), 400



	db = _get_fish_db()

	if not db:

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		# Проверяем тип доступа

		with db._connect() as conn:

			cursor = conn.cursor()

			cursor.execute("SELECT access_type FROM webapp_clan_profiles WHERE clan_id = ?", (guild_id,))

			row = cursor.fetchone()

			access_type = row[0] if row else "open"



		if access_type != "open":

			return jsonify({"ok": False, "error": "invite_only"}), 403



		result = db.join_clan(user_id, guild_id)

		return jsonify(result)

	except Exception:

		logger.exception("WebApp guild join failed for user_id=%s guild_id=%s", user_id, guild_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500





@app.post("/api/guilds/apply")

def apply_guild():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.json or {}

	guild_id = data.get("guild_id")

	if not guild_id:

		return jsonify({"ok": False, "error": "missing_guild_id"}), 400


	db = _get_fish_db()

	if not db:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.add_webapp_clan_request(user_id, int(guild_id))

	except Exception:

		logger.exception("WebApp guild apply failed for user_id=%s guild_id=%s", user_id, guild_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500


	if not result.get("ok"):

		error = str(result.get("reason") or "apply_failed")

		status = 403 if error in {"already_in_clan", "not_invite_only", "forbidden"} else 400
		return jsonify({"ok": False, "error": error}), status


	return jsonify(result)



@app.post("/api/guilds/leave")

def leave_guild():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	db = _get_fish_db()

	if not db:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.leave_clan(user_id)

		return jsonify(result)

	except Exception:

		logger.exception("WebApp guild leave failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500



@app.post("/api/guilds/request/respond")

def guild_request_respond():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])
	data = request.get_json(silent=True) or {}
	request_id = _safe_int(data.get("request_id"))
	action = str(data.get("action") or "").strip().lower()

	if request_id is None:

		return jsonify({"ok": False, "error": "request_id_required"}), 400

	if action not in {"accept", "decline"}:

		return jsonify({"ok": False, "error": "invalid_action"}), 400



	db = _get_fish_db()

	if not db:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.respond_webapp_clan_request(user_id, request_id, action)

	except Exception:

		logger.exception("WebApp clan request respond failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500



	if not result.get("ok"):

		error = str(result.get("reason") or "request_respond_failed")

		status = 403 if error == "forbidden" else 400

		if error == "request_not_found":

			status = 404

		return jsonify({"ok": False, "error": error}), status



	return jsonify(result)





@app.post("/api/guilds/create")

def create_guild():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.json or {}

	name = data.get("name")

	avatar = data.get("avatar", "🔱")

	color = data.get("color", "#00b4d8")

	access_type = data.get("type", "open")

	min_level = data.get("min_level", 0)



	if not name:

		return jsonify({"ok": False, "error": "missing_name"}), 400



	db = _get_fish_db()

	if not db:

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.create_clan(user_id, name)

		if result.get("ok"):

			clan_id = result["clan"]["id"]

			db.save_webapp_clan_profile(

				clan_id=clan_id,

				avatar_emoji=avatar,

				color_hex=color,

				access_type=access_type,

				description="",

				min_level=min_level,

				updated_by=user_id

			)

			return jsonify({"ok": True, "clan_id": clan_id})

		return jsonify(result)

	except Exception:

		logger.exception("WebApp guild create failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500





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

		rarity = "Обычная"

		try:

			fish = db.get_fish_by_name(str(trophy.get("fish_name") or ""))

			rarity = str((fish or {}).get("rarity") or "Обычная")

		except Exception:

			rarity = "Обычная"



		payload = _build_trophy_payload(trophy, fish_rarity=rarity)

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

	ticket_type = str(request.args.get("ticket_type") or "normal").strip().lower()
	if ticket_type not in ("normal", "gold"):
		ticket_type = "normal"



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		rows = db.get_tickets_leaderboard(limit=limit, ticket_type=ticket_type)

		my_rank = db.get_user_tickets_rank(user_id, ticket_type=ticket_type)

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

		"ticket_type": ticket_type,

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

	ticket_type = str(data.get("ticket_type") or "normal").strip().lower()
	if ticket_type not in ("normal", "gold"):
		ticket_type = "normal"



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

		result = db.create_ticket_draw_results(
			ticket_type=ticket_type,
			start_at=start_date,
			end_at=end_date,
			requested_count=count,
			created_by=user_id,
		)

		draws = result.get('items') or []

		user_counts = db.get_ticket_counts_for_users_in_period(

			[user_id for user_id in {int(row.get("user_id") or 0) for row in draws}],

			start_date,

			end_date,

			ticket_type=ticket_type,

		)

	except Exception:

		logger.exception("WebApp ticket draw failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	if not draws:

		return jsonify({

			"ok": True,

			"items": [],

			"ticket_type": ticket_type,

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

		"ticket_type": ticket_type,

		"period": {

			"start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),

			"end_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),

			"count": len(items),

		},

	})




@app.get("/api/tickets/results")

def tickets_results():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	ticket_type = str(request.args.get("ticket_type") or "normal").strip().lower()
	if ticket_type not in ("normal", "gold"):
		ticket_type = "normal"



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.get_latest_ticket_draw_results(ticket_type=ticket_type)

	except Exception:

		logger.exception("WebApp ticket results read failed for type=%s", ticket_type)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	if not result:

		return jsonify({

			"ok": True,

			"items": [],

			"ticket_type": ticket_type,

			"period": None,

		})



	items = []

	for idx, row in enumerate(result.get('items') or [], start=1):

		items.append({

			"place": idx,

			"ticket_code": row.get("ticket_code"),

			"user_id": int(row.get("user_id") or 0),

			"username": str(row.get("username") or "Неизвестно"),

			"created_at": row.get("created_at"),

			"source_type": row.get("source_type"),

			"source_ref": row.get("source_ref"),

		})



	period = {

		"start_date": str(result.get('start_at') or ''),

		"end_date": str(result.get('end_at') or ''),

		"count": len(items),

	}

	return jsonify({

		"ok": True,

		"items": items,

		"ticket_type": ticket_type,

		"period": period,

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



	ticket_type = str(request.args.get("ticket_type") or "").strip().lower()
	if ticket_type not in ("", "normal", "gold"):
		ticket_type = ""

	try:

		row = db.get_random_ticket(ticket_type=ticket_type or None)

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





@app.get("/api/book")

def book_entries():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	search = str(request.args.get("search") or "").strip()

	limit = _safe_int(request.args.get("limit")) or 128



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		items = db.get_webapp_book_entries(user_id=user_id, search=search, limit=limit)

		total_all = db.get_webapp_book_total_count()

	except Exception:

		logger.exception("WebApp book read failed for user_id=%s", auth_user.get("id"))

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	return jsonify({"ok": True, "items": items, "count": len(items), "total_all": int(total_all or 0), "search": search})





@app.get("/api/adventures")

def adventures_state():

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

		state = db.get_webapp_adventures_state(user_id)

	except Exception:

		logger.exception("WebApp adventures read failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	return jsonify({"ok": True, **state})





@app.post("/api/adventures/submit")

def adventures_submit():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.get_json(silent=True) or {}

	game_code = str(data.get("game_code") or "").strip().lower()

	score = _safe_int(data.get("score")) or 0

	try:

		distance = float(data.get("distance") or 0)

	except Exception:

		distance = 0.0



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.save_webapp_adventure_result(user_id, game_code, score, distance)

	except Exception:

		logger.exception("WebApp adventures submit failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500



	if not result.get("ok"):

		return jsonify(result), 400



	return jsonify(result)





@app.get("/api/guilds")

def guilds_state():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	limit = _safe_int(request.args.get("limit")) or 20



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		payload = db.get_webapp_guilds_snapshot(user_id, limit=limit)

	except Exception:

		logger.exception("WebApp guilds read failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	return jsonify({"ok": True, **payload})





@app.post("/api/guilds/profile")

def guilds_profile_save():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.get_json(silent=True) or {}

	avatar_emoji = str(data.get("avatar_emoji") or "🏰").strip()

	color_hex = str(data.get("color_hex") or "#00b4d8").strip()

	access_type = str(data.get("access_type") or "open").strip().lower()

	description = str(data.get("description") or "").strip()



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		my_clan = db.get_clan_by_user(user_id)

	except Exception:

		logger.exception("WebApp guild profile load failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	if not my_clan:

		return jsonify({"ok": False, "error": "not_in_clan"}), 400

	if str(my_clan.get("role") or "member") != "leader":

		return jsonify({"ok": False, "error": "leader_only"}), 403



	try:

		result = db.save_webapp_clan_profile(

			clan_id=int(my_clan.get("id") or 0),

			avatar_emoji=avatar_emoji,

			color_hex=color_hex,

			access_type=access_type,

			description=description,

			updated_by=user_id,

		)

	except Exception:

		logger.exception("WebApp guild profile save failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500



	return jsonify(result)





@app.get("/api/friends")

def friends_list():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	limit = _safe_int(request.args.get("limit")) or 50



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		items = db.get_webapp_friends(user_id, limit=limit)
		incoming_requests = db.get_webapp_friend_requests(user_id, limit=limit)

	except Exception:

		logger.exception("WebApp friends read failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_read_failed"}), 500



	return jsonify({
		"ok": True,
		"items": items,
		"count": len(items),
		"incoming_requests": incoming_requests,
		"incoming_count": len(incoming_requests),
	})





@app.post("/api/friends/add")

def friends_add():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.get_json(silent=True) or {}

	username = str(data.get("username") or "").strip()



	if not username:

		return jsonify({"ok": False, "error": "username_required"}), 400



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.add_webapp_friend_by_username(user_id, username)

	except Exception:

		logger.exception("WebApp friend add failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500



	if not result.get("ok"):

		error = str(result.get("reason") or "friend_add_failed")

		return jsonify({"ok": False, "error": error}), 400



	return jsonify(result)




@app.post("/api/friends/request/respond")

def friends_request_respond():

	auth_user, auth_error = _get_verified_user_from_request()

	if auth_error:

		return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)



	user_id = int(auth_user["id"])

	data = request.get_json(silent=True) or {}

	request_id = _safe_int(data.get("request_id"))

	action = str(data.get("action") or "").strip().lower()

	if request_id is None:

		return jsonify({"ok": False, "error": "request_id_required"}), 400

	if action not in {"accept", "decline"}:

		return jsonify({"ok": False, "error": "invalid_action"}), 400



	db = _get_fish_db()

	if db is None:

		if fish_db_import_error is not None:

			logger.error("WebApp DB unavailable: %s", fish_db_import_error)

		return jsonify({"ok": False, "error": "db_unavailable"}), 500



	try:

		result = db.respond_webapp_friend_request(user_id, request_id, action)

	except Exception:

		logger.exception("WebApp friend request respond failed for user_id=%s", user_id)

		return jsonify({"ok": False, "error": "db_write_failed"}), 500



	if not result.get("ok"):

		error = str(result.get("reason") or "request_respond_failed")

		status = 403 if error == "forbidden" else 400

		if error == "request_not_found":

			status = 404

		return jsonify({"ok": False, "error": error}), status



	return jsonify(result)





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

