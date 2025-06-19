import logging
import os
import json
import aiohttp
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "7770796733:AAHrR9GlvFqbD2TL6JPnlhWtoV844-3IxSw"
OWNER_ID = 5525952879
FIREBASE_URL = "https://animebotstorage-default-rtdb.asia-southeast1.firebasedatabase.app/files.json"
REQUIRED_CHANNEL = "@ongoinganiime"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_pending_files = {}

async def is_user_in_channel(user_id: int, session: aiohttp.ClientSession) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={REQUIRED_CHANNEL}&user_id={user_id}"
    async with session.get(url) as resp:
        data = await resp.json()
        return data.get("result", {}).get("status") in ["member", "administrator", "creator"]

async def load_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(FIREBASE_URL) as resp:
            return await resp.json() or {}

async def save_data(data):
    async with aiohttp.ClientSession() as session:
        async with session.put(FIREBASE_URL, json=data) as resp:
            return await resp.json()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiohttp.ClientSession() as session:
        if not await is_user_in_channel(update.effective_user.id, session):
            await update.message.reply_text("📢 Join our channel to use this bot: @ongoinganiime")
            return
    data = await load_data()
    if not data:
        await update.message.reply_text("📭 No anime available yet.")
        return
    msg = "\ud83d\udccc Available Anime:\n\n" + "\n".join(f"- {key}" for key in data.keys())
    await update.message.reply_text(msg)

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    media_group_id = update.message.media_group_id
    if media_group_id:
        group = user_pending_files.setdefault(update.effective_user.id, {}).setdefault(media_group_id, [])
        group.append(update.message)
    else:
        user_pending_files.setdefault(update.effective_user.id, {}).setdefault("single", []).append(update.message)
    total = sum(len(v) for v in user_pending_files[OWNER_ID].values())
    await update.message.reply_text(f"\ud83d\udce9 {total} files received. Now send a name to store them.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    async with aiohttp.ClientSession() as session:
        if not await is_user_in_channel(user_id, session):
            await update.message.reply_text("📢 Join our channel to use this bot: @ongoinganiime")
            return

    if user_id == OWNER_ID and user_id in user_pending_files:
        pending = user_pending_files.pop(user_id)
        all_files = []
        for msgs in pending.values():
            for msg in msgs:
                file_id = (msg.document or msg.video or msg.audio).file_id
                all_files.append(file_id)
        data = await load_data()
        if text in data:
            data[text].extend(all_files)
            await update.message.reply_text(f"\u2705 {len(all_files)} new files added under {text}")
        else:
            data[text] = all_files
            await update.message.reply_text(f"\u2705 {len(all_files)} files saved under {text}")
        await save_data(data)
        return

    # User requested an anime
    data = await load_data()
    key = text.strip("#")  # allow with or without hashtag
    if key in data:
        for file_id in data[key]:
            await update.message.reply_document(file_id)
    else:
        await update.message.reply_text(
            "\u2692\ufe0f This anime is not available yet. We are working under maintenance to make it available soon. Stay tuned! @ongoinganiime"
        )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.Audio.ALL, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()
    
