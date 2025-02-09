import logging, html, json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from db import crud
from moodle_api.api import MoodleApi
import redis.asyncio as redis

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


async def get_from_cache(key: str):
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_to_cache(key: str, value, expiration: int = 300):
    await redis_client.set(key, json.dumps(value), ex=expiration)


EXPECTING_API_KEY = 1
user_last_refresh_time = {}

CALLBACK_ASSIGNMENTS = "get_assignments"
CALLBACK_GRADES = "grades_menu"
CALLBACK_NOTIFICATION_SETTINGS = "notification_settings"
CALLBACK_PROFILE = "view_profile"
CALLBACK_DELETE_ACCOUNT = "delete_account"
CALLBACK_BACK_TO_MENU = "back_to_menu"
CALLBACK_REFRESH_ASSIGNMENTS = "refresh_assignments"

CALLBACK_GRADES_ASSIGNMENT = "grades_assignment"
CALLBACK_GRADES_MIDTERM = "grades_midterm"
CALLBACK_GRADES_ENDTERM = "grades_endterm"

INTERVALS = [
    ("1 Hour", "1_hour"),
    ("4 Hours", "4_hours"),
    ("8 Hours", "8_hours"),
    ("12 Hours", "12_hours"),
    ("1 Day", "1_day"),
    ("3 Days", "3_days"),
    ("4 Days", "4_days"),
    ("1 Week", "1_week"),
]
NOTIF_DEADLINE_REMINDER = "deadline_reminder"


async def send_long_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE, chunk_size: int = 4000):
    lines = text.split("\n")
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > chunk_size:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)
    for chunk in chunks:
        await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    user = await crud.get_user_by_telegram_id(telegram_id)
    if user:
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_html(
            "🌐 <b>Welcome to PyMoodle.</b> 🌐\n\nPlease provide your <b>Moodle Mobile web service API key</b> to continue.\n\n🔑 "
            "Obtain your API key here: <a href='https://moodle.astanait.edu.kz/user/managetoken.php'>Get API Key</a>"
        )
        return EXPECTING_API_KEY


async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    api_key = update.message.text.strip()
    moodle_api = MoodleApi()
    moodle_api.set_api_key(api_key)
    user_id = await moodle_api.get_user_id()
    if user_id is None:
        await update.message.reply_html("🚫 Invalid API key. Please try again.")
        return EXPECTING_API_KEY
    await crud.create_or_update_user(telegram_id, api_key)
    await update.message.reply_text("✅ Your API key has been registered successfully!")
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Deadlines", callback_data=CALLBACK_ASSIGNMENTS)],
        [InlineKeyboardButton("📊 Grades", callback_data=CALLBACK_GRADES)],
        [InlineKeyboardButton("🔔 Notification Settings", callback_data=CALLBACK_NOTIFICATION_SETTINGS)],
        [InlineKeyboardButton("👤 Profile", callback_data=CALLBACK_PROFILE)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🔧 Welcome! Choose an option:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    user = await crud.get_user_by_telegram_id(telegram_id)
    if user:
        moodle_api = MoodleApi()
        moodle_api.set_api_key(user.api_key)
        full_name, _ = await moodle_api.fetch_user_details()
        if full_name:
            name_parts = full_name.split(" ")
            first_name = name_parts[0] if name_parts else "N/A"
            surname = name_parts[1] if len(name_parts) > 1 else "N/A"
            profile_message = (
                f"👤 <b>Name:</b> {first_name}\n"
                f"👤 <b>Surname:</b> {surname}\n"
                f"🔑 <b>Telegram ID:</b> {telegram_id}\n"
                f"🔑 <b>Moodle Token:</b> {user.api_key}\n"
            )
        else:
            profile_message = "🔒 <b>Could not fetch user details.</b>"
    else:
        profile_message = "🔑 <b>You need to register your API token first.</b>"

    keyboard = [
        [InlineKeyboardButton("🗑️ Delete Account", callback_data=CALLBACK_DELETE_ACCOUNT)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(profile_message, reply_markup=reply_markup, parse_mode="HTML")


async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    await crud.delete_user(telegram_id)
    await update.callback_query.answer("Your account has been deleted.")
    await update.callback_query.edit_message_text("🔒 Your account has been successfully deleted.")


async def get_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    user = await crud.get_user_by_telegram_id(telegram_id)
    if not user:
        await update.callback_query.edit_message_text("🔑 <b>You need to register your API token first.</b>",
                                                      parse_mode="HTML")
        return
    moodle_api = MoodleApi()
    moodle_api.set_api_key(user.api_key)

    # Use caching for assignments data
    cache_key = f"assignments:{telegram_id}"
    courses = await get_from_cache(cache_key)
    if courses is None:
        courses = await moodle_api.fetch_assignments()
        await set_to_cache(cache_key, courses, expiration=300)

    assignments_list = []
    current_time = datetime.now()
    if courses:
        for course in courses:
            for assignment in course.get('assignments', []):
                due_date = datetime.fromtimestamp(assignment["duedate"])
                time_left = due_date - current_time
                # Skip past due assignments and certain types (e.g., midterm/endterm)
                if time_left.total_seconds() <= 0 or 'Midterm' in assignment["name"] or 'Endterm' in assignment["name"]:
                    continue
                assignment_info = (
                    f"📅 <b>Assignment:</b> <i>{assignment['name']}</i>\n"
                    f"📚 <b>Course:</b> <i>{course.get('fullname')}</i>\n"
                    f"⏰ <b>Due Date:</b> <i>{due_date.strftime('%d %B %Y, %H:%M')}</i>\n"
                    f"⏳ <b>Time Left:</b> <i>{time_left.days} days, {time_left.seconds // 3600} hours, {(time_left.seconds // 60) % 60} minutes</i>\n"
                )
                assignments_list.append(assignment_info)
                await crud.insert_seen_assignment(telegram_id, assignment["id"])
    final_message = ("🔒 <b>No upcoming assignments found.</b>" if not assignments_list else
                     "✨ <b>Upcoming Deadlines</b> ✨\n\n" + "\n".join(assignments_list))
    keyboard = [
        [InlineKeyboardButton("↻ Refresh", callback_data=CALLBACK_REFRESH_ASSIGNMENTS)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(final_message, reply_markup=reply_markup, parse_mode="HTML")


async def refresh_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    now = datetime.now()
    last_refresh = user_last_refresh_time.get(telegram_id)
    if last_refresh and now < last_refresh + timedelta(seconds=3600):
        await update.callback_query.answer("Please wait before refreshing again.")
        return
    user_last_refresh_time[telegram_id] = now
    await update.callback_query.answer("Refreshing assignments...")
    await get_assignments(update, context)



async def get_grades(update: Update, context: ContextTypes.DEFAULT_TYPE, grade_type: str):
    telegram_id = update.callback_query.from_user.id
    user = await crud.get_user_by_telegram_id(telegram_id)
    if not user:
        await update.callback_query.edit_message_text("🔑 <b>You need to register your API token first.</b>",
                                                      parse_mode="HTML")
        return
    moodle_api = MoodleApi()
    moodle_api.set_api_key(user.api_key)

    # Cache grades by user and grade type
    cache_key = f"grades:{telegram_id}:{grade_type}"
    grades = await get_from_cache(cache_key)
    if grades is None:
        grades = await moodle_api.fetch_grades_current_trimester(grade_type=grade_type)
        await set_to_cache(cache_key, grades, expiration=300)

    if grades:
        lines = []
        for grade in grades:
            lines.append(
                f"📚 <b>Course:</b> <i>{html.escape(str(grade['course']))}</i>\n"
                f"📋 <b>{html.escape(str(grade_type.title()))}:</b> <i>{html.escape(str(grade['assignment']))}</i>\n"
                f"🔢 <b>Grade:</b> <i>{html.escape(str(grade['grade']))} / {html.escape(str(grade['maxgrade']))}</i>\n"
            )
        message = f"🔍 <b>Your {grade_type.title()} Grades (Current Trimester):</b>\n\n" + "\n".join(lines)
    else:
        message = f"🔒 <b>No {grade_type} grades found for the current trimester.</b>"
    keyboard = [[InlineKeyboardButton("← Back", callback_data=CALLBACK_GRADES)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if len(message) > 4096:
        await update.callback_query.edit_message_text("🔍 Sending your grades in multiple messages...",
                                                      parse_mode="HTML")
        await send_long_message(telegram_id, message, context)
    else:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")


async def grades_assignment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_grades(update, context, grade_type='assignment')


async def grades_midterm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_grades(update, context, grade_type='midterm')


async def grades_endterm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_grades(update, context, grade_type='endterm')


async def show_grades_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Assignment Grades", callback_data=CALLBACK_GRADES_ASSIGNMENT)],
        [InlineKeyboardButton("📝 Midterm Grades", callback_data=CALLBACK_GRADES_MIDTERM)],
        [InlineKeyboardButton("📝 Endterm Grades", callback_data=CALLBACK_GRADES_ENDTERM)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("🔍 Choose grade category:", reply_markup=reply_markup,
                                                  parse_mode="HTML")
async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚨 Deadline Reminder", callback_data="deadline_reminder_settings")],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("🔔 Notification Settings:", reply_markup=reply_markup)


async def show_deadline_reminder_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    current_settings = await crud.get_notification_settings(telegram_id) or set()
    keyboard = []
    reminder_emoji = "✅" if NOTIF_DEADLINE_REMINDER in current_settings else "❌"
    keyboard.append(
        [InlineKeyboardButton(f"{reminder_emoji} Enable Deadline Reminder", callback_data="toggle_deadline_reminder")])
    for label, value in INTERVALS:
        emoji = "✅" if value in current_settings else "❌"
        keyboard.append([InlineKeyboardButton(f"{emoji} {label}", callback_data=f"toggle_{value}")])
    keyboard.append([InlineKeyboardButton("← Back", callback_data="back_to_notification_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("🚨 Deadline Reminder Settings:", reply_markup=reply_markup)


async def toggle_deadline_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    current_settings = await crud.get_notification_settings(telegram_id) or set()
    if NOTIF_DEADLINE_REMINDER in current_settings:
        await crud.delete_notification_setting(telegram_id, NOTIF_DEADLINE_REMINDER)
    else:
        await crud.insert_notification_setting(telegram_id, NOTIF_DEADLINE_REMINDER)
    await show_deadline_reminder_settings(update, context)


async def toggle_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    current_settings = await crud.get_notification_settings(telegram_id) or set()
    callback_data = update.callback_query.data.replace("toggle_", "")
    if callback_data in current_settings:
        await crud.delete_notification_setting(telegram_id, callback_data)
    else:
        await crud.insert_notification_setting(telegram_id, callback_data)
    await show_deadline_reminder_settings(update, context)


async def back_to_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_notification_settings(update, context)


async def check_upcoming_deadlines(context: ContextTypes.DEFAULT_TYPE):
    users = await crud.get_all_users()
    current_time = datetime.now()
    intervals = {
        "1_hour": (timedelta(hours=1), "less than 1 hour"),
        "4_hours": (timedelta(hours=4), "less than 4 hours"),
        "8_hours": (timedelta(hours=8), "less than 8 hours"),
        "12_hours": (timedelta(hours=12), "less than 12 hours"),
        "1_day": (timedelta(days=1), "less than 1 day"),
        "2_days": (timedelta(days=2), "less than 2 days"),
        "3_days": (timedelta(days=3), "less than 3 days"),
        "4_days": (timedelta(days=4), "less than 4 days"),
        "1_week": (timedelta(weeks=1), "less than 1 week"),
    }
    for user in users:
        telegram_id = user.telegram_id
        moodle_api = MoodleApi()
        moodle_api.set_api_key(user.api_key)
        courses = await moodle_api.fetch_assignments()
        notif_settings = await crud.get_notification_settings(telegram_id)
        if NOTIF_DEADLINE_REMINDER not in notif_settings:
            continue
        if courses:
            for course in courses:
                course_name = course.get('fullname')
                for assignment in course.get('assignments', []):
                    due_date = datetime.fromtimestamp(assignment["duedate"])
                    time_left = due_date - current_time
                    if time_left.total_seconds() <= 0:
                        continue
                    for interval_key in notif_settings:
                        if interval_key in intervals and time_left <= intervals[interval_key][0]:
                            already_sent = await crud.has_sent_reminder(telegram_id, assignment["id"], interval_key)
                            if already_sent:
                                continue
                            message = (
                                f"🚨 <b>Deadline Reminder</b>\n"
                                f"📚 <b>Course:</b> {course_name}\n"
                                f"📋 <b>Assignment:</b> <i>{assignment['name']}</i>\n"
                                f"⏳ <b>Time Left:</b> {intervals[interval_key][1]}\n"
                                f"🛑 <b>Don't miss it!</b>"
                            )
                            await context.bot.send_message(telegram_id, message, parse_mode='HTML')
                            await crud.insert_sent_reminder(telegram_id, assignment["id"], interval_key)
                            break

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

def get_callback_query_handlers():
    return [
        CallbackQueryHandler(view_profile, pattern=f"^{CALLBACK_PROFILE}$"),
        CallbackQueryHandler(get_assignments, pattern=f"^{CALLBACK_ASSIGNMENTS}$"),
        CallbackQueryHandler(refresh_assignments, pattern=f"^{CALLBACK_REFRESH_ASSIGNMENTS}$"),
        CallbackQueryHandler(back_to_menu, pattern=f"^{CALLBACK_BACK_TO_MENU}$"),
        CallbackQueryHandler(delete_account, pattern=f"^{CALLBACK_DELETE_ACCOUNT}$"),
        CallbackQueryHandler(show_notification_settings, pattern="^notification_settings$"),
        CallbackQueryHandler(toggle_deadline_reminder, pattern="^toggle_deadline_reminder$"),
        CallbackQueryHandler(show_deadline_reminder_settings, pattern="^deadline_reminder_settings$"),
        CallbackQueryHandler(back_to_notification_settings, pattern="^back_to_notification_settings$"),
        CallbackQueryHandler(toggle_interval, pattern="^toggle_"),
        CallbackQueryHandler(show_grades_menu, pattern=f"^{CALLBACK_GRADES}$"),
        CallbackQueryHandler(grades_assignment_handler, pattern=f"^{CALLBACK_GRADES_ASSIGNMENT}$"),
        CallbackQueryHandler(grades_midterm_handler, pattern=f"^{CALLBACK_GRADES_MIDTERM}$"),
        CallbackQueryHandler(grades_endterm_handler, pattern=f"^{CALLBACK_GRADES_ENDTERM}$")
    ]