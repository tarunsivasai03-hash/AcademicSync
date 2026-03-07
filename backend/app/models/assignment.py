"""
Assignment model.
"""
from datetime import datetime, timezone
from app.extensions import db


class Assignment(db.Model):
    __tablename__ = "assignments"

    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(250), nullable=False)
    description     = db.Column(db.Text)
    course_id       = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    faculty_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    due_date        = db.Column(db.DateTime)
    total_points    = db.Column(db.Integer, default=100)
    assignment_type = db.Column(db.String(30), default="homework")  # homework|quiz|project|exam
    priority        = db.Column(db.String(10), default="medium")    # low|medium|high
    status          = db.Column(db.String(20), default="active")    # active|closed|draft
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))

    course      = db.relationship("Course", back_populates="assignments")
    faculty     = db.relationship("User", foreign_keys=[faculty_id], backref=db.backref("assignments_created", lazy="dynamic"))
    submissions = db.relationship("Submission", back_populates="assignment",
                                  cascade="all, delete-orphan", lazy="dynamic")

    @property
    def submissions_count(self) -> int:
        return self.submissions.count()

    @property
    def avg_grade(self):
        graded = self.submissions.filter(Submission.grade.isnot(None)).all()
        if not graded:
            return None
        return round(sum(s.grade for s in graded) / len(graded), 2)

    def to_dict(self, student_id: int = None) -> dict:
        data = {
            "id":               self.id,
            "title":            self.title,
            "description":      self.description,
            "course_id":        self.course_id,
            "course_name":      self.course.course_name if self.course else None,
            "course_code":      self.course.course_code if self.course else None,
            "due_date":         self.due_date.isoformat() if self.due_date else None,
            "total_points":     self.total_points,
            "assignment_type":  self.assignment_type,
            "priority":         self.priority,
            "status":           self.status,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }
        if student_id:
            sub = self.submissions.filter_by(student_id=student_id).first()
            data["submission_status"] = sub.status if sub else "not_submitted"
            data["grade"] = sub.grade if sub else None
        else:
            graded_count = self.submissions.filter(Submission.grade.isnot(None)).count()
            total_students = self.course.enrolled_count if self.course else 0
            data["submissions_count"] = self.submissions_count
            data["graded_count"]      = graded_count
            data["total_students"]    = total_students
            data["avg_grade"]         = self.avg_grade
        return data


# Avoid circular import — needed only after Assignment class defined
from app.models.submission import Submission  # noqa: E402
