from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request


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


@app.get("/")
def index():
	return render_template(
		"index.html",
		domain=os.getenv("APP_DOMAIN", "fish.monkeysdynasty.website"),
	)


@app.get("/health")
def health():
	return jsonify({"ok": True})


@app.get("/api/profile")
def profile():
	username = _normalize_username(request.args.get("username"))

	# Placeholder payload. Can be replaced with real DB reads from fishbot profile.
	payload = {
		"username": username,
		"level": 12,
		"xp": 1480,
		"coins": 93200,
		"title": "Морской охотник",
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
	app.run(
		host=os.getenv("APP_HOST", "0.0.0.0"),
		port=int(os.getenv("APP_PORT", "8008")),
		debug=os.getenv("APP_DEBUG", "0") == "1",
	)
