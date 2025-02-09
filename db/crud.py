from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import User, SeenAssignment, NotificationSetting, SentReminder
from db.database import async_session

async def get_user_by_telegram_id(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def create_or_update_user(telegram_id: int, api_key: str):
    async with async_session() as session:
        user = await get_user_by_telegram_id(telegram_id)
        if user:
            user.api_key = api_key
        else:
            user = User(telegram_id=telegram_id, api_key=api_key)
            session.add(user)
        await session.commit()

async def delete_user(telegram_id: int):
    async with async_session() as session:
        await session.execute(delete(User).where(User.telegram_id == telegram_id))
        await session.execute(delete(SeenAssignment).where(SeenAssignment.telegram_id == telegram_id))
        await session.execute(delete(NotificationSetting).where(NotificationSetting.telegram_id == telegram_id))
        await session.execute(delete(SentReminder).where(SentReminder.telegram_id == telegram_id))
        await session.commit()

async def insert_seen_assignment(telegram_id: int, assignment_id: int):
    async with async_session() as session:
        stmt = pg_insert(SeenAssignment).values(telegram_id=telegram_id, assignment_id=assignment_id)
        stmt = stmt.on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()

async def get_seen_assignments(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(SeenAssignment.assignment_id).where(SeenAssignment.telegram_id == telegram_id))
        return [row[0] for row in result.all()]

async def insert_notification_setting(telegram_id: int, interval: str):
    async with async_session() as session:
        stmt = pg_insert(NotificationSetting).values(telegram_id=telegram_id, interval=interval)
        stmt = stmt.on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()

async def delete_notification_setting(telegram_id: int, interval: str):
    async with async_session() as session:
        await session.execute(
            delete(NotificationSetting).where(NotificationSetting.telegram_id == telegram_id,
                                               NotificationSetting.interval == interval)
        )
        await session.commit()

async def get_notification_settings(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(NotificationSetting.interval).where(NotificationSetting.telegram_id == telegram_id)
        )
        return {row[0] for row in result.all()}

async def get_all_users():
    async with async_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()

async def has_sent_reminder(telegram_id: int, assignment_id: int, interval: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(SentReminder).where(
                SentReminder.telegram_id == telegram_id,
                SentReminder.assignment_id == assignment_id,
                SentReminder.interval == interval
            )
        )
        return result.scalar_one_or_none() is not None

async def insert_sent_reminder(telegram_id: int, assignment_id: int, interval: str):
    async with async_session() as session:
        stmt = pg_insert(SentReminder).values(telegram_id=telegram_id, assignment_id=assignment_id, interval=interval)
        stmt = stmt.on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()