# Исправление ошибки "The asyncio extension requires an async driver"

Если вы получили эту ошибку при запуске на Replit, следуйте этой инструкции:

## Быстрое исправление (2 минуты)

### Вариант 1: Обновить проект из GitHub

1. В Replit откройте **Shell** (вкладка внизу)
2. Выполните команды:
   ```bash
   git fetch origin
   git pull origin main
   pip install -r requirements.txt
   ```
3. Нажмите **Run** снова

### Вариант 2: Переимпортировать проект

1. Удалите текущий Repl (Settings → Delete Repl)
2. Создайте новый: **+ Create Repl** → **Import from GitHub**
3. Вставьте URL: `https://github.com/ByteNich/massage-booking-bot`
4. Добавьте Secrets снова (BOT_TOKEN, ADMIN_ID, EMPLOYEE_IDS)
5. Нажмите **Run**

### Вариант 3: Отключить PostgreSQL от Replit (самый простой)

Если Replit автоматически добавил PostgreSQL, можно его отключить:

1. В Replit зайдите в **Tools** → **Database**
2. Если видите PostgreSQL - отключите его
3. Или в Secrets удалите переменную `DATABASE_URL` (если она есть)
4. Нажмите **Run** - бот будет использовать SQLite

## Что было исправлено?

- ✅ Добавлена автоматическая конвертация DATABASE_URL в async-версию
- ✅ Добавлен драйвер `asyncpg` для PostgreSQL
- ✅ Теперь бот работает и с SQLite, и с PostgreSQL

## Проверка

После исправления в консоли должно появиться:
```
INFO - Database initialized
INFO - Notification scheduler started
INFO - Bot started
```

Если проблема осталась - напишите мне, помогу!
