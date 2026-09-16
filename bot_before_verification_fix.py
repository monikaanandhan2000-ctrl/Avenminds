import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ContextTypes,
    filters,
)
from ai import ask_ai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_FILE, override=True)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ADMIN_CHAT_ID_VALUE = os.environ.get("ADMIN_CHAT_ID")

print("========================================")
print("ENVIRONMENT CHECK")
print(f".env path: {ENV_FILE}")
print(f".env exists: {os.path.exists(ENV_FILE)}")
print(f"BOT_TOKEN loaded: {bool(BOT_TOKEN)}")
print(f"OPENAI_API_KEY loaded: {bool(OPENAI_API_KEY)}")
print(f"ADMIN_CHAT_ID loaded: {bool(ADMIN_CHAT_ID_VALUE)}")
print("========================================")

if not BOT_TOKEN:
    raise RuntimeError(f"BOT_TOKEN is missing from .env file: {ENV_FILE}")
if not OPENAI_API_KEY:
    raise RuntimeError(f"OPENAI_API_KEY is missing from .env file: {ENV_FILE}")
if not ADMIN_CHAT_ID_VALUE:
    raise RuntimeError(f"ADMIN_CHAT_ID is missing from .env file: {ENV_FILE}")
try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_VALUE)
except ValueError:
    raise RuntimeError("ADMIN_CHAT_ID must be a numeric Telegram user ID.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

verification_sessions = {}
STATE_NAME = "name"
STATE_AGE = "age"
STATE_GENDER = "gender"
STATE_LOCATION = "location"
STATE_PURPOSE = "purpose"
STATE_PHOTO = "photo"
STATE_WAITING_ADMIN = "waiting_admin"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if update.effective_chat and update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "Hello! 👋\n\n"
            "I am the group's verification and AI assistant bot.\n\n"
            "If you are trying to join a protected group, use the group's "
            "verification join-request link.\n\n"
            "Once you submit a join request, I will contact you privately "
            "and collect your verification details.\n\n"
            "You can also send me any normal message and I will respond using AI."
        )
    else:
        await update.message.reply_text("This bot handles private verification and AI assistance.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "🤖 Bot Help\n\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/joinlink <group_id> - Create a verification join-request link\n\n"
        "Normal private messages are sent to the AI.\n\n"
        "Protected groups require a pending join request and administrator "
        "approval before entry."
    )


async def joinlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ You are not authorized to create verification links.")
        return
    if not context.args:
        await update.message.reply_text(
            "Usage:\n\n/joinlink -1001234567890\n\nReplace the example with your real group ID."
        )
        return
    try:
        group_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID.\n\nExample:\n/joinlink -1001234567890")
        return
    try:
        chat = await context.bot.get_chat(group_id)
        if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await update.message.reply_text("❌ The supplied chat is not a group or supergroup.")
            return
        bot_member = await context.bot.get_chat_member(chat_id=group_id, user_id=context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ The bot is not an administrator in this group.")
            return
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=group_id,
            name="Verification Join Link",
            creates_join_request=True,
        )
        await update.message.reply_text(
            "✅ Verification join-request link created.\n\n"
            f"Group: {chat.title}\n\n"
            "Users using this link will NOT enter immediately. Their join request "
            "will remain pending until an admin approves it.\n\n"
            f"🔗 {invite_link.invite_link}\n\n"
            "⚠️ Give users this link instead of an ordinary invite link."
        )
        logger.info("Verification link created for group %s", group_id)
    except Exception:
        logger.exception("JOIN LINK CREATION ERROR")
        await update.message.reply_text(
            "❌ Could not create the verification join link.\n\nCheck the terminal for the full error."
        )


async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    if not request:
        return
    user = request.from_user
    group = request.chat
    user_id = user.id
    group_id = group.id
    logger.info("JOIN REQUEST RECEIVED | user=%s | group=%s", user_id, group_id)

    verification_sessions[user_id] = {
        "user_id": user_id,
        "group_id": group_id,
        "group_title": group.title or "Group",
        "telegram_username": user.username or "",
        "name": "",
        "age": "",
        "gender": "",
        "location": "",
        "purpose": "",
        "photo_file_id": "",
        "state": STATE_NAME,
        "admin_message_id": None,
        "status": "verification",
    }

    try:
        await context.bot.send_message(
            chat_id=request.user_chat_id,
            text=(
                "🔐 GROUP VERIFICATION\n\n"
                f"You requested to join: {group.title or 'the group'}\n\n"
                "Your join request is currently PENDING.\n"
                "You are NOT inside the group yet.\n\n"
                "Please complete the verification below. Your information will be "
                "sent privately to the administrator for review.\n\n"
                "👤 Please enter your FULL NAME:"
            ),
        )
    except Exception:
        logger.exception("Could not send private verification message to user %s", user_id)


async def private_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    if not text:
        return

    session = verification_sessions.get(user_id)
    if session:
        state = session.get("state")
        if state == STATE_NAME:
            if len(text) < 2:
                await update.message.reply_text("❌ Please enter a valid full name.")
                return
            session["name"] = text
            session["state"] = STATE_AGE
            await update.message.reply_text("🎂 Thank you.\n\nNow enter your AGE.\n\nExample: 25")
            return
        if state == STATE_AGE:
            if not text.isdigit():
                await update.message.reply_text("❌ Please enter your age as a number.\n\nExample: 25")
                return
            age = int(text)
            if age < 18:
                await update.message.reply_text("❌ You must be 18 or older to continue.")
                return
            if age > 120:
                await update.message.reply_text("❌ Please enter a valid age.")
                return
            session["age"] = str(age)
            session["state"] = STATE_GENDER
            keyboard = [[
                InlineKeyboardButton("Male", callback_data=f"verify_gender|{user_id}|Male"),
                InlineKeyboardButton("Female", callback_data=f"verify_gender|{user_id}|Female"),
            ], [InlineKeyboardButton("Other", callback_data=f"verify_gender|{user_id}|Other")]]
            await update.message.reply_text("⚧ Please select your GENDER:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if state == STATE_GENDER:
            await update.message.reply_text("Please select your gender using the buttons.")
            return
        if state == STATE_LOCATION:
            if len(text) < 2:
                await update.message.reply_text("❌ Please enter a valid location.")
                return
            session["location"] = text
            session["state"] = STATE_PURPOSE
            await update.message.reply_text("🎯 What is your PURPOSE for joining the group?\n\nPlease describe briefly.")
            return
        if state == STATE_PURPOSE:
            if len(text) < 2:
                await update.message.reply_text("❌ Please enter your purpose.")
                return
            session["purpose"] = text
            session["state"] = STATE_PHOTO
            await update.message.reply_text(
                "📸 Almost finished.\n\nPlease send a clear SELFIE PHOTO now.\n\n"
                "The photo will be sent privately to the admin with your verification details."
            )
            return
        if state == STATE_PHOTO:
            await update.message.reply_text("📸 Please send the selfie as a Telegram photo.")
            return
        if state == STATE_WAITING_ADMIN:
            await update.message.reply_text(
                "⏳ Your verification has already been submitted.\n\n"
                "Please wait while the administrator reviews your join request."
            )
            return

    try:
        logger.info("AI MESSAGE | user=%s | text=%s", user_id, text)
        answer = await ask_ai(text)
        await update.message.reply_text(answer)
    except Exception:
        logger.exception("AI ERROR")
        await update.message.reply_text(
            "❌ I could not generate an AI response.\n\nCheck the terminal for the full error."
        )


async def private_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    user_id = update.effective_user.id
    session = verification_sessions.get(user_id)
    if not session:
        await update.message.reply_text("📸 I received your photo.\n\nFor normal AI chat, please send a text message.")
        return
    if session.get("state") != STATE_PHOTO:
        await update.message.reply_text("📸 Please send the selfie when the verification process asks for it.")
        return
    try:
        file_id = update.message.photo[-1].file_id
        session["photo_file_id"] = file_id
        session["state"] = STATE_WAITING_ADMIN
        session["status"] = "waiting_admin"
        username = f"@{session['telegram_username']}" if session["telegram_username"] else "No username"
        admin_caption = (
            "🔔 NEW GROUP JOIN VERIFICATION\n\n"
            "👤 USER INFORMATION\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Name: {session['name']}\n"
            f"Age: {session['age']}\n"
            f"Gender: {session['gender']}\n"
            f"Location: {session['location']}\n"
            f"Purpose: {session['purpose']}\n\n"
            "📱 TELEGRAM INFORMATION\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Username: {username}\n"
            f"User ID: {session['user_id']}\n\n"
            "👥 GROUP\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Group: {session['group_title']}\n"
            f"Group ID: {session['group_id']}\n\n"
            "📸 Selfie attached.\n\n"
            "⏳ STATUS: WAITING FOR ADMIN APPROVAL\n\n"
            "⚠️ The user is still OUTSIDE the group."
        )
        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_join|{user_id}|{session['group_id']}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_join|{user_id}|{session['group_id']}"),
        ]]
        admin_message = await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=file_id,
            caption=admin_caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        session["admin_message_id"] = admin_message.message_id
        await update.message.reply_text(
            "✅ VERIFICATION SUBMITTED\n\n"
            "Your information and selfie have been sent to the administrator.\n\n"
            "⏳ Your join request is still pending.\n"
            "You are NOT inside the group yet.\n\n"
            "Please wait for the administrator's decision."
        )
        logger.info("VERIFICATION SUBMITTED | user=%s | group=%s", user_id, session["group_id"])
    except Exception:
        logger.exception("VERIFICATION SUBMISSION ERROR")
        session["state"] = STATE_PHOTO
        session["status"] = "verification"
        await update.message.reply_text("❌ I could not submit your verification to the admin.\n\nPlease send the selfie again.")


async def verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if not query.from_user:
        return
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("You are not authorized to perform this action.", show_alert=True)
        return
    data = query.data or ""

    if data.startswith("verify_gender|"):
        parts = data.split("|")
        if len(parts) != 3:
            return
        try:
            user_id = int(parts[1])
        except ValueError:
            return
        gender = parts[2]
        session = verification_sessions.get(user_id)
        if not session:
            await query.answer("Verification session no longer exists.", show_alert=True)
            return
        session["gender"] = gender
        session["state"] = STATE_LOCATION
        await query.edit_message_text(
            f"⚧ Gender selected: {gender}\n\n📍 Now send your LOCATION.\n\nExample: Chennai, Tamil Nadu"
        )
        return

    if data.startswith("approve_join|"):
        parts = data.split("|")
        if len(parts) != 3:
            return
        try:
            user_id = int(parts[1])
            group_id = int(parts[2])
        except ValueError:
            return
        session = verification_sessions.get(user_id)
        if not session:
            await query.answer("Verification information is no longer available.", show_alert=True)
            return
        if session["group_id"] != group_id:
            await query.answer("Group verification mismatch.", show_alert=True)
            return
        if session.get("status") != "waiting_admin":
            await query.answer("This request has already been processed.", show_alert=True)
            return
        try:
            await context.bot.approve_chat_join_request(chat_id=group_id, user_id=user_id)
            session["status"] = "approved"
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "✅ YOUR JOIN REQUEST HAS BEEN APPROVED!\n\n"
                        f"You have been approved to join {session['group_title']}.\n\n"
                        "You can now open the group and enter."
                    ),
                )
            except Exception:
                logger.exception("Could not notify approved user %s", user_id)
            username = f"@{session['telegram_username']}" if session["telegram_username"] else "No username"
            await query.edit_message_caption(
                caption=(
                    "✅ JOIN REQUEST APPROVED\n\n"
                    f"Name: {session['name']}\n"
                    f"Age: {session['age']}\n"
                    f"Gender: {session['gender']}\n"
                    f"Location: {session['location']}\n"
                    f"Purpose: {session['purpose']}\n"
                    f"Username: {username}\n"
                    f"User ID: {user_id}\n\n"
                    "The user has been approved and can enter the group."
                ),
                reply_markup=None,
            )
            await query.answer("User approved successfully.", show_alert=True)
            logger.info("USER APPROVED | user=%s | group=%s", user_id, group_id)
            verification_sessions.pop(user_id, None)
        except Exception:
            logger.exception("APPROVAL ERROR | user=%s | group=%s", user_id, group_id)
            await query.answer("❌ Approval failed. Check the terminal.", show_alert=True)
        return

    if data.startswith("reject_join|"):
        parts = data.split("|")
        if len(parts) != 3:
            return
        try:
            user_id = int(parts[1])
            group_id = int(parts[2])
        except ValueError:
            return
        session = verification_sessions.get(user_id)
        if not session:
            await query.answer("Verification information is no longer available.", show_alert=True)
            return
        if session["group_id"] != group_id:
            await query.answer("Group verification mismatch.", show_alert=True)
            return
        if session.get("status") != "waiting_admin":
            await query.answer("This request has already been processed.", show_alert=True)
            return
        try:
            await context.bot.decline_chat_join_request(chat_id=group_id, user_id=user_id)
            session["status"] = "rejected"
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Your request to join the group was not approved by the administrator.",
                )
            except Exception:
                logger.exception("Could not notify rejected user %s", user_id)
            await query.edit_message_caption(
                caption=(
                    "❌ JOIN REQUEST REJECTED\n\n"
                    f"Name: {session['name']}\n"
                    f"Age: {session['age']}\n"
                    f"Gender: {session['gender']}\n"
                    f"Location: {session['location']}\n"
                    f"Purpose: {session['purpose']}\n\n"
                    "The user was NOT admitted to the group."
                ),
                reply_markup=None,
            )
            await query.answer("User rejected.", show_alert=True)
            logger.info("USER REJECTED | user=%s | group=%s", user_id, group_id)
            verification_sessions.pop(user_id, None)
        except Exception:
            logger.exception("REJECTION ERROR | user=%s | group=%s", user_id, group_id)
            await query.answer("❌ Rejection failed. Check the terminal.", show_alert=True)
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("BOT ERROR", exc_info=context.error)


async def post_init(application: Application):
    try:
        bot = application.bot
        me = await bot.get_me()
        logger.info("========================================")
        logger.info("BOT CONNECTED")
        logger.info("Username: @%s", me.username)
        logger.info("Bot ID: %s", me.id)
        logger.info("========================================")
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.warning("Existing webhook detected. Removing it...")
            await bot.delete_webhook(drop_pending_updates=False)
            logger.info("Webhook removed.")
    except Exception:
        logger.exception("BOT INITIALIZATION ERROR")


def main():
    logger.info("Starting Telegram AI + Verification Bot...")
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("joinlink", joinlink))
    application.add_handler(ChatJoinRequestHandler(join_request))
    application.add_handler(CallbackQueryHandler(verification_callback))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, private_photo))
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            private_text,
        )
    )
    application.add_error_handler(error_handler)
    logger.info("Starting polling...")
    application.run_polling(
        allowed_updates=["message", "callback_query", "chat_join_request"],
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
