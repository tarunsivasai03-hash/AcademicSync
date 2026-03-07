"""
Submission model (student answers to assignments).
"""
from datetime import datetime, timezone
from app.extensions import db


class Submission(db.Model):
    __tablename__ = "submissions"
    __table_args__ = (
        db.UniqueConstraint("assignment_id", "student_id", name="uq_submission"),
    )

    id              = db.Column(db.Integer, primary_key=True)
    assignment_id   = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    student_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submission_text = db.Column(db.Text)
    file_path       = db.Column(db.String(300))         # filename in uploads/
    original_filename = db.Column(db.String(300))
    grade           = db.Column(db.Float)               # points out of total_points
    feedback        = db.Column(db.Text)
    status          = db.Column(db.String(20), default="submitted")  # submitted|graded|late|draft
    submitted_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    graded_at       = db.Column(db.DateTime)

    assignment  = db.relationship("Assignment", back_populates="submissions")
    student     = db.relationship("User", foreign_keys=[student_id],
                                  backref=db.backref("submissions", lazy="dynamic"))

    def to_dict(self, include_student: bool = False) -> dict:
        data = {
            "id":                self.id,
            "assignment_id":     self.assignment_id,
            "assignment_title":  self.assignment.title if self.assignment else None,
            "student_id":        self.student_id,
            "submission_text":   self.submission_text,
            "file_path":         self.file_path,
            "original_filename": self.original_filename,
            "grade":             self.grade,
            "feedback":          self.feedback,
            "status":            self.status,
            "submitted_at":      self.submitted_at.isoformat() if self.submitted_at else None,
            "graded_at":         self.graded_at.isoformat() if self.graded_at else None,
        }
        if include_student and self.student:
            data["student_name"]    = self.student.full_name
            data["student_user_id"] = self.student.user_id
        return data
