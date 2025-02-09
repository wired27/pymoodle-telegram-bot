from sqlalchemy import select, delete
from models.notification import NotificationSetting, SentReminder
from core.database import async_session

class NotificationRepository:
    def __init__(self):
        pass

    async def insert_setting(self, telegram_id: int, interval: str):
        async with async_session() as session:
            stmt = NotificationSetting.__table__.insert().values(telegram_id=telegram_id, interval=interval)
            try:
                await session.execute(stmt)
            except Exception:
                # Ignore if already exists
                pass
            await session.commit()

    async def delete_setting(self, telegram_id: int, interval: str):
        async with async_session() as session:
            await session.execute(delete(NotificationSetting).where(
                NotificationSetting.telegram_id == telegram_id,
                NotificationSetting.interval == interval
            ))
            await session.commit()

    async def get_settings(self, telegram_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(NotificationSetting.interval).where(NotificationSetting.telegram_id == telegram_id)
            )
            return {row[0] for row in result.all()}

    async def has_sent_reminder(self, telegram_id: int, assignment_id: int, interval: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(SentReminder).where(
                    SentReminder.telegram_id == telegram_id,
                    SentReminder.assignment_id == assignment_id,
                    SentReminder.interval == interval
                )
            )
            return result.scalar_one_or_none() is not None

    async def insert_sent_reminder(self, telegram_id: int, assignment_id: int, interval: str):
        async with async_session() as session:
            stmt = SentReminder.__table__.insert().values(
                telegram_id=telegram_id, assignment_id=assignment_id, interval=interval
            )
            try:
                await session.execute(stmt)
            except Exception:
                pass
            await session.commit()