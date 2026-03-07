"""
AcademicYear, Semester, Course, and Enrollment models.
Academic structure: AcademicYear → Semester → Course → Enrollment
"""
from datetime import datetime, timezone
from app.extensions import db


class AcademicYear(db.Model):
    __tablename__ = "academic_years"

    id          = db.Column(db.Integer, primary_key=True)
    year_label  = db.Column(db.String(20), unique=True, nullable=False)  # "2025-2026"
    start_date  = db.Column(db.Date)
    end_date    = db.Column(db.Date)
    is_current  = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    semesters = db.relationship("Semester", back_populates="academic_year",
                                cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {
            "id":         self.id,
            "year_label": self.year_label,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date":   self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
        }


class Semester(db.Model):
    __tablename__ = "semesters"

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(50), nullable=False)         # "Fall 2025"
    semester_type    = db.Column(db.String(20), default="fall")         # fall | spring | summer
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    start_date       = db.Column(db.Date)
    end_date         = db.Column(db.Date)
    is_current       = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    academic_year = db.relationship("AcademicYear", back_populates="semesters")
    courses       = db.relationship("Course", back_populates="semester", lazy="dynamic")

    def to_dict(self):
        return {
            "id":               self.id,
            "name":             self.name,
            "semester_type":    self.semester_type,
            "academic_year_id": self.academic_year_id,
            "academic_year":    self.academic_year.year_label if self.academic_year else None,
            "start_date":       self.start_date.isoformat() if self.start_date else None,
            "end_date":         self.end_date.isoformat() if self.end_date else None,
            "is_current":       self.is_current,
        }


class Course(db.Model):
    __tablename__ = "courses"

    id            = db.Column(db.Integer, primary_key=True)
    course_code   = db.Column(db.String(20), unique=True, nullable=False, index=True)
    course_name   = db.Column(db.String(200), nullable=False)
    description   = db.Column(db.Text)
    credits       = db.Column(db.Integer, default=3)

    # Academic structure FKs
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    department    = db.Column(db.String(100))           # denormalised for quick access
    semester_id   = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=True)
    faculty_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    max_students  = db.Column(db.Integer, default=50)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    faculty        = db.relationship("User", foreign_keys=[faculty_id],
                                     backref=db.backref("taught_courses", lazy="dynamic"))
    department_rel = db.relationship("Department", foreign_keys=[department_id],
                                     back_populates="courses")
    semester       = db.relationship("Semester", back_populates="courses")
    enrollments    = db.relationship("Enrollment", back_populates="course",
                                     cascade="all, delete-orphan", lazy="dynamic")
    assignments    = db.relationship("Assignment", back_populates="course",
                                     cascade="all, delete-orphan", lazy="dynamic")
    resources      = db.relationship("Resource", back_populates="course",
                                     cascade="all, delete-orphan", lazy="dynamic")
    sessions       = db.relationship("CourseSession", back_populates="course",
                                     cascade="all, delete-orphan", lazy="dynamic")

    @property
    def enrolled_count(self) -> int:
        return self.enrollments.filter_by(status="active").count()

    @property
    def semester_name(self) -> str:
        return self.semester.name if self.semester else ""

    def to_dict(self, include_faculty: bool = True) -> dict:
        data = {
            "id":            self.id,
            "course_code":   self.course_code,
            "course_name":   self.course_name,
            "description":   self.description,
            "credits":       self.credits,
            "department":    self.department,
            "department_id": self.department_id,
            "semester_id":   self.semester_id,
            "semester":      self.semester_name,
            "max_students":  self.max_students,
            "enrolled_count":self.enrolled_count,
            "is_active":     self.is_active,
        }
        if include_faculty and self.faculty:
            data["faculty_id"]   = self.faculty.user_id
            data["faculty_name"] = self.faculty.full_name
        else:
            data["faculty_id"]   = None
            data["faculty_name"] = "Unassigned"
        return data


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", name="uq_enrollment"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id    = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    grade        = db.Column(db.String(5))          # letter: A, B+, C-, etc.
    grade_points = db.Column(db.Float)              # numeric GPA contribution
    status       = db.Column(db.String(20), default="active")   # active | dropped | completed
    enrolled_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student = db.relationship("User", foreign_keys=[student_id],
                              backref=db.backref("enrollments", lazy="dynamic"))
    course  = db.relationship("Course", back_populates="enrollments")

    def to_dict(self):
        return {
            "id":           self.id,
            "student_id":   self.student_id,
            "course_id":    self.course_id,
            "grade":        self.grade,
            "grade_points": self.grade_points,
            "status":       self.status,
            "enrolled_at":  self.enrolled_at.isoformat() if self.enrolled_at else None,
        }
