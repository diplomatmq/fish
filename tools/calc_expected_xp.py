"""
Script: calc_expected_xp.py
Usage: edit USER_ID at top and run `python tools/calc_expected_xp.py` from project root.

This script computes the expected XP for a user based on sold caught_fish entries
and compares it to the player's stored XP in the `players` table.

It uses the project's `database.db` instance and calculation helpers.
"""
from typing import List
import pprint

# Change this ID to the target user
USER_ID = 7855666356
# chat_id used for lookups; set -1 to match global rows (code treats <1 as global)
CHAT_ID = -1

if __name__ == '__main__':
    # Import here to allow running as standalone script from project root
    from database import db

    pp = pprint.PrettyPrinter(indent=2)

    print(f"Inspecting user: {USER_ID} (chat_id lookup: {CHAT_ID})\n")

    # Fetch all caught fish visible to the user (read-only)
    caught = db.get_caught_fish(USER_ID, CHAT_ID)
    print(f"Total caught rows returned: {len(caught)}")

    # Partition into sold / unsold
    sold = [f for f in caught if int(f.get('sold') or 0) == 1]
    unsold = [f for f in caught if int(f.get('sold') or 0) == 0]

    print(f"Sold items: {len(sold)}\nUnsold items: {len(unsold)}\n")

    # Compute expected XP from sold items using DB helper
    per_item = []
    total_expected_xp = 0
    for item in sold:
        # The DB helper expects keys like 'weight', 'min_weight', 'max_weight', 'rarity', 'is_trash'
        xp = db.calculate_item_xp(item)
        per_item.append({
            'id': item.get('id'),
            'name': item.get('fish_name'),
            'weight': item.get('weight'),
            'rarity': item.get('rarity'),
            'price': item.get('price'),
            'xp': xp,
        })
        total_expected_xp += xp

    # Sort by xp desc for visibility
    per_item.sort(key=lambda x: x['xp'], reverse=True)

    print("Per-sold-item XP (top 50):")
    pp.pprint(per_item[:50])
    print('\nTotal expected XP from sold items:', total_expected_xp)

    # Also compute expected XP from ALL items (in case some sold were not flagged)
    total_all_xp = sum(db.calculate_item_xp(it) for it in caught)
    print('Total expected XP from all caught items:', total_all_xp)

    # Player stored XP
    player = db.get_player(USER_ID, CHAT_ID)
    if player:
        stored_xp = int(player.get('xp') or 0)
        stored_level = int(player.get('level') or 0)
        print(f"\nPlayer stored XP: {stored_xp} (level: {stored_level})")
        print(f"Difference (expected_from_sold - stored): {total_expected_xp - stored_xp}")
    else:
        print('\nPlayer row not found with provided user_id/chat_id lookup.')

    # Helpful totals by weight / price
    total_sold_weight = sum(float(it.get('weight') or 0) for it in sold)
    total_sold_value = sum(int(it.get('price') or 0) for it in sold)
    print(f"\nSold weight total: {total_sold_weight:.3f} kg")
    print(f"Sold coins total: {total_sold_value} 🪙")

    print('\nDone.')
