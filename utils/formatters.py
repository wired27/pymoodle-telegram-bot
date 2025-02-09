def format_assignments(courses: list) -> str:
    from datetime import datetime
    lines = []
    current_time = datetime.now()
    for course in courses:
        course_name = course.get("fullname", "Unknown Course")
        for assignment in course.get("assignments", []):
            due_date = datetime.fromtimestamp(assignment["duedate"])
            time_left = due_date - current_time
            if time_left.total_seconds() <= 0 or 'midterm' in assignment["name"].lower() or 'endterm' in assignment["name"].lower():
                continue
            lines.append(
                f"📅 <b>Assignment:</b> <i>{assignment['name']}</i>\n"
                f"📚 <b>Course:</b> <i>{course_name}</i>\n"
                f"⏰ <b>Due Date:</b> <i>{due_date.strftime('%d %B %Y, %H:%M')}</i>\n"
                f"⏳ <b>Time Left:</b> <i>{time_left.days} days, {time_left.seconds // 3600} hours, {(time_left.seconds // 60) % 60} minutes</i>\n"
            )
    if not lines:
        return "🔒 <b>No upcoming assignments found.</b>"
    return "✨ <b>Upcoming Deadlines</b> ✨\n\n" + "\n".join(lines)