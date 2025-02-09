import os
import logging
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv
from bot import handlers
from db import database, base
import nest_asyncio

nest_asyncio.apply()
load_dotenv()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def init_db():
    async with database.engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.create_all)

async def main():
    await init_db()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', handlers.start)],
        states={
            handlers.EXPECTING_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_api_key)],
        },
        fallbacks=[CommandHandler('start', handlers.start)],
    )
    application.add_handler(conv_handler)

    for cb_handler in handlers.get_callback_query_handlers():
        application.add_handler(cb_handler)

    application.job_queue.run_repeating(handlers.check_upcoming_deadlines, interval=3600, first=10)

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
