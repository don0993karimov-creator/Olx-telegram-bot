import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")
OLX_URL = "https://www.olx.uz/nedvizhimost/kvartiry/prodazha/tashkent/"
DB_FILE = "seen_ads.sqlite3"
def init_db():
    with sqlite3.connect(DB_FILE) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS seen_ads (
                url TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)
def looks_like_owner(text: str) -> bool:
    """Фильтр по словам. Он не может гарантировать, что автор — собственник."""
    text = text.lower()
    realtor_words = [
        "агентство", "риелтор", "риэлтор", "маклер",
        "комиссия", "комиссионные", "агент недвижимости",
    ]
    owner_words = [
        "собственник", "от хозяина", "от владельца",
        "без посредников", "от собственника",
    ]
    if any(word in text for word in realtor_words):
        return False
    return any(word in text for word in owner_words)
async def fetch_ads():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(
        headers=headers, timeout=25, follow_redirects=True
    ) as client:
        response = await client.get(OLX_URL)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for card in soup.select("div[data-cy='l-card']"):
        link = card.select_one("a[href]")
        if not link:
            continue
        url = urljoin(OLX_URL, link.get("href", "")).split("?")[0]
        title = link.get_text(" ", strip=True)
        text = card.get_text(" ", strip=True)
        if "/obyavlenie/" not in url:
            continue
        if not title or not looks_like_owner(text):
            continue
        results.append({"url": url, "title": title, "text": text})
    return results
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Бот запущен.\n"
        "Команды: /help, /test_channel, /check"
    )
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "/start — проверка бота\n"
        "/test_channel — тестовая публикация в канал\n"
        "/check — поиск новых объявлений"
    )
async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_ID:
        await update.effective_message.reply_text(
            "Не настроен TELEGRAM_CHANNEL_ID в GitHub Secrets."
        )
        return
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="Тест: бот может отправлять сообщения в канал."
        )
        await update.effective_message.reply_text(
            "Тестовое сообщение отправлено. Проверь канал."
        )
    except Exception:
        logger.exception("Не удалось отправить сообщение в канал")
        await update.effective_message.reply_text(
            "Не получилось отправить сообщение. Проверь, что бот добавлен "
            "в канал администратором с правом публикации."
        )
async def check_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and str(update.effective_user.id) != ADMIN_ID:
        await update.effective_message.reply_text("Эта команда доступна администратору.")
        return
    await update.effective_message.reply_text("Ищу объявления на OLX…")
    try:
        ads = await fetch_ads()
        new_ads = []
        with sqlite3.connect(DB_FILE) as db:
            for ad in ads:
                exists = db.execute(
                    "SELECT 1 FROM seen_ads WHERE url = ?", (ad["url"],)
                ).fetchone()
                if not exists:
                    db.execute(
                        "INSERT INTO seen_ads(url, created_at) VALUES (?, ?)",
                        (ad["url"], datetime.now(timezone.utc).isoformat()),
                    )
                    new_ads.append(ad)
        if not new_ads:
            await update.effective_message.reply_text(
                "Новых объявлений, подходящих под фильтр собственников, не найдено."
            )
            return
        for ad in new_ads[:10]:
            message = (
                "Новое объявление — проверьте перед публикацией\n\n"
                f"{ad['title']}\n\n"
                f"{ad['text'][:700]}\n\n"
                f"{ad['url']}"
            )
            await update.effective_message.reply_text(message)
        await update.effective_message.reply_text(
            f"Найдено новых объявлений: {len(new_ads)}. "
            "Они отправлены сюда для проверки, не в канал автоматически."
        )
    except Exception:
        logger.exception("Ошибка поиска OLX")
        await update.effective_message.reply_text(
            "Не удалось получить объявления с OLX. Возможно, сайт временно "
            "ограничил запросы или изменил страницу."
        )
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("test_channel", test_channel))
    app.add_handler(CommandHandler("check", check_ads))
    app.run_polling()
if __name__ == "__main__":
    main()
