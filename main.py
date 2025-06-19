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
    # If user sends /start with junk text, block it with warning
    text = update.message.text.strip().lower()
    junk_texts = ["hi", "hey", "hello", "hola", "wassup", "yo"]
    if any(word in text for word in junk_texts):
        await update.message.reply_text(
            "🚫 You are trying to interrupt the bot by sending these bullshit messages.\n"
            "If you want to store your files, go to @filestorebot\n"
            "If not, get lost @zeqseed"
        )
        return

    # Normal start behavior
    if data:
        anime_list = "\n".join([f"🎬 `{tag}` — {len(files)} episode(s)" for tag, files in data.items()])
        await update.message.reply_text(f"📌 *Available Anime:*\n\n{anime_list}", parse_mode="Markdown")
    else:
        await update.message.reply_text("📭 No hashtags available. Upload anime using your owner access.")

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

    # Only show message once per batch
    if context.chat_data["file_count"] == 1:
        await update.message.reply_text("📥 Receiving files...\n(I'll let you know once all are received.)")

async def handle_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_files
    tag = update.message.text.strip()

    # If user sends unrelated text starting with #, block and warn
    junk_texts = ["hi", "hey", "hello", "hola", "wassup", "yo"]
    if any(word in tag.lower() for word in junk_texts):
        await update.message.reply_text(
            "🚫 You are trying to interrupt the bot by sending these bullshit messages.\n"
            "If you want to store your files, go to @filestorebot\n"
            "If not, get lost @zeqseed"
        )
        return

    if not tag.startswith("#"):
        await update.message.reply_text("❌ Invalid hashtag format. Use `#Naruto`, `#AOT`, etc.")
        return

    # Save mode (when files are waiting to be tagged)
    if temp_files:
        if tag not in data:
            data[tag] = []

        new_files = [f for f in temp_files if f not in data[tag]]
        added_count = len(new_files)

        data[tag].extend(new_files)
        save_data()
        temp_files.clear()
        context.chat_data["file_count"] = 0

        if added_count == 0:
            await update.message.reply_text(f"⚠️ All files were already saved under `{tag}`.", parse_mode="Markdown")
        else:
            message = (
                f"✅ {added_count} new file(s) *added* under `{tag}`"
                if tag in data and len(data[tag]) > added_count
                else f"✅ {added_count} file(s) *saved* under `{tag}`"
            )
            await update.message.reply_text(message, parse_mode="Markdown")
    else:
        # Retrieval mode
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

