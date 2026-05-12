# Критические исправления UI

## Дата: 2026-05-12

## Исправленные проблемы

### ✅ 1. Профиль не открывается после книги

**Проблема:**
- После открытия книги и попытки открыть профиль - пропадают все кнопки
- Остается только задний фон
- Невозможно взаимодействовать с интерфейсом

**Причина:**
В `animations/effects.ts` функция `ScreenTransition.transitionTo()` устанавливала `pointerEvents = 'none'` на новый экран, но не включала обратно после завершения анимации.

**Исправление:**
```typescript
// Добавлен setTimeout для включения pointer events после анимации
setTimeout(() => {
  to.style.pointerEvents = 'all';
}, 400);
```

**Файл:** `webapp/ui_from_testpers/src/animations/effects.ts`

---

### ✅ 2. Капча не работает - нет полей

**Проблема:**
- Пользователи жалуются что капча не работает
- Нет полей для ввода
- Не видны подсказки и условия

**Причина:**
Блоки с подсказками и условиями скрывались (`display: none`) если данные не загружались сразу, что создавало впечатление что полей нет вообще.

**Исправление 1 - JavaScript:**
```javascript
// Всегда показываем блоки, даже если нет данных
mapBlock.style.display = "block";
stepsBlock.style.display = "block";

// Показываем placeholder пока данные загружаются
if (!hasMap || symbolMap.length === 0) {
  const li = document.createElement("li");
  li.textContent = "Загрузка подсказок...";
  li.style.opacity = "0.6";
  captchaMap.appendChild(li);
}
```

**Исправление 2 - HTML:**
```html
<!-- Добавлены inline стили для гарантированного отображения -->
<label class="field-label" for="captchaAnswer" style="display: block; margin-top: 16px;">
  ⌨️ Ответ
</label>
<div class="trophy-row" style="display: flex; gap: 8px;">
  <input id="captchaAnswer" style="flex: 1; min-width: 0;" />
  <button id="captchaSubmit" style="flex-shrink: 0;">✅ Проверить</button>
</div>
```

**Файлы:**
- `webapp/static/js/app.js`
- `webapp/templates/index.html`

---

## Измененные файлы

### 1. `webapp/ui_from_testpers/src/animations/effects.ts`
```diff
+ // ИСПРАВЛЕНИЕ: Включаем pointer events после завершения анимации
+ setTimeout(() => {
+   to.style.pointerEvents = 'all';
+ }, 400);
```

### 2. `webapp/static/js/app.js`
```diff
- mapBlock.style.display = hasMap ? "block" : "none";
+ mapBlock.style.display = "block";

+ if (!hasMap || symbolMap.length === 0) {
+   const li = document.createElement("li");
+   li.textContent = "Загрузка подсказок...";
+   li.style.opacity = "0.6";
+   captchaMap.appendChild(li);
+ }
```

### 3. `webapp/templates/index.html`
```diff
- <label class="field-label" for="captchaAnswer">⌨️ Ответ</label>
+ <label class="field-label" for="captchaAnswer" style="display: block; margin-top: 16px;">⌨️ Ответ</label>

- <div class="trophy-row">
+ <div class="trophy-row" style="display: flex; gap: 8px;">
```

---

## Как применить исправления

### Для UI (TypeScript):
```bash
cd webapp/ui_from_testpers
npm run build
```

### Для старого UI (HTML/JS):
Файлы уже исправлены, просто перезапустите приложение:
```bash
docker-compose restart
# или
pm2 restart fishbot
```

---

## Тестирование

### Проверка профиля:
1. ✅ Открыть приложение
2. ✅ Перейти в "Книга"
3. ✅ Вернуться в "Профиль"
4. ✅ Убедиться что все кнопки работают
5. ✅ Попробовать переключаться между разными вкладками

### Проверка капчи:
1. ✅ Открыть капчу через бота
2. ✅ Убедиться что видны блоки:
   - 💡 Подсказка (с символами или "Загрузка...")
   - 📜 Условия (со списком или "Загрузка...")
   - ⌨️ Ответ (поле ввода)
   - ✅ Проверить (кнопка)
3. ✅ Ввести ответ
4. ✅ Нажать "Проверить"
5. ✅ Убедиться что капча работает

---

## Дополнительные улучшения

### Капча:
- ✅ Всегда показываются блоки (не скрываются)
- ✅ Placeholder пока данные загружаются
- ✅ Поле ввода всегда видно
- ✅ Кнопка не сжимается на мобильных

### Переходы между экранами:
- ✅ Плавная анимация
- ✅ Pointer events включаются после анимации
- ✅ Нет "мертвых" экранов
- ✅ Все кнопки кликабельны

---

## Известные проблемы (исправлены)

### ❌ Было:
- Профиль не открывается после книги
- Капча без полей
- Кнопки не работают после перехода
- Блоки скрываются если нет данных

### ✅ Стало:
- Профиль всегда открывается
- Капча всегда показывает поля
- Все кнопки работают
- Блоки всегда видны с placeholder'ами

---

## Контрольный список

- [x] Исправлен баг с pointer events
- [x] Исправлено отображение капчи
- [x] Добавлены placeholder'ы для загрузки
- [x] Улучшены inline стили
- [x] Протестированы переходы между экранами
- [x] Протестирована капча
- [x] Обновлена документация

---

## Rollback (если нужно)

### Откатить через git:
```bash
git checkout HEAD~1 webapp/ui_from_testpers/src/animations/effects.ts
git checkout HEAD~1 webapp/static/js/app.js
git checkout HEAD~1 webapp/templates/index.html
```

### Пересобрать:
```bash
cd webapp/ui_from_testpers
npm run build
docker-compose restart
```

---

**Статус:** ✅ Все исправления применены  
**Приоритет:** 🔴 Критический  
**Тестирование:** ✅ Пройдено  
**Готово к деплою:** ✅ Да
