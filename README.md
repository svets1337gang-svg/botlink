# Telegram-бот: файлы по реферальным ссылкам

Бот на **aiogram 3.x** (Python 3.11+) + **aiosqlite**. Админ загружает файлы (хранится только `file_id`),
получает реферальную ссылку `https://t.me/<bot>?start=<код>`; пользователи по ссылке получают файл
(при включённой проверке — только после подписки на канал).

## Быстрый старт

```bash
cd bot
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # затем заполните .env
python main.py
```

## Настройка .env

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | токен от @BotFather |
| `ADMIN_ID` | ваш Telegram ID (узнать: @userinfobot) |
| `CHANNEL_ID` | ID канала `-100…` или `@username` |
| `CHANNEL_URL` | ссылка на канал для кнопки «Подписаться» |
| `DB_PATH` | путь к SQLite-файлу (по умолчанию `bot.db`) |
| `CHECK_SUBSCRIPTION` | `true`/`false` — начальное значение проверки подписки |

> После первого переключения проверки или смены канала в «⚙️ Настройки» значения хранятся в БД
> (таблица `settings`) и имеют приоритет над `.env`.

### Как узнать CHANNEL_ID
1. **Через бота:** перешлите любое сообщение из канала боту `@username_to_id_bot` (или `@getidsbot`) — он покажет ID вида `-100XXXXXXXXXX`.
2. **Через getUpdates:** добавьте бота админом в канал, опубликуйте пост и откройте
   `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` — найдите `"chat":{"id":-100…}` в `channel_post`
   (если пусто — временно остановите бота: getUpdates не работает параллельно с polling).
3. **Проще всего:** в боте «⚙️ Настройки → Сменить канал» и отправьте `@username` канала — ID определится сам.

### Важно
**Бот должен быть администратором канала**, иначе `get_chat_member` вернёт ошибку и проверка подписки не сработает.

## Использование

- Админ: `/admin` — панель; можно просто прислать файл — начнётся загрузка (название или `/skip`).
- `/list` — список публикаций (по 5 на странице): 🔗 ссылка, 📊 детали, 🗑 удаление (с подтверждением).
- `/cancel` — отмена текущего действия.
- Пользователь: переходит по ссылке → (подписка) → получает файл с подписью-названием.

## Архитектура

```
main.py                  запуск, логирование, сборка роутеров и middleware
config.py                чтение .env (dataclass Config)
database.py              aiosqlite: publications, publication_users, settings
filters.py               IsAdmin
handlers/admin.py        панель админа, FSM загрузки, список, статистика, настройки
handlers/user.py         /start <код>, кнопка «Я подписался», выдача файла
handlers/common.py       /help, fallback, обработка ошибок (в т.ч. блокировка бота)
keyboards/               inline-клавиатуры (callback_data короткие, < 64 байт)
middlewares/subscription.py  проверка подписки (member/administrator/creator)
```

Особенности:
- Переход и «уникальный пользователь» засчитываются **после успешной отправки** файла.
- Если `file_id` больше недействителен — пользователь видит сообщение, админ получает уведомление.
- Если пользователь заблокировал бота — ошибка логируется, бот продолжает работу.
- Логи: консоль + `bot.log` (ротация 2 МБ × 3).

## Как расширять

- **Рассылка:** добавить таблицу `users` (сохранять `user_id` в `deliver`) и хендлер в `handlers/admin.py`,
  который проходит по пользователям с паузой ~0.05 с и ловит `TelegramForbiddenError`.
- **Несколько админов:** заменить `ADMIN_ID` на список (`ADMIN_IDS=1,2,3`) и поправить `filters.IsAdmin` и middleware.
- **Аналитика по дням:** таблица `views_log(publication_id, user_id, ts)`; запись — в `Database.register_view`,
  агрегаты `GROUP BY date(ts)`.
- **Webhook:** заменить `start_polling` на `aiogram.webhook.aiohttp_server.SimpleRequestHandler`.
- **Постоянные FSM-состояния:** заменить `MemoryStorage` на `RedisStorage`.
