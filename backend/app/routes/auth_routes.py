"""
Auth routes — /api/auth/*
  POST /login
  POST /register
  POST /logout
  POST /refresh
  GET  /me
"""
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies,
)

from app.extensions import db
from app.models.user import User, StudentProfile, FacultyProfile, AuditLog
from app.utils.decorators import get_current_user
from app.utils.validators import validate_registration, validate_login
from app.utils.id_generator import generate_user_id

auth_bp = Blueprint("auth", __name__)

# ── Simple in-memory rate limiter for /login ───────────────────────────────────
_login_attempts: dict[str, list] = defaultdict(list)
_login_lock = threading.Lock()
_LOGIN_WINDOW  = 60   # seconds
_LOGIN_MAX     = 5    # attempts per window


def _is_rate_limited(ip: str) -> bool:
    """Return True if the IP has exceeded the login attempt limit."""
    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_LOGIN_WINDOW)
    with _login_lock:
        _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
        if len(_login_attempts[ip]) >= _LOGIN_MAX:
            return True
        _login_attempts[ip].append(now)
        return False


def _make_tokens(user_id: int):
    """Create access + refresh JWT tokens with the user's PK as identity."""
    access  = create_access_token(identity=str(user_id))
    refresh = create_refresh_token(identity=str(user_id))
    return access, refresh


# ── POST /api/auth/login ───────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    ip   = request.remote_addr or "unknown"
    if _is_rate_limited(ip):
        return jsonify({"error": "Too many login attempts. Please wait 60 seconds."}), 429

    data = request.get_json(silent=True) or {}

    ok, err = validate_login(data)
    if not ok:
        return jsonify({"error": err}), 400

    user = User.query.filter_by(user_id=data["user_id"].strip()).first()

    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account has been deactivated. Contact admin."}), 403

    # Optional role check (frontend passes 'role' for confirmation)
    if data.get("role") and data["role"] != user.role:
        return jsonify({"error": f"This account is not a {data['role']} account."}), 403

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    AuditLog.log("login", user=user, ip=request.remote_addr)
    db.session.commit()

    access_token, refresh_token = _make_tokens(user.id)

    response = jsonify({
        "message":    "Login successful",
        "user":       user.to_dict(include_profile=True),
        "access_token": access_token,
    })
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 200


# ── POST /api/auth/register ────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    ok, err = validate_registration(data)
    if not ok:
        return jsonify({"error": err}), 400

    # Duplicate checks
    if User.query.filter_by(email=data["email"].strip().lower()).first():
        return jsonify({"error": "Email is already registered."}), 409

    role = data.get("role", "student").lower()

    # Allow caller to specify a custom user_id (admin use) or auto-generate
    custom_uid = data.get("user_id", "").strip()
    if custom_uid:
        if User.query.filter_by(user_id=custom_uid).first():
            return jsonify({"error": f"User ID '{custom_uid}' is already taken."}), 409
        user_id_str = custom_uid
    else:
        user_id_str = generate_user_id(role)

    user = User(
        user_id=user_id_str,
        full_name=data["full_name"].strip(),
        email=data["email"].strip().lower(),
        role=role,
        department=data.get("department", "").strip() or None,
        phone=data.get("phone", "").strip() or None,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()   # get user.id before committing

    # Create role-specific profile
    if role == "student":
        profile = StudentProfile(
            user_id=user.id,
            year=int(data.get("year", 1)),
        )
        db.session.add(profile)
    elif role == "faculty":
        profile = FacultyProfile(
            user_id=user.id,
            specialization=data.get("specialization", ""),
        )
        db.session.add(profile)

    AuditLog.log("register", user=user, details=f"role={role}", ip=request.remote_addr)
    db.session.commit()

    return jsonify({
        "message": "Registration successful",
        "user_id": user.user_id,
        "role":    user.role,
    }), 201


# ── POST /api/auth/logout ──────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@jwt_required(optional=True)
def logout():
    identity = get_jwt_identity()
    if identity:
        user = db.session.get(User, int(identity))
        if user:
            AuditLog.log("logout", user=user, ip=request.remote_addr)
            db.session.commit()

    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)
    return response, 200


# ── POST /api/auth/refresh ─────────────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity     = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    response     = jsonify({"access_token": access_token})
    set_access_cookies(response, access_token)
    return response, 200


# ── GET /api/auth/me ───────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    identity = get_jwt_identity()
    user     = db.session.get(User, int(identity))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict(include_profile=True)), 200


# ── PUT /api/auth/me ──────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    """Update the currently authenticated user's own profile (any role)."""
    identity = get_jwt_identity()
    user     = db.session.get(User, int(identity))
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}

    if "full_name" in data and data["full_name"]:
        user.full_name = str(data["full_name"]).strip()

    if "phone" in data:
        user.phone = str(data["phone"]).strip()

    if "department" in data:
        user.department = str(data["department"]).strip()

    if "email" in data and data["email"]:
        new_email = str(data["email"]).strip().lower()
        conflict = User.query.filter(User.email == new_email, User.id != user.id).first()
        if conflict:
            return jsonify({"error": "Email is already in use by another account."}), 409
        user.email = new_email

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict(include_profile=True)}), 200


# ── PUT /api/auth/change-password ─────────────────────────────────────────────
@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    identity = get_jwt_identity()
    user     = db.session.get(User, int(identity))
    if not user:
        return jsonify({"error": "User not found"}), 404

    data         = request.get_json(silent=True) or {}
    current_pwd  = data.get("current_password", "")
    new_pwd      = data.get("new_password", "")
    confirm_pwd  = data.get("confirm_password", "")

    if not current_pwd or not new_pwd:
        return jsonify({"error": "current_password and new_password are required."}), 400
    if not user.check_password(current_pwd):
        return jsonify({"error": "Current password is incorrect."}), 401
    if len(new_pwd) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400
    if confirm_pwd and new_pwd != confirm_pwd:
        return jsonify({"error": "Passwords do not match."}), 400

    user.set_password(new_pwd)
    AuditLog.log("change_password", user=user, ip=request.remote_addr)
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200
