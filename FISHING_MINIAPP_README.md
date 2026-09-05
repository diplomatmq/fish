# 🎣 Fishing Mini-App - Реализация

## ✅ Что сделано

### 1. Добавлен экран "ИГРЫ" в таббар
- Яркая анимированная кнопка с переливающимся свечением (красный → золотой → фиолетовый)
- Полноэкранная страница с двумя большими кнопками:
  - **🎣 РЫБАЛКА** - открывает игру рыбалка
  - **🎯 МИНИ ИГРЫ** - заглушка для будущих мини-игр

### 2. Создан экран рыбалки (FishingScreen)
**Файлы:**
- `webapp/ui_from_testpers/src/ui/fishingScreen.ts` - логика экрана
- `webapp/ui_from_testpers/src/fishing.css` - стили

**Функционал:**
- ✅ Кнопка "Назад" (верхний левый угол)
- ✅ Баланс звезд и TON коинов (верхний правый угол)
- ✅ Выпадающий список с балансом обеих валют
- ✅ Кнопки пополнения для каждой валюты
- ✅ Переключение между звездами и TON
- ✅ Слот-машина (3 барабана с анимацией)
- ✅ Большая кнопка "FISH" с анимацией
- ✅ Кулдаун на кнопке FISH (таймер 10 минут)
- ✅ Выбор локации (4 локации снизу)
- ✅ Статус лодки (показывает "На берегу" или "В лодке")

### 3. API интеграция
**Добавлены методы в `api.ts`:**
- `getProfile()` - получение данных игрока
- `updateLocation(location)` - смена локации
- `fish(location, guaranteed)` - ловля рыбы
- `checkCooldown()` - проверка кулдауна
- `getInventory()` - получение инвентаря

### 4. Анимации и эффекты
- Вращение барабанов слот-машины
- Пульсирующая кнопка FISH
- Анимированные переходы между экранами
- Плавные выпадающие списки

## ⚠️ Что нужно доработать на бэкенде

### 1. База данных
**Добавить поле в таблицу `players`:**
```sql
ALTER TABLE players ADD COLUMN ton_balance REAL DEFAULT 0;
```

Скрипт миграции создан: `add_ton_balance_migration.py`

**Запустить миграцию:**
```bash
# Если используется Docker
docker exec -it fishbot-bot python add_ton_balance_migration.py

# Или локально (нужно настроить подключение к PostgreSQL)
python add_ton_balance_migration.py
```

### 2. API эндпоинты (webapp/app.py)

**ВСЕ ЭНДПОИНТЫ ГОТОВЫ В ФАЙЛЕ `fishing_api_endpoints.py`**

Скопируйте содержимое файла `fishing_api_endpoints.py` в `webapp/app.py`:

1. Добавьте импорты в начало файла
2. Добавьте helper функцию `calculate_remaining_cooldown`
3. Добавьте все эндпоинты:
   - `/api/update-location` (POST) - обновление локации
   - `/api/cooldown` (GET) - проверка кулдауна
   - `/api/fish` (POST) - ловля рыбы
   - `/api/create-stars-invoice` (POST) - создание счета на звезды
   - `/api/confirm-ton-topup` (POST) - подтверждение пополнения TON

### 3. Обновить `/api/profile` 

Добавить поле `ton_balance` в ответ:
```python
@app.get("/api/profile")
def profile():
    # ... существующий код ...
    
    payload = {
        "user_id": user_id,
        # ... остальные поля ...
        "ton_balance": float(player.get("ton_balance") or 0.0),
        # ... остальные поля ...
    }
```

### 4. TON Connect настройка

**Манифест создан:** `webapp/ui_from_testpers/public/tonconnect-manifest.json`

**Разместите манифест на сервере:**
```bash
# Копировать в статические файлы webapp
cp webapp/ui_from_testpers/public/tonconnect-manifest.json webapp/static/

# Убедитесь что файл доступен по URL:
# https://fish.monkeysdynasty.website/tonconnect-manifest.json
```

**Кошелек для приема платежей:**
- Address (raw): `EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs`
- Address (friendly): `tensazangetsu.ton`

### 5. Синхронизация между ботом и мини-приложением

**ВАЖНО: Используется единое хранилище**

Все данные синхронизируются через таблицу `players`:
- `current_location` - текущая локация (одна для бота и webapp)
- `last_fish_time` - время последней ловли (общий кулдаун)
- `stars` - баланс звезд
- `ton_balance` - баланс TON

**Логика синхронизации в API:**
```python
# При изменении локации в webapp - обновляется и для бота
db.update_player(user_id, -1, current_location=location)  # webapp
db.update_player(user_id, 0, current_location=location)   # bot main chat

# При ловле в webapp - кулдаун применяется к боту
db.update_player(user_id, -1, last_fish_time=datetime.now().isoformat())
db.update_player(user_id, 0, last_fish_time=datetime.now().isoformat())
```

### 6. Цены и стоимости

**Гарантированный улов:**
- ⭐ **1 звезда** = 1 гарантированный улов
- 💎 **0.01 TON** = 1 гарантированный улов

**Кулдаун:** 10 минут (600 секунд)

**TON транзакции:**
- Все платежи идут на кошелек: `tensazangetsu.ton`
- Конвертация: 1 TON = 1,000,000,000 nanoTON
- Комментарий к транзакции: `TopUp:TON:{timestamp}` или `Guaranteed Fish`

## 📁 Структура файлов

```
webapp/ui_from_testpers/
├── src/
│   ├── ui/
│   │   ├── gamesScreen.ts        # Экран выбора игр
│   │   └── fishingScreen.ts      # Экран рыбалки (НОВЫЙ) ✅
│   ├── modules/
│   │   ├── api.ts                # API методы (ОБНОВЛЕН) ✅
│   │   └── tonConnect.ts         # TON Connect интеграция (НОВЫЙ) ✅
│   ├── games.css                  # Стили экрана игр
│   └── fishing.css                # Стили экрана рыбалки (НОВЫЙ) ✅
├── public/
│   └── tonconnect-manifest.json   # TON Connect манифест (НОВЫЙ) ✅
└── main.ts                        # Подключение экранов (ОБНОВЛЕН) ✅

Корневые файлы:
├── add_ton_balance_migration.py   # Миграция БД (НОВЫЙ) ✅
├── fishing_api_endpoints.py       # API эндпоинты (НОВЫЙ) ✅
└── FISHING_MINIAPP_README.md      # Документация (ЭТОТ ФАЙЛ) ✅
```

## 📦 Установленные зависимости

```json
{
  "@tonconnect/ui": "^2.0.0"  // TON Connect SDK
}
```

## 🚀 Как запустить

1. **Применить миграцию базы данных:**
```bash
python add_ton_balance_migration.py
```

2. **Добавить API эндпоинты** в `webapp/app.py` (см. раздел выше)

3. **Собрать фронтенд:**
```bash
cd webapp/ui_from_testpers
npm run build
```

4. **Запустить сервер:**
```bash
# В Docker
docker-compose up -d

# Или локально
python webapp/app.py
```

## 🎮 Как использовать

1. Открыть мини-приложение
2. Нажать на вкладку "ИГРЫ" (🎮) внизу
3. Нажать на кнопку "РЫБАЛКА" (🎣)
4. Выбрать локацию снизу
5. Нажать кнопку "FISH"
6. Ждать результат на слот-машине

**При наличии кулдауна:**
- Нажать на баланс звезд/TON сверху
- Выбрать валюту
- Нажать FISH - автоматически спишется валюта и выполнится гарантированный улов

## 📝 TODO (дополнительные улучшения)

- [ ] Добавить звуковые эффекты
- [ ] Добавить вибрацию при ловле
- [ ] Добавить историю уловов в реальном времени
- [ ] Добавить анимацию появления рыбы
- [ ] Добавить таблицу лидеров по локациям
- [ ] Добавить ачивки за ловлю в мини-приложении
- [ ] Добавить push-уведомления когда кулдаун закончился

## 🐛 Известные проблемы

1. Миграция БД требует доступ к PostgreSQL (в Docker)
2. API эндпоинты нужно добавить вручную
3. Telegram payment API для TON нужно настроить

## 💡 Примечания

- Все стили адаптированы под темную тему подводного мира
- Анимации оптимизированы для мобильных устройств
- Используется система кулдаунов из основной игры (10 минут)
- Интеграция с существующей логикой рыбалки через `game_logic.py`
