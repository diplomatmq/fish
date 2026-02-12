import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import db, DB_PATH
from database import BAMBOO_ROD

print('DB path:', DB_PATH)
print('Testing update_player with typical kwargs...')
try:
    db.update_player(1, -100, coins=123)
    print('OK: coins')
except Exception as e:
    print('ERR coins', e)

try:
    db.update_player(1, -100, current_rod=BAMBOO_ROD)
    print('OK: current_rod')
except Exception as e:
    print('ERR current_rod', e)

try:
    db.update_player(1, -100, chat_id=555)
    print('OK: chat_id')
except Exception as e:
    print('ERR chat_id', e)

try:
    db.update_player(1, -100, coins=100, last_fish_time='2026-02-09T00:00:00')
    print('OK: coins+last_fish_time')
except Exception as e:
    print('ERR coins+last_fish_time', e)

print('Done')
