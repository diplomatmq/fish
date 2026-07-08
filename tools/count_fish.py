import re
import sys
sys.path.insert(0, '.')
from fish_stickers import FISH_STICKERS, FISH_INFO

with open('database.py', encoding='utf-8') as f:
    content = f.read()

names = re.findall(
    r'\("([^"]+)",\s*"(?:Обычная|Редкая|Легендарная|Мифическая|Аквариумная|Аномалия)"',
    content,
)
db_set = set(names)
print('Fish in database.py fish_data:', len(names))

sticker_new = [n for n in FISH_STICKERS if n not in db_set and n != 'Рыбнадзор']
print('FISH_STICKERS not in database.py:', len(sticker_new))

prefixes = ('Коралловый риф', 'Глубоководный желоб', 'Мангровые заросли')
new_loc = []
for n, v in FISH_INFO.items():
    habitat = (v.get('habitat') or '').strip()
    if any(habitat.startswith(p) for p in prefixes):
        new_loc.append(n)
new_loc_not_db = [n for n in new_loc if n not in db_set]
print('New location FISH_INFO not in db:', len(new_loc_not_db))

# Fish with stickers in new sections but not in db
new_sections = [
    'Канальный сомик', 'Амурский чебачок',  # pond new
]
for n in sticker_new:
    pass
print('\nMissing fish list:')
for n in sorted(sticker_new):
    info = FISH_INFO.get(n, {})
    habitat = info.get('habitat', '?')
    print(f'  {n} | {habitat}')
