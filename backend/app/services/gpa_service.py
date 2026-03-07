"""
GPA service — recalculates and persists a student's GPA whenever grades change.

Grade → GPA Points mapping (standard 4.0 scale):
    A+  → 4.0   A  → 4.0   A- → 3.7
    B+  → 3.3   B  → 3.0   B- → 2.7
    C+  → 2.3   C  → 2.0   C- → 1.7
    D+  → 1.3   D  → 1.0   D- → 0.7
    F   → 0.0
"""
from app.extensions import db
from app.models.course import Enrollment
from app.models.user import User
from app.models.attendance import Attendance


GRADE_POINTS: dict[str, float] = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F":  0.0,
}

# Percentage-score → letter grade thresholds (descending order)
_SCORE_LETTER: list[tuple[float, str]] = [
    (97, "A+"), (93, "A"), (90, "A-"),
    (87, "B+"), (83, "B"), (80, "B-"),
    (77, "C+"), (73, "C"), (70, "C-"),
    (67, "D+"), (63, "D"), (60, "D-"),
]


def numeric_score_to_letter(score: float, total_points: float) -> str:
    """Convert a raw numeric score to a letter grade string."""
    if total_points <= 0:
        return "F"
    pct = (score / total_points) * 100
    for threshold, letter in _SCORE_LETTER:
        if pct >= threshold:
            return letter
    return "F"


def letter_to_points(grade: str) -> float:
    """Convert a letter grade string to GPA points. Returns 0.0 if unknown."""
    return GRADE_POINTS.get(str(grade).strip().upper(), 0.0)


def recalculate_student_gpa(student_id: int) -> float:

    student = db.session.get(User, student_id)
    if not student or not student.student_profile:
        return 0.0

    graded_enrollments = (
        Enrollment.query
        .join(Enrollment.course)
        .filter(Enrollment.student_id == student_id)
        .filter(Enrollment.grade.isnot(None))
        .all()
    )

    if not graded_enrollments:
        student.student_profile.gpa = 0.0
        db.session.commit()
        return 0.0

    total_credits  = 0
    total_weighted = 0.0

    for enroll in graded_enrollments:
        credits       = enroll.course.credits or 3
        points        = letter_to_points(enroll.grade)
        # Also store points on the enrollment row for quick access
        enroll.grade_points = points
        total_weighted += points * credits
        total_credits  += credits

    gpa = round(total_weighted / total_credits, 2) if total_credits else 0.0
    student.student_profile.gpa = gpa
    db.session.commit()
    return gpa


def recalculate_attendance_pct(student_id: int, course_id: int = None) -> float:
    """
    Calculate and persist attendance percentage for a student.
    If course_id is given, compute only for that course.
    Otherwise compute across all enrolled courses.
    """
    student = db.session.get(User, student_id)
    if not student or not student.student_profile:
        return 0.0

    query = Attendance.query.filter_by(student_id=student_id)
    if course_id:
        query = query.filter_by(course_id=course_id)

    records = query.all()
    if not records:
        return 0.0

    present = sum(1 for r in records if r.status in ("present", "late"))
    pct     = round((present / len(records)) * 100, 1)

    if not course_id:
        student.student_profile.attendance_pct = pct
        db.session.commit()

    return pct
