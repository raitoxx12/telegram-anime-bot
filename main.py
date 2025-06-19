import json
import asyncio
import aiohttp
import nest_asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

# === CONFIG ===
BOT_TOKEN = "7770796733:AAHrR9GlvFqbD2TL6JPnlhWtoV844-3IxSw"
OWNER_ID = 5525952879
GIST_URL = "https://gist.githubusercontent.com/raitoxx12/cb30c6e29ff7ef61404cc1f9296a0445/raw/623775477ae730081f8805c32703d7cf70beef4a/data.json"

data = {}
temp_files = []

# === DATA STORAGE ===
async def load_data():
    global data
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GIST_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("✅ Data loaded from Gist")
                else:
                    data = {}
                    print("⚠️ Gist is empty or not found")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        data = {}

async def save_data():
    try:
        headers = {'Content-Type': 'application/json'}
        async with aiohttp.ClientSession() as session:
            async with session.put(GIST_URL, headers=headers, data=json.dumps(data)):
                print("✅ Data saved to Gist")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

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
        anime_list = "\n".join(
            [f"🎬 `{tag}` — {len(files)} episode(s)" for tag, files in data.items()]
        )
        await update.message.reply_text(
            f"📌 *Available Anime:*\n\n{anime_list}", parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("📭 No anime available. Upload using owner access.")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_files
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("🚫 You are not allowed to upload files.")
        return

    file = update.message.document or update.message.video or update.message.audio
    if file:
        temp_files.append(file.file_id)

    context.chat_data["file_count"] = context.chat_data.get("file_count", 0) + 1

    if context.chat_data["file_count"] == 1:
        await update.message.reply_text(
            f"📥 {len(temp_files)} file(s) received. Now send a hashtag to tag them."
        )

async def handle_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_files
    tag = update.message.text.strip()

    if not tag.startswith("#"):
        await update.message.reply_text("❌ Invalid hashtag format. Use #Naruto, #OnePiece etc.")
        return

    if temp_files:
        if tag not in data:
            data[tag] = []

        new_files = [f for f in temp_files if f not in data[tag]]
        data[tag].extend(new_files)
        await save_data()

        msg = (
            f"✅ {len(new_files)} new file(s) saved under `{tag}`"
            if new_files
            else f"⚠️ All files were already saved under `{tag}`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        temp_files.clear()
        context.chat_data["file_count"] = 0
    else:
        files = data.get(tag)
        if not files:
            await update.message.reply_text("⚠️ No files found under this hashtag.")
        else:
            await update.message.reply_text(
                f"📦 Sending *{len(files)}* file(s) under `{tag}`...",
                parse_mode="Markdown"
            )
            for file_id in files:
                try:
                    await update.message.reply_document(file_id)
                except Exception as e:
                    print(f"❌ Error sending file: {e}")

async def handle_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚫 *You are trying to interrupt the bot by sending these messages.*\n"
        "Use hashtags to fetch files or /start to see available anime.",
        parse_mode="Markdown"
    )

# === MAIN ===
async def main():
    await load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^#"), handle_hashtag))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.Regex(r"^#") & ~filters.COMMAND), handle_spam))

    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    keep_alive()
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print(f"⚠️ RuntimeError caught: {e}")
            
