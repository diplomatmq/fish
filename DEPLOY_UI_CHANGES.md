# Деплой изменений UI лавки

## Быстрый старт

```bash
# 1. Перейти в директорию UI
cd webapp/ui_from_testpers

# 2. Установить зависимости (если нужно)
npm install

# 3. Собрать production версию
npm run build

# 4. Перезапустить приложение
# (файлы из dist/ автоматически используются)
```

## Что изменилось

### Файлы для сборки:
- ✅ `src/ui/shopScreen.ts` - логика лавки
- ✅ `src/style.css` - стили

### Результат сборки:
- `dist/assets/index-*.js` - скомпилированный JavaScript
- `dist/assets/index-*.css` - скомпилированный CSS
- `dist/index.html` - главная страница

## Проверка изменений

### Локально (dev режим):
```bash
cd webapp/ui_from_testpers
npm run dev
# Откройте http://localhost:5173
```

### Production:
```bash
npm run build
# Проверьте что файлы созданы в dist/
ls -la dist/assets/
```

## Деплой на сервер

### Вариант 1: Docker (автоматически)
```bash
# Пересобрать Docker образ
docker-compose build

# Перезапустить контейнер
docker-compose up -d
```

### Вариант 2: Вручную
```bash
# Собрать UI
cd webapp/ui_from_testpers
npm run build

# Скопировать на сервер (если нужно)
scp -r dist/* user@server:/path/to/webapp/ui_from_testpers/dist/

# Перезапустить приложение
systemctl restart fishbot
# или
pm2 restart fishbot
```

## Проверка на production

1. Откройте приложение в Telegram
2. Перейдите в лавку
3. Проверьте:
   - ✅ Кнопка "ПРОДАТЬ" компактная
   - ✅ Текст "Выбрано: X" читается (белый на темном)
   - ✅ Панель остается внизу при скролле
   - ✅ Клик на рыбу открывает модальное окно
   - ✅ Можно выбрать действие (трофей/продажа)
   - ✅ Показываются все рыбы из группы
   - ✅ Можно выбрать конкретные рыбы

## Откат изменений

Если что-то пошло не так:

```bash
# Откатить через git
git checkout HEAD~1 webapp/ui_from_testpers/src/ui/shopScreen.ts
git checkout HEAD~1 webapp/ui_from_testpers/src/style.css

# Пересобрать
cd webapp/ui_from_testpers
npm run build

# Перезапустить
docker-compose restart
```

## Troubleshooting

### Изменения не видны в браузере
```bash
# Очистить кэш браузера
Ctrl+Shift+R (Chrome/Firefox)
Cmd+Shift+R (Mac)

# Или добавить версию в URL
?v=2
```

### Ошибки TypeScript при сборке
```bash
# Проверить типы
npm run type-check

# Если ошибки - исправить и пересобрать
npm run build
```

### Ошибки в консоли браузера
```bash
# Открыть DevTools (F12)
# Проверить вкладку Console
# Проверить вкладку Network
```

### API не отвечает
```bash
# Проверить логи сервера
docker-compose logs -f

# Проверить что API endpoints доступны
curl http://localhost:8080/api/inventory/grouped
```

## Мониторинг

### Логи приложения:
```bash
# Docker
docker-compose logs -f

# PM2
pm2 logs fishbot

# Systemd
journalctl -u fishbot -f
```

### Метрики:
- Время загрузки страницы
- Время ответа API
- Количество ошибок
- Использование памяти

## Контрольный список деплоя

- [ ] Код изменен
- [ ] Локально протестировано (npm run dev)
- [ ] Собрано (npm run build)
- [ ] Файлы в dist/ обновлены
- [ ] Закоммичено в git
- [ ] Задеплоено на сервер
- [ ] Приложение перезапущено
- [ ] Проверено в production
- [ ] Кэш браузера очищен
- [ ] Все функции работают
- [ ] Нет ошибок в консоли
- [ ] Нет ошибок в логах

## Команды для быстрого деплоя

```bash
# Полный цикл
cd webapp/ui_from_testpers && \
npm run build && \
cd ../.. && \
docker-compose build && \
docker-compose up -d && \
docker-compose logs -f
```

## Полезные ссылки

- [BUILD_INSTRUCTIONS.md](webapp/ui_from_testpers/BUILD_INSTRUCTIONS.md) - детальная инструкция по сборке
- [SHOP_UI_IMPROVEMENTS.md](SHOP_UI_IMPROVEMENTS.md) - описание улучшений
- [package.json](webapp/ui_from_testpers/package.json) - npm скрипты

---

**Время деплоя:** ~2-5 минут  
**Downtime:** 0 секунд (hot reload)  
**Rollback time:** ~1 минута
