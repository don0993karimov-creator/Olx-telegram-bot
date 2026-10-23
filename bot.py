import os import logging from telegram import Update from telegram.ext import ( Application, CommandHandler, ContextTypes, )
logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)
Список объявлений, ожидающих одобрения.
Пока хранится в памяти; позже добавим постоянное хранилище.
pending_ads = {}
async def start( update: Update, context: ContextTypes.DEFAULT_TYPE, ): await update.message.reply_text( "Бот OLX → Telegram работает.\n\n" "Команды:\n" "/help — помощь\n\n" "Следующий этап — подключение объявлений " "и проверка перед публикацией." )
async def help_command( update: Update, context: ContextTypes.DEFAULT_TYPE, ): await update.message.reply_text( "На следующем этапе подключим поиск объявлений " "о продаже квартир в Ташкенте и публикацию " "только после вашего одобрения." )
def main(): token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise RuntimeError(
        "Не задан секрет TELEGRAM_BOT_TOKEN"
    )

app = Application.builder().token(token).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))

logger.info("Запускаем Telegram-бота")
app.run_polling()
if name == "main": main()
