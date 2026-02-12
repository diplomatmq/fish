import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import db
from game_logic import FishingGame

user_id = 793216884
chat_id = -1003864313222

print('Ensure player exists...')
if not db.has_any_player_profile(user_id):
    db.create_player(user_id, 'testuser', chat_id)
    print('Player created')
else:
    print('Player exists')

game = FishingGame()
print('Calling fish...')
res = game.fish(user_id, chat_id, 'Городской пруд')
print('Result:', res)
