"""
Route decorators — role-based access control on top of JWT.
"""
from functools import wraps
from typing import Optional
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.extensions import db
from app.models.user import User


def get_current_user() -> Optional[User]:
    """Return the User object for the current JWT identity."""
    identity = get_jwt_identity()           # returns str(user.id) stored at login
    if identity is None:
        return None
    return db.session.get(User, int(identity))


def roles_required(*roles):
    """
    Decorator: requires JWT + one of the specified roles.
    Usage:
        @roles_required('admin')
        @roles_required('faculty', 'admin')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if not user or not user.is_active:
                return jsonify({"error": "Account not found or deactivated"}), 401
            if user.role not in roles:
                return jsonify({
                    "error": "Permission denied",
                    "required_roles": list(roles),
                    "your_role": user.role,
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def student_required(fn):
    """Shortcut for @roles_required('student')."""
    return roles_required("student")(fn)


def faculty_required(fn):
    """Shortcut for @roles_required('faculty')."""
    return roles_required("faculty")(fn)


def admin_required(fn):
    """Shortcut for @roles_required('admin')."""
    return roles_required("admin")(fn)


def any_authenticated(fn):
    """Allow any authenticated user regardless of role."""
    return roles_required("student", "faculty", "admin")(fn)
