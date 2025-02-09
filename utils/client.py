import aiohttp
from config import settings

class MoodleAPIClient:
    def __init__(self):
        self.api_key = None
        self.base_url = settings.MOODLE_URL

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    async def get_user_id(self) -> int:
        async with aiohttp.ClientSession() as session:
            params = {
                "wstoken": self.api_key,
                "wsfunction": "core_webservice_get_site_info",
                "moodlewsrestformat": "json"
            }
            async with session.get(f"{self.base_url}/webservice/rest/server.php", params=params) as response:
                data = await response.json()
                return data.get("userid")

    async def fetch_assignments(self, api_key: str):
        async with aiohttp.ClientSession() as session:
            params = {
                "wstoken": api_key,
                "wsfunction": "mod_assign_get_assignments",
                "moodlewsrestformat": "json"
            }
            async with session.get(f"{self.base_url}/webservice/rest/server.php", params=params) as response:
                data = await response.json()
                return data.get("courses", [])

    async def fetch_grades_current_trimester(self, api_key: str, grade_type: str):
        async with aiohttp.ClientSession() as session:
            params = {
                "wstoken": api_key,
                "wsfunction": "gradereport_user_get_grade_items",
                "moodlewsrestformat": "json"
            }
            async with session.get(f"{self.base_url}/webservice/rest/server.php", params=params) as response:
                data = await response.json()
                # Use "itemname" for filtering instead of "assignment"
                grades = data.get("grades", [])
                return [g for g in grades if grade_type in g.get("itemname", "").lower()]