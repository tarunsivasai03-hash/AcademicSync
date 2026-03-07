"""
Task model — personal to-do items per user.
The frontend's Tasks page shows personal tasks managed per student/faculty.
"""
from datetime import datetime, timezone
from app.extensions import db


class Task(db.Model):
    __tablename__ = "tasks"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=True)
    title         = db.Column(db.String(300), nullable=False)
    description   = db.Column(db.Text)
    due_date      = db.Column(db.DateTime)
    priority      = db.Column(db.String(10), default="medium")  # low | medium | high
    is_completed  = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    user       = db.relationship("User", back_populates="tasks")
    assignment = db.relationship("Assignment", backref=db.backref("tasks", lazy="dynamic"))

    def to_dict(self):
        return {
            "id":            self.id,
            "assignment_id": self.assignment_id,
            "title":         self.title,
            "description":   self.description,
            "due_date":      self.due_date.isoformat() if self.due_date else None,
            "priority":      self.priority,
            "completed":     self.is_completed,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }
