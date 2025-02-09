import os
import logging
from datetime import datetime
import aiohttp
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

MOODLE_URL = os.getenv("MOODLE_URL")
logger = logging.getLogger(__name__)

class MoodleApi:
    def __init__(self):
        self.api_key = None
        self.user_id = None

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    async def api_call(self, function: str, **params):
        if not self.api_key:
            logger.error("API key not set")
            return None
        params.update({
            'wstoken': self.api_key,
            'wsfunction': function,
            'moodlewsrestformat': 'json'
        })
        url = urljoin(MOODLE_URL, '/webservice/rest/server.php')
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                logger.error(f"HTTP Request failed: {e}")
                return None

    async def get_user_id(self):
        user_info = await self.api_call('core_webservice_get_site_info')
        if user_info and "userid" in user_info:
            self.user_id = user_info["userid"]
            return self.user_id
        logger.error("Failed to get user ID.")
        return None

    async def fetch_user_details(self):
        user_info = await self.api_call('core_webservice_get_site_info')
        if user_info and "fullname" in user_info:
            return user_info["fullname"], user_info.get("userid")
        logger.error("Failed to get user details.")
        return None, None

    async def fetch_assignments(self):
        data = await self.api_call('mod_assign_get_assignments')
        return data.get('courses', []) if data else []

    async def fetch_courses(self):
        if not self.user_id:
            await self.get_user_id()
        courses_response = await self.api_call('core_enrol_get_users_courses', userid=self.user_id)
        return courses_response or []

    async def fetch_course_details(self, course_id: int):
        params = {'courseids[0]': course_id}
        response = await self.api_call('core_course_get_courses', **params)
        if response:
            if isinstance(response, list):
                return response[0] if len(response) > 0 else {}
            elif isinstance(response, dict):
                courses = response.get('courses')
                if courses and isinstance(courses, list) and len(courses) > 0:
                    return courses[0]
                return response
        return {}

    async def fetch_submissions(self, assignment_id: int, user_id: int):
        params = {'assignmentids[0]': assignment_id, 'userid': user_id}
        response = await self.api_call('mod_assign_get_submissions', **params)
        if response and 'submissions' in response:
            return response['submissions']
        return []

    async def fetch_grades_for_course(self, course_id: int, grade_type: str = 'assignment'):
        if not self.user_id:
            await self.get_user_id()
        grade_data = await self.api_call('gradereport_user_get_grade_items', courseid=course_id, userid=self.user_id)
        graded_items = []
        if grade_data and 'usergrades' in grade_data and grade_data['usergrades']:
            for item in grade_data['usergrades'][0]['gradeitems']:
                name = item.get('itemname', 'Unnamed Assignment')
                if grade_type == 'assignment' and ('midterm' in name.lower() or 'endterm' in name.lower()):
                    continue
                if grade_type == 'midterm' and 'midterm' not in name.lower():
                    continue
                if grade_type == 'endterm' and 'endterm' not in name.lower():
                    continue
                grade_raw = item.get('graderaw')
                if grade_raw is not None:
                    graded_items.append({
                        'name': name,
                        'grade': grade_raw,
                        'maxgrade': item.get('grademax', 'N/A')
                    })
        return graded_items

    async def fetch_grades_current_trimester(self, grade_type: str = 'assignment'):
        courses = await self.fetch_courses()
        now_ts = datetime.now().timestamp()
        current_courses = [
            course for course in courses
            if course.get('startdate') and course.get('enddate') and course['startdate'] <= now_ts <= course['enddate']
        ]
        grades_list = []
        for course in current_courses:
            course_name = course.get('fullname')
            course_id = course.get('id')
            grade_items = await self.fetch_grades_for_course(course_id, grade_type=grade_type)
            for item in grade_items:
                grades_list.append({
                    'course': course_name,
                    'assignment': item['name'],
                    'grade': item['grade'],
                    'maxgrade': item['maxgrade']
                })
        return grades_list