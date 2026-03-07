"""
Dashboard service — computes summary stats for each portal.

All metrics are calculated live from database records (not stored snapshots)
so dashboards always reflect real-time state.

Public API
----------
  calculate_gpa(student_id)                -> float
  calculate_attendance(student_id)         -> float  (percentage 0-100)
  count_pending_assignments(student_id)    -> int

  get_student_stats(student)               -> dict
  get_faculty_stats(faculty)               -> dict
  get_admin_stats()                        -> dict
"""
from datetime import datetime, timezone
from sqlalchemy import func

from app.extensions import db
from app.models.user import User, Department
from app.models.course import Course, Enrollment
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.attendance import Attendance
from app.models.resource import Resource


# ══════════════════════════════════════════════════════════════════════════════
# Core Calculation Functions  (shared / testable in isolation)
# ══════════════════════════════════════════════════════════════════════════════

def calculate_gpa(student_id: int) -> float:
    """
    Calculate GPA live using credit-weighted average.

    Formula: sum(grade_points × credits) / sum(credits)
    Returns 0.0 if the student has no graded enrollments.
    """
    rows = (
        db.session.query(Enrollment.grade_points, Course.credits)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.status == "active",
            Enrollment.grade_points.isnot(None),
        )
        .all()
    )
    if not rows:
        return 0.0
    total_weighted = sum(r.grade_points * (r.credits or 3) for r in rows)
    total_credits  = sum(r.credits or 3 for r in rows)
    return round(total_weighted / total_credits, 2) if total_credits else 0.0


def calculate_attendance(student_id: int, course_id=None) -> float:
    """
    Calculate attendance percentage live from attendance_records.

    If course_id is given, restricts to that course.
    Returns 0.0 if no records found.
    Formula: present_or_late / total * 100
    """
    query = Attendance.query.filter_by(student_id=student_id)
    if course_id:
        query = query.filter_by(course_id=course_id)

    total   = query.count()
    if total == 0:
        return 0.0
    present = query.filter(Attendance.status.in_(["present", "late"])).count()
    return round(present / total * 100, 1)


def count_pending_assignments(student_id: int) -> int:
    """
    Count assignments that are due but have NOT been submitted by this student.

    Logic:
      1. Get all active course_ids for the student.
      2. Find all active assignments for those courses.
      3. Subtract the ones the student has already submitted.
    """
    enrolled_course_ids = [
        e.course_id for e in
        Enrollment.query.filter_by(student_id=student_id, status="active").all()
    ]
    if not enrolled_course_ids:
        return 0

    now = datetime.now(timezone.utc)

    all_assignments = (
        Assignment.query
        .filter(Assignment.course_id.in_(enrolled_course_ids))
        .filter_by(status="active")
        .filter((Assignment.due_date >= now) | (Assignment.due_date.is_(None)))
        .with_entities(Assignment.id)
        .all()
    )
    all_ids = {r.id for r in all_assignments}
    if not all_ids:
        return 0

    submitted_ids = {
        r.assignment_id for r in
        Submission.query
        .filter_by(student_id=student_id)
        .filter(Submission.assignment_id.in_(all_ids))
        .with_entities(Submission.assignment_id)
        .all()
    }
    return len(all_ids - submitted_ids)


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard Aggregators  (called by route handlers)
# ══════════════════════════════════════════════════════════════════════════════

# ── Student dashboard ──────────────────────────────────────────────────────────

def get_student_stats(student: User) -> dict:
    """Return stats shown on the student dashboard header cards."""
    enrollment_count    = student.enrollments.filter_by(status="active").count()
    gpa                 = calculate_gpa(student.id)
    attendance_pct      = calculate_attendance(student.id)
    pending_assignments = count_pending_assignments(student.id)

    return {
        "enrollment_count":      enrollment_count,
        "pending_assignments":   pending_assignments,
        "gpa":                   gpa,
        "attendance_percentage": attendance_pct,
    }


# ── Faculty dashboard ──────────────────────────────────────────────────────────

def get_faculty_stats(faculty: User) -> dict:
    """Return stats shown on the faculty dashboard header cards."""
    courses_q = faculty.taught_courses.filter_by(is_active=True)
    course_ids = [c.id for c in courses_q.all()]

    students_count = (
        Enrollment.query
        .filter(Enrollment.course_id.in_(course_ids))
        .filter_by(status="active")
        .count()
        if course_ids else 0
    )

    total_assignments = (
        Assignment.query.filter(Assignment.course_id.in_(course_ids)).count()
        if course_ids else 0
    )

    pending_grading = (
        Submission.query
        .join(Assignment)
        .filter(Assignment.course_id.in_(course_ids))
        .filter_by(status="submitted")
        .count()
        if course_ids else 0
    )

    return {
        "courses_count":   courses_q.count(),
        "students_count":  students_count,
        "assignments": {
            "total":   total_assignments,
            "pending": pending_grading,
        },
        "pending_grading": pending_grading,
    }


# ── Admin dashboard ────────────────────────────────────────────────────────────

def get_admin_stats() -> dict:
    """Return system-wide stats shown on the admin dashboard."""
    total_users    = User.query.filter_by(is_active=True).count()
    students_count = User.query.filter_by(role="student", is_active=True).count()
    faculty_count  = User.query.filter_by(role="faculty", is_active=True).count()
    courses_count  = Course.query.filter_by(is_active=True).count()

    pending_submissions = Submission.query.filter_by(status="submitted").count()

    resources_count    = Resource.query.count()
    total_enrollments  = Enrollment.query.filter_by(status="active").count()
    departments_count  = Department.query.count()

    return {
        "users": {
            "total":    total_users,
            "students": students_count,
            "faculty":  faculty_count,
            "admins":   total_users - students_count - faculty_count,
        },
        "courses_count":        courses_count,
        "pending_submissions":  pending_submissions,
        "resources_count":      resources_count,
        "total_enrollments":    total_enrollments,
        "departments_count":    departments_count,
    }
