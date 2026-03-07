"""
Attendance model.
"""
from datetime import datetime, date, timezone
from app.extensions import db


class Attendance(db.Model):
    __tablename__ = "attendance_records"
    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", "date", name="uq_attendance"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    status      = db.Column(db.String(15), nullable=False)   # present | absent | late | excused
    notes       = db.Column(db.String(250))
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student  = db.relationship("User", foreign_keys=[student_id],
                               backref=db.backref("attendance_records", lazy="dynamic"))
    course   = db.relationship("Course", backref=db.backref("attendance_records", lazy="dynamic"))
    recorder = db.relationship("User", foreign_keys=[recorded_by])

    def to_dict(self):
        return {
            "id":         self.id,
            "student_id": self.student_id,
            "course_id":  self.course_id,
            "date":       self.date.isoformat() if self.date else None,
            "status":     self.status,
            "notes":      self.notes,
        }
