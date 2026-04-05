from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request

try:
	from database import db as fish_db
except Exception:
	fish_db = None


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


@app.get("/")
def index():
	return render_template("index.html")


@app.get("/health")
def health():
	return jsonify({"ok": True})


@app.get("/api/profile")
def profile():
	user_id = _safe_int(request.args.get("user_id"))
	fallback_username = request.args.get("username")

	if not user_id:
		return jsonify({"ok": False, "error": "missing_user_id"}), 400

	if fish_db is None:
		return jsonify({"ok": False, "error": "db_unavailable"}), 500

	try:
		player = fish_db.get_player(user_id, -1)
	except Exception:
		return jsonify({"ok": False, "error": "db_read_failed"}), 500

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
	return jsonify({"items": DEFAULT_TROPHIES})


@app.post("/api/trophy/select")
def select_trophy():
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
