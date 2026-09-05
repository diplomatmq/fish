# 🚀 Руководство по развертыванию FishBot Mini-App

## ✅ Что уже готово

### Фронтенд
- ✅ Экран "ИГРЫ" с анимированной кнопкой
- ✅ Полнофункциональный экран рыбалки
- ✅ TON Connect интеграция
- ✅ API клиент с методами оплаты
- ✅ Слот-машина с анимациями
- ✅ Система кулдаунов
- ✅ Управление балансами (Stars & TON)

### Backend заготовки
- ✅ Миграция БД (`add_ton_balance_migration.py`)
- ✅ API эндпоинты (`fishing_api_endpoints.py`)
- ✅ TON Connect манифест

## 🔧 Шаги развертывания

### 1. Обновление базы данных

```bash
# Подключитесь к Docker контейнеру с ботом
docker exec -it fishbot-bot bash

# Запустите миграцию
python add_ton_balance_migration.py

# Или через docker-compose
docker-compose exec bot python add_ton_balance_migration.py
```

**Что добавится:**
- Колонка `ton_balance REAL DEFAULT 0` в таблицу `players`

### 2. Обновление Backend API

**Откройте файл `webapp/app.py`**

#### 2.1 Добавьте импорты (в начало файла):
```python
from game_logic import FishingGame
from datetime import datetime, timedelta
```

#### 2.2 Добавьте helper функцию:
```python
def calculate_remaining_cooldown(last_fish_time_str):
    """Calculate remaining cooldown in seconds"""
    if not last_fish_time_str:
        return 0
    
    COOLDOWN_MINUTES = 10
    
    last_time = datetime.fromisoformat(last_fish_time_str)
    time_passed = datetime.now() - last_time
    cooldown_duration = timedelta(minutes=COOLDOWN_MINUTES)
    
    if time_passed >= cooldown_duration:
        return 0
    
    remaining = cooldown_duration - time_passed
    return int(remaining.total_seconds())
```

#### 2.3 Скопируйте все эндпоинты из `fishing_api_endpoints.py`

Добавьте следующие эндпоинты:
- `/api/update-location` (POST)
- `/api/cooldown` (GET)
- `/api/fish` (POST)
- `/api/create-stars-invoice` (POST)
- `/api/confirm-ton-topup` (POST)

#### 2.4 Обновите `/api/profile`:

Найдите функцию `profile()` и добавьте в payload:
```python
"ton_balance": float(player.get("ton_balance") or 0.0),
```

### 3. Настройка TON Connect

#### 3.1 Скопируйте манифест на сервер:
```bash
# Из локальной папки проекта
scp webapp/ui_from_testpers/dist/tonconnect-manifest.json your_server:/path/to/webapp/static/

# Или если файлы уже на сервере
docker cp webapp/ui_from_testpers/dist/tonconnect-manifest.json fishbot-webapp:/app/static/
```

#### 3.2 Проверьте доступность манифеста:
```bash
curl https://fish.monkeysdynasty.website/tonconnect-manifest.json
```

Должен вернуть JSON с информацией о приложении.

### 4. Сборка и развертывание фронтенда

```bash
# Перейдите в папку UI
cd webapp/ui_from_testpers

# Установите зависимости (если еще не установлены)
npm install

# Соберите проект
npm run build

# Скопируйте собранные файлы на сервер
# Вариант 1: прямое копирование
scp -r dist/* your_server:/path/to/webapp/ui_from_testpers/dist/

# Вариант 2: через Docker
docker cp dist/. fishbot-webapp:/app/ui_from_testpers/dist/
```

### 5. Перезапуск сервисов

```bash
# Перезапустите webapp
docker-compose restart webapp

# Или полный перезапуск
docker-compose down
docker-compose up -d
```

### 6. Проверка работоспособности

#### 6.1 Проверьте API эндпоинты:
```bash
# Проверка здоровья
curl https://fish.monkeysdynasty.website/health

# Проверка TON манифеста
curl https://fish.monkeysdynasty.website/tonconnect-manifest.json
```

#### 6.2 Откройте мини-приложение в Telegram:
1. Откройте бота `@your_bot`
2. Нажмите кнопку открытия мини-приложения
3. Перейдите на вкладку "ИГРЫ" (🎮)
4. Нажмите "РЫБАЛКА" (🎣)

#### 6.3 Проверьте функционал:
- [ ] Экран рыбалки открывается
- [ ] Отображается текущий баланс
- [ ] Можно выбрать локацию
- [ ] Кнопка FISH работает
- [ ] После ловли запускается кулдаун
- [ ] Слот-машина крутится
- [ ] Можно переключить валюту (Stars ↔ TON)

## 🔑 Важные параметры

### Кошелек для приема TON
```
Address (raw): EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs
Address (friendly): tensazangetsu.ton
```

### Цены
- **Гарантированный улов (Stars):** 1 ⭐
- **Гарантированный улов (TON):** 0.01 💎
- **Кулдаун:** 10 минут (600 секунд)

### URLs
- **Webapp:** `https://fish.monkeysdynasty.website`
- **TON Manifest:** `https://fish.monkeysdynasty.website/tonconnect-manifest.json`

## 🐛 Troubleshooting

### Проблема: TON Connect не подключается

**Решение:**
1. Проверьте доступность манифеста по URL
2. Убедитесь что используется HTTPS
3. Проверьте консоль браузера на ошибки
4. Попробуйте очистить кэш браузера

### Проблема: API возвращает ошибку 500

**Решение:**
1. Проверьте логи backend:
   ```bash
   docker logs fishbot-webapp
   ```
2. Убедитесь что миграция БД выполнена
3. Проверьте импорты в app.py

### Проблема: Кулдаун не синхронизируется между ботом и webapp

**Решение:**
1. Проверьте что используется `chat_id=-1` для webapp
2. Убедитесь что в API `fish()` обновляется `last_fish_time` для обоих chat_id (0 и -1)
3. Проверьте код синхронизации в `api_fish()`:
   ```python
   # Sync to main chat
   db.update_player(user_id, 0, last_fish_time=datetime.now().isoformat())
   ```

### Проблема: Баланс не обновляется после оплаты

**Решение:**
1. Проверьте что транзакция прошла успешно в блокчейне
2. Убедитесь что вызывается `apiService.confirmTonTopup()`
3. Проверьте логи backend на наличие ошибок

## 📊 Мониторинг

### Логи для отслеживания:
```bash
# Логи webapp
docker logs -f fishbot-webapp

# Логи бота
docker logs -f fishbot-bot

# Логи базы данных
docker logs -f fishbot-postgres
```

### Ключевые метрики:
- Количество уловов через webapp
- Количество TON транзакций
- Средний кулдаун между уловами
- Ошибки API

## 🎉 После успешного развертывания

1. **Протестируйте все сценарии:**
   - Обычная ловля
   - Ловля с кулдауном (гарантированная)
   - Оплата звездами
   - Оплата TON
   - Смена локации
   - Синхронизация с ботом

2. **Объявите пользователям:**
   ```
   🎣 Новая функция!
   
   Теперь можно ловить рыбу прямо в мини-приложении!
   
   ✨ Возможности:
   • Красивый слот-машина интерфейс
   • Выбор локации
   • Оплата TON или Stars
   • Единый кулдаун с ботом
   
   Попробуйте: Меню → ИГРЫ → РЫБАЛКА
   ```

3. **Соберите обратную связь:**
   - Работает ли TON Connect?
   - Понятен ли интерфейс?
   - Есть ли баги?

## 📝 Контрольный список развертывания

- [ ] Миграция БД выполнена
- [ ] API эндпоинты добавлены в app.py
- [ ] TON Connect манифест доступен по URL
- [ ] Фронтенд собран и развернут
- [ ] Сервисы перезапущены
- [ ] API эндпоинты отвечают
- [ ] Мини-приложение открывается
- [ ] Экран рыбалки работает
- [ ] TON Connect подключается
- [ ] Обычная ловля работает
- [ ] Гарантированная ловля работает (Stars)
- [ ] Гарантированная ловля работает (TON)
- [ ] Кулдаун синхронизируется с ботом
- [ ] Локация синхронизируется с ботом
- [ ] Балансы обновляются корректно

## 🎯 Следующие шаги

После успешного развертывания можно добавить:
- [ ] Звуковые эффекты при ловле
- [ ] Анимацию появления рыбы
- [ ] Статистику уловов в реальном времени
- [ ] Ачивки за ловлю в webapp
- [ ] Push-уведомления когда кулдаун закончился
- [ ] Интеграцию с лодками
- [ ] Отображение крушения лодки
- [ ] История последних уловов
- [ ] Мини-игры (вторая кнопка на экране ИГРЫ)
