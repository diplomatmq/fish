# Инструкция по деплою исправлений

## Быстрый старт

```bash
# 1. Остановить бота (если запущен)
# Ctrl+C или kill процесс

# 2. Применить изменения уже сделаны в коде

# 3. Webapp уже пересобран (dist обновлен)

# 4. Перезапустить бота
python bot.py
```

## Детальная инструкция

### 1. Подготовка

```bash
# Убедитесь что вы в корневой директории проекта
cd c:\Users\dip663322o2244\PycharmProjects\fishbot

# Проверьте что все изменения применены
git status
```

### 2. Остановка бота

**Если бот запущен как процесс:**
```bash
# Найти процесс
ps aux | grep bot.py

# Остановить
kill <PID>
```

**Если бот запущен в screen/tmux:**
```bash
# Подключиться к сессии
screen -r fishbot
# или
tmux attach -t fishbot

# Остановить (Ctrl+C)
```

### 3. Проверка изменений

Измененные файлы:
- ✅ `bot.py` - основной файл бота
- ✅ `webapp/ui_from_testpers/src/ui/captchaScreen.ts` - экран капчи
- ✅ `webapp/ui_from_testpers/dist/` - пересобранный webapp

### 4. Запуск бота

**Вариант 1: Прямой запуск**
```bash
python bot.py
```

**Вариант 2: С логированием**
```bash
python bot.py 2>&1 | tee -a bot.log
```

**Вариант 3: В фоне (screen)**
```bash
screen -S fishbot
python bot.py
# Ctrl+A, D для отключения
```

**Вариант 4: В фоне (tmux)**
```bash
tmux new -s fishbot
python bot.py
# Ctrl+B, D для отключения
```

### 5. Проверка работы

```bash
# Проверить что бот запустился
tail -f bot.log

# Должны увидеть:
# INFO - Bot started successfully
# INFO - Polling started
```

### 6. Тестирование

#### Тест 1: Гарантированный улов
1. Отправить `/fish` в чат
2. Если рыба сорвалась, оплатить гарантированный улов (1⭐)
3. **Ожидаемый результат:** Сообщение о рыбе приходит в чат

#### Тест 2: Капча
1. Вызвать капчу (спамить `/fish` или другие команды)
2. Открыть webapp с капчей
3. Ввести правильный ответ
4. **Ожидаемый результат:** "✅ Капча пройдена! Ограничение снято."

#### Тест 3: Случайные сообщения
1. Отправить случайное сообщение (например "2406", "test", "123")
2. **Ожидаемый результат:** Бот игнорирует сообщение, нет ошибок в логах

### 7. Мониторинг

```bash
# Следить за логами в реальном времени
tail -f bot.log

# Искать ошибки
grep ERROR bot.log

# Искать конкретную ошибку
grep "async_generator" bot.log
```

### 8. Откат (если что-то пошло не так)

```bash
# Остановить бота
# Ctrl+C или kill процесс

# Откатить изменения
git checkout bot.py
git checkout webapp/ui_from_testpers/src/ui/captchaScreen.ts

# Пересобрать webapp (если нужно)
cd webapp/ui_from_testpers
npm run build
cd ../..

# Запустить бота снова
python bot.py
```

## Проверка успешности деплоя

### ✅ Чеклист

- [ ] Бот запустился без ошибок
- [ ] Гарантированный улов работает (сообщение приходит)
- [ ] Капча проходится без ошибок
- [ ] Случайные сообщения не вызывают ошибок
- [ ] В логах нет ошибок "async_generator"
- [ ] В логах нет ошибок "Ошибка отправки ответа"

### 📊 Метрики для мониторинга

```bash
# Количество ошибок за последний час
grep ERROR bot.log | grep "$(date +%Y-%m-%d)" | wc -l

# Количество успешных гарантированных уловов
grep "Guaranteed catch message sent successfully" bot.log | wc -l

# Количество ошибок капчи
grep "Failed to submit captcha" bot.log | wc -l
```

## Troubleshooting

### Проблема: Бот не запускается

```bash
# Проверить зависимости
pip install -r requirements.txt

# Проверить переменные окружения
cat .env

# Проверить порты
netstat -tulpn | grep 8008
```

### Проблема: Webapp не обновляется

```bash
# Пересобрать webapp
cd webapp/ui_from_testpers
npm run build

# Проверить что dist обновился
ls -la dist/

# Очистить кеш браузера
# Ctrl+Shift+R в браузере
```

### Проблема: Ошибки в логах

```bash
# Посмотреть последние 100 строк логов
tail -n 100 bot.log

# Посмотреть только ошибки
grep ERROR bot.log | tail -n 50

# Посмотреть traceback
grep -A 10 "Traceback" bot.log
```

## Контакты

Если возникли проблемы:
1. Проверьте логи: `tail -f bot.log`
2. Проверьте чеклист выше
3. Посмотрите FIXES_2026_05_17.md для деталей исправлений

## Дополнительно

### Автоматический перезапуск (systemd)

Создайте файл `/etc/systemd/system/fishbot.service`:

```ini
[Unit]
Description=Fish Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/fishbot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fishbot
sudo systemctl start fishbot
sudo systemctl status fishbot
```

### Логирование в файл

Добавьте в начало `bot.py`:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
```
