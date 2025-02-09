from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.user import UserService
from services.moodle import MoodleService

# State constant for conversation
EXPECTING_API_KEY = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    user_service: UserService = context.application.bot_data["user_service"]
    user = await user_service.get_user(telegram_id)
    if user:
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_html(
            "🌐 <b>Welcome to PyMoodle.</b> 🌐\n\n"
            "Please provide your <b>Moodle Mobile web service API key</b> to continue.\n\n"
            "🔑 Obtain your API key here: <a href='https://moodle.astanait.edu.kz/user/managetoken.php'>Get API Key</a>"
        )
        return EXPECTING_API_KEY

async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    api_key = update.message.text.strip()
    moodle_service: MoodleService = context.application.bot_data["moodle_service"]
    user_service = context.application.bot_data["user_service"]
    user_info = await moodle_service.verify_api_key(api_key)
    if not user_info:
        await update.message.reply_html("🚫 Invalid API key. Please try again.")
        return EXPECTING_API_KEY
    # Extract first and last name from the 'fullname' field (if available)
    full_name = user_info.get("fullname", "")
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) == 2 else ""

    await user_service.register_api_key(telegram_id, api_key, first_name, last_name)
    await update.message.reply_text("✅ Your API key has been registered successfully!")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Deadlines", callback_data="get_assignments")],
        [InlineKeyboardButton("📊 Grades", callback_data="grades_menu")],
        [InlineKeyboardButton("🔔 Notification Settings", callback_data="notification_settings")],
        [InlineKeyboardButton("👤 Profile", callback_data="view_profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🔧 Welcome! Choose an option:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")