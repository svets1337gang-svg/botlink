"""Хендлеры обычных пользователей: выдача файла по реферальной ссылке."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database
from middlewares.subscription import CODE_RE, is_subscribed, load_sub_settings

logger = logging.getLogger(__name__)
router = Router(name="user")

# тип файла -> (метод бота, имя параметра с file_id)
SEND_METHODS = {
    "document": ("send_document", "document"),
    "photo": ("send_photo", "photo"),
    "video": ("send_video", "video"),
    "audio": ("send_audio", "audio"),
    "voice": ("send_voice", "voice"),
    "animation": ("send_animation", "animation"),
}


async def send_publication(bot: Bot, chat_id: int, pub: dict) -> None:
    method, param = SEND_METHODS[pub["file_type"]]
    await getattr(bot, method)(chat_id=chat_id, **{param: pub["file_id"]},
                               caption=escape(pub["title"]))


async def deliver(bot: Bot, db: Database, config: Config, user_id: int, code: str) -> str | None:
    """Отправляет файл. Возвращает текст ошибки для пользователя или None."""
    if not CODE_RE.match(code):
        return "Публикация не найдена или удалена."
    pub = await db.get_by_code(code)
    if not pub:
        return "Публикация не найдена или удалена."
    try:
        await send_publication(bot, user_id, pub)
    except TelegramForbiddenError:
        logger.warning("Пользователь %s заблокировал бота — файл не отправлен", user_id)
        return None
    except TelegramBadRequest as e:
        # file_id больше недействителен (файл удалён с серверов Telegram и т.п.)
        logger.error("Не удалось отправить публикацию #%s: %s", pub["id"], e)
        try:
            await bot.send_message(
                config.admin_id,
                f"⚠️ Публикация <b>#{pub['id']}</b> «{escape(pub['title'])}» недоступна: "
                f"{escape(str(e))}\nЗагрузите файл заново.",
            )
        except TelegramAPIError:
            pass
        return "😔 Файл временно недоступен. Мы уже сообщили администратору."
    # Считаем переход только после успешной отправки
    await db.register_view(pub["id"], user_id)
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot,
                    db: Database, config: Config) -> None:
    code = (command.args or "").strip()
    if not code:
        if message.from_user.id == config.admin_id:
            await message.answer("Привет, админ! Откройте панель: /admin")
        else:
            await message.answer("👋 Привет! Перейдите по реферальной ссылке, чтобы получить файл.")
        return
    error = await deliver(bot, db, config, message.from_user.id, code)
    if error:
        await message.answer(error)


@router.callback_query(F.data.startswith("chk:"))
async def cb_check(call: CallbackQuery, bot: Bot, db: Database, config: Config) -> None:
    code = call.data.split(":", 1)[1]
    user_id = call.from_user.id
    sub = await load_sub_settings(db, config)
    if sub.enabled and user_id != config.admin_id:
        status = await is_subscribed(bot, sub.channel_id, user_id)
        if status is None:
            await call.answer("⚠️ Не удалось проверить подписку. Попробуйте позже.", show_alert=True)
            return
        if not status:
            await call.answer("Вы ещё не подписались ❌", show_alert=True)
            return
    await call.answer("Спасибо за подписку! ✅")
    try:
        await call.message.delete()
    except TelegramAPIError:
        pass
    if code == "-":
        await bot.send_message(user_id, "✅ Подписка подтверждена! Перейдите по реферальной ссылке ещё раз.")
        return
    error = await deliver(bot, db, config, user_id, code)
    if error:
        await bot.send_message(user_id, error)
