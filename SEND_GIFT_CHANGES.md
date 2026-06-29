# Изменения для реализации команды /send

## Новые файлы

### 1. `send_gift_system.py` (новый файл, 378 строк)
Полная логика системы отправки подарков:
- Меню выбора типа подарка
- Клавиатуры для выбора удочек, одежды, наживок
- Валидация ресурсов перед отправкой
- Функция передачи подарка
- Поиск получателя по username или ID

**Основные функции:**
- `get_send_main_menu_keyboard()` - главное меню
- `get_rods_keyboard(page)` - список удочек с пагинацией
- `get_clothing_keyboard(page)` - список одежды с пагинацией
- `get_bait_locations_keyboard()` - выбор локации для наживок
- `get_baits_for_location_keyboard(location, page)` - наживки для локации
- `validate_gift_item(...)` - проверка ресурсов отправителя
- `execute_gift_transfer(...)` - передача подарка
- `find_user_by_username_or_id(...)` - поиск получателя

### 2. `SEND_GIFT_README.md` (документация)
Полное описание системы отправки подарков, примеры использования, технические детали.

### 3. `SEND_GIFT_TESTING.md` (чеклист тестирования)
Подробный чеклист для тестирования всех аспектов команды /send.

### 4. `SEND_GIFT_CHANGES.md` (этот файл)
Сводка всех изменений.

## Изменения в существующих файлах

### `bot.py`

#### Новые handler-методы (добавлено ~420 строк кода):

1. **`handle_send_select_type`** - обработка выбора типа подарка
2. **`handle_send_cancel`** - отмена отправки подарка
3. **`handle_send_back_main`** - возврат в главное меню
4. **`handle_send_rod_selection`** - выбор удочки
5. **`handle_send_rods_page`** - пагинация удочек
6. **`handle_send_clothing_selection`** - выбор одежды
7. **`handle_send_clothing_page`** - пагинация одежды
8. **`handle_send_bait_location_selection`** - выбор локации для наживок
9. **`handle_send_bait_selection`** - выбор наживки
10. **`handle_send_baits_page`** - пагинация наживок
11. **`handle_send_text_input`** - обработка ввода количества и username
12. **`handle_send_gift_precheckout`** - pre-checkout проверка перед оплатой
13. **`handle_send_gift_successful_payment`** - обработка успешной оплаты

#### Изменения в `send_command` (уже существовал):
- Добавлена полная реализация

#### Изменения в `cancel_command`:
- Добавлена проверка `send_gift_draft` для отмены отправки подарка
- Текст отмены: "✅ Ваша попытка отправить подарок отменена."
- Не показывает лишние сообщения

#### Изменения в `precheckout_callback`:
```python
elif payload.startswith("send_gift_"):
    await self.handle_send_gift_precheckout(update, context)
    return
```

#### Изменения в `successful_payment_callback`:
```python
if payload and payload.startswith("send_gift_"):
    await self.handle_send_gift_successful_payment(update, context)
    return
```

#### Регистрация handlers (строка ~15722):
```python
application.add_handler(CommandHandler("send", bot_instance.send_command))
```

#### Регистрация callback handlers (строки ~15370-15382):
```python
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_cancel, pattern="^send_cancel$"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_back_main, pattern="^send_back_main$"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_select_type, pattern="^send_select_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_rods_page, pattern="^send_rods_page_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_rod_selection, pattern="^send_rod_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_clothing_page, pattern="^send_clothing_page_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_clothing_selection, pattern="^send_clothing_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_baits_page, pattern="^send_baits_page_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_bait_location_selection, pattern="^send_bait_loc_"))
application.add_handler(CallbackQueryHandler(bot_instance.handle_send_bait_selection, pattern="^send_bait_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_send_text_input), group=4)
```

### `database.py`

#### Новая функция:
```python
def get_any_chat_id_for_user(self, user_id: int) -> Optional[int]:
    """Получить любой chat_id для пользователя"""
    with self._connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id FROM players WHERE user_id = ? LIMIT 1', (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None
```

**Расположение:** После функции `has_any_player_profile`, перед `has_any_referral` (строка ~7860)

**Назначение:** Находит любой chat_id пользователя для отправки подарка (когда получатель может иметь профили в разных чатах)

#### Существующие функции, используемые в /send:
- `get_player(user_id, chat_id)` - получить профиль игрока
- `get_player_by_username(username)` - найти игрока по username
- `has_any_player_profile(user_id)` - проверить существование профиля
- `get_all_rods()` - список всех удочек
- `get_all_locations()` - список локаций
- `get_baits_for_location(location)` - наживки для локации
- `get_player_rod(user_id, rod_name, chat_id)` - проверить наличие удочки
- `get_rod(rod_name)` - данные удочки
- `get_bait(bait_name)` - данные наживки
- `get_bait_count(user_id, bait_name)` - количество наживки
- `get_player_clothing(user_id, clothing_code)` - проверить наличие одежды
- `update_player(user_id, chat_id, **kwargs)` - обновить профиль
- `grant_rod(user_id, rod_name, chat_id, stack=True)` - выдать удочку
- `add_bait(user_id, bait_name, quantity)` - добавить наживку
- `remove_bait(user_id, bait_name, quantity)` - убрать наживку
- `add_clothing(user_id, clothing_code)` - добавить одежду

## Структура данных

### Context.user_data['send_gift_draft']
Временное хранилище состояния отправки:
```python
{
    'step': str,  # 'select_type', 'select_rod', 'enter_coins', 'enter_username', etc.
    'sender_id': int,
    'sender_chat_id': int,
    'gift_type': str,  # 'coins', 'rods', 'baits', 'nets', 'clothing'
    'item_name': str,  # Название удочки/наживки/одежды
    'quantity': int,  # Количество
    'location': str,  # Локация (для наживок)
    'recipient_id': int,  # ID получателя
}
```

### Payment payload format
```
send_gift_{sender_id}_{recipient_id}
```

## Логика работы

### Основной флоу:
1. Пользователь: `/send` (только в ЛС)
2. Бот: Показывает меню выбора типа подарка
3. Пользователь: Выбирает тип (монеты/удочки/наживки/сети/одежда)
4. Бот: Запрашивает детали (конкретный предмет или количество)
5. Пользователь: Выбирает/вводит детали
6. Бот: Запрашивает @username или ID получателя
7. Пользователь: Вводит получателя
8. Бот: Валидирует ресурсы, отправляет инвойс 25 звезд
9. Пользователь: Оплачивает
10. Бот: Pre-checkout проверяет ресурсы еще раз
11. Бот: Списывает ресурсы у отправителя, добавляет получателю
12. Бот: Отправляет уведомления обоим игрокам

### Валидация:
- **Монеты:** Проверка наличия достаточного количества монет
- **Удочки:** Проверка наличия удочки + достаточно монет для покрытия стоимости
- **Наживки:** Проверка наличия наживки + достаточно монет для покрытия стоимости
- **Сети:** Проверка наличия достаточного количества сетей
- **Одежда:** Проверка наличия одежды + достаточно бриллиантов для покрытия стоимости

### Передача:
- **Монеты/Сети:** Прямая передача через update_player
- **Удочки:** grant_rod с stack=True (для временных удочек суммируются использования)
- **Наживки:** remove_bait у отправителя + add_bait получателю
- **Одежда:** add_clothing получателю

## Особенности реализации

1. **Работает только в ЛС:** Проверка `update.effective_chat.type != 'private'` → игнор
2. **Отмена через /cancel:** Единая обработка для RAF и /send без лишних сообщений
3. **Стакание удочек:** При передаче временной удочки использования суммируются
4. **Поиск получателя:** Поддержка @username, username без @, и ID
5. **Защита от дублирования:** Payload добавляется в `paid_payloads`
6. **Pre-checkout валидация:** Двойная проверка ресурсов (перед инвойсом и перед оплатой)
7. **Уведомления:** Оба игрока получают сообщения (получатель - если бот может отправить DM)

## Зависимости

### Внешние модули:
- `telegram` - Telegram Bot API
- `telegram.ext` - PTB framework

### Внутренние модули:
- `database` - работа с БД
- `bot` - константы (CLOTHING_ITEMS, CLOTHING_ITEM_BY_CODE)

## Статистика изменений

- **Новых файлов:** 4 (send_gift_system.py, 3 markdown документа)
- **Измененных файлов:** 2 (bot.py, database.py)
- **Новых строк кода:** ~800
- **Новых функций:** 14 (13 в bot.py, 1 в database.py)
- **Новых callback patterns:** 11

## Совместимость

- ✅ PostgreSQL (через существующую обертку)
- ✅ Асинхронная архитектура (через _run_sync)
- ✅ Существующая система платежей
- ✅ Существующая система валидации
- ✅ Существующая система уведомлений

## Что еще может потребоваться

1. **Логирование транзакций подарков** - отдельная таблица для истории (опционально)
2. **Лимиты на отправку** - например, не более 10 подарков в день (опционально)
3. **Статистика** - счетчики отправленных/полученных подарков (опционально)
4. **Админ-панель** - просмотр истории подарков (опционально)
