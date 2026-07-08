const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const databasePath = path.join(root, 'database.py');
const generatedPath = path.join(__dirname, 'generated_fish_entries.txt');

let db = fs.readFileSync(databasePath, 'utf8');
const generated = fs.readFileSync(generatedPath, 'utf8');

const coralBlock = generated.split('# ===== ГЛУБОКОВОДНЫЙ ЖЕЛОБ (новые виды) =====')[0].trim();
const deepAndMangrove = generated.split('# ===== ГЛУБОКОВОДНЫЙ ЖЕЛОБ (новые виды) =====')[1];
const deepBlock = '# ===== ГЛУБОКОВОДНЫЙ ЖЕЛОБ (новые виды) =====' + deepAndMangrove.split('# ===== МАНГРОВЫЕ ЗАРОСЛИ (новые виды) =====')[0];
const mangroveBlock = '# ===== МАНГРОВЫЕ ЗАРОСЛИ (новые виды) =====' + deepAndMangrove.split('# ===== МАНГРОВЫЕ ЗАРОСЛИ (новые виды) =====')[1];

const insertions = [
  {
    anchor: '                ("Спинорог", "Редкая", 0.3, 2.0, 15, 40, 60, "Коралловый риф", "Все", "Креветка,Кусочки рыбы,Морской червь,Моллюск", 10, None),\n',
    block: '\n' + coralBlock + '\n',
  },
  {
    anchor: '                ("Стеклянный кальмар", "Редкая", 0.3, 2.0, 10, 40, 120, "Глубоководный желоб", "Все", "Кусочки рыбы,Морской червь,Креветка", 12, None),\n',
    block: '\n' + deepBlock.trim() + '\n',
  },
  {
    anchor: '                ("Личинка угря (лептоцефал)", "Редкая", 0.01, 0.1, 5, 15, 60, "Мангровые заросли", "Все", "Мотыль,Опарыш,Морской червь", 5, None),\n',
    block: '\n' + mangroveBlock.trim() + '\n',
  },
];

for (const { anchor, block } of insertions) {
  if (!db.includes(anchor)) {
    throw new Error('Anchor not found: ' + anchor.slice(0, 80));
  }
  if (db.includes(block.trim().split('\n')[1])) {
    console.log('Already inserted:', block.trim().split('\n')[1].slice(0, 60));
    continue;
  }
  db = db.replace(anchor, anchor + block);
}

fs.writeFileSync(databasePath, db, 'utf8');
console.log('database.py updated successfully');
