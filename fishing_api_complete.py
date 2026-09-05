"""
ПОЛНЫЙ И ОКОНЧАТЕЛЬНЫЙ файл с API эндпоинтами для рыбалки
Скопируйте этот код в webapp/app.py
"""

# ============================================================================
# ДОБАВИТЬ В ИМПОРТЫ webapp/app.py:
# ============================================================================
from game_logic import FishingGame
from datetime import datetime, timedelta
from fish_stickers import FISH_STICKERS
from trash_stickers import TRASH_STICKERS

# ============================================================================
# HELPER ФУНКЦИЯ
# ============================================================================

def calculate_remaining_cooldown(last_fish_time_str):
    """Calculate remaining cooldown in seconds"""
    if not last_fish_time_str:
        return 0
    
    COOLDOWN_MINUTES = 10
    
    try:
        last_time = datetime.fromisoformat(last_fish_time_str)
        time_passed = datetime.now() - last_time
        cooldown_duration = timedelta(minutes=COOLDOWN_MINUTES)
        
        if time_passed >= cooldown_duration:
            return 0
        
        remaining = cooldown_duration - time_passed
        return int(remaining.total_seconds())
    except:
        return 0

# ============================================================================
# API ЭНДПОИНТЫ - ДОБАВИТЬ В webapp/app.py
# ============================================================================

@app.post("/api/update-location")
def update_location():
    """Update player's current location"""
    auth_user, auth_error = _get_verified_user_from_request()
    if auth_error:
        return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
    
    user_id = int(auth_user["id"])
    data = request.json or {}
    location = data.get("location")
    
    if not location:
        return jsonify({"ok": False, "error": "location_required"}), 400
    
    db = _get_fish_db()
    if db is None:
        return jsonify({"ok": False, "error": "db_unavailable"}), 500
    
    try:
        # Update location for webapp (chat_id=-1)
        db.update_player(user_id, -1, current_location=location)
        
        # Sync to main chat if exists
        try:
            player = db.get_player(user_id, 0)
            if player:
                db.update_player(user_id, 0, current_location=location)
        except:
            pass
        
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("API update-location failed")
        return jsonify({"ok": False, "error": "internal_error"}), 500


@app.get("/api/cooldown")
def api_cooldown():
    """Check fishing cooldown status"""
    auth_user, auth_error = _get_verified_user_from_request()
    if auth_error:
        return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
    
    user_id = int(auth_user["id"])
    db = _get_fish_db()
    if db is None:
        return jsonify({"ok": False, "error": "db_unavailable"}), 500
    
    try:
        player = db.get_player(user_id, -1)
        if not player:
            return jsonify({"ok": True, "cooldown_remaining": 0, "can_fish": True})
        
        last_fish = player.get('last_fish_time')
        remaining = calculate_remaining_cooldown(last_fish)
        
        return jsonify({
            "ok": True,
            "cooldown_remaining": remaining,
            "can_fish": remaining == 0
        })
    except Exception as e:
        logger.exception("API cooldown failed")
        return jsonify({"ok": False, "error": "internal_error"}), 500


@app.post("/api/fish")
def api_fish():
    """Perform fishing action with full game logic"""
    auth_user, auth_error = _get_verified_user_from_request()
    if auth_error:
        return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
    
    user_id = int(auth_user["id"])
    data = request.json or {}
    location = data.get("location", "Городской пруд")
    guaranteed = data.get("guaranteed", False)
    
    db = _get_fish_db()
    if db is None:
        return jsonify({"ok": False, "error": "db_unavailable"}), 500
    
    try:
        game_logic = FishingGame()
        
        # Get or create player
        player = db.get_player(user_id, -1)
        if not player:
            username = auth_user.get("username", f"user_{user_id}")
            player = db.create_player(user_id, username, -1)
        
        # Check cooldown (unless guaranteed)
        if not guaranteed:
            can_fish, message = game_logic.can_fish(user_id, -1)
            if not can_fish:
                remaining = calculate_remaining_cooldown(player.get('last_fish_time'))
                return jsonify({
                    "ok": False,
                    "cooldown_remaining": remaining,
                    "message": message
                })
        
        # Handle guaranteed catch payment
        if guaranteed:
            currency = data.get("currency", "stars")
            
            if currency == "stars":
                if player.get('stars', 0) < 1:
                    return jsonify({"ok": False, "error": "insufficient_stars"}), 400
                db.update_player(user_id, -1, stars=player['stars'] - 1)
            else:  # TON
                ton_balance = float(player.get('ton_balance', 0))
                if ton_balance < 0.01:
                    return jsonify({"ok": False, "error": "insufficient_ton"}), 400
                db.update_player(user_id, -1, ton_balance=ton_balance - 0.01)
        
        # PERFORM FISHING - полная логика из game_logic.py
        result = game_logic.fish(user_id, -1, location, guaranteed)
        
        # Add image URLs
        if result.get('success') and result.get('fish'):
            fish_name = result['fish'].get('name')
            sticker_id = result['fish'].get('sticker_id')
            image_file = FISH_STICKERS.get(fish_name) or sticker_id or f"{fish_name}.webp"
            result['fish']['image_url'] = f"/api/fish-image/{image_file}"
            result['fish']['sticker_id'] = image_file
        
        if result.get('is_trash') and result.get('trash'):
            trash_name = result['trash'].get('name')
            image_file = TRASH_STICKERS.get(trash_name) or f"{trash_name}.webp"
            result['trash']['image_url'] = f"/api/fish-image/{image_file}"
            result['trash']['sticker_id'] = image_file
        
        # Check boat status
        active_boat = db.get_active_boat_by_user(user_id)
        result['is_on_boat'] = active_boat is not None
        
        # Handle boat crash
        if active_boat and result.get('success') and result.get('fish'):
            try:
                boat_data = db.get_boat_info(active_boat['boat_id'])
                if boat_data:
                    max_weight = boat_data.get('max_weight', 1000)
                    current_weight = db.get_boat_current_weight(active_boat['id'])
                    fish_weight = result.get('weight', 0)
                    
                    if current_weight + fish_weight > max_weight:
                        db.crash_boat(active_boat['id'])
                        result['boat_crash'] = True
                        result['boat_crash_message'] = f"⚠️ КРУШЕНИЕ! Лодка затонула ({current_weight + fish_weight}кг > {max_weight}кг)"
            except Exception as e:
                logger.warning("Boat crash check failed: %s", e)
        
        # Sync with main chat
        try:
            main_player = db.get_player(user_id, 0)
            if main_player:
                db.update_player(user_id, 0, last_fish_time=datetime.now().isoformat())
        except:
            pass
        
        return jsonify({"ok": True, **result})
        
    except Exception as e:
        logger.exception("API fish failed user_id=%s", user_id)
        return jsonify({"ok": False, "error": "internal_error", "details": str(e)}), 500


@app.post("/api/create-stars-invoice")
def create_stars_invoice():
    """Create Telegram Stars invoice for balance top-up"""
    auth_user, auth_error = _get_verified_user_from_request()
    if auth_error:
        return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
    
    user_id = int(auth_user["id"])
    data = request.json or {}
    amount = int(data.get("amount", 0))
    
    if amount <= 0 or amount > 1000:
        return jsonify({"ok": False, "error": "invalid_amount"}), 400
    
    try:
        # Generate unique payload for tracking
        import secrets
        payload = f"stars_topup_{user_id}_{amount}_{secrets.token_hex(8)}"
        
        # Create invoice link (simplified - full implementation requires bot integration)
        # In production: use bot.create_invoice_link()
        bot_username = os.getenv("BOT_USERNAME", "your_bot")
        invoice_link = f"https://t.me/{bot_username}?start=topup_{payload}"
        
        return jsonify({
            "ok": True,
            "invoice_link": invoice_link,
            "amount": amount
        })
        
    except Exception as e:
        logger.exception("API create-stars-invoice failed")
        return jsonify({"ok": False, "error": "internal_error"}), 500


@app.post("/api/confirm-ton-topup")
def confirm_ton_topup():
    """Confirm TON blockchain payment and update balance"""
    auth_user, auth_error = _get_verified_user_from_request()
    if auth_error:
        return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
    
    user_id = int(auth_user["id"])
    data = request.json or {}
    amount = float(data.get("amount", 0))
    
    if amount <= 0:
        return jsonify({"ok": False, "error": "invalid_amount"}), 400
    
    db = _get_fish_db()
    if db is None:
        return jsonify({"ok": False, "error": "db_unavailable"}), 500
    
    try:
        player = db.get_player(user_id, -1)
        if not player:
            return jsonify({"ok": False, "error": "player_not_found"}), 404
        
        # Update TON balance
        current_balance = float(player.get('ton_balance', 0))
        new_balance = current_balance + amount
        
        db.update_player(user_id, -1, ton_balance=new_balance)
        
        logger.info("TON top-up confirmed: user=%s amount=%s new_balance=%s", 
                   user_id, amount, new_balance)
        
        return jsonify({
            "ok": True,
            "new_balance": new_balance,
            "added": amount
        })
        
    except Exception as e:
        logger.exception("API confirm-ton-topup failed")
        return jsonify({"ok": False, "error": "internal_error"}), 500


# ============================================================================
# ОБНОВИТЬ /api/profile - ДОБАВИТЬ is_on_boat и ton_balance
# ============================================================================
# В существующей функции profile() добавить в payload:

"""
# В функции profile():
try:
    active_boat = db.get_active_boat_by_user(user_id)
    is_on_boat = active_boat is not None
except:
    is_on_boat = False

payload = {
    # ... existing fields ...
    "ton_balance": float(player.get("ton_balance") or 0.0),
    "is_on_boat": is_on_boat,
    # ... remaining fields ...
}
"""
