const fs = require('fs');
const s = fs.readFileSync('../database.py', 'utf8');
const anchor = '                ("Спинорог", "Редкая", 0.3, 2.0, 15, 40, 60, "Коралловый риф", "Все", "Креветка,Кусочки рыбы,Морской червь,Моллюск", 10, None),\n';
console.log('includes anchor:', s.includes(anchor));
const idx = s.indexOf('("Спинорог"');
console.log('idx', idx);
if (idx >= 0) {
  const snippet = s.slice(idx - 16, idx + anchor.length);
  console.log('snippet bytes', [...snippet].map(c => c.charCodeAt(0)).slice(0, 30));
  console.log('line ending', snippet.includes('\r\n') ? 'CRLF' : 'LF');
}
