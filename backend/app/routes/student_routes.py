"""
Student routes — /api/student/*
All endpoints require a valid JWT with role='student'.

  GET    /dashboard              — dashboard summary stats
  GET    /courses                — enrolled courses
  POST   /courses/enroll         — enroll in a course
  GET    /courses/<id>           — single course detail
  GET    /courses/<id>/resources — resources for a specific course
  DELETE /courses/<id>/drop      — drop a course
  GET    /assignments            — all assignments for enrolled courses
  GET    /assignments/<id>       — single assignment detail
  POST   /assignments/<id>/submit — submit a file/text for an assignment
  GET    /resources              — all resources across enrolled courses
  GET    /schedule               — weekly timetable
  GET    /attendance             — attendance records per course
  GET    /profile
  PUT    /profile

Tasks (accessible by all roles) are at /api/tasks  (common_routes).
"""
import os
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.utils.decorators import student_required, get_current_user
from app.utils.validators import allowed_file
from app.models.course import Course, Enrollment
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.resource import Resource
from app.models.attendance import Attendance
from app.models.user import User
from app.services.dashboard_service import (
    get_student_stats, calculate_attendance, count_pending_assignments
)
from app.services.schedule_service import get_student_schedule

student_bp = Blueprint("student", __name__)


# ── GET /api/student/dashboard ────────────────────────────────────────────────
@student_bp.route("/dashboard", methods=["GET"])
@student_required
def dashboard_stats():
    user = get_current_user()
    return jsonify(get_student_stats(user)), 200


# ── GET /api/student/courses ───────────────────────────────────────────────────
@student_bp.route("/courses", methods=["GET"])
@student_required
def get_courses():
    user        = get_current_user()
    enrollments = user.enrollments.filter_by(status="active").all()
    result      = []
    for enroll in enrollments:
        course_data = enroll.course.to_dict()
        course_data["grade"]  = enroll.grade
        course_data["status"] = enroll.status
        result.append(course_data)
    return jsonify(result), 200


# ── POST /api/student/courses/enroll ──────────────────────────────────────────
@student_bp.route("/courses/enroll", methods=["POST"])
@student_required
def enroll_course():
    """
    Enroll the authenticated student in a course.
    Body: { "course_id": <int> }
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    course_id = data.get("course_id")
    if not course_id:
        return jsonify({"error": "'course_id' is required"}), 400

    course = db.session.get(Course, int(course_id))
    if not course or not course.is_active:
        return jsonify({"error": "Course not found or inactive"}), 404

    # Check capacity
    if course.enrolled_count >= course.max_students:
        return jsonify({"error": "Course is full"}), 409

    # Check duplicate enrollment
    existing = Enrollment.query.filter_by(
        student_id=user.id, course_id=course.id
    ).first()
    if existing:
        if existing.status == "active":
            return jsonify({"error": "Already enrolled in this course"}), 409
        # Re-activate a previously dropped enrollment
        existing.status = "active"
        db.session.commit()
        return jsonify({"message": "Re-enrolled successfully", "course": course.to_dict()}), 200

    enroll = Enrollment(
        student_id=user.id,
        course_id=course.id,
        status="active",
    )
    db.session.add(enroll)
    db.session.commit()
    return jsonify({"message": "Enrolled successfully", "course": course.to_dict()}), 201


# ── DELETE /api/student/courses/<id>/drop ─────────────────────────────────────
@student_bp.route("/courses/<int:course_id>/drop", methods=["DELETE"])
@student_required
def drop_course(course_id):
    """Soft-drop an active enrollment."""
    user = get_current_user()
    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "Enrollment not found"}), 404

    enroll.status = "dropped"
    db.session.commit()
    return jsonify({"message": "Course dropped successfully"}), 200


# ── GET /api/student/courses/<id> ──────────────────────────────────────────────
@student_bp.route("/courses/<int:course_id>", methods=["GET"])
@student_required
def get_course_detail(course_id):
    user   = get_current_user()
    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "You are not enrolled in this course"}), 403

    course      = enroll.course
    assignments = [a.to_dict(student_id=user.id) for a in course.assignments.filter_by(status="active").all()]
    resources   = [r.to_dict() for r in course.resources.all()]
    schedules   = [s.to_dict() for s in course.sessions.all()]

    return jsonify({
        "course":      course.to_dict(),
        "enrollment":  enroll.to_dict(),
        "assignments": assignments,
        "resources":   resources,
        "schedule":    schedules,
    }), 200


# ── GET /api/student/courses/<id>/resources ───────────────────────────────────
@student_bp.route("/courses/<int:course_id>/resources", methods=["GET"])
@student_required
def get_course_resources(course_id):
    user   = get_current_user()
    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "You are not enrolled in this course"}), 403

    resources = Resource.query.filter_by(course_id=course_id).all()
    return jsonify([r.to_dict() for r in resources]), 200


# ── GET /api/student/assignments ───────────────────────────────────────────────
@student_bp.route("/assignments", methods=["GET"])
@student_required
def get_assignments():
    user               = get_current_user()
    enrolled_course_ids = [
        e.course_id for e in user.enrollments.filter_by(status="active").all()
    ]
    if not enrolled_course_ids:
        return jsonify([]), 200

    assignments = (
        Assignment.query
        .filter(Assignment.course_id.in_(enrolled_course_ids))
        .filter_by(status="active")
        .order_by(Assignment.due_date.asc())
        .all()
    )
    return jsonify([a.to_dict(student_id=user.id) for a in assignments]), 200


# ── GET /api/student/assignments/<id> ──────────────────────────────────────────
@student_bp.route("/assignments/<int:assignment_id>", methods=["GET"])
@student_required
def get_assignment_detail(assignment_id):
    user       = get_current_user()
    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    # Verify student is enrolled in the assignment's course
    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=assignment.course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "Access denied"}), 403

    submission = Submission.query.filter_by(
        assignment_id=assignment_id, student_id=user.id
    ).first()

    return jsonify({
        "assignment": assignment.to_dict(student_id=user.id),
        "submission": submission.to_dict() if submission else None,
    }), 200


# ── POST /api/student/assignments/<id>/submit  (+ legacy alias) ────────────────
@student_bp.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
@student_bp.route("/submit-assignment/<int:assignment_id>",  methods=["POST"])
@student_required
def submit_assignment(assignment_id):
    user       = get_current_user()
    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=assignment.course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "Access denied"}), 403

    # Prevent re-submission of graded assignments
    existing = Submission.query.filter_by(
        assignment_id=assignment_id, student_id=user.id
    ).first()
    if existing and existing.status == "graded":
        return jsonify({"error": "This assignment has already been graded and cannot be resubmitted."}), 409

    submission_text = request.form.get("submission_text", "").strip()
    file_path = None
    original_filename = None

    # Handle optional file upload
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed"}), 400
            filename = secure_filename(f"sub_{assignment_id}_{user.id}_{file.filename}")
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            file_path         = filename
            original_filename = file.filename

    if not submission_text and not file_path:
        return jsonify({"error": "Submission must include text or a file"}), 400

    # Determine late status
    now = datetime.now(timezone.utc)
    due = assignment.due_date
    if due and due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    is_late = due and now > due

    if existing:
        # Resubmission (before grading)
        existing.submission_text   = submission_text or existing.submission_text
        existing.file_path         = file_path or existing.file_path
        existing.original_filename = original_filename or existing.original_filename
        existing.submitted_at      = now
        existing.status            = "late" if is_late else "submitted"
        db.session.commit()
        return jsonify({"message": "Assignment resubmitted", "submission_id": existing.id}), 200

    sub = Submission(
        assignment_id=assignment_id,
        student_id=user.id,
        submission_text=submission_text,
        file_path=file_path,
        original_filename=original_filename,
        status="late" if is_late else "submitted",
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({"message": "Assignment submitted successfully", "submission_id": sub.id}), 201


# ── GET /api/student/resources ────────────────────────────────────────────────
@student_bp.route("/resources", methods=["GET"])
@student_required
def get_resources():
    user = get_current_user()
    enrolled_course_ids = [
        e.course_id for e in user.enrollments.filter_by(status="active").all()
    ]
    if not enrolled_course_ids:
        return jsonify([]), 200

    resources = (
        Resource.query
        .filter(Resource.course_id.in_(enrolled_course_ids))
        .order_by(Resource.uploaded_at.desc())
        .all()
    )
    return jsonify([r.to_dict() for r in resources]), 200


# ── GET /api/student/schedule ──────────────────────────────────────────────────
@student_bp.route("/schedule", methods=["GET"])
@student_required
def get_schedule():
    user = get_current_user()
    return jsonify(get_student_schedule(user.id)), 200


# ── GET /api/student/attendance ────────────────────────────────────────────────
@student_bp.route("/attendance", methods=["GET"])
@student_required
def get_attendance():
    """
    Return attendance records for all enrolled courses.
    Optional ?course_id=<id> to filter to a single course.
    Response includes per-course summary + individual records.
    """
    user      = get_current_user()
    course_id = request.args.get("course_id", type=int)

    enrollments = user.enrollments.filter_by(status="active").all()
    if course_id:
        enrollments = [e for e in enrollments if e.course_id == course_id]

    result = []
    for enroll in enrollments:
        course   = enroll.course
        records  = (
            Attendance.query
            .filter_by(student_id=user.id, course_id=course.id)
            .order_by(Attendance.date.desc())
            .all()
        )
        pct = calculate_attendance(user.id, course.id)
        result.append({
            "course_id":      course.id,
            "course_code":    course.course_code,
            "course_name":    course.course_name,
            "attendance_pct": pct,
            "total":          len(records),
            "present":        sum(1 for r in records if r.status in ("present", "late")),
            "absent":         sum(1 for r in records if r.status == "absent"),
            "records": [r.to_dict() for r in records],
        })

    overall_pct = calculate_attendance(user.id)
    return jsonify({
        "overall_attendance_pct": overall_pct,
        "courses": result,
    }), 200


# ── GET /api/student/profile ──────────────────────────────────────────────────
@student_bp.route("/profile", methods=["GET"])
@student_required
def get_profile():
    user = get_current_user()
    return jsonify(user.to_dict(include_profile=True)), 200


# ── PUT /api/student/profile ──────────────────────────────────────────────────
@student_bp.route("/profile", methods=["PUT"])
@student_required
def update_profile():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    updatable = ("full_name", "email", "phone", "department")
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(user, field, str(data[field]).strip())

    # Check email uniqueness if it changed
    if "email" in data:
        conflict = User.query.filter(
            User.email == data["email"].strip().lower(),
            User.id    != user.id,
        ).first()
        if conflict:
            return jsonify({"error": "Email is already in use by another account"}), 409
        user.email = data["email"].strip().lower()

    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "user": user.to_dict(include_profile=True)}), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  ONLINE QUIZ ROUTES — Student
# ═══════════════════════════════════════════════════════════════════════════════
from app.models.quiz import Quiz, QuizQuestion, QuizOption, QuizAttempt, QuizAnswer  # noqa: E402
from app.models.notification import Notification  # noqa: E402


# ── GET /api/student/courses/<id>/quizzes ─────────────────────────────────────
@student_bp.route("/courses/<int:course_id>/quizzes", methods=["GET"])
@student_required
def get_course_quizzes(course_id):
    user = get_current_user()
    # Verify student is enrolled
    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "Not enrolled in this course"}), 403

    now = datetime.now(timezone.utc)
    quizzes = Quiz.query.filter(
        Quiz.course_id == course_id,
        db.or_(
            Quiz.is_published == True,
            db.and_(
                Quiz.scheduled_publish_at.isnot(None),
                Quiz.scheduled_publish_at <= now
            )
        )
    ).all()
    return jsonify([q.to_dict(student_id=user.id) for q in quizzes]), 200


# ── GET /api/student/quizzes/<id> ─────────────────────────────────────────────
@student_bp.route("/quizzes/<int:quiz_id>", methods=["GET"])
@student_required
def get_quiz(quiz_id):
    user = get_current_user()
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found or not available"}), 404
    now = datetime.now(timezone.utc)
    sched = quiz.scheduled_publish_at
    if sched is not None and sched.tzinfo is None:
        sched = sched.replace(tzinfo=timezone.utc)
    effectively_published = quiz.is_published or (sched is not None and sched <= now)
    if not effectively_published:
        return jsonify({"error": "Quiz not found or not available"}), 404

    # Verify enrollment
    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=quiz.course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "Not enrolled in this course"}), 403

    # Check if an in-progress attempt exists
    in_progress = QuizAttempt.query.filter_by(
        quiz_id=quiz_id, student_id=user.id, status="in_progress"
    ).first()

    quiz_data = quiz.to_dict(include_questions=False, student_id=user.id)
    # Include questions but hide correct answers
    quiz_data["questions"] = [q.to_dict(include_correct=False) for q in quiz.questions]
    quiz_data["in_progress_attempt_id"] = in_progress.id if in_progress else None
    return jsonify(quiz_data), 200


# ── POST /api/student/quizzes/<id>/start ──────────────────────────────────────
@student_bp.route("/quizzes/<int:quiz_id>/start", methods=["POST"])
@student_required
def start_quiz(quiz_id):
    """Start a new quiz attempt. Returns attempt_id."""
    user = get_current_user()
    quiz = Quiz.query.get(quiz_id)
    if not quiz or not quiz.is_published:
        return jsonify({"error": "Quiz not found"}), 404

    enroll = Enrollment.query.filter_by(
        student_id=user.id, course_id=quiz.course_id, status="active"
    ).first()
    if not enroll:
        return jsonify({"error": "Not enrolled in this course"}), 403

    # Check if already in-progress
    in_progress = QuizAttempt.query.filter_by(
        quiz_id=quiz_id, student_id=user.id, status="in_progress"
    ).first()
    if in_progress:
        return jsonify({"message": "Attempt already in progress", "attempt_id": in_progress.id}), 200

    # Check max_attempts
    if quiz.max_attempts > 0:
        used = QuizAttempt.query.filter_by(
            quiz_id=quiz_id, student_id=user.id
        ).count()
        if used >= quiz.max_attempts:
            return jsonify({"error": "Maximum attempts reached"}), 400

    attempt_number = QuizAttempt.query.filter_by(
        quiz_id=quiz_id, student_id=user.id
    ).count() + 1

    attempt = QuizAttempt(
        quiz_id        = quiz.id,
        student_id     = user.id,
        max_score      = float(quiz.total_points),
        attempt_number = attempt_number,
        status         = "in_progress",
    )
    db.session.add(attempt)
    db.session.commit()
    return jsonify({"message": "Quiz started", "attempt_id": attempt.id}), 201


# ── POST /api/student/quizzes/<id>/submit ─────────────────────────────────────
@student_bp.route("/quizzes/<int:quiz_id>/submit", methods=["POST"])
@student_required
def submit_quiz(quiz_id):
    """
    Submit quiz answers.
    Body: { "attempt_id": <int>, "answers": { "<question_id>": <option_id>, ... } }
    """
    user = get_current_user()
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    data = request.get_json(silent=True) or {}
    attempt_id = data.get("attempt_id")
    if not attempt_id:
        return jsonify({"error": "'attempt_id' is required"}), 400

    attempt = QuizAttempt.query.filter_by(
        id=attempt_id, student_id=user.id, quiz_id=quiz_id
    ).first()
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    if attempt.status == "submitted":
        return jsonify({"error": "Attempt already submitted"}), 400

    answers_map = data.get("answers", {})   # { "question_id": option_id }

    total_score = 0.0
    answer_results = []

    for question in quiz.questions:
        qid = str(question.id)
        selected_opt_id = answers_map.get(qid) or answers_map.get(int(qid))

        is_correct   = False
        points_earned = 0.0
        selected_opt  = None

        if selected_opt_id:
            selected_opt = QuizOption.query.filter_by(
                id=int(selected_opt_id), question_id=question.id
            ).first()
            if selected_opt and selected_opt.is_correct:
                is_correct    = True
                points_earned = float(question.points)
                total_score  += points_earned

        answer = QuizAnswer(
            attempt_id         = attempt.id,
            question_id        = question.id,
            selected_option_id = selected_opt.id if selected_opt else None,
            is_correct         = is_correct,
            points_earned      = points_earned,
        )
        db.session.add(answer)
        answer_results.append({
            "question_id":    question.id,
            "is_correct":     is_correct,
            "points_earned":  points_earned,
            "correct_option": next(
                (o.option_text for o in question.options if o.is_correct), None
            ) if quiz.show_answers_after else None,
            "explanation":    question.explanation if quiz.show_answers_after else None,
        })

    max_score  = float(quiz.total_points) or 1.0
    percentage = round((total_score / max_score) * 100, 1) if max_score else 0
    passed     = percentage >= quiz.pass_score

    attempt.score        = total_score
    attempt.max_score    = max_score
    attempt.percentage   = percentage
    attempt.passed       = passed
    attempt.status       = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)

    db.session.commit()

    # Notify student
    Notification.create(
        user_id=user.id,
        title=f"Quiz submitted: {quiz.title}",
        message=(
            f"You scored {total_score}/{max_score} ({percentage}%) — "
            + ("Passed ✓" if passed else "Not passed")
        ),
        notification_type="grade",
        related_id=quiz.id,
        related_type="quiz",
    )

    return jsonify({
        "message":     "Quiz submitted",
        "score":       total_score,
        "max_score":   max_score,
        "percentage":  percentage,
        "passed":      passed,
        "answer_results": answer_results if quiz.show_answers_after else [],
    }), 200


# ── GET /api/student/quizzes/<id>/result ──────────────────────────────────────
@student_bp.route("/quizzes/<int:quiz_id>/result", methods=["GET"])
@student_required
def quiz_result(quiz_id):
    user = get_current_user()
    attempt = QuizAttempt.query.filter_by(
        quiz_id=quiz_id, student_id=user.id, status="submitted"
    ).order_by(QuizAttempt.submitted_at.desc()).first()
    if not attempt:
        return jsonify({"error": "No submitted attempt found"}), 404
    return jsonify(attempt.to_dict(include_answers=True)), 200
