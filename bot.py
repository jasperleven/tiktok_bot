import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
import asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_ID = "1JXhy8umRsU8UCxdPEKvd-suXb6Hcrfh0_Z_wEoGUG_k"

GOOGLE_CREDS = {
    "type": "service_account",
    "project_id": "lively-welder-480714-h9",
    "private_key_id": "317763c1365925cff1c8d309099701df70164154",
    "private_key": os.environ.get("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": "birthday-bot@lively-welder-480714-h9.iam.gserviceaccount.com",
    "client_id": "114057745621034407943",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/birthday-bot%40lively-welder-480714-h9.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}


def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet


def load_birthdays():
    try:
        sheet = get_sheet()
        records = sheet.get_all_values()
        birthdays = {}
        for row in records:
            if len(row) >= 2 and row[0] and row[1]:
                birthdays[row[0]] = row[1]
        return birthdays
    except Exception as e:
        logging.error(f"Ошибка загрузки из Sheets: {e}")
        return {}


def save_birthdays(birthdays):
    try:
        sheet = get_sheet()
        sheet.clear()
        rows = [[name, date] for name, date in birthdays.items()]
        if rows:
            sheet.update(rows, "A1")
    except Exception as e:
        logging.error(f"Ошибка сохранения в Sheets: {e}")


def get_todays_birthdays():
    birthdays = load_birthdays()
    today = datetime.now().strftime("%d.%m")
    celebrants = [name for name, date in birthdays.items() if date == today]
    if celebrants:
        names = ", ".join(celebrants)
        return f"🎂 Сегодня день рождения: {names}! Не забудьте поздравить! 🎉"
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


async def send_daily_notification():
    bot = Bot(token=TOKEN)
    result = get_todays_birthdays()
    if result:
        await bot.send_message(chat_id=CHAT_ID, text=result)
    else:
        await bot.send_message(chat_id=CHAT_ID, text="Сегодня дней рождения нет 🙂")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Привет! Я бот-напоминалка о днях рождения.\n\n"
        "Команды:\n"
        "/add — добавить дни рождения\n"
        "/list — показать всех\n"
        "/delete Имя — удалить\n"
        "/check — проверить сегодняшние ДР\n\n"
        "Формат добавления:\n"
        "/add Мама 15.03, Папа 22.07, Сестра 01.01\n\n"
        "Автоматические уведомления приходят каждый день в 9:00 по Минску."
    )
    await update.message.reply_text(text)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    text = message[4:].strip()

    if not text:
        await update.message.reply_text(
            "Укажите имена и даты:\n/add Мама 15.03, Папа 22.07, Сестра 01.01"
        )
        return

    entries = [e.strip() for e in text.split(",") if e.strip()]
    birthdays = load_birthdays()
    added = []
    errors = []

    for entry in entries:
        parts = entry.rsplit(" ", 1)
        if len(parts) != 2:
            errors.append(f"❌ Не понял: {entry}")
            continue
        name, date = parts
        try:
            datetime.strptime(date.strip(), "%d.%m")
            birthdays[name.strip()] = date.strip()
            added.append(f"✅ {name.strip()} — {date.strip()}")
        except ValueError:
            errors.append(f"❌ Неверная дата: {entry} (нужен формат ДД.ММ)")

    save_birthdays(birthdays)

    result = ""
    if added:
        result += "Добавлено:\n" + "\n".join(added)
    if errors:
        result += "\n\nОшибки:\n" + "\n".join(errors)

    await update.message.reply_text(result)


async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdays = load_birthdays()
    if not birthdays:
        await update.message.reply_text("Список пуст. Добавьте через /add")
        return

    sorted_b = sorted(birthdays.items(), key=lambda x: datetime.strptime(x[1], "%d.%m").replace(year=2000))
    text = "🎂 Дни рождения:\n\n"
    for name, date in sorted_b:
        text += f"{date} — {name}\n"
    await update.message.reply_text(text)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите имя: /delete Мама")
        return

    name = " ".join(context.args)
    birthdays = load_birthdays()

    if name in birthdays:
        del birthdays[name]
        save_birthdays(birthdays)
        await update.message.reply_text(f"✅ {name} удалён")
    else:
        await update.message.reply_text(f"❌ {name} не найден в списке")


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = get_todays_birthdays()
    if result:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Сегодня дней рождения нет 🙂")


async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk")
    scheduler.add_job(send_daily_notification, 'cron', hour=10, minute=0)
    scheduler.start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_birthdays))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("check", check))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()


if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    asyncio.run(main())
