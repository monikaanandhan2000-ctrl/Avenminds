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
    ChatMemberHandler,
    ContextTypes,
    filters,
)

from ai import ask_ai


# ============================================================
# ENVIRONMENT
# ============================================================

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
    raise RuntimeError(
        f"BOT_TOKEN is missing from .env file: {ENV_FILE}"
    )

if not OPENAI_API_KEY:
    raise RuntimeError(
        f"OPENAI_API_KEY is missing from .env file: {ENV_FILE}"
    )

if not ADMIN_CHAT_ID_VALUE:
    raise RuntimeError(
        f"ADMIN_CHAT_ID is missing from .env file: {ENV_FILE}"
    )

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_VALUE)
except ValueError:
    raise RuntimeError(
        "ADMIN_CHAT_ID must be a numeric Telegram user ID."
    )


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# VERIFICATION STORAGE
# ============================================================

verification_sessions = {}

# Users explicitly approved through OUR bot.
# Key = (group_id, user_id)
approved_users = set()

# Verification join-request links created by this bot.
# Key = group_id
# Value = invite link
verification_links = {}


# ============================================================
# VERIFICATION STATES
# ============================================================

STATE_NAME = "name"
STATE_AGE = "age"
STATE_GENDER = "gender"
STATE_LOCATION = "location"
STATE_PURPOSE = "purpose"
STATE_PHOTO = "photo"
STATE_WAITING_ADMIN = "waiting_admin"


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user or not update.message:
        return

    if (
        update.effective_chat
        and update.effective_chat.type == ChatType.PRIVATE
    ):

        session = verification_sessions.get(
            update.effective_user.id
        )

        if session:
            await update.message.reply_text(
                "🔐 Your group verification session is active.\n\n"
                "Please continue with the verification steps "
                "sent by the bot.\n\n"
                "You must complete verification before your "
                "join request can be approved."
            )
            return

        await update.message.reply_text(
            "Hello! 👋\n\n"
            "I am the group's verification and AI assistant bot.\n\n"
            "If you are trying to join a protected group, use the "
            "group's verification join-request link.\n\n"
            "Once you submit a join request, I will contact you "
            "privately and collect your verification details.\n\n"
            "You must complete verification before your request "
            "can be approved.\n\n"
            "You can also send me any normal message and I will "
            "respond using AI."
        )

    else:

        await update.message.reply_text(
            "This bot handles private verification and AI assistance."
        )


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    await update.message.reply_text(
        "🤖 Bot Help\n\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/joinlink <group_id> - Create a mandatory "
        "verification join-request link\n\n"
        "Protected groups require:\n"
        "1. Join request\n"
        "2. Verification\n"
        "3. Admin review\n"
        "4. Bot approval\n\n"
        "Normal private messages are sent to the AI."
    )


# ============================================================
# /JOINLINK
# ============================================================

async def joinlink(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_user or not update.message:
        return

    if update.effective_user.id != ADMIN_CHAT_ID:

        await update.message.reply_text(
            "❌ You are not authorized to create verification links."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "Usage:\n\n"
            "/joinlink -1001234567890\n\n"
            "Replace the example with your real group ID."
        )

        return

    try:

        group_id = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ Invalid group ID.\n\n"
            "Example:\n"
            "/joinlink -1001234567890"
        )

        return

    try:

        # ====================================================
        # GET GROUP
        # ====================================================

        chat = await context.bot.get_chat(
            group_id
        )

        logger.info("========================================")
        logger.info("JOIN LINK DIAGNOSTIC")
        logger.info("Group ID: %s", group_id)
        logger.info("Group Title: %s", chat.title)
        logger.info("Group Type: %s", chat.type)
        logger.info("========================================")

        if chat.type not in (
            ChatType.GROUP,
            ChatType.SUPERGROUP,
        ):

            await update.message.reply_text(
                "❌ The supplied chat is not a group or supergroup."
            )

            return

        # ====================================================
        # CHECK BOT ADMIN
        # ====================================================

        bot_member = await context.bot.get_chat_member(
            chat_id=group_id,
            user_id=context.bot.id,
        )

        logger.info(
            "BOT STATUS | group=%s | status=%s",
            group_id,
            bot_member.status,
        )

        if bot_member.status not in (
            "administrator",
            "creator",
        ):

            await update.message.reply_text(
                "❌ The bot is not an administrator in this group."
            )

            return

        # ====================================================
        # CHECK INVITE PERMISSION
        # ====================================================

        can_invite = getattr(
            bot_member,
            "can_invite_users",
            None,
        )

        logger.info(
            "BOT INVITE PERMISSION | group=%s | can_invite_users=%s",
            group_id,
            can_invite,
        )

        if (
            bot_member.status == "administrator"
            and can_invite is False
        ):

            await update.message.reply_text(
                "❌ The bot does not have permission to invite/add users.\n\n"
                "Open:\n"
                "Group Settings → Administrators → Bot\n\n"
                "Enable the permission to invite/add subscribers."
            )

            return

        # ====================================================
        # CREATE MANDATORY JOIN-REQUEST LINK
        # ====================================================

        invite_link = await context.bot.create_chat_invite_link(
            chat_id=group_id,
            name="MANDATORY VERIFICATION",
            creates_join_request=True,
        )

        logger.info("========================================")
        logger.info("TELEGRAM CREATED INVITE LINK")
        logger.info(
            "Invite URL: %s",
            invite_link.invite_link,
        )
        logger.info(
            "creates_join_request: %s",
            invite_link.creates_join_request,
        )
        logger.info("========================================")

        # ====================================================
        # HARD CHECK
        # ====================================================

        if not invite_link.creates_join_request:

            await update.message.reply_text(
                "❌ SECURITY ERROR\n\n"
                "Telegram did not create this as a join-request link.\n\n"
                "The link has NOT been saved or presented as a "
                "verification link.\n\n"
                "Do not distribute this link."
            )

            return

        # ====================================================
        # SAVE VERIFIED LINK
        # ====================================================

        verification_links[group_id] = (
            invite_link.invite_link
        )

        logger.info(
            "MANDATORY VERIFICATION LINK SAVED | "
            "group=%s | link=%s",
            group_id,
            invite_link.invite_link,
        )

        # ====================================================
        # SEND LINK
        # ====================================================

        await update.message.reply_text(

            "✅ MANDATORY VERIFICATION LINK CREATED\n\n"

            f"Group: {chat.title}\n"
            f"Group ID: {group_id}\n\n"

            "🔐 VERIFICATION FLOW\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "1️⃣ User opens THIS link\n"
            "2️⃣ Telegram creates a JOIN REQUEST\n"
            "3️⃣ User remains OUTSIDE the group\n"
            "4️⃣ Bot starts private verification\n"
            "5️⃣ User submits all required details\n"
            "6️⃣ User submits selfie\n"
            "7️⃣ Bot sends verification to admin\n"
            "8️⃣ Request remains PENDING\n"
            "9️⃣ Admin presses APPROVE\n"
            "🔟 Bot approves Telegram request\n"
            "1️⃣1️⃣ User can then enter the group\n\n"

            "🚫 VERIFICATION IS MANDATORY.\n"
            "🚫 USER CANNOT BE APPROVED BEFORE VERIFICATION.\n"
            "🚫 BOT DOES NOT AUTO-APPROVE JOIN REQUESTS.\n"
            "🚫 DO NOT DISTRIBUTE ORDINARY INVITE LINKS.\n\n"

            "⚠️ IMPORTANT:\n"
            "Users who enter through an ordinary invite link "
            "will be removed by the bot's security guard.\n\n"

            f"🔗 {invite_link.invite_link}"
        )

    except Exception:

        logger.exception(
            "JOIN LINK CREATION ERROR"
        )

        await update.message.reply_text(
            "❌ Could not create the verification join link.\n\n"
            "Check the terminal for the full error."
        )


# ============================================================
# JOIN REQUEST RECEIVED
# ============================================================

async def join_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    request = update.chat_join_request

    if not request:
        return

    user = request.from_user
    group = request.chat

    user_id = user.id
    group_id = group.id

    logger.info("================================================")
    logger.info("MANDATORY JOIN REQUEST RECEIVED")
    logger.info("User ID: %s", user_id)
    logger.info("Username: @%s", user.username or "none")
    logger.info("Group ID: %s", group_id)
    logger.info("Group: %s", group.title)
    logger.info("Invite Link: %s",
                getattr(request.invite_link, "invite_link", None))
    logger.info("Creates Join Request: %s",
                getattr(request.invite_link, "creates_join_request", None))
    logger.info("================================================")

    # ========================================================
    # CRITICAL SECURITY RULE
    #
    # NEVER APPROVE HERE.
    #
    # Telegram keeps the user outside the group while this
    # join request is pending.
    # ========================================================

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

        "verification_complete": False,

        "approved_by_bot": False,

        "join_request_received": True,

        "join_request_link": (
            getattr(
                request.invite_link,
                "invite_link",
                None,
            )
        ),
    }

    try:

        await context.bot.send_message(

            chat_id=request.user_chat_id,

            text=(

                "🔐 MANDATORY GROUP VERIFICATION\n\n"

                f"You requested to join:\n"
                f"{group.title or 'the group'}\n\n"

                "⏳ JOIN REQUEST STATUS: PENDING\n\n"

                "🚫 You are NOT inside the group.\n\n"

                "You must complete verification before "
                "your request can be approved.\n\n"

                "Required information:\n"
                "• Full name\n"
                "• Age\n"
                "• Gender\n"
                "• Location\n"
                "• Purpose\n"
                "• Selfie\n\n"

                "🔒 Your request will remain pending until "
                "verification is completed and the administrator "
                "approves it.\n\n"

                "👤 Please enter your FULL NAME:"
            ),
        )

        logger.info(
            "MANDATORY VERIFICATION STARTED | user=%s | group=%s",
            user_id,
            group_id,
        )

    except Exception:

        logger.exception(
            "Could not send private verification message to user %s",
            user_id,
        )


# ============================================================
# DIRECT / UNAUTHORIZED JOIN GUARD
# ============================================================

async def direct_join_guard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    """
    Security fallback.

    The PRIMARY security gate is the Telegram JOIN REQUEST.

    If a user enters using an ordinary invite link, Telegram
    can technically admit them before the bot receives the
    membership update. This handler immediately removes that
    unauthorized member.

    If another administrator manually approves a join request
    before our verification is complete, this handler also
    removes the user.

    The bot cannot disable Telegram's native administrator
    approval controls, so this is the enforcement fallback.
    """

    member_update = update.chat_member

    if not member_update:
        return

    old_member = member_update.old_chat_member
    new_member = member_update.new_chat_member

    if not old_member or not new_member:
        return

    old_status = old_member.status
    new_status = new_member.status

    user = new_member.user
    chat = member_update.chat

    user_id = user.id
    chat_id = chat.id

    joined_statuses = {
        "member",
        "administrator",
        "creator",
        "restricted",
    }

    previous_statuses = {
        "left",
        "kicked",
    }

    if old_status not in previous_statuses:
        return

    if new_status not in joined_statuses:
        return

    # ========================================================
    # NEVER REMOVE GROUP ADMINS / OWNER
    # ========================================================

    if new_status in {
        "administrator",
        "creator",
    }:
        return

    approval_key = (
        chat_id,
        user_id,
    )

    # ========================================================
    # OUR BOT APPROVED THIS USER
    # ========================================================

    if approval_key in approved_users:

        approved_users.discard(
            approval_key
        )

        try:

            await context.bot.send_message(

                chat_id=chat_id,

                text=(
                    f"🎉 Welcome {user.mention_html()}!\n\n"
                    "Your verification has been approved.\n"
                    "Welcome to the group!"
                ),

                parse_mode="HTML",
            )

        except Exception:

            logger.exception(
                "Could not send approval welcome | user=%s | group=%s",
                user_id,
                chat_id,
            )

        logger.info(
            "APPROVED USER JOINED | user=%s | group=%s",
            user_id,
            chat_id,
        )

        return

    # ========================================================
    # CHECK WHETHER THIS USER HAD A VALID BOT APPROVAL
    # ========================================================

    session = verification_sessions.get(
        user_id
    )

    if (
        session
        and session.get("group_id") == chat_id
        and session.get("approved_by_bot") is True
        and session.get("verification_complete") is True
        and session.get("status") == "approved"
    ):

        logger.info(
            "VALIDATED USER JOINED | user=%s | group=%s",
            user_id,
            chat_id,
        )

        return

    # ========================================================
    # ANY OTHER JOIN IS UNAUTHORIZED
    #
    # This covers:
    # - ordinary invite links
    # - old invite links
    # - manually approved users
    # - unauthorized membership
    # ========================================================

    logger.warning(
        "UNAUTHORIZED GROUP ENTRY DETECTED | "
        "user=%s | group=%s | via_join_request=%s | invite=%s",
        user_id,
        chat_id,
        getattr(
            member_update,
            "via_join_request",
            False,
        ),
        getattr(
            member_update.invite_link,
            "invite_link",
            None,
        ),
    )

    # ========================================================
    # REMOVE USER
    # ========================================================

    try:

        bot_member = await context.bot.get_chat_member(
            chat_id=chat_id,
            user_id=context.bot.id,
        )

        if bot_member.status not in (
            "administrator",
            "creator",
        ):

            logger.error(
                "BOT IS NOT ADMIN - cannot enforce verification | "
                "group=%s",
                chat_id,
            )

            return

        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
        )

        await context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=True,
        )

        logger.info(
            "UNAUTHORIZED USER REMOVED | user=%s | group=%s",
            user_id,
            chat_id,
        )

    except Exception:

        logger.exception(
            "Could not remove unauthorized user | "
            "user=%s | group=%s",
            user_id,
            chat_id,
        )

        return

    # ========================================================
    # GET / CREATE VERIFICATION LINK
    # ========================================================

    verification_link = verification_links.get(
        chat_id
    )

    if not verification_link:

        try:

            new_link = await context.bot.create_chat_invite_link(
                chat_id=chat_id,
                name="MANDATORY VERIFICATION",
                creates_join_request=True,
            )

            if new_link.creates_join_request:

                verification_link = new_link.invite_link

                verification_links[chat_id] = (
                    verification_link
                )

                logger.info(
                    "NEW VERIFICATION LINK CREATED | group=%s",
                    chat_id,
                )

        except Exception:

            logger.exception(
                "Could not create verification link | group=%s",
                chat_id,
            )

    # ========================================================
    # TELL USER
    # ========================================================

    try:

        if verification_link:

            await context.bot.send_message(

                chat_id=user_id,

                text=(

                    "🚫 MANDATORY VERIFICATION REQUIRED\n\n"

                    f"You attempted to enter "
                    f"{chat.title or 'the group'} "
                    "without completing the verification process.\n\n"

                    "Your entry has been removed.\n\n"

                    "You must use the verification link below:\n\n"

                    f"🔗 {verification_link}\n\n"

                    "You will remain outside the group until:\n"
                    "1️⃣ Verification is completed\n"
                    "2️⃣ Administrator reviews it\n"
                    "3️⃣ The bot approves your join request"
                ),
            )

        else:

            await context.bot.send_message(

                chat_id=user_id,

                text=(

                    "🚫 MANDATORY VERIFICATION REQUIRED\n\n"

                    "You entered the group without completing "
                    "the verification process.\n\n"

                    "You have been removed.\n\n"

                    "Please contact the administrator for the "
                    "official verification join-request link."
                ),
            )

    except Exception:

        logger.info(
            "Could not notify unauthorized user %s",
            user_id,
        )


# ============================================================
# PRIVATE TEXT
# ============================================================

async def private_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.message
        or not update.effective_user
        or not update.effective_chat
    ):
        return

    if update.effective_chat.type != ChatType.PRIVATE:
        return

    user_id = update.effective_user.id

    text = (
        update.message.text or ""
    ).strip()

    if not text:
        return

    session = verification_sessions.get(
        user_id
    )

    # ========================================================
    # ACTIVE VERIFICATION
    # ========================================================

    if session:

        state = session.get(
            "state"
        )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if state == STATE_NAME:

            if len(text) < 2:

                await update.message.reply_text(
                    "❌ Please enter a valid full name."
                )

                return

            session["name"] = text
            session["state"] = STATE_AGE

            await update.message.reply_text(
                "🎂 Thank you.\n\n"
                "Now enter your AGE.\n\n"
                "Example: 25"
            )

            return

        # ----------------------------------------------------
        # AGE
        # ----------------------------------------------------

        if state == STATE_AGE:

            if not text.isdigit():

                await update.message.reply_text(
                    "❌ Please enter your age as a number.\n\n"
                    "Example: 25"
                )

                return

            age = int(text)

            if age < 18:

                await update.message.reply_text(
                    "❌ You must be 18 or older to continue."
                )

                return

            if age > 120:

                await update.message.reply_text(
                    "❌ Please enter a valid age."
                )

                return

            session["age"] = str(age)
            session["state"] = STATE_GENDER

            keyboard = [

                [
                    InlineKeyboardButton(
                        "Male",
                        callback_data=(
                            f"verify_gender|{user_id}|Male"
                        ),
                    ),

                    InlineKeyboardButton(
                        "Female",
                        callback_data=(
                            f"verify_gender|{user_id}|Female"
                        ),
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "Other",
                        callback_data=(
                            f"verify_gender|{user_id}|Other"
                        ),
                    )
                ],
            ]

            await update.message.reply_text(
                "⚧ Please select your GENDER:",
                reply_markup=InlineKeyboardMarkup(
                    keyboard
                ),
            )

            return

        # ----------------------------------------------------
        # GENDER
        # ----------------------------------------------------

        if state == STATE_GENDER:

            await update.message.reply_text(
                "Please select your gender using the buttons."
            )

            return

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        if state == STATE_LOCATION:

            if len(text) < 2:

                await update.message.reply_text(
                    "❌ Please enter a valid location."
                )

                return

            session["location"] = text
            session["state"] = STATE_PURPOSE

            await update.message.reply_text(
                "🎯 What is your PURPOSE for joining the group?\n\n"
                "Please describe briefly."
            )

            return

        # ----------------------------------------------------
        # PURPOSE
        # ----------------------------------------------------

        if state == STATE_PURPOSE:

            if len(text) < 2:

                await update.message.reply_text(
                    "❌ Please enter your purpose."
                )

                return

            session["purpose"] = text
            session["state"] = STATE_PHOTO

            await update.message.reply_text(
                "📸 Almost finished.\n\n"
                "Please send a clear SELFIE PHOTO now.\n\n"
                "The photo will be sent privately to the "
                "administrator with your verification details."
            )

            return

        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------

        if state == STATE_PHOTO:

            await update.message.reply_text(
                "📸 Please send the selfie as a Telegram photo."
            )

            return

        # ----------------------------------------------------
        # WAITING FOR ADMIN
        # ----------------------------------------------------

        if state == STATE_WAITING_ADMIN:

            await update.message.reply_text(
                "⏳ Your verification has already been submitted.\n\n"
                "Your join request is still pending.\n\n"
                "🚫 You are not inside the group yet.\n\n"
                "Please wait for the administrator's decision."
            )

            return

        # ----------------------------------------------------
        # ALREADY APPROVED
        # ----------------------------------------------------

        if session.get("status") == "approved":

            await update.message.reply_text(
                "✅ Your verification was approved.\n\n"
                "You may enter the group."
            )

            return

    # ========================================================
    # NORMAL AI CHAT
    # ========================================================

    try:

        logger.info(
            "AI MESSAGE | user=%s | text=%s",
            user_id,
            text,
        )

        answer = await ask_ai(
            text
        )

        await update.message.reply_text(
            answer
        )

    except Exception:

        logger.exception(
            "AI ERROR"
        )

        await update.message.reply_text(
            "❌ I could not generate an AI response.\n\n"
            "Check the terminal for the full error."
        )


# ============================================================
# PRIVATE PHOTO
# ============================================================

async def private_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.message
        or not update.effective_user
        or not update.effective_chat
    ):
        return

    if update.effective_chat.type != ChatType.PRIVATE:
        return

    user_id = update.effective_user.id

    session = verification_sessions.get(
        user_id
    )

    if not session:

        await update.message.reply_text(
            "📸 I received your photo.\n\n"
            "For normal AI chat, please send a text message."
        )

        return

    if session.get("state") != STATE_PHOTO:

        await update.message.reply_text(
            "📸 Please send the selfie when the verification "
            "process asks for it."
        )

        return

    try:

        file_id = update.message.photo[-1].file_id

        session["photo_file_id"] = file_id

        # ====================================================
        # VERIFICATION COMPLETE
        # ====================================================

        session["verification_complete"] = True
        session["state"] = STATE_WAITING_ADMIN
        session["status"] = STATE_WAITING_ADMIN

        username = (
            f"@{session['telegram_username']}"
            if session["telegram_username"]
            else "No username"
        )

        # ====================================================
        # ADMIN MESSAGE
        # ====================================================

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

            "✅ VERIFICATION COMPLETE\n\n"

            "⏳ STATUS: WAITING FOR ADMIN APPROVAL\n\n"

            "🚫 USER IS STILL OUTSIDE THE GROUP\n"
            "🚫 TELEGRAM JOIN REQUEST IS STILL PENDING\n\n"

            "Only the APPROVE button below will admit the user."
        )

        keyboard = [

            [
                InlineKeyboardButton(
                    "✅ APPROVE",
                    callback_data=(
                        f"approve_join|"
                        f"{user_id}|"
                        f"{session['group_id']}"
                    ),
                ),

                InlineKeyboardButton(
                    "❌ REJECT",
                    callback_data=(
                        f"reject_join|"
                        f"{user_id}|"
                        f"{session['group_id']}"
                    ),
                ),
            ]

        ]

        admin_message = await context.bot.send_photo(

            chat_id=ADMIN_CHAT_ID,

            photo=file_id,

            caption=admin_caption,

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        session["admin_message_id"] = (
            admin_message.message_id
        )

        # ====================================================
        # USER CONFIRMATION
        # ====================================================

        await update.message.reply_text(

            "✅ VERIFICATION COMPLETED\n\n"

            "Your name, age, gender, location, purpose and selfie "
            "have been submitted successfully.\n\n"

            "⏳ Your join request is STILL PENDING.\n\n"

            "🚫 You are NOT inside the group yet.\n\n"

            "The administrator must review your verification and "
            "press APPROVE before Telegram allows you to enter."
        )

        logger.info(
            "VERIFICATION COMPLETE | user=%s | group=%s",
            user_id,
            session["group_id"],
        )

        logger.info(
            "WAITING FOR ADMIN APPROVAL | user=%s | group=%s",
            user_id,
            session["group_id"],
        )

    except Exception:

        logger.exception(
            "VERIFICATION SUBMISSION ERROR"
        )

        session["state"] = STATE_PHOTO
        session["status"] = "verification"
        session["verification_complete"] = False

        await update.message.reply_text(
            "❌ I could not submit your verification to the admin.\n\n"
            "Please send the selfie again."
        )


# ============================================================
# CALLBACKS
# ============================================================

async def verification_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    if not query.from_user:
        return

    data = query.data or ""

    # ========================================================
    # GENDER BUTTON
    # ========================================================

    if data.startswith(
        "verify_gender|"
    ):

        parts = data.split("|")

        if len(parts) != 3:

            await query.answer(
                "Invalid verification action.",
                show_alert=True,
            )

            return

        try:

            user_id = int(parts[1])

        except ValueError:

            await query.answer(
                "Invalid user ID.",
                show_alert=True,
            )

            return

        # Only the actual user can select their gender.
        if query.from_user.id != user_id:

            await query.answer(
                "This verification button belongs to another user.",
                show_alert=True,
            )

            return

        gender = parts[2]

        session = verification_sessions.get(
            user_id
        )

        if not session:

            await query.answer(
                "Verification session no longer exists.",
                show_alert=True,
            )

            return

        if session.get("state") != STATE_GENDER:

            await query.answer(
                "This step is no longer active.",
                show_alert=True,
            )

            return

        session["gender"] = gender
        session["state"] = STATE_LOCATION

        await query.answer(
            "Gender saved."
        )

        await query.edit_message_text(

            f"⚧ Gender selected: {gender}\n\n"

            "📍 Now send your LOCATION.\n\n"

            "Example: Chennai, Tamil Nadu"
        )

        return

    # ========================================================
    # ADMIN ONLY AFTER THIS POINT
    # ========================================================

    if query.from_user.id != ADMIN_CHAT_ID:

        await query.answer(
            "You are not authorized to perform this action.",
            show_alert=True,
        )

        return

    # ========================================================
    # APPROVE
    # ========================================================

    if data.startswith(
        "approve_join|"
    ):

        parts = data.split("|")

        if len(parts) != 3:

            await query.answer(
                "Invalid approval data.",
                show_alert=True,
            )

            return

        try:

            user_id = int(parts[1])
            group_id = int(parts[2])

        except ValueError:

            await query.answer(
                "Invalid user or group ID.",
                show_alert=True,
            )

            return

        session = verification_sessions.get(
            user_id
        )

        if not session:

            await query.answer(
                "Verification information is no longer available.",
                show_alert=True,
            )

            return

        if session.get("group_id") != group_id:

            await query.answer(
                "Group verification mismatch.",
                show_alert=True,
            )

            return

        # ====================================================
        # MANDATORY VERIFICATION CHECK
        # ====================================================

        required_fields = [
            "name",
            "age",
            "gender",
            "location",
            "purpose",
            "photo_file_id",
        ]

        missing_fields = [

            field

            for field in required_fields

            if not session.get(field)

        ]

        if missing_fields:

            await query.answer(
                "❌ Verification is incomplete. "
                "The user cannot be approved.",
                show_alert=True,
            )

            logger.warning(
                "APPROVAL BLOCKED - INCOMPLETE VERIFICATION | "
                "user=%s | group=%s | missing=%s",
                user_id,
                group_id,
                missing_fields,
            )

            return

        if not session.get(
            "verification_complete"
        ):

            await query.answer(
                "❌ Verification is not complete.",
                show_alert=True,
            )

            return

        if session.get(
            "status"
        ) != STATE_WAITING_ADMIN:

            await query.answer(
                "This request has already been processed.",
                show_alert=True,
            )

            return

        # ====================================================
        # VERIFY REQUEST STILL EXISTS
        # ====================================================

        try:

            current_member = await context.bot.get_chat_member(
                chat_id=group_id,
                user_id=user_id,
            )

            logger.info(
                "CURRENT MEMBER STATUS BEFORE APPROVAL | "
                "user=%s | group=%s | status=%s",
                user_id,
                group_id,
                current_member.status,
            )

            # If already inside the group, do NOT approve again.
            if current_member.status in (
                "member",
                "administrator",
                "creator",
            ):

                await query.answer(
                    "⚠️ User is already inside the group.",
                    show_alert=True,
                )

                return

        except Exception:

            # get_chat_member can fail for pending users.
            # That is normal, so continue to approval.
            logger.info(
                "User is not currently a group member. "
                "Proceeding with pending join request."
            )

        try:

            logger.info(
                "ADMIN APPROVAL STARTED | user=%s | group=%s",
                user_id,
                group_id,
            )

            # =================================================
            # IMPORTANT:
            # Mark this BEFORE Telegram approval.
            # =================================================

            approved_users.add(
                (
                    group_id,
                    user_id,
                )
            )

            session["approved_by_bot"] = True

            # =================================================
            # ACTUALLY APPROVE TELEGRAM JOIN REQUEST
            # =================================================

            await context.bot.approve_chat_join_request(
                chat_id=group_id,
                user_id=user_id,
            )

            session["status"] = "approved"

            logger.info(
                "TELEGRAM JOIN REQUEST APPROVED | "
                "user=%s | group=%s",
                user_id,
                group_id,
            )

            # =================================================
            # NOTIFY USER
            # =================================================

            try:

                await context.bot.send_message(

                    chat_id=user_id,

                    text=(

                        "✅ VERIFICATION APPROVED!\n\n"

                        f"Your request to join "
                        f"{session['group_title']} "
                        "has been approved.\n\n"

                        "🎉 You can now enter the group.\n\n"

                        "Welcome!"
                    ),
                )

            except Exception:

                logger.exception(
                    "Could not notify approved user %s",
                    user_id,
                )

            # =================================================
            # UPDATE ADMIN MESSAGE
            # =================================================

            username = (

                f"@{session['telegram_username']}"

                if session["telegram_username"]

                else "No username"
            )

            await query.edit_message_caption(

                caption=(

                    "✅ VERIFICATION APPROVED\n\n"

                    "👤 USER INFORMATION\n"
                    "━━━━━━━━━━━━━━━━━━\n"

                    f"Name: {session['name']}\n"
                    f"Age: {session['age']}\n"
                    f"Gender: {session['gender']}\n"
                    f"Location: {session['location']}\n"
                    f"Purpose: {session['purpose']}\n\n"

                    "📱 TELEGRAM\n"
                    "━━━━━━━━━━━━━━━━━━\n"

                    f"Username: {username}\n"
                    f"User ID: {user_id}\n\n"

                    "👥 GROUP\n"
                    "━━━━━━━━━━━━━━━━━━\n"

                    f"{session['group_title']}\n"
                    f"Group ID: {group_id}\n\n"

                    "✅ Verification completed.\n"
                    "✅ Admin approved the request.\n"
                    "✅ Telegram join request approved.\n"
                    "🎉 User can now enter the group."
                ),

                reply_markup=None,
            )

            await query.answer(
                "✅ User approved and admitted.",
                show_alert=True,
            )

        except Exception:

            # =================================================
            # TELEGRAM APPROVAL FAILED
            # =================================================

            approved_users.discard(
                (
                    group_id,
                    user_id,
                )
            )

            session["approved_by_bot"] = False
            session["status"] = STATE_WAITING_ADMIN

            logger.exception(
                "APPROVAL ERROR | user=%s | group=%s",
                user_id,
                group_id,
            )

            await query.answer(
                "❌ Approval failed. "
                "The user remains unapproved. "
                "Check the terminal.",
                show_alert=True,
            )

        return

    # ========================================================
    # REJECT
    # ========================================================

    if data.startswith(
        "reject_join|"
    ):

        parts = data.split("|")

        if len(parts) != 3:

            await query.answer(
                "Invalid rejection data.",
                show_alert=True,
            )

            return

        try:

            user_id = int(parts[1])
            group_id = int(parts[2])

        except ValueError:

            await query.answer(
                "Invalid user or group ID.",
                show_alert=True,
            )

            return

        session = verification_sessions.get(
            user_id
        )

        if not session:

            await query.answer(
                "Verification information is no longer available.",
                show_alert=True,
            )

            return

        if session.get("group_id") != group_id:

            await query.answer(
                "Group verification mismatch.",
                show_alert=True,
            )

            return

        if session.get(
            "status"
        ) != STATE_WAITING_ADMIN:

            await query.answer(
                "This request has already been processed.",
                show_alert=True,
            )

            return

        try:

            await context.bot.decline_chat_join_request(
                chat_id=group_id,
                user_id=user_id,
            )

            session["status"] = "rejected"
            session["approved_by_bot"] = False

            # =================================================
            # NOTIFY USER
            # =================================================

            try:

                await context.bot.send_message(

                    chat_id=user_id,

                    text=(
                        "❌ Your verification was not approved.\n\n"
                        "Your request to join the group has been rejected."
                    ),
                )

            except Exception:

                logger.exception(
                    "Could not notify rejected user %s",
                    user_id,
                )

            # =================================================
            # UPDATE ADMIN MESSAGE
            # =================================================

            await query.edit_message_caption(

                caption=(

                    "❌ VERIFICATION REJECTED\n\n"

                    f"Name: {session['name']}\n"
                    f"Age: {session['age']}\n"
                    f"Gender: {session['gender']}\n"
                    f"Location: {session['location']}\n"
                    f"Purpose: {session['purpose']}\n\n"

                    "🚫 The user was NOT admitted to the group."
                ),

                reply_markup=None,
            )

            await query.answer(
                "User rejected.",
                show_alert=True,
            )

            logger.info(
                "USER REJECTED | user=%s | group=%s",
                user_id,
                group_id,
            )

            verification_sessions.pop(
                user_id,
                None,
            )

        except Exception:

            logger.exception(
                "REJECTION ERROR | user=%s | group=%s",
                user_id,
                group_id,
            )

            await query.answer(
                "❌ Rejection failed. Check the terminal.",
                show_alert=True,
            )

        return

    # ========================================================
    # UNKNOWN CALLBACK
    # ========================================================

    await query.answer(
        "Unknown action.",
        show_alert=True,
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "BOT ERROR",
        exc_info=context.error,
    )


# ============================================================
# BOT INITIALIZATION
# ============================================================

async def post_init(
    application: Application,
):

    try:

        bot = application.bot

        me = await bot.get_me()

        logger.info(
            "========================================"
        )

        logger.info(
            "BOT CONNECTED"
        )

        logger.info(
            "Username: @%s",
            me.username,
        )

        logger.info(
            "Bot ID: %s",
            me.id,
        )

        logger.info(
            "========================================"
        )

        webhook_info = await bot.get_webhook_info()

        if webhook_info.url:

            logger.warning(
                "Existing webhook detected. Removing it..."
            )

            await bot.delete_webhook(
                drop_pending_updates=False
            )

            logger.info(
                "Webhook removed."
            )

    except Exception:

        logger.exception(
            "BOT INITIALIZATION ERROR"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting Telegram AI + Mandatory Verification Bot..."
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ========================================================
    # COMMANDS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "joinlink",
            joinlink,
        )
    )

    # ========================================================
    # TELEGRAM JOIN REQUEST
    #
    # THIS IS THE PRIMARY SECURITY GATE.
    #
    # IMPORTANT:
    # We NEVER approve inside this handler.
    # ========================================================

    application.add_handler(
        ChatJoinRequestHandler(
            join_request
        )
    )

    # ========================================================
    # MEMBERSHIP SECURITY GUARD
    # ========================================================

    application.add_handler(
        ChatMemberHandler(
            direct_join_guard,
            ChatMemberHandler.CHAT_MEMBER,
        )
    )

    # ========================================================
    # CALLBACKS
    # ========================================================

    application.add_handler(
        CallbackQueryHandler(
            verification_callback
        )
    )

    # ========================================================
    # PRIVATE PHOTOS
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.PHOTO,
            private_photo,
        )
    )

    # ========================================================
    # PRIVATE TEXT
    # ========================================================

    application.add_handler(

        MessageHandler(

            filters.ChatType.PRIVATE
            & filters.TEXT
            & ~filters.COMMAND,

            private_text,
        )
    )

    # ========================================================
    # ERROR HANDLER
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "========================================"
    )

    logger.info(
        "STARTING POLLING"
    )

    logger.info(
        "Allowed updates:"
    )

    logger.info(
        "message"
    )

    logger.info(
        "callback_query"
    )

    logger.info(
        "chat_join_request"
    )

    logger.info(
        "chat_member"
    )

    logger.info(
        "========================================"
    )

    # ========================================================
    # POLLING
    # ========================================================

    application.run_polling(

        allowed_updates=[
            "message",
            "callback_query",
            "chat_join_request",
            "chat_member",
        ],

        drop_pending_updates=False,
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
