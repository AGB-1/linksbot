import logging
import re
import pandas as pd
from datetime import datetime, time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# --- CONFIGURATION ---
BOT_TOKEN = "7881181524:AAF4QGOC4pudrjKhLKQSSaPbS8dn58ggOMU"   # <<< put your token here
group_links = {}

# --- Capture Links Handler ---
async def capture_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in group_links:
        group_links[chat_id] = []

    username = user.username
    if username:
        display_name = f"@{username}"
    else:
        display_name = f"{user.full_name}"

    text = update.effective_message.text or ""
    found_links = re.findall(r"https?://\S+", text)

    for link in found_links:
        if (display_name, link) not in group_links[chat_id]:
            group_links[chat_id].append((display_name, link))
            logging.info(f"Captured link from {display_name}: {link}")

# --- Send Links Handler (Automatic + Manual) ---
async def send_links(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M")

    logging.info(f"Auto/manual send triggered at {now}...")

    for chat_id, entries in group_links.items():
        if not entries:
            continue

        # --- Save as Text file ---
        txt_filename = f"links_{chat_id}_{date_str}.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            for username, link in entries:
                f.write(f"{username}: {link}\n")

        # --- Save as Excel file ---
        excel_filename = f"links_{chat_id}_{date_str}.xlsx"
        df = pd.DataFrame(entries, columns=["Username", "Link"])
        df.to_excel(excel_filename, index=False)

        # --- Send files ---
        try:
            await context.bot.send_document(chat_id=chat_id, document=open(txt_filename, "rb"))
            await context.bot.send_document(chat_id=chat_id, document=open(excel_filename, "rb"))
            logging.info(f"Sent files to chat {chat_id}")
        except Exception as e:
            logging.error(f"Failed to send files to chat {chat_id}: {e}")

        # --- Clear after sending ---
        group_links[chat_id] = []

# --- Manual Command /sendlinks ---
async def manual_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_links(context)
    await update.message.reply_text("Manual send complete!")

# --- Main Setup ---
def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Capture links from text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_links))

    # Manual command to send immediately
    app.add_handler(CommandHandler("sendlinks", manual_send))

    # Setup automatic sending every day at 10:00 AM
    app.job_queue.run_daily(
        send_links,
        time=time(hour=10, minute=0, second=0),
        name="daily-auto-send",
    )

    logging.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()