# Fish Mini App (Python Flask)

This mini app is backend-driven by Python (Flask) and intended for Telegram mobile WebApp usage.

## Implemented now

- Mobile-first fish-themed UI
- Top player panel: username, title, level, XP, coins
- Trophy picker block (UI and temporary API endpoint, full bot-sync later)
- Bottom tabs: Profile / Character
- Character tab with 3D scene
- Automatic fallback 3D fisherman (white tank top + anchor-print family shorts)
- Optional high-quality model loading from `/static/models/fisherman.glb`
- Domain label rendered from env (`APP_DOMAIN`, default `fish.monkeysdynasty.website`)
- Background image uses `webapp/static/images/back.jpg`

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start app:

```bash
python webapp/app.py
```

3. Open:

- http://127.0.0.1:8008

## Environment variables

- `APP_DOMAIN` (default: `fish.monkeysdynasty.website`)
- `APP_HOST` (default: `0.0.0.0`)
- `APP_PORT` (default: `8008`)
- `APP_DEBUG` (`1` to enable debug mode)

## Important note about "fully Python"

Telegram WebApp UI always renders in a browser context, so HTML/CSS/JS are required for interface and 3D rendering.
Backend/business logic in this implementation is Python Flask.
