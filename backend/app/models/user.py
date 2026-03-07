"""
User, StudentProfile, FacultyProfile, AdminProfile, Department, AuditLog, SystemSetting models.
Centralising identity here keeps joins simple.
"""
from datetime import datetime, timezone
from app.extensions import db, bcrypt


class Department(db.Model):
    __tablename__ = "departments"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), unique=True, nullable=False)
    code        = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users       = db.relationship("User", foreign_keys="User.department_id", back_populates="department_rel", lazy="dynamic")
    courses     = db.relationship("Course", back_populates="department_rel", lazy="dynamic")

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "code":        self.code,
            "description": self.description,
        }


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    # Human-readable ID shown in the UI, e.g. "STU001", "FAC002", "ADM001"
    user_id       = db.Column(db.String(30), unique=True, nullable=False, index=True)
    full_name     = db.Column(db.String(150), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False)            # student | faculty | admin
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    department    = db.Column(db.String(100))                           # denormalised for quick access
    phone         = db.Column(db.String(30))
    is_active     = db.Column(db.Boolean, default=True, nullable=False)
    last_login    = db.Column(db.DateTime)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    department_rel   = db.relationship("Department", foreign_keys=[department_id], back_populates="users")
    student_profile  = db.relationship("StudentProfile", back_populates="user",
                                       uselist=False, cascade="all, delete-orphan")
    faculty_profile  = db.relationship("FacultyProfile", back_populates="user",
                                       uselist=False, cascade="all, delete-orphan")
    admin_profile    = db.relationship("AdminProfile", back_populates="user",
                                       uselist=False, cascade="all, delete-orphan")
    tasks            = db.relationship("Task", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    notifications    = db.relationship("Notification", back_populates="user",
                                       cascade="all, delete-orphan", lazy="dynamic")
    audit_logs       = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    # ── Password helpers ───────────────────────────────────────────────────
    def set_password(self, plain_password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(plain_password).decode("utf-8")

    def check_password(self, plain_password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, plain_password)

    # ── Serialisation ──────────────────────────────────────────────────────
    def to_dict(self, include_profile: bool = False) -> dict:
        data = {
            "id":           self.id,
            "user_id":      self.user_id,
            "full_name":    self.full_name,
            "email":        self.email,
            "role":         self.role,
            "department":   self.department,
            "phone":        self.phone,
            "is_active":    self.is_active,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "last_login":   self.last_login.isoformat() if self.last_login else None,
        }
        if include_profile:
            if self.role == "student" and self.student_profile:
                data.update(self.student_profile.to_dict())
            elif self.role == "faculty" and self.faculty_profile:
                data.update(self.faculty_profile.to_dict())
            elif self.role == "admin" and self.admin_profile:
                data.update(self.admin_profile.to_dict())
        return data

    def __repr__(self):
        return f"<User {self.user_id} ({self.role})>"


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    year                = db.Column(db.Integer, default=1)              # academic year 1-4
    gpa                 = db.Column(db.Float, default=0.0)
    attendance_pct      = db.Column(db.Float, default=0.0)
    enrollment_date     = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())

    user = db.relationship("User", back_populates="student_profile")

    def to_dict(self):
        return {
            "year":            self.year,
            "gpa":             round(self.gpa, 2),
            "attendance_pct":  round(self.attendance_pct, 1),
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
        }


class FacultyProfile(db.Model):
    __tablename__ = "faculty_profiles"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    specialization   = db.Column(db.String(150))
    office_location  = db.Column(db.String(80))
    hire_date        = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())

    user = db.relationship("User", back_populates="faculty_profile")

    def to_dict(self):
        return {
            "specialization":  self.specialization,
            "office_location": self.office_location,
            "hire_date":       self.hire_date.isoformat() if self.hire_date else None,
        }


class AdminProfile(db.Model):
    __tablename__ = "admin_profiles"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    access_level     = db.Column(db.String(20), default="standard")  # standard | super
    managed_depts    = db.Column(db.Text)                             # comma-separated dept IDs, None = all
    notes            = db.Column(db.Text)
    appointed_at     = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())

    user = db.relationship("User", back_populates="admin_profile")

    def to_dict(self):
        return {
            "access_level":  self.access_level,
            "managed_depts": self.managed_depts,
            "notes":         self.notes,
            "appointed_at":  self.appointed_at.isoformat() if self.appointed_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action     = db.Column(db.String(80), nullable=False)   # login | logout | create_user | etc.
    details    = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self):
        return {
            "id":         self.id,
            "user":       self.user.full_name if self.user else "System",
            "user_id_str":self.user.user_id if self.user else None,
            "action":     self.action,
            "details":    self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def log(action: str, user=None, details: str = None, ip: str = None):
        entry = AuditLog(
            user_id=user.id if user else None,
            action=action,
            details=details,
            ip_address=ip,
        )
        db.session.add(entry)


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id         = db.Column(db.Integer, primary_key=True)
    key        = db.Column(db.String(80), unique=True, nullable=False)
    value      = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    @staticmethod
    def get_all() -> dict:
        rows = SystemSetting.query.all()
        return {r.key: r.value for r in rows}

    @staticmethod
    def set_many(data: dict) -> None:
        for key, value in data.items():
            row = SystemSetting.query.filter_by(key=key).first()
            if row:
                row.value = str(value)
            else:
                db.session.add(SystemSetting(key=key, value=str(value)))
