from typing import Any, Dict, List, Optional
from utils.decorators import cache
from repositories.user import UserRepository
from repositories.assignment import AssignmentRepository
from repositories.notification import NotificationRepository
from utils.client import MoodleAPIClient

class MoodleService:
    def __init__(self, client: MoodleAPIClient, user_repo: UserRepository,
                 assignment_repo: AssignmentRepository, notification_repo: NotificationRepository):
        self.client = client
        self.user_repo = user_repo
        self.assignment_repo = assignment_repo
        self.notification_repo = notification_repo

    @cache(key="assignments:{telegram_id}", ex=300)
    async def get_assignments(self, telegram_id: int) -> List[Dict[str, Any]]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return []
        return await self.client.fetch_assignments(user.api_key)

    async def verify_api_key(self, api_key: str) -> Optional[dict]:
        self.client.set_api_key(api_key)
        # Fetch user profile information from Moodle
        user_info = await self.client.fetch_user_profile(api_key)
        if not user_info or "userid" not in user_info:
            return None
        return user_info

    async def get_grades(self, telegram_id: int, grade_type: str) -> List[Dict[str, Any]]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return []
        grades = await self.client.fetch_grades_current_trimester(api_key=user.api_key, grade_type=grade_type)
        return grades