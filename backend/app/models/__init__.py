"""
Models package — imported by app/__init__.py to ensure
Flask-Migrate discovers every table.
"""
from app.models.user import User, StudentProfile, FacultyProfile, AdminProfile, Department, AuditLog, SystemSetting  # noqa
from app.models.course import AcademicYear, Semester, Course, Enrollment  # noqa
from app.models.assignment import Assignment  # noqa
from app.models.submission import Submission  # noqa
from app.models.attendance import Attendance  # noqa
from app.models.task import Task  # noqa
from app.models.resource import Resource  # noqa
from app.models.notification import Notification  # noqa
from app.models.schedule import CourseSession  # noqa
from app.models.quiz import Quiz, QuizQuestion, QuizOption, QuizAttempt, QuizAnswer  # noqa
