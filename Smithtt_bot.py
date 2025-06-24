import os
import uuid
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters,
                          CallbackQueryHandler, ContextTypes, ConversationHandler)

# Folder setup
INPUT_DIR = "input_videos"
OUTPUT_DIR = "spoofed_videos"
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# States for conversation
ASK_VIDEO, ASK_COPIES = range(2)

user_data = {}  # Temporary per-user data store

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the TikTok Spoofer Bot.\n\nSend me a video file (.mp4 or .mov) to begin.")
    return ASK_VIDEO

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("Please send a .mp4 or .mov video file.")
        return ASK_VIDEO

    file_id = video.file_id
    new_file = await context.bot.get_file(file_id)
    filename = f"{uuid.uuid4().hex[:8]}.mp4"
    input_path = os.path.join(INPUT_DIR, filename)
    await new_file.download_to_drive(input_path)

    user_data[update.effective_user.id] = {"input_path": input_path}

    keyboard = [[InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(1, 4)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("How many spoofed copies would you like?", reply_markup=reply_markup)
    return ASK_COPIES

async def select_copies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    copies = int(query.data)
    uid = update.effective_user.id
    user_data[uid]["copies"] = copies

    await query.edit_message_text(text=f"Spoofing {copies} copy/copies. Please wait...")
    input_path = user_data[uid]["input_path"]

    spoofed_files = spoof_video(input_path, OUTPUT_DIR, copies)
    for path in spoofed_files:
        await context.bot.send_document(chat_id=uid, document=open(path, 'rb'))

    return ConversationHandler.END

def spoof_video(input_path, output_dir, num_copies):
    output_files = []
    for i in range(1, num_copies + 1):
        unique_id = str(uuid.uuid4().hex[:8])
        output_filename = f"{os.path.splitext(os.path.basename(input_path))[0]}_spoofed_{unique_id}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-metadata", f"title=spoofed_{unique_id}",
            "-metadata", f"comment=TikTokSpoof_{i}",
            "-vf", "eq=brightness=0.003:saturation=1.01",
            "-map_metadata", "-1",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            output_path
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True)
            output_files.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e}")
    return output_files

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled. Send a new video to start again.")
    return ConversationHandler.END

if __name__ == '__main__':
    import asyncio
    import os
    from telegram.ext import Application

    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video)],
            ASK_COPIES: [CallbackQueryHandler(select_copies)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    print("Bot is running...")
    asyncio.run(app.run_polling())

