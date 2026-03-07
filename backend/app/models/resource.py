"""
Resource model — course materials uploaded by faculty.
"""
from datetime import datetime, timezone
from app.extensions import db


class Resource(db.Model):
    __tablename__ = "resources"

    id                = db.Column(db.Integer, primary_key=True)
    title             = db.Column(db.String(250), nullable=False)
    description       = db.Column(db.Text)
    course_id         = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    faculty_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_path         = db.Column(db.String(300))            # stored filename in uploads/
    original_filename = db.Column(db.String(300))
    resource_type     = db.Column(db.String(30), default="document")  # pdf|video|link|document|slides
    file_size         = db.Column(db.Integer)                # bytes; None for link resources
    external_url      = db.Column(db.String(500))            # for link-type resources
    visibility        = db.Column(db.String(20), default="enrolled")  # all | enrolled | specific
    uploaded_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    course   = db.relationship("Course", back_populates="resources")
    faculty  = db.relationship("User", foreign_keys=[faculty_id],
                               backref=db.backref("uploaded_resources", lazy="dynamic"))

    def to_dict(self):
        return {
            "id":               self.id,
            "title":            self.title,
            "description":      self.description,
            "course_id":        self.course_id,
            "course_name":      self.course.course_name if self.course else None,
            "course_code":      self.course.course_code if self.course else None,
            "faculty_name":     self.faculty.full_name if self.faculty else None,
            "resource_type":    self.resource_type,
            "file_path":        self.file_path,
            "original_filename":self.original_filename,
            "file_size":        self.file_size,
            "external_url":     self.external_url,
            "visibility":       self.visibility,
            "uploaded_at":      self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
