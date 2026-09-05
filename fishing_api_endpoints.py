"""
API эндпоинты для рыбалки в мини-приложении
Добавьте эти эндпоинты в webapp/app.py
"""

# ============================================================================
# ДОБАВИТЬ В ИМПОРТЫ webapp/app.py:
# ============================================================================
# from game_logic import FishingGame
# from datetime import datetime, timedelta

# ============================================================================
# HELPER ФУНКЦИИ
# ============================================================================

def calculate_remaining_cooldown(last_fish_time_str):
    """Calculate remaining cooldown in seconds"""
    if not last_fish_time_str:
        return 0
    
    from datetime import datetime, timedelta
    COOLDOWN_MINUTES = 10
    
    last_time = datetime.fromisoformat(last_fish_time_str)
    time_passed = datetime.now() - last_time
    cooldown_duration = timedelta(minutes=COOLDOWN_MINUTES)
    
    if time_passed >= cooldown_duration:
        return 0
    
    remaining = cooldown_duration - time_passed
    return int(remaining.total_seconds())

# ============================================================================
# API ЭНДПОИНТЫ
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
        # Update location for both chat_id=-1 (webapp) and any existing chats
        db.update_player(user_id, -1, current_location=location)
        
        # Also update for main chat if exists
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
            return jsonify({"ok": True, "cooldown_remaining": 0})
        
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
    """Perform fishing action"""
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
        from game_logic import FishingGame
        game_logic = FishingGame()
        
        # Get player
        player = db.get_player(user_id, -1)
        if not player:
            # Create player if doesn't exist
            player = db.create_player(user_id, auth_user.get("username", f"user_{user_id}"), -1)
        
        # Check cooldown (if not guaranteed)
        if not guaranteed:
            can_fish, message = game_logic.can_fish(user_id, -1)
            if not can_fish:
                last_fish = player.get('last_fish_time')
                remaining = calculate_remaining_cooldown(last_fish)
                return jsonify({
                    "ok": False,
                    "cooldown_remaining": remaining,
                    "message": message
                })
        
        # Handle guaranteed catch payment
        if guaranteed:
            selected_currency = data.get("currency", "stars")
            
            if selected_currency == "stars":
                if player.get('stars', 0) < 1:
                    return jsonify({"ok": False, "error": "insufficient_stars"}), 400
                db.update_player(user_id, -1, stars=player['stars'] - 1)
            else:  # TON
                # TON payment is handled on frontend via blockchain
                # Backend just verifies and updates balance
                ton_balance = float(player.get('ton_balance', 0))
                if ton_balance < 0.01:
                    return jsonify({"ok": False, "error": "insufficient_ton"}), 400
                db.update_player(user_id, -1, ton_balance=ton_balance - 0.01)
        
        # Perform fishing
        result = game_logic.fish(user_id, -1, location, guaranteed)
        
        # Sync last_fish_time to main chat if exists
        try:
            main_player = db.get_player(user_id, 0)
            if main_player:
                db.update_player(user_id, 0, last_fish_time=datetime.now().isoformat())
        except:
            pass
        
        return jsonify({"ok": True, **result})
    except Exception as e:
        logger.exception("API fish failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/create-stars-invoice")
def create_stars_invoice():
    """Create Telegram Stars invoice for top-up"""
    auth_user, auth_error = _get_verified_user_from_request()
    if auth_error:
        return jsonify({"ok": False, "error": auth_error}), _auth_error_status(auth_error)
    
    user_id = int(auth_user["id"])
    data = request.json or {}
    amount = int(data.get("amount", 0))
    
    if amount <= 0:
        return jsonify({"ok": False, "error": "invalid_amount"}), 400
    
    try:
        # TODO: Implement Telegram Stars invoice creation
        # This requires bot integration with Telegram Payments API
        # For now, return placeholder
        return jsonify({
            "ok": True,
            "invoice_link": f"https://t.me/YOUR_BOT?start=topup_stars_{amount}_{user_id}"
        })
    except Exception as e:
        logger.exception("API create-stars-invoice failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/confirm-ton-topup")
def confirm_ton_topup():
    """Confirm TON top-up and update balance"""
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
        
        return jsonify({
            "ok": True,
            "new_balance": new_balance
        })
    except Exception as e:
        logger.exception("API confirm-ton-topup failed")
        return jsonify({"ok": False, "error": str(e)}), 500
