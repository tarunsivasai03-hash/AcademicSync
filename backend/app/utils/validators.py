"""
Input validators — return (is_valid: bool, error_message: str | None).
"""
import re
import os
from datetime import datetime
from flask import current_app


# ── Field validators ───────────────────────────────────────────────────────────

def validate_email(email: str) -> tuple[bool, str | None]:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not email or not re.match(pattern, email.strip()):
        return False, "Invalid email address."
    return True, None


def validate_password(password: str) -> tuple[bool, str | None]:
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters."
    return True, None


def validate_role(role: str) -> tuple[bool, str | None]:
    valid = {"student", "faculty", "admin"}
    if role not in valid:
        return False, f"Role must be one of: {', '.join(valid)}."
    return True, None


def validate_required(value, field_name: str) -> tuple[bool, str | None]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, f"'{field_name}' is required."
    return True, None


def validate_date_string(value: str, field_name: str = "date") -> tuple[bool, str | None]:
    """Accepts ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            datetime.strptime(value, fmt)
            return True, None
        except (ValueError, TypeError):
            continue
    return False, f"'{field_name}' must be a valid date (YYYY-MM-DD)."


# ── File validators ────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())


# ── Bulk validators ────────────────────────────────────────────────────────────

def validate_registration(data: dict) -> tuple[bool, str | None]:
    """Validate all required fields for user registration."""
    required_fields = ["full_name", "email", "password"]
    for field in required_fields:
        ok, err = validate_required(data.get(field), field)
        if not ok:
            return False, err

    ok, err = validate_email(data["email"])
    if not ok:
        return False, err

    ok, err = validate_password(data["password"])
    if not ok:
        return False, err

    if data.get("role"):
        ok, err = validate_role(data["role"])
        if not ok:
            return False, err

    return True, None


def validate_login(data: dict) -> tuple[bool, str | None]:
    for field in ("user_id", "password"):
        ok, err = validate_required(data.get(field), field)
        if not ok:
            return False, err
    return True, None
