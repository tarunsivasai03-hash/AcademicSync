"""
Admin routes — /api/admin/*
All endpoints require JWT with role='admin'.

  GET    /dashboard/stats
  GET    /users
  POST   /users                  — create any user (role in body)
  PUT    /users/<id>
  DELETE /users/<id>
  POST   /users/<id>/reset-password — admin force-reset a user's password

  POST   /create-student         — shorthand; role forced to 'student'
  POST   /create-faculty         — shorthand; role forced to 'faculty'
  POST   /create-course          — create course (admin can assign any faculty)
  POST   /create-department      — shorthand alias for /departments

  GET    /courses
  PUT    /courses/<id>/assign-faculty
  GET    /departments
  POST   /departments
  GET    /settings
  PUT    /settings
  GET    /analytics/enrollment-trends
  GET    /analytics/grade-distribution
  GET    /audit-logs
"""
from datetime import datetime, timezone
from collections import defaultdict

from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.extensions import db
from app.utils.decorators import admin_required, get_current_user
from app.utils.id_generator import generate_user_id
from app.models.user import (
    User, StudentProfile, FacultyProfile, AdminProfile,
    Department, AuditLog, SystemSetting,
)
from app.models.course import AcademicYear, Semester, Course, Enrollment
from app.models.notification import Notification
from app.services.dashboard_service import get_admin_stats

admin_bp = Blueprint("admin", __name__)


# ── GET /api/admin/dashboard/stats ────────────────────────────────────────────
@admin_bp.route("/dashboard/stats", methods=["GET"])
@admin_required
def dashboard_stats():
    return jsonify(get_admin_stats()), 200


# ── GET /api/admin/users ──────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    role    = request.args.get("role", "").strip().lower()
    search  = request.args.get("search", "").strip()
    limit   = min(int(request.args.get("limit",  100)), 500)
    offset  = int(request.args.get("offset", 0))

    query = User.query
    if role:
        query = query.filter_by(role=role)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.user_id.ilike(pattern),
            )
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "users":  [u.to_dict(include_profile=True) for u in users],
    }), 200

# ── GET /api/admin/users/<id> ──────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict(include_profile=True)}), 200

# ── POST /api/admin/users ─────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    import secrets, string
    admin = get_current_user()
    data  = request.get_json(silent=True) or {}

    required = ("full_name", "email", "role")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400

    if User.query.filter_by(email=data["email"].strip().lower()).first():
        return jsonify({"error": "Email already registered"}), 409

    role   = data["role"].lower()
    uid    = data.get("user_id", "").strip() or generate_user_id(role)

    if User.query.filter_by(user_id=uid).first():
        return jsonify({"error": f"User ID '{uid}' already taken"}), 409

    # Auto-generate a password if none was provided
    alphabet = string.ascii_letters + string.digits
    temp_password = data.get("password") or ''.join(secrets.choice(alphabet) for _ in range(12))

    user = User(
        user_id       = uid,
        full_name     = data["full_name"].strip(),
        email         = data["email"].strip().lower(),
        role          = role,
        department    = data.get("department", ""),
        department_id = data.get("department_id"),
        phone         = data.get("phone", ""),
    )
    user.set_password(temp_password)
    db.session.add(user)
    db.session.flush()

    if role == "student":
        db.session.add(StudentProfile(user_id=user.id, year=int(data.get("year", 1))))
    elif role == "faculty":
        db.session.add(FacultyProfile(user_id=user.id))

    AuditLog.log("admin_create_user", user=admin,
                 details=f"Created {role} {uid}", ip=request.remote_addr)
    db.session.commit()

    resp = {"message": "User created", "user_id": uid, "user": user.to_dict(include_profile=True)}
    if not data.get("password"):
        resp["password"] = temp_password   # Only reveal auto-generated passwords
    return jsonify(resp), 201


# ── POST /api/admin/create-student ──────────────────────────────────────────────────────
@admin_bp.route("/create-student", methods=["POST"])
@admin_required
def create_student():
    """Convenience endpoint — forces role='student' so the caller doesn't need to set it."""
    from flask import g
    data = request.get_json(silent=True) or {}
    data["role"] = "student"   # always override
    # Delegate to create_user logic inline
    return _create_user_with_role(data, "student")


# ── POST /api/admin/create-faculty ─────────────────────────────────────────────────────
@admin_bp.route("/create-faculty", methods=["POST"])
@admin_required
def create_faculty():
    """Convenience endpoint — forces role='faculty'."""
    data = request.get_json(silent=True) or {}
    return _create_user_with_role(data, "faculty")


def _create_user_with_role(data: dict, forced_role: str):
    """Shared helper for create-student / create-faculty / create_user."""
    import secrets, string
    admin = get_current_user()

    required = ("full_name", "email")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    uid = data.get("user_id", "").strip() or generate_user_id(forced_role)
    if User.query.filter_by(user_id=uid).first():
        return jsonify({"error": f"User ID '{uid}' already taken"}), 409

    # Auto-generate if not provided
    alphabet = string.ascii_letters + string.digits
    temp_password = data.get("password") or ''.join(secrets.choice(alphabet) for _ in range(12))

    user = User(
        user_id    = uid,
        full_name  = data["full_name"].strip(),
        email      = email,
        role       = forced_role,
        department = data.get("department", ""),
        department_id = data.get("department_id"),
        phone      = data.get("phone", ""),
    )
    user.set_password(temp_password)
    db.session.add(user)
    db.session.flush()

    if forced_role == "student":
        db.session.add(StudentProfile(
            user_id = user.id,
            year    = int(data.get("year", 1)),
        ))
    elif forced_role == "faculty":
        db.session.add(FacultyProfile(
            user_id        = user.id,
            specialization = data.get("specialization", ""),
            office_location= data.get("office_location", ""),
        ))

    AuditLog.log("admin_create_user", user=admin,
                 details=f"Created {forced_role} {uid} via /create-{forced_role}",
                 ip=request.remote_addr)
    db.session.commit()
    resp = {"message": f"{forced_role.title()} created",
            "user_id": uid, "user": user.to_dict(include_profile=True)}
    if not data.get("password"):
        resp["password"] = temp_password
    return jsonify(resp), 201


# ── POST /api/admin/create-course ──────────────────────────────────────────────────────
@admin_bp.route("/create-course", methods=["POST"])
@admin_required
def create_course():
    """
    Create a new course. Admins can assign any faculty member.
    Body: course_code, course_name, faculty_user_id (optional), department,
          semester_id, credits, max_students, description
    """
    admin = get_current_user()
    data  = request.get_json(silent=True) or {}

    for f in ("course_code", "course_name"):
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400

    code = data["course_code"].strip().upper()
    if Course.query.filter_by(course_code=code).first():
        return jsonify({"error": "Course code already exists"}), 409

    faculty_id = None
    if data.get("faculty_user_id"):
        faculty = User.query.filter_by(
            user_id=data["faculty_user_id"], role="faculty"
        ).first()
        if not faculty:
            return jsonify({"error": "Faculty member not found"}), 404
        faculty_id = faculty.id

    course = Course(
        course_code   = code,
        course_name   = data["course_name"].strip(),
        description   = data.get("description", ""),
        credits       = int(data.get("credits", 3)),
        department    = data.get("department", ""),
        department_id = data.get("department_id"),
        semester_id   = data.get("semester_id"),
        faculty_id    = faculty_id,
        max_students  = int(data.get("max_students", 50)),
    )
    db.session.add(course)

    AuditLog.log("admin_create_course", user=admin,
                 details=f"Created course {code}", ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": "Course created", "course": course.to_dict()}), 201


# ── POST /api/admin/create-department ──────────────────────────────────────────────
@admin_bp.route("/create-department", methods=["POST"])
@admin_required
def create_department_alias():
    """Alias for POST /departments — same behaviour, explicit name."""
    admin = get_current_user()
    data  = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    code = data.get("code", "").strip().upper()
    if not name:
        return jsonify({"error": "'name' is required"}), 400
    if not code:
        code = "".join(w[0] for w in name.split()).upper()[:6]

    if Department.query.filter_by(name=name).first():
        return jsonify({"error": "Department already exists"}), 409

    dept = Department(name=name, code=code, description=data.get("description", ""))
    db.session.add(dept)
    db.session.commit()
    return jsonify({"message": "Department created", "department": dept.to_dict()}), 201


# ── PUT /api/admin/users/<id> ─────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    admin  = get_current_user()
    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    data   = request.get_json(silent=True) or {}

    # Note: 'role' is intentionally excluded — use a dedicated role-change endpoint
    editable = ("full_name", "email", "department", "phone", "is_active")
    for field in editable:
        if field in data:
            setattr(target, field, data[field])

    if "password" in data and data["password"]:
        target.set_password(data["password"])

    AuditLog.log("admin_update_user", user=admin,
                 details=f"Updated user {target.user_id}", ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": "User updated", "user": target.to_dict()}), 200


# ── DELETE /api/admin/users/<id> ──────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    admin  = get_current_user()
    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    if target.id == admin.id:
        return jsonify({"error": "You cannot delete your own account"}), 400

    # Soft-delete: deactivate instead of hard delete to preserve history
    target.is_active = False
    AuditLog.log("admin_deactivate_user", user=admin,
                 details=f"Deactivated {target.user_id}", ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": f"User {target.user_id} deactivated"}), 200


# ── POST /api/admin/users/<id>/reset-password ─────────────────────────────────
@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_user_password(user_id):
    """
    Admin reset a user's password.
    Body: { "new_password": "<string>" }  (min 6 characters)
    """
    admin  = get_current_user()
    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    import secrets, string
    data         = request.get_json(silent=True) or {}
    new_password = data.get("new_password", "").strip()

    # Auto-generate a secure password if none was supplied
    if not new_password:
        alphabet     = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    elif len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    target.set_password(new_password)
    AuditLog.log("admin_reset_password", user=admin,
                 details=f"Reset password for {target.user_id}",
                 ip=request.remote_addr)
    db.session.commit()
    return jsonify({
        "message":      f"Password reset successfully for {target.user_id}",
        "new_password": new_password,
    }), 200


# ── GET /api/admin/semesters ────────────────────────────────────────────────
@admin_bp.route("/semesters", methods=["GET"])
@admin_required
def list_semesters():
    semesters = Semester.query.order_by(Semester.start_date.desc()).all()
    return jsonify([s.to_dict() for s in semesters]), 200


# ── GET /api/admin/academic-years ────────────────────────────────────────────
@admin_bp.route("/academic-years", methods=["GET"])
@admin_required
def list_academic_years():
    years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    return jsonify([y.to_dict() for y in years]), 200


# ── GET /api/admin/courses ────────────────────────────────────────────────────
@admin_bp.route("/courses", methods=["GET"])
@admin_required
def list_courses():
    department      = request.args.get("department", "").strip()
    faculty_id      = request.args.get("faculty_id", "").strip()
    semester_id     = request.args.get("semester_id", "").strip()
    academic_year_id = request.args.get("academic_year_id", "").strip()
    search          = request.args.get("search", "").strip()

    query = Course.query
    if department:
        query = query.filter(Course.department.ilike(f"%{department}%"))
    if faculty_id:
        fac = User.query.filter_by(user_id=faculty_id, role="faculty").first()
        if fac:
            query = query.filter_by(faculty_id=fac.id)
    if semester_id and semester_id.isdigit():
        query = query.filter_by(semester_id=int(semester_id))
    if academic_year_id and academic_year_id.isdigit():
        query = query.join(Semester).filter(Semester.academic_year_id == int(academic_year_id))
    if search:
        query = query.filter(
            Course.course_name.ilike(f"%{search}%") |
            Course.course_code.ilike(f"%{search}%")
        )

    courses = query.order_by(Course.course_code).all()
    return jsonify([c.to_dict() for c in courses]), 200


# ── POST /api/admin/courses ───────────────────────────────────────────────────
@admin_bp.route("/courses", methods=["POST"])
@admin_required
def create_course_admin():
    admin = get_current_user()
    data  = request.get_json(silent=True) or {}

    code = (data.get("course_code") or "").strip().upper()
    name = (data.get("course_name") or "").strip()
    if not code or not name:
        return jsonify({"error": "'course_code' and 'course_name' are required"}), 400

    if Course.query.filter_by(course_code=code).first():
        return jsonify({"error": f"Course code '{code}' already exists"}), 409

    semester_id  = data.get("semester_id")
    department_id = data.get("department_id")
    faculty_uid  = (data.get("faculty_id") or "").strip()
    faculty      = User.query.filter_by(user_id=faculty_uid, role="faculty").first() if faculty_uid else None
    dept         = db.session.get(Department, int(department_id)) if department_id else None

    course = Course(
        course_code   = code,
        course_name   = name,
        credits       = int(data.get("credits", 3)),
        description   = data.get("description", ""),
        semester_id   = int(semester_id) if semester_id else None,
        department_id = dept.id if dept else None,
        department    = dept.name if dept else data.get("department", ""),
        faculty_id    = faculty.id if faculty else None,
        max_students  = int(data.get("max_students", 50)),
    )
    db.session.add(course)

    AuditLog.log("create_course", user=admin,
                 details=f"Created course {code}", ip=request.remote_addr)
    db.session.commit()
    return jsonify(course.to_dict()), 201


# ── PUT /api/admin/courses/<id> ───────────────────────────────────────────────
@admin_bp.route("/courses/<int:course_id>", methods=["PUT"])
@admin_required
def update_course_admin(course_id):
    admin  = get_current_user()
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    data = request.get_json(silent=True) or {}
    if "course_name"  in data: course.course_name  = data["course_name"]
    if "credits"      in data: course.credits       = int(data["credits"])
    if "description"  in data: course.description   = data["description"]
    if "max_students" in data: course.max_students  = int(data["max_students"])
    if "is_active"    in data: course.is_active      = bool(data["is_active"])
    if "semester_id"  in data: course.semester_id    = int(data["semester_id"]) if data["semester_id"] else None

    dept_id = data.get("department_id")
    if dept_id:
        dept = db.session.get(Department, int(dept_id))
        if dept:
            course.department_id = dept.id
            course.department    = dept.name

    fac_uid = (data.get("faculty_id") or "").strip()
    if fac_uid:
        fac = User.query.filter_by(user_id=fac_uid, role="faculty").first()
        if fac:
            course.faculty_id = fac.id

    AuditLog.log("update_course", user=admin,
                 details=f"Updated course {course.course_code}", ip=request.remote_addr)
    db.session.commit()
    return jsonify(course.to_dict()), 200


# ── DELETE /api/admin/courses/<id> ────────────────────────────────────────────
@admin_bp.route("/courses/<int:course_id>", methods=["DELETE"])
@admin_required
def delete_course_admin(course_id):
    admin  = get_current_user()
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    code = course.course_code
    course.is_active = False
    AuditLog.log("archive_course", user=admin,
                 details=f"Archived course {code}", ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": f"Course {code} archived"}), 200


# ── PUT /api/admin/courses/<id>/assign-faculty ────────────────────────────────
@admin_bp.route("/courses/<int:course_id>/assign-faculty", methods=["PUT"])
@admin_required
def assign_faculty(course_id):
    admin  = get_current_user()
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    data   = request.get_json(silent=True) or {}

    faculty_id_str = data.get("faculty_id", "")
    if not faculty_id_str:
        return jsonify({"error": "'faculty_id' is required"}), 400

    faculty = User.query.filter_by(user_id=str(faculty_id_str), role="faculty").first()
    if not faculty:
        # Try by numeric PK
        faculty = User.query.filter_by(id=int(faculty_id_str) if str(faculty_id_str).isdigit() else -1, role="faculty").first()
    if not faculty:
        return jsonify({"error": "Faculty not found"}), 404

    course.faculty_id = faculty.id
    AuditLog.log("assign_faculty", user=admin,
                 details=f"Assigned {faculty.user_id} to {course.course_code}",
                 ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": "Faculty assigned", "course": course.to_dict()}), 200


# ── GET /api/admin/departments ────────────────────────────────────────────────
@admin_bp.route("/departments", methods=["GET"])
@admin_required
def list_departments():
    depts = Department.query.order_by(Department.name).all()
    return jsonify([d.to_dict() for d in depts]), 200


# ── POST /api/admin/departments ───────────────────────────────────────────────
@admin_bp.route("/departments", methods=["POST"])
@admin_required
def create_department():
    admin = get_current_user()
    data  = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    code = data.get("code", "").strip().upper()
    if not name:
        return jsonify({"error": "'name' is required"}), 400
    if not code:
        # Auto-generate code from first letters
        code = "".join(w[0] for w in name.split()).upper()[:6]

    if Department.query.filter_by(name=name).first():
        return jsonify({"error": "Department already exists"}), 409

    dept = Department(name=name, code=code, description=data.get("description", ""))
    db.session.add(dept)
    db.session.commit()
    return jsonify({"message": "Department created", "department": dept.to_dict()}), 201


# ── PUT /api/admin/departments/<id> ─────────────────────────────────────────────
@admin_bp.route("/departments/<int:dept_id>", methods=["PUT"])
@admin_required
def update_department(dept_id):
    dept = db.session.get(Department, dept_id)
    if not dept:
        return jsonify({"error": "Department not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"]:
        dept.name = data["name"].strip()
    if "code" in data and data["code"]:
        dept.code = data["code"].strip().upper()
    if "description" in data:
        dept.description = data["description"]

    db.session.commit()
    return jsonify({"message": "Department updated", "department": dept.to_dict()}), 200


# ── GET /api/admin/settings ───────────────────────────────────────────────────
@admin_bp.route("/settings", methods=["GET"])
@admin_required
def get_settings():
    return jsonify(SystemSetting.get_all()), 200


# ── PUT /api/admin/settings ───────────────────────────────────────────────────
@admin_bp.route("/settings", methods=["PUT"])
@admin_required
def update_settings():
    admin = get_current_user()
    data  = request.get_json(silent=True) or {}

    if not data:
        return jsonify({"error": "No settings provided"}), 400

    SystemSetting.set_many(data)
    AuditLog.log("update_settings", user=admin,
                 details=f"Updated keys: {list(data.keys())}", ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": "Settings updated", "settings": SystemSetting.get_all()}), 200


# ── GET /api/admin/profile ───────────────────────────────────────────────────
@admin_bp.route("/profile", methods=["GET"])
@admin_required
def get_admin_profile():
    user = get_current_user()
    return jsonify({"user": user.to_dict(include_profile=True)}), 200


# ── PUT /api/admin/profile ───────────────────────────────────────────────────
@admin_bp.route("/profile", methods=["PUT"])
@admin_required
def update_admin_profile():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    for field in ("full_name", "phone", "department"):
        if field in data and data[field] is not None:
            setattr(user, field, str(data[field]).strip())
    if "email" in data and data["email"]:
        new_email = str(data["email"]).strip().lower()
        conflict = User.query.filter(User.email == new_email, User.id != user.id).first()
        if conflict:
            return jsonify({"error": "Email already in use by another account."}), 409
        user.email = new_email
    AuditLog.log("admin_update_profile", user=user, ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict(include_profile=True)}), 200


# ── DELETE /api/admin/departments/<id> ────────────────────────────────────────
@admin_bp.route("/departments/<int:dept_id>", methods=["DELETE"])
@admin_required
def delete_department(dept_id):
    admin = get_current_user()
    dept = db.session.get(Department, dept_id)
    if not dept:
        return jsonify({"error": "Department not found"}), 404
    db.session.delete(dept)
    AuditLog.log("delete_department", user=admin,
                 details=f"Deleted department {dept.name}", ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": f"Department '{dept.name}' deleted"}), 200


# ── GET /api/admin/analytics/enrollment-trends ────────────────────────────────
@admin_bp.route("/analytics/enrollment-trends", methods=["GET"])
@admin_required
def enrollment_trends():
    """Return monthly enrollment counts for the past 12 months."""
    rows = (
        db.session.query(
            func.strftime("%Y-%m", Enrollment.enrolled_at).label("month"),
            func.count().label("count"),
        )
        .group_by("month")
        .order_by("month")
        .limit(12)
        .all()
    )
    return jsonify([{"month": r.month, "count": r.count} for r in rows]), 200


# ── GET /api/admin/analytics/grade-distribution ───────────────────────────────
@admin_bp.route("/analytics/grade-distribution", methods=["GET"])
@admin_required
def grade_distribution():
    """Return count of each grade letter across all enrollments."""
    rows = (
        db.session.query(Enrollment.grade, func.count().label("count"))
        .filter(Enrollment.grade.isnot(None))
        .group_by(Enrollment.grade)
        .all()
    )
    distribution = defaultdict(int)
    for grade, count in rows:
        distribution[grade] = count
    return jsonify(dict(distribution)), 200


# ── GET /api/admin/audit-logs ─────────────────────────────────────────────────
# ── POST /api/admin/announcements ────────────────────────────────────────────
@admin_bp.route("/announcements", methods=["POST"])
@admin_required
def post_announcement():
    """Broadcast an announcement as a notification to users by role (or all).
    Body: { title, message, target ('all'|'student'|'faculty'), priority ('normal'|'urgent') }
    """
    data     = request.get_json(silent=True) or {}
    title    = (data.get("title") or "").strip()
    message  = (data.get("message") or "").strip()
    target   = (data.get("target") or "all").lower()
    priority = (data.get("priority") or "normal").lower()

    if not title or not message:
        return jsonify({"error": "Title and message are required."}), 400
    if target not in ("all", "student", "faculty"):
        return jsonify({"error": "target must be 'all', 'student', or 'faculty'"}), 400
    if priority not in ("normal", "urgent"):
        priority = "normal"

    # Prepend [URGENT] marker when priority is urgent
    formatted_title = f"[URGENT] {title}" if priority == "urgent" else title

    query = User.query.filter_by(is_active=True)
    if target in ("student", "faculty"):
        query = query.filter_by(role=target)

    recipients = query.all()
    # Encode target as notification_type so GET can reconstruct it
    notif_type = f"announce_{target}"

    admin = get_current_user()
    sender_name = admin.full_name or admin.user_id or "Administrator"

    for user in recipients:
        Notification.create(
            user_id           = user.id,
            title             = f"[Announcement] {formatted_title}",
            message           = message,
            notification_type = notif_type,
            related_id        = admin.id,
            related_type      = f"admin:{sender_name}",
        )

    AuditLog.log("post_announcement", user=admin,
                 details=f"Sent '{formatted_title}' to {len(recipients)} {target} user(s) (priority={priority})",
                 ip=request.remote_addr)
    db.session.commit()
    return jsonify({
        "message":    f"Announcement sent to {len(recipients)} user(s).",
        "recipients": len(recipients),
        "target":     target,
        "priority":   priority,
    }), 200


# ── GET /api/admin/announcements ─────────────────────────────────────────────
@admin_bp.route("/announcements", methods=["GET"])
@admin_required
def list_announcements():
    """Return the last 50 unique announcements with target, priority, and recipient count."""
    notifs = (
        Notification.query
        .filter(Notification.title.like("[Announcement]%"))
        .order_by(Notification.created_at.desc())
        .limit(500)
        .all()
    )
    seen, unique = set(), []
    for n in notifs:
        key = (n.title, n.message)
        if key not in seen:
            seen.add(key)

            # Decode target from notification_type (e.g. 'announce_all' -> 'all')
            ntype = n.notification_type or ""
            target = ntype[len("announce_"):] if ntype.startswith("announce_") else "all"

            # Decode priority and clean display title
            raw = n.title.replace("[Announcement] ", "", 1)
            if raw.startswith("[URGENT] "):
                priority      = "urgent"
                display_title = raw[len("[URGENT] "):]
            else:
                priority      = "normal"
                display_title = raw

            # Count how many recipients got this broadcast
            recipient_count = Notification.query.filter_by(
                title=n.title, message=n.message
            ).count()

            unique.append({
                "id":              n.id,
                "title":           display_title,
                "message":         n.message,
                "target":          target,
                "priority":        priority,
                "recipient_count": recipient_count,
                "created_at":      n.created_at.isoformat(),
            })
            if len(unique) >= 50:
                break
    return jsonify(unique), 200


# ── DELETE /api/admin/announcements/<id> ─────────────────────────────────────
@admin_bp.route("/announcements/<int:notif_id>", methods=["DELETE"])
@admin_required
def delete_announcement(notif_id):
    """Delete an entire announcement broadcast (all recipient copies) by any one notification id."""
    admin = get_current_user()
    notif = db.session.get(Notification, notif_id)
    if not notif:
        return jsonify({"error": "Announcement not found"}), 404

    deleted = Notification.query.filter_by(
        title=notif.title, message=notif.message
    ).delete()

    AuditLog.log("delete_announcement", user=admin,
                 details=f"Deleted broadcast '{notif.title}' ({deleted} notifications)",
                 ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": f"Announcement deleted ({deleted} notifications removed)"}), 200


@admin_bp.route("/audit-logs", methods=["GET"])
@admin_required
def audit_logs():
    action = request.args.get("action", "").strip()
    limit  = min(int(request.args.get("limit", 50)), 200)

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify([log.to_dict() for log in logs]), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN QUIZ MANAGEMENT
#  Admins can view all quizzes, toggle publish, and delete any quiz.
# ═══════════════════════════════════════════════════════════════════════════════
from app.models.quiz import Quiz, QuizAttempt  # noqa: E402


# ── GET /api/admin/quizzes ────────────────────────────────────────────────────
@admin_bp.route("/quizzes", methods=["GET"])
@admin_required
def get_all_quizzes():
    course_id = request.args.get("course_id")
    faculty_id_param = request.args.get("faculty_id")
    is_published_param = request.args.get("is_published")

    query = Quiz.query
    if course_id:
        query = query.filter_by(course_id=int(course_id))
    if faculty_id_param:
        faculty = User.query.filter_by(user_id=faculty_id_param, role="faculty").first()
        if faculty:
            query = query.filter_by(faculty_id=faculty.id)
    if is_published_param is not None:
        is_pub = is_published_param.lower() in ("true", "1")
        query = query.filter_by(is_published=is_pub)

    quizzes = query.order_by(Quiz.created_at.desc()).all()
    return jsonify({
        "quizzes": [q.to_dict() for q in quizzes],
        "total":   len(quizzes),
    }), 200


# ── PUT /api/admin/quizzes/<id> ───────────────────────────────────────────────
@admin_bp.route("/quizzes/<int:quiz_id>", methods=["PUT"])
@admin_required
def admin_update_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "is_published", "time_limit_minutes",
                  "max_attempts", "pass_score", "show_answers_after"):
        if field in data:
            setattr(quiz, field, data[field])

    db.session.commit()
    return jsonify({"message": "Quiz updated", "quiz": quiz.to_dict()}), 200


# ── DELETE /api/admin/quizzes/<id> ────────────────────────────────────────────
@admin_bp.route("/quizzes/<int:quiz_id>", methods=["DELETE"])
@admin_required
def admin_delete_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    db.session.delete(quiz)
    db.session.commit()
    return jsonify({"message": "Quiz deleted"}), 200


# ── GET /api/admin/quizzes/<id>/attempts ──────────────────────────────────────
@admin_bp.route("/quizzes/<int:quiz_id>/attempts", methods=["GET"])
@admin_required
def admin_get_quiz_attempts(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    attempts = quiz.attempts.filter_by(status="submitted").all()
    return jsonify({
        "quiz":     quiz.to_dict(include_questions=True),
        "attempts": [a.to_dict() for a in attempts],
        "total":    len(attempts),
    }), 200
