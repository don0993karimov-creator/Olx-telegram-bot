
import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.message:
        await update.message.reply_text(
            "Бот OLX → Telegram запущен! Напишите /help."
        )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.message:
        await update.message.reply_text(
            "Бот готов. Команда /test_channel проверяет отправку "
            "тестового сообщения в канал."
        )


async def test_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_user or not update.message:
        return

    admin_id = os.getenv("TELEGRAM_ADMIN_ID")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    if not admin_id or not channel_id:
        await update.message.reply_text(
            "Не настроены TELEGRAM_ADMIN_ID или TELEGRAM_CHANNEL_ID."
        )
        return

    if str(update.effective_user.id) != admin_id:
        await update.message.reply_text(
            "Эта команда доступна только владельцу бота."
        )
        return

    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=(
                "✅ Тест OLX → Telegram прошёл успешно!\n\n"
                "Бот может отправлять сообщения в канал."
            ),
        )
        await update.message.reply_text(
            "Готово! Проверьте канал — тестовое сообщение отправлено."
        )
    except Exception:
        logger.exception("Ошибка отправки тестового сообщения")
        await update.message.reply_text(
            "Не удалось отправить сообщение. Проверьте права бота "
            "и значение TELEGRAM_CHANNEL_ID в GitHub Secrets."
        )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Не задан секрет TELEGRAM_BOT_TOKEN в GitHub."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("test_channel", test_channel))

    logger.info("Запускаем Telegram-бота")
    app.run_polling()


if __name__ == "__main__":
    main()
