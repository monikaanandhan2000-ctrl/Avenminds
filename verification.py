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
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from database import (
    create_verification,
    update_verification_details,
    update_verification_status,
    save_user,
)

NAME, AGE, LOCATION, SELFIE = range(4)


async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    chat = update.effective_chat

    # Verification works ONLY inside groups/supergroups
    if chat.type not in ["group", "supergroup"]:
        return

    for member in update.message.new_chat_members:

        if member.is_bot:
            continue

        save_user(member)

        create_verification(
            member,
            chat.id
        )

        # Restrict new member
        try:

            permissions = ChatPermissions(
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

            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=member.id,
                permissions=permissions
            )

            print(
                f"Restricted new member {member.id} "
                f"in group {chat.id}"
            )

        except Exception as e:

            print(
                "Restriction error:",
                type(e).__name__,
                str(e)
            )

        # Create private verification link
        bot_info = await context.bot.get_me()

        verification_link = (
            f"https://t.me/{bot_info.username}"
            f"?start=verify_{chat.id}_{member.id}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔐 Start Verification",
                    url=verification_link
                )
            ]
        ])

        await update.message.reply_text(

            f"👋 Welcome, {member.first_name}!\n\n"

            "🔐 Verification is required before "
            "you can participate in this group.\n\n"

            "You are currently restricted.\n\n"

            "Please complete your verification privately "
            "with our bot.\n\n"

            "Click the button below to begin.",

            reply_markup=keyboard
        )


async def start_verification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return ConversationHandler.END

    # Verification can ONLY be started in private chat
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    args = context.args

    if not args or not args[0].startswith("verify_"):

        await update.message.reply_text(
            "Please use the verification button from the group "
            "to start verification."
        )

        return ConversationHandler.END

    try:

        parts = args[0].split("_")

        group_chat_id = int(parts[1])
        target_user_id = int(parts[2])

    except (ValueError, IndexError):

        await update.message.reply_text(
            "❌ Invalid verification link."
        )

        return ConversationHandler.END

    # Make sure the verification link belongs to this user
    if update.effective_user.id != target_user_id:

        await update.message.reply_text(
            "❌ This verification link belongs to another user."
        )

        return ConversationHandler.END

    user = update.effective_user

    save_user(user)

    create_verification(
        user,
        group_chat_id
    )

    context.user_data.clear()

    context.user_data["verification_group_id"] = group_chat_id
    context.user_data["verification_user_id"] = target_user_id

    await update.message.reply_text(

        "🔐 Verification Started\n\n"

        "You need to complete the following steps:\n\n"

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


async def verification_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return NAME

    name = update.message.text.strip()

    if len(name) < 2:

        await update.message.reply_text(
            "❌ Please enter a valid name."
        )

        return NAME

    context.user_data["name"] = name

    await update.message.reply_text(

        "🎂 Step 2/4\n\n"
        "Please enter your age:"
    )

    return AGE


async def verification_age(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return AGE

    age_text = update.message.text.strip()

    try:

        age = int(age_text)

    except ValueError:

        await update.message.reply_text(
            "❌ Please enter your age as a number."
        )

        return AGE

    if age < 18 or age > 120:

        await update.message.reply_text(
            "❌ Please enter a valid age between 18 and 120."
        )

        return AGE

    context.user_data["age"] = age

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

        "📍 Step 3/4\n\n"

        "Please share your current location "
        "using the button below.",

        reply_markup=keyboard
    )

    return LOCATION


async def verification_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return LOCATION

    if not update.message.location:

        await update.message.reply_text(
            "❌ Please use the '📍 Share My Location' "
            "button to send your location."
        )

        return LOCATION

    location = update.message.location

    context.user_data["latitude"] = location.latitude
    context.user_data["longitude"] = location.longitude

    await update.message.reply_text(

        "📸 Step 4/4\n\n"

        "Please send a selfie/photo for verification.",

        reply_markup=ReplyKeyboardRemove()
    )

    return SELFIE


async def verification_selfie(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return SELFIE

    if not update.message.photo:

        await update.message.reply_text(
            "❌ Please send a photo/selfie."
        )

        return SELFIE

    photo = update.message.photo[-1]

    selfie_file_id = photo.file_id

    user_id = context.user_data.get(
        "verification_user_id"
    )

    group_id = context.user_data.get(
        "verification_group_id"
    )

    name = context.user_data.get("name")
    age = context.user_data.get("age")
    latitude = context.user_data.get("latitude")
    longitude = context.user_data.get("longitude")

    if not all([
        user_id,
        group_id,
        name,
        age,
        latitude is not None,
        longitude is not None
    ]):

        await update.message.reply_text(
            "❌ Verification data is incomplete. "
            "Please start the verification again."
        )

        context.user_data.clear()

        return ConversationHandler.END

    update_verification_details(

        telegram_id=user_id,
        chat_id=group_id,
        name=name,
        age=age,
        latitude=latitude,
        longitude=longitude,
        selfie_file_id=selfie_file_id
    )

    await update.message.reply_text(

        "✅ Verification Submitted!\n\n"

        "Your verification has been successfully submitted "
        "for administrator review.\n\n"

        "Status: 🟡 PENDING\n\n"

        "You will remain restricted in the group until "
        "an administrator approves your verification.\n\n"

        "You will be notified when a decision is made."
    )

    context.user_data.clear()

    return ConversationHandler.END


async def cancel_verification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    if update.message:

        await update.message.reply_text(
            "❌ Verification cancelled."
        )

    return ConversationHandler.END


def get_verification_conversation():

    return ConversationHandler(

        entry_points=[
            CommandHandler(
                "start",
                start_verification
            )
        ],

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
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_verification
            )
        ],

        allow_reentry=True
    )