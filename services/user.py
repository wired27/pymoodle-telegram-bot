from repositories.user import UserRepository

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_user(self, telegram_id: int):
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def register_api_key(self, telegram_id: int, api_key: str, first_name: str = None, last_name: str = None):
        return await self.user_repo.create_or_update(telegram_id, api_key, first_name, last_name)

    async def delete_user(self, telegram_id: int):
        return await self.user_repo.delete(telegram_id)