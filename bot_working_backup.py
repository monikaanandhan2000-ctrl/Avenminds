import os

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

from ai import ask_ai

from database import (
    initialize_database,
    save_user,
    create_verification,
    update_verification_details,
)


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


# Verification conversation states
NAME, AGE, LOCATION, SELFIE = range(4)


# =========================================================
# PRIVATE /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    args = context.args

    # -----------------------------------------------------
    # Verification deep link
    # Format:
    # /start verify_GROUPID_USERID
    # -----------------------------------------------------

    if args and args[0].startswith("verify_"):

        try:

            parts = args[0].split("_")

            group_chat_id = int(parts[1])
            target_user_id = int(parts[2])

        except (ValueError, IndexError):

            await update.message.reply_text(
                "❌ Invalid verification link."
            )

            return

        # Make sure the correct person opened the link
        if update.effective_user.id != target_user_id:

            await update.message.reply_text(
                "❌ This verification link belongs to another user."
            )

            return

        # Save verification information
        create_verification(
            update.effective_user,
            group_chat_id
        )

        context.user_data["verification_group_id"] = group_chat_id

        context.user_data["verification_user_id"] = (
            target_user_id
        )

        await update.message.reply_text(
            "🔐 Verification Started\n\n"
            "You must complete the following steps:\n\n"
            "1️⃣ Enter your name\n"
            "2️⃣ Enter your age\n"
            "3️⃣ Share your location\n"
            "4️⃣ Send a selfie\n\n"
            "Your information will be saved for "
            "group verification.\n\n"
            "Let's begin.\n\n"
            "👤 Please enter your name:"
        )

        return NAME

    # -----------------------------------------------------
    # Normal private /start
    # -----------------------------------------------------

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "I am your AI assistant.\n"
        "Send me a message and I will try to help you."
    )


# =========================================================
# HELP
# =========================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(
        "Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/ask - Ask the AI assistant\n"
        "/cancel - Cancel verification"
    )


# =========================================================
# AI ASK
# =========================================================

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

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

        print("AI Error:", repr(e))

        await update.message.reply_text(
            "Sorry, I couldn't process your request right now."
        )


# =========================================================
# NORMAL PRIVATE CHAT
# =========================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user or not update.message:
        return

    # NEVER answer ordinary group messages
    if update.effective_chat.type != "private":
        return

    save_user(update.effective_user)

    user_message = update.message.text

    try:

        answer = ask_ai(user_message)

        await update.message.reply_text(answer)

    except Exception as e:

        print("AI Error:", repr(e))

        await update.message.reply_text(
            "Sorry, something went wrong while processing your request."
        )


# =========================================================
# NEW GROUP MEMBER
# =========================================================

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    chat_id = update.effective_chat.id

    for member in update.message.new_chat_members:

        if member.is_bot:
            continue

        # Save user
        save_user(member)

        # Create pending verification
        create_verification(
            member,
            chat_id
        )

        # Restrict the new member
        try:

            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member.id,
                permissions={
                    "can_send_messages": False,
                    "can_send_audios": False,
                    "can_send_documents": False,
                    "can_send_photos": False,
                    "can_send_videos": False,
                    "can_send_video_notes": False,
                    "can_send_voice_notes": False,
                    "can_send_polls": False,
                    "can_send_other_messages": False,
                    "can_add_web_page_previews": False,
                    "can_change_info": False,
                    "can_invite_users": False,
                    "can_pin_messages": False,
                    "can_manage_topics": False,
                }
            )

        except Exception as e:

            print(
                "Restriction Error:",
                repr(e)
            )

        # Get bot username
        bot_info = await context.bot.get_me()

        verification_link = (
            f"https://t.me/{bot_info.username}"
            f"?start=verify_{chat_id}_{member.id}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔐 Start Verification",
                    url=verification_link
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(
            keyboard
        )

        # Only a short message is shown in the group
        await update.message.reply_text(
            f"👋 Welcome, {member.first_name}!\n\n"
            "🔐 Verification is required before you "
            "can participate in this group.\n\n"
            "Please click **Start Verification** and "
            "complete the process privately with the bot.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


# =========================================================
# VERIFICATION - NAME
# =========================================================

async def verification_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return NAME

    name = update.message.text.strip()

    if len(name) < 2:

        await update.message.reply_text(
            "Please enter a valid name."
        )

        return NAME

    context.user_data["verification_name"] = name

    await update.message.reply_text(
        "✅ Name received.\n\n"
        "🎂 Now enter your age.\n\n"
        "Example: 25"
    )

    return AGE


# =========================================================
# VERIFICATION - AGE
# =========================================================

async def verification_age(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return AGE

    try:

        age = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "Please enter your age as a number.\n\n"
            "Example: 25"
        )

        return AGE

    if age < 18 or age > 120:

        await update.message.reply_text(
            "Please enter a valid age between 18 and 120."
        )

        return AGE

    context.user_data["verification_age"] = age

    location_button = KeyboardButton(
        "📍 Share My Location",
        request_location=True
    )

    keyboard = ReplyKeyboardMarkup(
        [[location_button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "📍 Now share your current location.\n\n"
        "Tap **Share My Location** below.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    return LOCATION


# =========================================================
# VERIFICATION - LOCATION
# =========================================================

async def verification_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return LOCATION

    if not update.message.location:

        await update.message.reply_text(
            "Please use the **Share My Location** button.",
            parse_mode="Markdown"
        )

        return LOCATION

    location = update.message.location

    context.user_data["latitude"] = location.latitude
    context.user_data["longitude"] = location.longitude

    await update.message.reply_text(
        "✅ Location received.\n\n"
        "📸 Now send a selfie photo.\n\n"
        "Please send the photo directly in this private chat.",
        reply_markup=ReplyKeyboardRemove()
    )

    return SELFIE


# =========================================================
# VERIFICATION - SELFIE
# =========================================================

async def verification_selfie(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return SELFIE

    if not update.message.photo:

        await update.message.reply_text(
            "📸 Please send a selfie photo."
        )

        return SELFIE

    photo = update.message.photo[-1]

    selfie_file_id = photo.file_id

    group_chat_id = context.user_data.get(
        "verification_group_id"
    )

    name = context.user_data.get(
        "verification_name"
    )

    age = context.user_data.get(
        "verification_age"
    )

    latitude = context.user_data.get(
        "latitude"
    )

    longitude = context.user_data.get(
        "longitude"
    )

    # Save complete verification
    update_verification_details(
        telegram_id=update.effective_user.id,
        chat_id=group_chat_id,
        name=name,
        age=age,
        latitude=latitude,
        longitude=longitude,
        selfie_file_id=selfie_file_id
    )

    await update.message.reply_text(
        "✅ Verification submitted successfully.\n\n"
        "👤 Name: Saved\n"
        "🎂 Age: Saved\n"
        "📍 Location: Saved\n"
        "📸 Selfie: Saved\n\n"
        "🔐 Status: **Pending Review**\n\n"
        "An administrator will review your verification.",
        parse_mode="Markdown"
    )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# CANCEL
# =========================================================

async def cancel_verification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    if update.message:

        await update.message.reply_text(
            "❌ Verification cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


# =========================================================
# MAIN
# =========================================================

def main():

    initialize_database()

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN is missing from .env"
        )

    print("BOT_TOKEN loaded successfully.")

    app = Application.builder().token(
        BOT_TOKEN
    ).build()


    # -----------------------------------------------------
    # Private commands
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("ask", ask_command)
    )


    # -----------------------------------------------------
    # Verification conversation
    # -----------------------------------------------------

    verification_conversation = ConversationHandler(

        entry_points=[],

        states={

            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    verification_name
                )
            ],

            AGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    verification_age
                )
            ],

            LOCATION: [
                MessageHandler(
                    filters.LOCATION,
                    verification_location
                ),

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    verification_location
                )
            ],

            SELFIE: [
                MessageHandler(
                    filters.PHOTO,
                    verification_selfie
                )
            ]
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_verification
            )
        ],

        allow_reentry=True
    )


    # -----------------------------------------------------
    # New members
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_member
        )
    )


    # -----------------------------------------------------
    # Normal messages
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )


    # -----------------------------------------------------
    # IMPORTANT:
    # Register verification conversation
    # -----------------------------------------------------

    app.add_handler(
        verification_conversation
    )


    print("AI Telegram Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()