import json
import asyncio
import nest_asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIG ===
BOT_TOKEN = "6822633489:AAEBQWl94eDTWqRMRwdhoEyElWETF6DFuPE"
OWNER_ID = 5525952879

DATA_FILE = "data.json"
data = {}
temp_files = []

def load_data():
    global data
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# === HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if data:
        anime_list = "\n".join([f"🎬 `{tag}` — {len(files)} episode(s)" for tag, files in data.items()])
        await update.message.reply_text(f"💻 *Available Anime:*\n\n{anime_list}", parse_mode="Markdown")
    else:
        await update.message.reply_text("📭 No anime saved yet.")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_files
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("🚫 You are not allowed to upload files.")
        return

    file = update.message.document or update.message.video or update.message.audio
    if file:
        temp_files.append(file.file_id)

    # Only show this message once when batch starts
    if len(temp_files) == 1:
        await update.message.reply_text("📥 Files are being received...\n(You will be notified once all are received.)")

async def handle_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_files
    tag = update.message.text.strip()

    if not tag.startswith("#"):
        await update.message.reply_text("❌ Invalid hashtag format. Use `#Naruto`, `#AOT`, etc.")
        return

    if temp_files:
        if tag not in data:
            data[tag] = []

        new_files = [f for f in temp_files if f not in data[tag]]
        data[tag].extend(new_files)
        save_data()

        await update.message.reply_text(f"✅ {len(new_files)} new file(s) saved under `{tag}`", parse_mode="Markdown")
        temp_files = []
    else:
        files = data.get(tag)
        if not files:
            await update.message.reply_text("⚠️ No files found under this hashtag.")
        else:
            await update.message.reply_text(f"📦 Sending *{len(files)}* file(s) under `{tag}`...", parse_mode="Markdown")
            for file_id in files:
                try:
                    await update.message.reply_document(file_id)
                except Exception as e:
                    print(f"❌ Error sending file: {e}")

# === MAIN ===
async def main():
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^#"), handle_hashtag))

    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    keep_alive()
    nest_asyncio.apply()
    asyncio.run(main())

