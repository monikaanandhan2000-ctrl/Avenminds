import os

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ChatPermissions,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
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


# Verification states
NAME, AGE, LOCATION, SELFIE = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return ConversationHandler.END

    # Verification must happen in private chat
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    args = context.args

    # --------------------------------------------------
    # VERIFICATION START
    # --------------------------------------------------

    if args and args[0].startswith("verify_"):

        try:
            parts = args[0].split("_")

            group_chat_id = int(parts[1])
            target_user_id = int(parts[2])

        except (ValueError, IndexError):

            await update.message.reply_text(
                "❌ Invalid verification link."
            )

            return ConversationHandler.END

        # Make sure this link belongs to this Telegram user
        if update.effective_user.id != target_user_id:

            await update.message.reply_text(
                "❌ This verification link belongs to another user."
            )

            return ConversationHandler.END

        # Create/reset verification record
        create_verification(
            update.effective_user,
            group_chat_id
        )

        context.user_data.clear()

        context.user_data["verification_group_id"] = group_chat_id
        context.user_data["verification_user_id"] = target_user_id

        await update.message.reply_text(
            "🔐 Verification Started\n\n"
            "You must complete 4 steps:\n\n"
            "1️⃣ Name\n"
            "2️⃣ Age\n"
            "3️⃣ Location\n"
            "4️⃣ Selfie\n\n"
            "Your information will be submitted privately "
            "for administrator review.\n\n"
            "👤 Step 1/4\n\n"
            "Please enter your full name:"
        )

        return NAME

    # --------------------------------------------------
    # NORMAL START
    # --------------------------------------------------

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "I am your AI assistant.\n"
        "Send me a message and I will try to help you."
    )

    return ConversationHandler.END


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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


async def ask_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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


# ------------------------------------------------------
# NEW GROUP MEMBER
# ------------------------------------------------------

async def new_member(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    chat_id = update.effective_chat.id

    for member in update.message.new_chat_members:

        if member.is_bot:
            continue

        save_user(member)

        create_verification(
            member,
            chat_id
        )

        # Restrict member
        try:

            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_manage_topics=False,
                )
            )

            print(
                f"Restricted new member: "
                f"{member.id}"
            )

        except Exception as e:

            print(
                "Restriction Error:",
                repr(e)
            )

        # Create private verification deep link
        try:

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

            await update.message.reply_text(
                f"👋 Welcome, {member.first_name}!\n\n"
                "🔐 Verification is required before "
                "you can participate in this group.\n\n"
                "Please complete the verification privately "
                "with our bot.\n\n"
                "Click the button below to begin.",
                reply_markup=reply_markup
            )

        except Exception as e:

            print(
                "Verification Link Error:",
                repr(e)
            )


# ------------------------------------------------------
# VERIFICATION — NAME
# ------------------------------------------------------

async def verification_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return NAME

    name = update.message.text.strip()

    if len(name) < 2:

        await update.message.reply_text(
            "❌ Please enter a valid name."
        )

        return NAME

    context.user_data[
        "verification_name"
    ] = name

    await update.message.reply_text(
        "✅ Name received.\n\n"
        "🎂 Step 2/4\n\n"
        "Please enter your age.\n\n"
        "Example: 25"
    )

    return AGE


# ------------------------------------------------------
# VERIFICATION — AGE
# ------------------------------------------------------

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
            "❌ Please enter your age as a number.\n\n"
            "Example: 25"
        )

        return AGE

    if age < 18 or age > 120:

        await update.message.reply_text(
            "❌ Please enter a valid age "
            "between 18 and 120."
        )

        return AGE

    context.user_data[
        "verification_age"
    ] = age

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
        "✅ Age received.\n\n"
        "📍 Step 3/4\n\n"
        "Please share your current location "
        "using the button below.",
        reply_markup=keyboard
    )

    return LOCATION


# ------------------------------------------------------
# VERIFICATION — LOCATION
# ------------------------------------------------------

async def verification_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return LOCATION

    if not update.message.location:

        await update.message.reply_text(
            "❌ Please use the "
            "\"📍 Share My Location\" button."
        )

        return LOCATION

    location = update.message.location

    context.user_data[
        "latitude"
    ] = location.latitude

    context.user_data[
        "longitude"
    ] = location.longitude

    await update.message.reply_text(
        "✅ Location received.\n\n"
        "📸 Step 4/4\n\n"
        "Please send a selfie photo "
        "directly in this private chat.",
        reply_markup=ReplyKeyboardRemove()
    )

    return SELFIE


# ------------------------------------------------------
# VERIFICATION — SELFIE
# ------------------------------------------------------

async def verification_selfie(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return SELFIE

    if not update.message.photo:

        await update.message.reply_text(
            "❌ Please send a selfie photo."
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

    if not group_chat_id:

        await update.message.reply_text(
            "❌ Verification session expired. "
            "Please start verification again."
        )

        context.user_data.clear()

        return ConversationHandler.END

    # Save completed verification
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
        "✅ Verification Submitted\n\n"
        "Your verification information has been "
        "successfully received.\n\n"
        "👤 Name: Saved\n"
        "🎂 Age: Saved\n"
        "📍 Location: Saved\n"
        "📸 Selfie: Saved\n\n"
        "🔐 Status: Pending Review\n\n"
        "An administrator will review your "
        "verification before you can participate "
        "in the group."
    )

    context.user_data.clear()

    return ConversationHandler.END


# ------------------------------------------------------
# CANCEL
# ------------------------------------------------------

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


# ------------------------------------------------------
# GENERIC PRIVATE AI
# ------------------------------------------------------

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    if not update.message:
        return

    # AI only in private chats
    if update.effective_chat.type != "private":
        return

    save_user(
        update.effective_user
    )

    user_message = update.message.text

    if not user_message:
        return

    try:

        answer = ask_ai(
            user_message
        )

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print(
            "AI Error:",
            repr(e)
        )

        await update.message.reply_text(
            "Sorry, something went wrong "
            "while processing your request."
        )


# ------------------------------------------------------
# MAIN
# ------------------------------------------------------

def main():

    initialize_database()

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN is missing from .env"
        )

    print(
        "BOT_TOKEN loaded successfully."
    )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ----------------------------------------------
    # Verification ConversationHandler
    # ----------------------------------------------

    verification_conversation = ConversationHandler(

        entry_points=[
            CommandHandler(
                "start",
                start
            )
        ],

        states={

            NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    verification_name
                )
            ],

            AGE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    verification_age
                )
            ],

            LOCATION: [

                MessageHandler(
                    filters.LOCATION,
                    verification_location
                ),

                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
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

    # IMPORTANT:
    # ConversationHandler comes before generic AI messages

    app.add_handler(
        verification_conversation
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    app.add_handler(
        CommandHandler(
            "ask",
            ask_command
        )
    )

    # New group members
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_member
        )
    )

    # Generic AI private chat
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "AI + Verification Telegram Bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()