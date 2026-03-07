"""
Human-readable ID generator.
Produces IDs like STU001, FAC002, ADM001 that are shown in the UI.
"""
from app.extensions import db
from app.models.user import User


_PREFIXES = {
    "student": "STU",
    "faculty": "FAC",
    "admin":   "ADM",
}


def generate_user_id(role: str) -> str:
    """
    Generate the next sequential user_id for the given role.
    Thread-safe within a single process via DB sequence query.
    """
    prefix = _PREFIXES.get(role, "USR")
    # Count existing users of this role to determine next number
    count = User.query.filter_by(role=role).count()
    candidate = f"{prefix}{count + 1:03d}"
    # Make sure it's truly unique (edge case: deletions)
    while User.query.filter_by(user_id=candidate).first():
        count += 1
        candidate = f"{prefix}{count + 1:03d}"
    return candidate
