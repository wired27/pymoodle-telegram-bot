import asyncio
import logging
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from config import settings
from core.database import create_tables
from core.bot import create_bot
from handlers.commands import start, handle_api_key, EXPECTING_API_KEY
from handlers.callbacks import (
    view_profile,
    delete_account,
    get_assignments,
    refresh_assignments,
    show_grades_menu,
    grades_assignment_handler,
    grades_midterm_handler,
    grades_endterm_handler,
    back_to_menu,
    show_notification_settings,
    check_upcoming_deadlines,
)
from repositories.user import UserRepository
from repositories.assignment import AssignmentRepository
from repositories.notification import NotificationRepository
from services.user import UserService
from services.moodle import MoodleService
from utils.client import MoodleAPIClient
import nest_asyncio

nest_asyncio.apply()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def main():
    # Initialize the database tables.
    await create_tables()

    # Create repositories.
    user_repo = UserRepository()
    assignment_repo = AssignmentRepository()
    notification_repo = NotificationRepository()

    # Initialize services.
    user_service = UserService(user_repo)
    moodle_client = MoodleAPIClient()
    moodle_service = MoodleService(moodle_client, user_repo, assignment_repo, notification_repo)

    # Create bot and application.
    application = create_bot(settings.TELEGRAM_TOKEN)

    # Inject dependencies into bot_data.
    application.bot_data["user_service"] = user_service
    application.bot_data["moodle_service"] = moodle_service

    # Conversation handler (for /start command and API key registration):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EXPECTING_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_key)]
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(conv_handler)

    # CallbackQueryHandlers for inline button presses.
    application.add_handler(CallbackQueryHandler(get_assignments, pattern="^get_assignments$"))
    application.add_handler(CallbackQueryHandler(refresh_assignments, pattern="^refresh_assignments$"))
    application.add_handler(CallbackQueryHandler(view_profile, pattern="^view_profile$"))
    application.add_handler(CallbackQueryHandler(delete_account, pattern="^delete_account$"))
    application.add_handler(CallbackQueryHandler(show_grades_menu, pattern="^grades_menu$"))
    application.add_handler(CallbackQueryHandler(grades_assignment_handler, pattern="^grades_assignment$"))
    application.add_handler(CallbackQueryHandler(grades_midterm_handler, pattern="^grades_midterm$"))
    application.add_handler(CallbackQueryHandler(grades_endterm_handler, pattern="^grades_endterm$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(show_notification_settings, pattern="^notification_settings$"))

    # Optional command handlers.
    application.add_handler(CommandHandler("profile", view_profile))
    application.add_handler(CommandHandler("assignments", get_assignments))

    # Schedule a job for checking deadlines.
    job_queue = application.job_queue
    job_queue.run_repeating(check_upcoming_deadlines, interval=3600, first=10)

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())