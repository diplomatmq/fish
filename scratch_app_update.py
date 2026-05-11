import sys, re
with open('webapp/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_endpoints = '''
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
			cursor.execute(\'\'\'
				SELECT cf.fish_name, f.rarity, f.price, f.sticker_id, COUNT(cf.id), SUM(cf.weight), GROUP_CONCAT(cf.id)
				FROM caught_fish cf
				LEFT JOIN fish f ON cf.fish_name = f.name
				WHERE cf.user_id = ? AND cf.sold = 0
				GROUP BY cf.fish_name, f.rarity, f.price, f.sticker_id
				ORDER BY f.rarity IS NOT NULL DESC, COUNT(cf.id) DESC
			\'\'\', (user_id,))
			rows = cursor.fetchall()
			items = []
			for r in rows:
				fish_name, rarity, price, sticker_id, count, tw, ids_str = r
				price = price or 0
				ids = [int(i) for i in ids_str.split(',')]
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
		return jsonify({"ok": False}), 500

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
				from bot import calculate_sale_summary
				xp, _, _, _, _ = calculate_sale_summary(fish_items)
				tot_xp += xp
				
			pid = ",".join("?" for _ in actual_ids)
			cursor.execute(f'UPDATE caught_fish SET sold = 1, sold_at = CURRENT_TIMESTAMP WHERE id IN ({pid})', actual_ids)
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
'''

if '@app.get("/api/inventory/grouped")' not in content:
    content = content.replace('@app.post("/api/sell-fish")', new_endpoints + '\\n@app.post("/api/sell-fish")')
    with open('webapp/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated app.py")
else:
    print("Already updated")
