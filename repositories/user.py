from sqlalchemy import select, delete
from models.user import User
from core.database import async_session

class UserRepository:
    def __init__(self):
        pass

    async def get_by_telegram_id(self, telegram_id: int) -> User:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            return result.scalar_one_or_none()

    async def create_or_update(self, telegram_id: int, api_key: str, first_name: str = None, last_name: str = None) -> User:
        async with async_session() as session:
            user = await self.get_by_telegram_id(telegram_id)
            if user:
                user.api_key = api_key
                user.first_name = first_name
                user.last_name = last_name
            else:
                user = User(telegram_id=telegram_id, api_key=api_key, first_name=first_name, last_name=last_name)
                session.add(user)
            await session.commit()
            return user

    async def delete(self, telegram_id: int):
        async with async_session() as session:
            await session.execute(delete(User).where(User.telegram_id == telegram_id))
            await session.commit()