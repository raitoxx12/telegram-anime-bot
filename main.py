import os
import json
import asyncio
import aiohttp
import nest_asyncio
from flask import Flask
from threading import Thread
from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

# === CONFIG ===
BOT_TOKEN = "7770796733:AAHrR9GlvFqbD2TL6JPnlhWtoV844-3IxSw"
OWNER_ID = 5525952879
FIREBASE_URL = "https://animebotstorage-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"
CHANNEL_USERNAME = "@ongoinganiime"

data = {}
temp_files = []

# === FIREBASE HANDLERS ===
async def load_data():
    global data
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FIREBASE_URL) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    data = result or {}
                    print("✅ Loaded data from Firebase")
                else:
                    print("❌ Firebase GET error:", await resp.text())
    except Exception as e:
        print(f"❌ Error loading data: {e}")

async def save_data():
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/json"}
            async with session.put(FIREBASE_URL, headers=headers, data=json.dumps(data)) as resp:
                result = await resp.text()
                print("✅ Firebase PUT response:", result)
    except Exception as e:
        print(f"❌ Error saving data: {e}")

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"
def run():
    app.run(host="0.0.0.0", port=8080)
def keep_alive():
    Thread(target=run).start()

# === CHECK CHANNEL JOIN ===
async def is_user_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except Exception as e:
        print(f"❌ Error checking user join: {e}")
        return False

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_joined(user_id, context):
        await update.message.reply_text(
            f"🔒 To use this bot, you must join our channel first:\n{CHANNEL_USERNAME}"
        )
        return

    if data:
        anime_list = "\n".join([f"🎬 `{tag}` — {len(files)} file(s)" for tag, files in data.items()])
        await update.message.reply_text(
            f"📌 *Available Anime:*\n\n{anime_list}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("📭 No anime available yet.")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global temp_files
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("⛔ Only the owner can upload files.")
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
    user_id = update.effective_user.id

    if not await is_user_joined(user_id, context):
        await update.message.reply_text(
            f"🔒 Please join {CHANNEL_USERNAME} to use this feature."
        )
        return

    tag = update.message.text.strip()

    if not tag.startswith("#"):
        await update.message.reply_text("❌ Invalid hashtag. Use #Naruto or #AOT.")
        return

    if temp_files:
        if tag not in data:
            data[tag] = []

        new_files = [f for f in temp_files if f not in data[tag]]
        data[tag].extend(new_files)

        await save_data()

        msg = (
            f"✅ {len(new_files)} new file(s) saved under `{tag}`"
            if new_files else f"⚠️ All files already exist under `{tag}`"
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
        "🚫 *Invalid message.* Use /start or send a hashtag like #Naruto.",
        parse_mode="Markdown"
    )

# === MAIN ===
async def main():
    await load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^#"), handle_hashtag))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.Regex(r"^#") & ~filters.COMMAND, handle_spam))

    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    keep_alive()
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print(f"⚠️ RuntimeError caught: {e}")
        
