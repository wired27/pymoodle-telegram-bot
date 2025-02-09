import html
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.formatters import format_assignments
from services.moodle import MoodleService
from services.user import UserService

# Callback constants
CALLBACK_ASSIGNMENTS = "get_assignments"
CALLBACK_REFRESH_ASSIGNMENTS = "refresh_assignments"
CALLBACK_PROFILE = "view_profile"
CALLBACK_DELETE_ACCOUNT = "delete_account"
CALLBACK_BACK_TO_MENU = "back_to_menu"
CALLBACK_NOTIFICATION_SETTINGS = "notification_settings"
CALLBACK_TOGGLE_DEADLINE = "toggle_deadline_reminder"
CALLBACK_GRADES = "grades_menu"
CALLBACK_GRADES_ASSIGNMENT = "grades_assignment"
CALLBACK_GRADES_MIDTERM = "grades_midterm"
CALLBACK_GRADES_ENDTERM = "grades_endterm"

# Local in-memory refresh tracker; in production, consider a persistent storage.
user_last_refresh_time = {}

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    user_service: UserService = context.application.bot_data["user_service"]
    moodle_service: MoodleService = context.application.bot_data["moodle_service"]
    user = await user_service.get_user(telegram_id)
    if user:
        # For demonstration, this dummy call assumes a "fullname" property. Replace as needed.
        details = await moodle_service.client.fetch_assignments(api_key=user.api_key)
        full_name = details.get("fullname", "N/A") if isinstance(details, dict) else "N/A"
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
        profile_message = "🔑 <b>You need to register your API token first.</b>"

    keyboard = [
        [InlineKeyboardButton("🗑️ Delete Account", callback_data=CALLBACK_DELETE_ACCOUNT)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(profile_message, reply_markup=reply_markup, parse_mode="HTML")

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    user_service: UserService = context.application.bot_data["user_service"]
    await user_service.delete_user(telegram_id)
    await update.callback_query.answer("Your account has been deleted.")
    await update.callback_query.edit_message_text("🔒 Your account has been successfully deleted.")

async def get_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    moodle_service: MoodleService = context.application.bot_data["moodle_service"]
    assignments = await moodle_service.get_assignments(telegram_id=telegram_id)
    message = format_assignments(assignments)
    keyboard = [
        [InlineKeyboardButton("↻ Refresh", callback_data=CALLBACK_REFRESH_ASSIGNMENTS)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")

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

async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    message = "🔔 <b>Notification Settings</b>\n\nToggle deadline reminders below."
    keyboard = [
        [InlineKeyboardButton("🔔 Toggle Deadline Reminders", callback_data=CALLBACK_TOGGLE_DEADLINE)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")

async def toggle_deadline_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    # Here you would normally update the user's deadline reminder settings in your repository.
    # For demonstration purposes, we simply notify the user that the reminders have been toggled.
    message = "🚨 Deadline reminders toggled!"
    keyboard = [
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_NOTIFICATION_SETTINGS)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")

async def show_grades_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Assignment Grades", callback_data=CALLBACK_GRADES_ASSIGNMENT)],
        [InlineKeyboardButton("📝 Midterm Grades", callback_data=CALLBACK_GRADES_MIDTERM)],
        [InlineKeyboardButton("📝 Endterm Grades", callback_data=CALLBACK_GRADES_ENDTERM)],
        [InlineKeyboardButton("← Back", callback_data=CALLBACK_BACK_TO_MENU)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("🔍 Choose grade category:", reply_markup=reply_markup, parse_mode="HTML")

async def get_grades(update: Update, context: ContextTypes.DEFAULT_TYPE, grade_type: str):
    telegram_id = update.callback_query.from_user.id
    moodle_service: MoodleService = context.application.bot_data["moodle_service"]
    grades = await moodle_service.get_grades(telegram_id, grade_type)
    if grades:
        lines = []
        for grade in grades:
            lines.append(
                f"📚 <b>Course:</b> <i>{html.escape(str(grade.get('course')))}</i>\n"
                f"📋 <b>{html.escape(grade_type.title())}:</b> <i>{html.escape(str(grade.get('itemname')))}</i>\n"
                f"🔢 <b>Grade:</b> <i>{html.escape(str(grade.get('grade')))} / {html.escape(str(grade.get('maxgrade')))}</i>\n"
            )
        message = f"🔍 <b>Your {grade_type.title()} Grades (Current Trimester):</b>\n\n" + "\n".join(lines)
    else:
        message = f"🔒 <b>No {grade_type} grades found for the current trimester.</b>"
    keyboard = [[InlineKeyboardButton("← Back", callback_data=CALLBACK_GRADES)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")

async def grades_assignment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_grades(update, context, grade_type='assignment')

async def grades_midterm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_grades(update, context, grade_type='midterm')

async def grades_endterm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_grades(update, context, grade_type='endterm')

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers/commands import show_main_menu
    await show_main_menu(update, context)

async def check_upcoming_deadlines(context: ContextTypes.DEFAULT_TYPE):
    from datetime import timedelta
    from services.moodle import MoodleService
    from services.user import UserService
    notification_intervals = {
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
    user_service: UserService = context.application.bot_data["user_service"]
    moodle_service: MoodleService = context.application.bot_data["moodle_service"]
    telegram_ids = []  # Replace with actual logic to retrieve user telegram_ids.
    for telegram_id in telegram_ids:
        user = await user_service.get_user(telegram_id)
        if not user:
            continue
        assignments = await moodle_service.get_assignments(telegram_id=telegram_id)
        current_time = datetime.now()
        for course in assignments:
            course_name = course.get("fullname")
            for assignment in course.get("assignments", []):
                due_date = datetime.fromtimestamp(assignment["duedate"])
                time_left = due_date - current_time
                if time_left.total_seconds() <= 0:
                    continue
                message = (
                    f"🚨 <b>Deadline Reminder</b>\n"
                    f"📚 <b>Course:</b> {course_name}\n"
                    f"📋 <b>Assignment:</b> <i>{assignment['name']}</i>\n"
                    f"⏳ <b>Time Left:</b> {notification_intervals.get('1_hour')[1]}\n"
                    f"🛑 <b>Don't miss it!</b>"
                )
                await context.bot.send_message(telegram_id, message, parse_mode='HTML')