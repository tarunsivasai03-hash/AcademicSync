"""
Notification model — in-app alerts for students and faculty.
"""
from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title             = db.Column(db.String(200), nullable=False)
    message           = db.Column(db.Text)
    notification_type = db.Column(db.String(50), default="info")  # info|assignment|grade|system|announce_all|announce_student|announce_faculty
    is_read           = db.Column(db.Boolean, default=False)
    related_id        = db.Column(db.Integer)               # optional: FK to related object
    related_type      = db.Column(db.Text)                  # optional: 'assignment'|'grade'|'faculty:Name|Course'|'admin:Name' etc.
    created_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id":                self.id,
            "title":             self.title,
            "message":           self.message,
            "notification_type": self.notification_type,
            "is_read":           self.is_read,
            "related_id":        self.related_id,
            "related_type":      self.related_type,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create(user_id: int, title: str, message: str = None,
               notification_type: str = "info",
               related_id: int = None, related_type: str = None):
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_id=related_id,
            related_type=related_type,
        )
        db.session.add(notif)
