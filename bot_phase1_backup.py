import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ai import ask_ai


# Load .env FIRST
load_dotenv()


# Get Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "I am your AI assistant.\n"
        "Send me any message and I will try to help you."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/ask - Ask the AI assistant"
    )


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Please type your question after /ask.\n\n"
            "Example:\n"
            "/ask I need a website for my business"
        )
        return

    user_message = " ".join(context.args)

    try:
        answer = ask_ai(user_message)
        await update.message.reply_text(answer)

    except Exception as e:
        print("AI Error:", e)

        await update.message.reply_text(
            "Sorry, I couldn't process your request right now."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    try:
        answer = ask_ai(user_message)
        await update.message.reply_text(answer)

    except Exception as e:
        print("AI Error:", e)

        await update.message.reply_text(
            "Sorry, something went wrong while processing your request."
        )


def main():

    # Check that Telegram token was loaded
    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN is missing from .env"
        )

    print("BOT_TOKEN loaded successfully.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("ask", ask_command)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("AI Telegram Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()