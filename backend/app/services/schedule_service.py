"""
Schedule service — retrieves and structures timetable data.
"""
from app.models.schedule import CourseSession
from app.models.course import Enrollment

ORDERED_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def get_student_schedule(student_id: int) -> list[dict]:
    """
    Return the weekly schedule for a student (all enrolled active courses).
    Sorted by day_of_week (Mon→Sat) then start_time.
    """
    enrolled_course_ids = [
        e.course_id for e in
        Enrollment.query.filter_by(student_id=student_id, status="active").all()
    ]

    if not enrolled_course_ids:
        return []

    sessions = (
        CourseSession.query
        .filter(CourseSession.course_id.in_(enrolled_course_ids))
        .all()
    )

    def sort_key(s):
        day_order = ORDERED_DAYS.index(s.day_of_week) if s.day_of_week in ORDERED_DAYS else 99
        return (day_order, s.start_time)

    return [s.to_dict() for s in sorted(sessions, key=sort_key)]


def get_faculty_schedule(faculty_id: int) -> list[dict]:
    """
    Return the weekly teaching schedule for a faculty member.
    """
    from app.models.course import Course

    course_ids = [
        c.id for c in
        Course.query.filter_by(faculty_id=faculty_id, is_active=True).all()
    ]

    if not course_ids:
        return []

    sessions = (
        CourseSession.query
        .filter(CourseSession.course_id.in_(course_ids))
        .all()
    )

    def sort_key(s):
        day_order = ORDERED_DAYS.index(s.day_of_week) if s.day_of_week in ORDERED_DAYS else 99
        return (day_order, s.start_time)

    return [s.to_dict() for s in sorted(sessions, key=sort_key)]
