"""
Faculty routes — /api/faculty/*
All endpoints require JWT with role='faculty'.

  GET  /dashboard/stats
  GET  /courses
  POST /courses
  PUT  /courses/<id>
  GET  /courses/<id>/students
  GET  /assignments
  POST /assignments
  GET  /assignments/<id>/submissions
  PUT  /submissions/<id>/grade
  GET  /resources
  POST /resources
  GET  /students
  POST /attendance
  PUT  /grades/bulk
  GET  /schedule
  GET  /profile
  PUT  /profile
"""
import os
from datetime import datetime, timezone, date as date_type

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.utils.decorators import faculty_required, get_current_user
from app.utils.validators import allowed_file
from app.models.course import Course, Enrollment, Semester, AcademicYear
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.resource import Resource
from app.models.attendance import Attendance
from app.models.task import Task
from app.models.notification import Notification
from app.services.dashboard_service import get_faculty_stats
from app.services.schedule_service import get_faculty_schedule
from app.services.gpa_service import (
    recalculate_student_gpa, recalculate_attendance_pct,
    numeric_score_to_letter, letter_to_points,
)

faculty_bp = Blueprint("faculty", __name__)


# ── POST /api/faculty/announcements ───────────────────────────────────────────
@faculty_bp.route("/announcements", methods=["POST"])
@faculty_required
def post_faculty_announcement():
    """Send an announcement notification to students of a specific course (or all courses).
    Body: { title, message, course_id ('all' or int), priority ('normal'|'urgent') }
    """
    data      = request.get_json(silent=True) or {}
    title     = (data.get("title") or "").strip()
    message   = (data.get("message") or "").strip()
    course_id = data.get("course_id", "all")
    priority  = (data.get("priority") or "normal").lower()

    if not title or not message:
        return jsonify({"error": "Title and message are required."}), 400
    if priority not in ("normal", "urgent"):
        priority = "normal"

    faculty = get_current_user()
    formatted_title = f"[URGENT] {title}" if priority == "urgent" else title

    # Resolve target courses
    if str(course_id).lower() == "all":
        courses = Course.query.filter_by(faculty_id=faculty.id, is_active=True).all()
    else:
        c = Course.query.filter_by(id=int(course_id), faculty_id=faculty.id).first()
        if not c:
            return jsonify({"error": "Course not found or not yours"}), 404
        courses = [c]

    # Collect unique student user IDs across target courses
    seen = set()
    recipients = []
    for course in courses:
        for enroll in course.enrollments.filter_by(status="active").all():
            if enroll.student_id not in seen:
                seen.add(enroll.student_id)
                recipients.append(enroll.student)

    course_label = "all your courses" if str(course_id).lower() == "all" else (courses[0].course_name if courses else "")
    notif_title  = f"[Announcement] {formatted_title}"
    sender_name  = faculty.full_name or faculty.user_id or "Faculty"
    course_name  = courses[0].course_name if len(courses) == 1 else "Multiple Courses"

    for student in recipients:
        Notification.create(
            user_id           = student.id,
            title             = notif_title,
            message           = message,
            notification_type = "announce_faculty",
            related_id        = faculty.id,
            related_type      = f"faculty:{sender_name}|{course_name}",
        )

    db.session.commit()
    return jsonify({
        "message":      f"Announcement sent to {len(recipients)} student(s) in {course_label}.",
        "recipients":   len(recipients),
        "course_label": course_label,
        "priority":     priority,
    }), 200


# ── GET /api/faculty/dashboard/stats ──────────────────────────────────────────
@faculty_bp.route("/dashboard/stats", methods=["GET"])
@faculty_required
def dashboard_stats():
    user = get_current_user()
    return jsonify(get_faculty_stats(user)), 200


# ── GET /api/faculty/semesters ────────────────────────────────────────────────
@faculty_bp.route("/semesters", methods=["GET"])
@faculty_required
def get_semesters():
    semesters = Semester.query.order_by(Semester.id.desc()).all()
    return jsonify([s.to_dict() for s in semesters]), 200


# ── DELETE /api/faculty/courses/<id> ──────────────────────────────────────────
@faculty_bp.route("/courses/<int:course_id>", methods=["DELETE"])
@faculty_required
def delete_course(course_id):
    user   = get_current_user()
    course = Course.query.filter_by(id=course_id, faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404
    course.is_active = False
    db.session.commit()
    return jsonify({"message": "Course archived"}), 200


# ── GET /api/faculty/courses ───────────────────────────────────────────────────
@faculty_bp.route("/courses", methods=["GET"])
@faculty_required
def get_courses():
    user    = get_current_user()
    courses = user.taught_courses.filter_by(is_active=True).all()
    return jsonify([c.to_dict() for c in courses]), 200


# ── POST /api/faculty/courses ─────────────────────────────────────────────────
@faculty_bp.route("/courses", methods=["POST"])
@faculty_required
def create_course():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    required = ("course_code", "course_name")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400

    if Course.query.filter_by(course_code=data["course_code"].strip().upper()).first():
        return jsonify({"error": "Course code already exists"}), 409

    course = Course(
        course_code   = data["course_code"].strip().upper(),
        course_name   = data["course_name"].strip(),
        description   = data.get("description", ""),
        credits       = int(data.get("credits", 3)),
        department    = data.get("department", user.department),
        semester_id   = data.get("semester_id"),
        max_students  = int(data.get("max_students", 50)),
        faculty_id    = user.id,
    )
    db.session.add(course)

    db.session.commit()
    return jsonify({"message": "Course created", "course_id": course.id, "course": course.to_dict()}), 201


# ── PUT /api/faculty/courses/<id> ─────────────────────────────────────────────
@faculty_bp.route("/courses/<int:course_id>", methods=["PUT"])
@faculty_required
def update_course(course_id):
    user   = get_current_user()
    course = Course.query.filter_by(id=course_id, faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    data = request.get_json(silent=True) or {}
    editable = ("course_name", "description", "credits", "department", "max_students", "semester_id")
    for field in editable:
        if field in data:
            setattr(course, field, data[field])

    db.session.commit()
    return jsonify({"message": "Course updated", "course": course.to_dict()}), 200


# ── GET /api/faculty/courses/<id>/students ────────────────────────────────────
@faculty_bp.route("/courses/<int:course_id>/students", methods=["GET"])
@faculty_required
def get_course_students(course_id):
    user   = get_current_user()
    course = Course.query.filter_by(id=course_id, faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    enrollments = course.enrollments.filter_by(status="active").all()

    # Batch-load attendance for this course in one query (avoids N+1 per student)
    all_att = Attendance.query.filter_by(course_id=course_id).all()
    att_totals: dict[int, dict] = {}
    for a in all_att:
        bucket = att_totals.setdefault(a.student_id, {"total": 0, "present": 0})
        bucket["total"] += 1
        if a.status in ("present", "late"):
            bucket["present"] += 1

    def _att_pct(sid: int) -> float:
        d = att_totals.get(sid, {})
        t = d.get("total", 0)
        return round(d.get("present", 0) / t * 100, 1) if t else 0.0

    result = []
    for enroll in enrollments:
        student     = enroll.student
        sp          = student.student_profile
        student_data = {
            "id":             student.id,
            "user_id":        student.user_id,
            "full_name":      student.full_name,
            "email":          student.email,
            "department":     student.department,
            "year":           sp.year if sp else None,
            "gpa":            round(sp.gpa, 2) if sp else 0.0,
            "grade":          enroll.grade,
            "attendance_pct": _att_pct(student.id),
            "enrollment_id":  enroll.id,
        }
        result.append(student_data)
    return jsonify(result), 200


# ── GET /api/faculty/assignments ──────────────────────────────────────────────
@faculty_bp.route("/assignments", methods=["GET"])
@faculty_required
def get_assignments():
    user = get_current_user()
    assignments = user.assignments_created.order_by(Assignment.due_date.desc()).all()
    return jsonify([a.to_dict() for a in assignments]), 200


# ── POST /api/faculty/assignments ─────────────────────────────────────────────
@faculty_bp.route("/assignments", methods=["POST"])
@faculty_required
def create_assignment():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    if not data.get("title"):
        return jsonify({"error": "'title' is required"}), 400
    if not data.get("course_id"):
        return jsonify({"error": "'course_id' is required"}), 400

    course = Course.query.filter_by(id=data["course_id"], faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid due_date format. Use ISO 8601."}), 400

    assignment = Assignment(
        title           = data["title"].strip(),
        description     = data.get("description", ""),
        course_id       = course.id,
        faculty_id      = user.id,
        due_date        = due_date,
        total_points    = int(data.get("total_points", 100)),
        assignment_type = data.get("assignment_type", "homework"),
        priority        = data.get("priority", "medium"),
    )
    db.session.add(assignment)
    # Flush so assignment.id is populated before we reference it in tasks
    db.session.flush()

    # Notify enrolled students + auto-create personal tasks
    enrolled_ids = [e.student_id for e in course.enrollments.filter_by(status="active").all()]
    for sid in enrolled_ids:
        Notification.create(
            user_id=sid,
            title=f"New assignment: {assignment.title}",
            message=(
                f"{course.course_name}: {assignment.title}. "
                f"Due: {due_date.strftime('%b %d, %Y') if due_date else 'No deadline'}. "
                f"Worth {assignment.total_points} points."
            ),
            notification_type="assignment",
            related_id=assignment.id,
            related_type="assignment",
        )
        # Only create a task if one doesn't already exist for this assignment+student
        existing_task = Task.query.filter_by(
            user_id=sid, assignment_id=assignment.id
        ).first()
        if not existing_task:
            task = Task(
                user_id       = sid,
                assignment_id = assignment.id,
                title         = assignment.title,
                description   = f"Complete assignment for {course.course_name}",
                due_date      = due_date,
                priority      = assignment.priority or "medium",
            )
            db.session.add(task)

    db.session.commit()
    return jsonify({"message": "Assignment created", "assignment_id": assignment.id}), 201


# ── GET /api/faculty/assignments/<id>/submissions ─────────────────────────────
@faculty_bp.route("/assignments/<int:assignment_id>/submissions", methods=["GET"])
@faculty_required
def get_submissions(assignment_id):
    user       = get_current_user()
    assignment = Assignment.query.filter_by(id=assignment_id, faculty_id=user.id).first()
    if not assignment:
        return jsonify({"error": "Assignment not found or not yours"}), 404

    submissions = assignment.submissions.all()
    return jsonify([s.to_dict(include_student=True) for s in submissions]), 200


# ── PUT /api/faculty/assignments/<id> ─────────────────────────────────────────
@faculty_bp.route("/assignments/<int:assignment_id>", methods=["PUT"])
@faculty_required
def update_assignment(assignment_id):
    user = get_current_user()
    assignment = Assignment.query.filter_by(id=assignment_id, faculty_id=user.id).first()
    if not assignment:
        return jsonify({"error": "Assignment not found or not yours"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data and data["title"]:
        assignment.title = data["title"].strip()
    if "description" in data:
        assignment.description = data["description"]
    if "assignment_type" in data:
        assignment.assignment_type = data["assignment_type"]
    if "total_points" in data:
        assignment.total_points = int(data["total_points"])
    if "due_date" in data:
        if data["due_date"]:
            try:
                assignment.due_date = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid due_date format"}), 400
        else:
            assignment.due_date = None
    if "status" in data:
        assignment.status = data["status"]
    if "priority" in data:
        assignment.priority = data["priority"]

    db.session.commit()
    return jsonify({"message": "Assignment updated", "assignment": assignment.to_dict()}), 200


# ── DELETE /api/faculty/assignments/<id> ──────────────────────────────────────
@faculty_bp.route("/assignments/<int:assignment_id>", methods=["DELETE"])
@faculty_required
def delete_assignment(assignment_id):
    user = get_current_user()
    assignment = Assignment.query.filter_by(id=assignment_id, faculty_id=user.id).first()
    if not assignment:
        return jsonify({"error": "Assignment not found or not yours"}), 404
    # Delete linked student tasks before removing the assignment
    Task.query.filter_by(assignment_id=assignment_id).delete(synchronize_session=False)
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({"message": "Assignment deleted"}), 200


# ── PUT /api/faculty/submissions/<id>/grade  (also: /grade/<id>) ────────────────
@faculty_bp.route("/submissions/<int:submission_id>/grade", methods=["PUT"])
@faculty_bp.route("/grade/<int:submission_id>",             methods=["PUT"])
@faculty_required
def grade_submission(submission_id):
    user       = get_current_user()
    submission = db.session.get(Submission, submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    # Verify this submission belongs to one of the faculty's assignments
    if submission.assignment.faculty_id != user.id:
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json(silent=True) or {}
    if "grade" not in data:
        return jsonify({"error": "'grade' is required"}), 400

    try:
        grade = float(data["grade"])
    except (ValueError, TypeError):
        return jsonify({"error": "Grade must be a number"}), 400

    if grade < 0 or grade > submission.assignment.total_points:
        return jsonify({
            "error": f"Grade must be between 0 and {submission.assignment.total_points}"
        }), 400

    submission.grade     = grade
    submission.feedback  = data.get("feedback", "")
    submission.status    = "graded"
    submission.graded_at = datetime.now(timezone.utc)

    # Convert numeric score → letter grade and persist to Enrollment
    letter = numeric_score_to_letter(grade, submission.assignment.total_points)
    enroll = Enrollment.query.filter_by(
        student_id=submission.student_id,
        course_id=submission.assignment.course_id,
        status="active",
    ).first()
    if enroll:
        enroll.grade        = letter
        enroll.grade_points = letter_to_points(letter)

    # Auto-complete the student's linked task (if any)
    linked_task = Task.query.filter_by(
        user_id=submission.student_id,
        assignment_id=submission.assignment_id,
    ).first()
    if linked_task:
        linked_task.is_completed = True

    # Notify student
    pct = round((grade / submission.assignment.total_points) * 100, 1) if submission.assignment.total_points else 0
    Notification.create(
        user_id=submission.student_id,
        title=f"Assignment graded: {submission.assignment.title}",
        message=(
            f"You scored {grade}/{submission.assignment.total_points} ({pct}%) — {letter}. "
            + (f"Feedback: {submission.feedback}" if submission.feedback else "")
        ),
        notification_type="grade",
        related_id=submission.assignment_id,
        related_type="assignment",
    )

    db.session.commit()

    # Recalculate GPA now that enrollment.grade is updated
    new_gpa = recalculate_student_gpa(submission.student_id)

    return jsonify({
        "message":     "Submission graded",
        "grade":        grade,
        "letter_grade": letter,
        "percentage":   pct,
        "new_gpa":      new_gpa,
    }), 200


# ── GET /api/faculty/resources ────────────────────────────────────────────────
@faculty_bp.route("/resources", methods=["GET"])
@faculty_required
def get_resources():
    user      = get_current_user()
    resources = user.uploaded_resources.order_by(Resource.uploaded_at.desc()).all()
    return jsonify([r.to_dict() for r in resources]), 200


# ── POST /api/faculty/resources ───────────────────────────────────────────────
@faculty_bp.route("/resources", methods=["POST"])
@faculty_required
def upload_resource():
    user = get_current_user()

    title     = request.form.get("title", "").strip()
    course_id = request.form.get("course_id")
    if not title:
        return jsonify({"error": "'title' is required"}), 400
    if not course_id:
        return jsonify({"error": "'course_id' is required"}), 400

    course = Course.query.filter_by(id=int(course_id), faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    resource_type = request.form.get("resource_type", "document")
    file_path = original_filename = file_size = None
    external_url = request.form.get("external_url", "")

    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed"}), 400
            filename          = secure_filename(f"res_{course_id}_{user.id}_{file.filename}")
            save_path         = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            file_path         = filename
            original_filename = file.filename
            file_size         = os.path.getsize(save_path)

    resource = Resource(
        title             = title,
        description       = request.form.get("description", ""),
        course_id         = course.id,
        faculty_id        = user.id,
        file_path         = file_path,
        original_filename = original_filename,
        resource_type     = resource_type,
        file_size         = file_size,
        external_url      = external_url or None,
    )
    db.session.add(resource)
    db.session.flush()   # get resource.id before commit

    # Notify all enrolled students in this course
    enrolled = Enrollment.query.filter_by(course_id=course.id, status="active").all()
    for enroll in enrolled:
        notif = Notification(
            user_id = enroll.student_id,
            title   = "New Resource Available",
            message = f'{user.full_name} uploaded "{title}" in {course.course_name}.',
            notification_type = "resource",
        )
        db.session.add(notif)

    db.session.commit()
    return jsonify({"message": "Resource uploaded", "resource_id": resource.id}), 201


# ── POST /api/faculty/resources/bulk-share ────────────────────────────────────
@faculty_bp.route("/resources/bulk-share", methods=["POST"])
@faculty_required
def bulk_share_resources():
    """Share one or more existing resources with additional courses by
    creating Notification records for every enrolled student in the
    target courses.

    Expected JSON body:
    {
        "resource_ids": [1, 2, 3],
        "course_ids":   [4, 5],
        "message":      "Check out these resources!"   (optional)
    }
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    resource_ids = data.get("resource_ids", [])
    target_course_ids = data.get("course_ids", [])
    message = data.get("message", "").strip()

    if not resource_ids:
        return jsonify({"error": "'resource_ids' is required"}), 400
    if not target_course_ids:
        return jsonify({"error": "'course_ids' is required"}), 400

    # Verify resources belong to the requesting faculty
    resources = Resource.query.filter(
        Resource.id.in_(resource_ids),
        Resource.faculty_id == user.id,
    ).all()
    if not resources:
        return jsonify({"error": "No valid resources found"}), 404

    # Verify courses belong to the requesting faculty
    courses = Course.query.filter(
        Course.id.in_(target_course_ids),
        Course.faculty_id == user.id,
    ).all()
    if not courses:
        return jsonify({"error": "No valid courses found"}), 404

    # Create notifications for every enrolled student in target courses
    notifications_created = 0
    for course in courses:
        enrollments = Enrollment.query.filter_by(
            course_id=course.id, status="active"
        ).all()
        for enrollment in enrollments:
            for resource in resources:
                body = f'{user.full_name} shared "{resource.title}" in {course.course_name}.'
                if message:
                    body += f" {message}"
                notif = Notification(
                    user_id=enrollment.student_id,
                    title="New Resource Shared",
                    message=body,
                    notification_type="resource",
                )
                db.session.add(notif)
                notifications_created += 1

    db.session.commit()

    return jsonify({
        "message": f"{len(resources)} resource(s) shared with {len(courses)} course(s)",
        "notifications_sent": notifications_created,
    }), 200


# ── DELETE /api/faculty/resources/<id> ───────────────────────────────────────
@faculty_bp.route("/resources/<int:resource_id>", methods=["DELETE"])
@faculty_required
def delete_resource(resource_id):
    user     = get_current_user()
    resource = Resource.query.filter_by(id=resource_id, faculty_id=user.id).first()
    if not resource:
        return jsonify({"error": "Resource not found or not yours"}), 404
    # Remove file from disk if present
    if resource.file_path:
        try:
            fp = os.path.join(current_app.config["UPLOAD_FOLDER"], resource.file_path)
            if os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass
    db.session.delete(resource)
    db.session.commit()
    return jsonify({"message": "Resource deleted"}), 200


# ── GET /api/faculty/students ─────────────────────────────────────────────────
@faculty_bp.route("/students", methods=["GET"])
@faculty_required
def get_all_students():
    user      = get_current_user()
    course_ids = [c.id for c in user.taught_courses.filter_by(is_active=True).all()]
    if not course_ids:
        return jsonify([]), 200

    enrollments = (
        Enrollment.query
        .filter(Enrollment.course_id.in_(course_ids))
        .filter_by(status="active")
        .all()
    )

    seen = set()
    result = []
    for enroll in enrollments:
        key = (enroll.student_id, enroll.course_id)
        if key in seen:
            continue
        seen.add(key)
        student = enroll.student
        sp      = student.student_profile
        result.append({
            "id":            student.id,
            "user_id":       student.user_id,
            "full_name":     student.full_name,
            "email":         student.email,
            "course_name":   enroll.course.course_name,
            "course_code":   enroll.course.course_code,
            "course_id":     enroll.course.id,
            "grade":         enroll.grade,
            "gpa":           round(sp.gpa, 2) if sp else 0.0,
            "attendance_pct": round(sp.attendance_pct, 1) if sp else 0.0,
        })
    return jsonify(result), 200


# ── POST /api/faculty/attendance ──────────────────────────────────────────────
@faculty_bp.route("/attendance", methods=["POST"])
@faculty_required
def record_attendance():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    course_id     = data.get("course_id")
    date_str      = data.get("date")
    attendance_list = data.get("attendance", [])

    if not course_id:
        return jsonify({"error": "'course_id' is required"}), 400
    if not date_str:
        return jsonify({"error": "'date' is required"}), 400

    course = Course.query.filter_by(id=course_id, faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    try:
        att_date = date_type.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    updated_student_ids = set()
    for entry in attendance_list:
        sid    = entry.get("student_id")
        status = entry.get("status", "present")

        if not sid:
            continue

        # Upsert
        record = Attendance.query.filter_by(
            student_id=sid, course_id=course_id, date=att_date
        ).first()
        if record:
            record.status      = status
            record.recorded_by = user.id
        else:
            record = Attendance(
                student_id=sid,
                course_id=course_id,
                date=att_date,
                status=status,
                recorded_by=user.id,
            )
            db.session.add(record)
        updated_student_ids.add(sid)

    db.session.commit()

    # Update attendance percentage for each affected student
    for sid in updated_student_ids:
        recalculate_attendance_pct(sid)

    return jsonify({
        "message": f"Attendance recorded for {len(updated_student_ids)} students"
    }), 200


# ── PUT /api/faculty/grades/bulk ──────────────────────────────────────────────
@faculty_bp.route("/grades/bulk", methods=["PUT"])
@faculty_required
def bulk_update_grades():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    course_id   = data.get("course_id")
    grades_list = data.get("grades", [])

    if not course_id:
        return jsonify({"error": "'course_id' is required"}), 400

    course = Course.query.filter_by(id=course_id, faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    updated = 0
    student_ids = []
    for item in grades_list:
        sid   = item.get("student_id")
        grade = item.get("grade")
        if not sid or grade is None:
            continue

        enroll = Enrollment.query.filter_by(
            course_id=course_id, student_id=sid, status="active"
        ).first()
        if enroll:
            from app.models.user import User as UserModel
            student = UserModel.query.filter_by(user_id=str(sid)).first()
            if not student:
                student = UserModel.query.get(sid)
            if student:
                enroll.grade = str(grade).strip().upper()
                student_ids.append(student.id)
                updated += 1

    db.session.commit()

    # Recalculate GPA for updated students
    for sid in set(student_ids):
        recalculate_student_gpa(sid)

    return jsonify({"message": f"Grades updated for {updated} students"}), 200


# ── GET /api/faculty/schedule ─────────────────────────────────────────────────
@faculty_bp.route("/schedule", methods=["GET"])
@faculty_required
def get_schedule():
    user = get_current_user()
    return jsonify(get_faculty_schedule(user.id)), 200


# ── POST /api/faculty/schedule/sessions ────────────────────────────────────────
@faculty_bp.route("/schedule/sessions", methods=["POST"])
@faculty_required
def create_session():
    """
    Create a new course timetable session (CourseSession).
    Body: {
        course_id, day_of_week, start_time, end_time,
        room (opt), session_type (opt: lecture|lab|tutorial)
    }
    Faculty can only add sessions for courses they teach.
    """
    from app.models.schedule import CourseSession
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    required = ("course_id", "day_of_week", "start_time", "end_time")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400

    course = Course.query.filter_by(id=int(data["course_id"]), faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    valid_days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
    if data["day_of_week"] not in valid_days:
        return jsonify({"error": f"'day_of_week' must be one of: {', '.join(valid_days)}"}), 400

    session = CourseSession(
        course_id    = course.id,
        day_of_week  = data["day_of_week"],
        start_time   = data["start_time"],
        end_time     = data["end_time"],
        room         = data.get("room", "").strip(),
        session_type = data.get("session_type", "lecture"),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({"message": "Session created", "session": session.to_dict()}), 201


# ── DELETE /api/faculty/schedule/sessions/<id> ──────────────────────────────────
@faculty_bp.route("/schedule/sessions/<int:session_id>", methods=["DELETE"])
@faculty_required
def delete_session(session_id):
    """Delete a course timetable session (faculty can only delete their own)."""
    from app.models.schedule import CourseSession
    user    = get_current_user()
    session = db.session.get(CourseSession, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Ownership check — the session must belong to a course taught by this faculty
    if session.course.faculty_id != user.id:
        return jsonify({"error": "Permission denied"}), 403

    db.session.delete(session)
    db.session.commit()
    return jsonify({"message": "Session deleted"}), 200


# ── GET /api/faculty/profile ──────────────────────────────────────────────────
@faculty_bp.route("/profile", methods=["GET"])
@faculty_required
def get_profile():
    user = get_current_user()
    return jsonify(user.to_dict(include_profile=True)), 200


# ── PUT /api/faculty/profile ──────────────────────────────────────────────────
@faculty_bp.route("/profile", methods=["PUT"])
@faculty_required
def update_profile():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    for field in ("full_name", "phone", "department"):
        if field in data:
            setattr(user, field, str(data[field]).strip())

    if "email" in data:
        from app.models.user import User as UserModel
        conflict = UserModel.query.filter(
            UserModel.email == data["email"].strip().lower(),
            UserModel.id    != user.id,
        ).first()
        if conflict:
            return jsonify({"error": "Email already in use"}), 409
        user.email = data["email"].strip().lower()

    if user.faculty_profile:
        fp = user.faculty_profile
        for field in ("specialization", "office_location"):
            if field in data:
                setattr(fp, field, data[field])

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict(include_profile=True)}), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  ONLINE QUIZ ROUTES
#  Faculty have full CRUD over quizzes + questions + options they create.
# ═══════════════════════════════════════════════════════════════════════════════
from app.models.quiz import Quiz, QuizQuestion, QuizOption, QuizAttempt  # noqa: E402


# ── GET /api/faculty/quizzes ──────────────────────────────────────────────────
@faculty_bp.route("/quizzes", methods=["GET"])
@faculty_required
def get_faculty_quizzes():
    user = get_current_user()
    quizzes = user.quizzes_created.order_by(Quiz.created_at.desc()).all()
    return jsonify([q.to_dict() for q in quizzes]), 200


# ── POST /api/faculty/quizzes ─────────────────────────────────────────────────
@faculty_bp.route("/quizzes", methods=["POST"])
@faculty_required
def create_quiz():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    if not data.get("title"):
        return jsonify({"error": "'title' is required"}), 400
    if not data.get("course_id"):
        return jsonify({"error": "'course_id' is required"}), 400

    course = Course.query.filter_by(id=int(data["course_id"]), faculty_id=user.id).first()
    if not course:
        return jsonify({"error": "Course not found or not yours"}), 404

    due_date = None
    if data.get("due_date"):
        try:
            raw = data["due_date"].replace("Z", "+00:00")
            # Append seconds if datetime-local omitted them ("YYYY-MM-DDTHH:MM")
            if len(raw) == 16:
                raw += ":00"
            due_date = datetime.fromisoformat(raw)
        except ValueError:
            return jsonify({"error": "Invalid due_date format (ISO 8601)"}), 400

    scheduled_publish_at = None
    if data.get("scheduled_publish_at"):
        try:
            raw = data["scheduled_publish_at"].replace("Z", "+00:00")
            if len(raw) == 16:
                raw += ":00"
            scheduled_publish_at = datetime.fromisoformat(raw)
        except ValueError:
            return jsonify({"error": "Invalid scheduled_publish_at format (ISO 8601)"}), 400

    quiz = Quiz(
        title                = data["title"].strip(),
        description          = data.get("description", "").strip(),
        course_id            = course.id,
        faculty_id           = user.id,
        time_limit_minutes   = data.get("time_limit_minutes") or None,
        max_attempts         = int(data.get("max_attempts", 1)),
        pass_score           = float(data.get("pass_score", 60.0)),
        show_answers_after   = bool(data.get("show_answers_after", True)),
        is_published         = bool(data.get("is_published", False)),
        due_date             = due_date,
        scheduled_publish_at = scheduled_publish_at,
    )
    db.session.add(quiz)
    db.session.commit()
    return jsonify({"message": "Quiz created", "quiz_id": quiz.id, "is_published": quiz.is_published, "scheduled_publish_at": quiz.scheduled_publish_at.isoformat() if quiz.scheduled_publish_at else None}), 201


# ── GET /api/faculty/quizzes/<id> ──────────────────────────────────────────────
@faculty_bp.route("/quizzes/<int:quiz_id>", methods=["GET"])
@faculty_required
def get_faculty_quiz(quiz_id):
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, faculty_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or not yours"}), 404
    return jsonify(quiz.to_dict(include_questions=True)), 200


# ── PUT /api/faculty/quizzes/<id> ─────────────────────────────────────────────
@faculty_bp.route("/quizzes/<int:quiz_id>", methods=["PUT"])
@faculty_required
def update_quiz(quiz_id):
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, faculty_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or not yours"}), 404

    data = request.get_json(silent=True) or {}

    # Snapshot the current published state BEFORE any changes
    was_published = quiz.is_published

    for field in ("title", "description"):
        if field in data:
            setattr(quiz, field, data[field].strip())
    for field in ("time_limit_minutes", "max_attempts", "pass_score",
                  "show_answers_after", "is_published"):
        if field in data:
            setattr(quiz, field, data[field])
    if "due_date" in data:
        if data["due_date"]:
            try:
                raw = data["due_date"].replace("Z", "+00:00")
                if len(raw) == 16:
                    raw += ":00"
                quiz.due_date = datetime.fromisoformat(raw)
            except ValueError:
                return jsonify({"error": "Invalid due_date format"}), 400
        else:
            quiz.due_date = None
    if "scheduled_publish_at" in data:
        if data["scheduled_publish_at"]:
            try:
                raw = data["scheduled_publish_at"].replace("Z", "+00:00")
                if len(raw) == 16:
                    raw += ":00"
                quiz.scheduled_publish_at = datetime.fromisoformat(raw)
            except ValueError:
                return jsonify({"error": "Invalid scheduled_publish_at format"}), 400
        else:
            quiz.scheduled_publish_at = None

    # ── Commit the quiz changes FIRST so publish is always saved ────────────
    db.session.commit()

    # ── Notify enrolled students only when transitioning draft → published ───
    if data.get("is_published") is True and not was_published:
        try:
            enrolled_ids = [e.student_id for e in
                            quiz.course.enrollments.filter_by(status="active").all()]
            for sid in enrolled_ids:
                Notification.create(
                    user_id=sid,
                    title=f"New Quiz: {quiz.title}",
                    message=(
                        f"{quiz.course.course_name}: A new online quiz '{quiz.title}' is now available. "
                        + (f"Due: {quiz.due_date.strftime('%b %d, %Y')}" if quiz.due_date else "")
                    ),
                    notification_type="assignment",
                    related_id=quiz.id,
                    related_type="quiz",
                )
            db.session.commit()  # save notifications
        except Exception:         # notification failure must not block the response
            db.session.rollback()

    return jsonify({"message": "Quiz updated", "quiz": quiz.to_dict(include_questions=True)}), 200


# ── DELETE /api/faculty/quizzes/<id> ──────────────────────────────────────────
@faculty_bp.route("/quizzes/<int:quiz_id>", methods=["DELETE"])
@faculty_required
def delete_quiz(quiz_id):
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, faculty_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or not yours"}), 404
    db.session.delete(quiz)
    db.session.commit()
    return jsonify({"message": "Quiz deleted"}), 200


# ── POST /api/faculty/quizzes/<id>/questions ──────────────────────────────────
@faculty_bp.route("/quizzes/<int:quiz_id>/questions", methods=["POST"])
@faculty_required
def add_question(quiz_id):
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, faculty_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or not yours"}), 404

    data = request.get_json(silent=True) or {}
    if not data.get("question_text"):
        return jsonify({"error": "'question_text' is required"}), 400

    options_data = data.get("options", [])
    if len(options_data) < 2:
        return jsonify({"error": "At least 2 options are required"}), 400
    if not any(o.get("is_correct") for o in options_data):
        return jsonify({"error": "At least one option must be marked correct"}), 400

    # Determine order_index
    max_order = max((q.order_index for q in quiz.questions), default=-1)

    question = QuizQuestion(
        quiz_id       = quiz.id,
        question_text = data["question_text"].strip(),
        question_type = data.get("question_type", "mcq"),
        points        = int(data.get("points", 1)),
        order_index   = max_order + 1,
        explanation   = data.get("explanation", "").strip(),
    )
    db.session.add(question)
    db.session.flush()

    for i, opt in enumerate(options_data):
        option = QuizOption(
            question_id = question.id,
            option_text = str(opt.get("option_text", "")).strip(),
            is_correct  = bool(opt.get("is_correct", False)),
            order_index = i,
        )
        db.session.add(option)

    db.session.commit()
    return jsonify({"message": "Question added", "question": question.to_dict()}), 201


# ── PUT /api/faculty/questions/<id> ───────────────────────────────────────────
@faculty_bp.route("/questions/<int:question_id>", methods=["PUT"])
@faculty_required
def update_question(question_id):
    user     = get_current_user()
    question = QuizQuestion.query.get(question_id)
    if not question or question.quiz.faculty_id != user.id:
        return jsonify({"error": "Question not found or permission denied"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("question_text", "explanation"):
        if field in data:
            setattr(question, field, data[field].strip())
    for field in ("question_type", "points", "order_index"):
        if field in data:
            setattr(question, field, data[field])

    # Replace options if provided
    if "options" in data:
        options_data = data["options"]
        if len(options_data) < 2:
            return jsonify({"error": "At least 2 options are required"}), 400
        if not any(o.get("is_correct") for o in options_data):
            return jsonify({"error": "At least one option must be marked correct"}), 400
        # Delete old options
        for opt in question.options:
            db.session.delete(opt)
        db.session.flush()
        for i, opt in enumerate(options_data):
            db.session.add(QuizOption(
                question_id = question.id,
                option_text = str(opt.get("option_text", "")).strip(),
                is_correct  = bool(opt.get("is_correct", False)),
                order_index = i,
            ))

    db.session.commit()
    return jsonify({"message": "Question updated", "question": question.to_dict()}), 200


# ── DELETE /api/faculty/questions/<id> ────────────────────────────────────────
@faculty_bp.route("/questions/<int:question_id>", methods=["DELETE"])
@faculty_required
def delete_question(question_id):
    user     = get_current_user()
    question = QuizQuestion.query.get(question_id)
    if not question or question.quiz.faculty_id != user.id:
        return jsonify({"error": "Question not found or permission denied"}), 404
    db.session.delete(question)
    db.session.commit()
    return jsonify({"message": "Question deleted"}), 200


# ── GET /api/faculty/quizzes/<id>/attempts ────────────────────────────────────
@faculty_bp.route("/quizzes/<int:quiz_id>/attempts", methods=["GET"])
@faculty_required
def get_quiz_attempts(quiz_id):
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, faculty_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or not yours"}), 404
    attempts = quiz.attempts.filter_by(status="submitted").all()
    return jsonify({
        "quiz":     quiz.to_dict(),
        "attempts": [a.to_dict(include_answers=True) for a in attempts],
    }), 200
