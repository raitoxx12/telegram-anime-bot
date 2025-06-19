import logging
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
import firebase_admin
from firebase_admin import credentials, db
import os

# === CONFIG ===
BOT_TOKEN = "7770796733:AAHrR9GlvFqbD2TL6JPnlhWtoV844-3IxSw"
OWNER_ID = 5525952879
FIREBASE_URL = "https://animebotstorage-default-rtdb.asia-southeast1.firebasedatabase.app/"
CHANNEL_ID = "@zxdverse"

# === INIT FIREBASE ===
if not firebase_admin._apps:
    cred = credentials.Certificate({
        # Your Firebase service account info here
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "...",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        "client_email": "...",
        "client_id": "...",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "..."
    })
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_URL
    })

db_ref = db.reference("anime")

# === SETUP LOGGING ===
logging.basicConfig(level=logging.INFO)
buffered_files = {}

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_in_channel(context, user.id):
        await update.message.reply_text(
            "🔐 Please join our channel to use this bot: https://t.me/zxdverse"
        )
        return

    data = db_ref.get()
    if data:
        animes = "\n".join([f"🔹 {name}" for name in data.keys()])
        await update.message.reply_text(f"📌 Available Anime:\n{animes}")
    else:
        await update.message.reply_text("📭 No anime available yet.")


async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    user_id = update.effective_user.id
    buffered_files[user_id] = buffered_files.get(user_id, [])

    if update.message.document:
        buffered_files[user_id].append(update.message.document.file_id)
    elif update.message.video:
        buffered_files[user_id].append(update.message.video.file_id)
    elif update.message.audio:
        buffered_files[user_id].append(update.message.audio.file_id)

    await update.message.reply_text(
        f"📥 {len(buffered_files[user_id])} files received. Now send a name to tag them."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip().lower()

    if text.startswith("/"):
        return

    if not await is_user_in_channel(context, user.id):
        await update.message.reply_text(
            "🔐 Please join our channel to use this bot: https://t.me/zxdverse"
        )
        return

    if user.id == OWNER_ID and user.id in buffered_files and buffered_files[user.id]:
        anime_ref = db_ref.child(text.replace(".", "").replace("$", "").replace("[", "").replace("]", "").replace("#", "").replace("/", ""))
        existing = anime_ref.get() or []
        new_files = buffered_files[user.id]
        anime_ref.set(existing + new_files)
        await update.message.reply_text(f"✅ {len(new_files)} files saved under {text}")
        buffered_files[user.id] = []
    else:
        anime_ref = db_ref.child(text)
        files = anime_ref.get()
        if files:
            for fid in files:
                await update.message.reply_document(document=InputFile(fid))
        else:
            await update.message.reply_text(
                f"⚠️ This anime is not available yet. We are working to make it available soon. Stay tuned! ✨"
            )

# === MAIN ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
