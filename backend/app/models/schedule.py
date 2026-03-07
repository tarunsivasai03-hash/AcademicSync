"""
CourseSession model — class timetable entries per course.
"""
from app.extensions import db

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


class CourseSession(db.Model):
    __tablename__ = "course_sessions"

    id            = db.Column(db.Integer, primary_key=True)
    course_id     = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    day_of_week   = db.Column(db.String(15), nullable=False)    # Monday … Saturday
    start_time    = db.Column(db.String(8), nullable=False)     # "09:00"
    end_time      = db.Column(db.String(8), nullable=False)     # "10:30"
    room          = db.Column(db.String(50))
    session_type  = db.Column(db.String(20), default="lecture") # lecture|lab|tutorial

    course = db.relationship("Course", back_populates="sessions")

    def to_dict(self):
        faculty = self.course.faculty if self.course else None
        return {
            "id":           self.id,
            "course_id":    self.course_id,
            "course_name":  self.course.course_name if self.course else None,
            "course_code":  self.course.course_code if self.course else None,
            "faculty_name": faculty.full_name if faculty else None,
            "day_of_week":  self.day_of_week,
            "start_time":   self.start_time,
            "end_time":     self.end_time,
            "room":         self.room,
            "session_type": self.session_type,
        }
