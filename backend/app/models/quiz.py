"""
Quiz models — online quiz system.

Tables:
  quizzes          — a quiz created by faculty for a specific course
  quiz_questions   — questions within a quiz (MCQ or True/False)
  quiz_options     — answer choices for each question (one flagged is_correct)
  quiz_attempts    — a student's single attempt at a quiz
  quiz_answers     — the student's selected option for each question
"""
from datetime import datetime, timezone
from app.extensions import db


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id                  = db.Column(db.Integer, primary_key=True)
    title               = db.Column(db.String(250), nullable=False)
    description         = db.Column(db.Text, default="")
    course_id           = db.Column(db.Integer, db.ForeignKey("courses.id"),  nullable=False)
    faculty_id          = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    time_limit_minutes  = db.Column(db.Integer, default=None)   # None = unlimited
    max_attempts        = db.Column(db.Integer, default=1)       # 0 = unlimited
    pass_score          = db.Column(db.Float,   default=60.0)    # percentage
    show_answers_after  = db.Column(db.Boolean, default=True)    # reveal answers post-submit
    is_published           = db.Column(db.Boolean, default=False)
    due_date               = db.Column(db.DateTime, default=None)
    scheduled_publish_at   = db.Column(db.DateTime, default=None)   # auto-publish at this time
    created_at             = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                    onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    course    = db.relationship("Course",  backref=db.backref("quizzes",   lazy="dynamic"))
    faculty   = db.relationship("User",    backref=db.backref("quizzes_created", lazy="dynamic"))
    questions = db.relationship("QuizQuestion", back_populates="quiz",
                                cascade="all, delete-orphan", order_by="QuizQuestion.order_index")
    attempts  = db.relationship("QuizAttempt",  back_populates="quiz",
                                cascade="all, delete-orphan", lazy="dynamic")

    @property
    def total_points(self):
        return sum(q.points for q in self.questions)

    @property
    def question_count(self):
        return len(self.questions)

    @property
    def attempt_count(self):
        return self.attempts.count()

    def to_dict(self, include_questions=False, student_id=None):
        d = {
            "id":                 self.id,
            "title":              self.title,
            "description":        self.description,
            "course_id":          self.course_id,
            "course_name":        self.course.course_name if self.course else None,
            "course_code":        self.course.course_code if self.course else None,
            "faculty_id":         self.faculty_id,
            "faculty_name":       self.faculty.full_name if self.faculty else None,
            "time_limit_minutes": self.time_limit_minutes,
            "max_attempts":       self.max_attempts,
            "pass_score":         self.pass_score,
            "show_answers_after": self.show_answers_after,
            "is_published":           self.is_published,
            "scheduled_publish_at":   self.scheduled_publish_at.isoformat() if self.scheduled_publish_at else None,
            "due_date":               self.due_date.isoformat() if self.due_date else None,
            "total_points":       self.total_points,
            "question_count":     self.question_count,
            "attempt_count":      self.attempt_count,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }
        if include_questions:
            d["questions"] = [q.to_dict() for q in self.questions]
        if student_id is not None:
            attempt = self.attempts.filter_by(
                student_id=student_id, status="submitted"
            ).order_by(QuizAttempt.submitted_at.desc()).first()
            in_progress = self.attempts.filter_by(
                student_id=student_id, status="in_progress"
            ).first()
            attempts_used = self.attempts.filter_by(student_id=student_id).count()
            d["student_attempt"]     = attempt.to_dict() if attempt else None
            d["in_progress_attempt"] = in_progress.to_dict() if in_progress else None
            d["attempts_used"]       = attempts_used
            now = datetime.now(timezone.utc)
            sched = self.scheduled_publish_at
            if sched is not None and sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            effectively_published = self.is_published or (sched is not None and sched <= now)
            d["effectively_published"] = bool(effectively_published)
            d["can_attempt"]           = (
                effectively_published
                and (self.max_attempts == 0 or attempts_used < self.max_attempts)
                and in_progress is None
            )
        return d


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id            = db.Column(db.Integer, primary_key=True)
    quiz_id       = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default="mcq")  # mcq | true_false
    points        = db.Column(db.Integer, default=1)
    order_index   = db.Column(db.Integer, default=0)
    explanation   = db.Column(db.Text, default="")  # shown to student after submission

    quiz    = db.relationship("Quiz", back_populates="questions")
    options = db.relationship("QuizOption", back_populates="question",
                              cascade="all, delete-orphan", order_by="QuizOption.order_index")
    answers = db.relationship("QuizAnswer", back_populates="question",
                              cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self, include_correct=True):
        return {
            "id":            self.id,
            "quiz_id":       self.quiz_id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "points":        self.points,
            "order_index":   self.order_index,
            "explanation":   self.explanation,
            "options":       [o.to_dict(include_correct=include_correct) for o in self.options],
        }


class QuizOption(db.Model):
    __tablename__ = "quiz_options"

    id          = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("quiz_questions.id"), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct  = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)

    question = db.relationship("QuizQuestion", back_populates="options")

    def to_dict(self, include_correct=True):
        d = {
            "id":          self.id,
            "question_id": self.question_id,
            "option_text": self.option_text,
            "order_index": self.order_index,
        }
        if include_correct:
            d["is_correct"] = self.is_correct
        return d


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id             = db.Column(db.Integer, primary_key=True)
    quiz_id        = db.Column(db.Integer, db.ForeignKey("quizzes.id"),  nullable=False)
    student_id     = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    started_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    submitted_at   = db.Column(db.DateTime, default=None)
    score          = db.Column(db.Float, default=0)      # points earned
    max_score      = db.Column(db.Float, default=0)      # total possible points
    percentage     = db.Column(db.Float, default=0)
    passed         = db.Column(db.Boolean, default=False)
    attempt_number = db.Column(db.Integer, default=1)
    status         = db.Column(db.String(20), default="in_progress")  # in_progress | submitted

    quiz    = db.relationship("Quiz",    back_populates="attempts")
    student = db.relationship("User",    backref=db.backref("quiz_attempts", lazy="dynamic"))
    answers = db.relationship("QuizAnswer", back_populates="attempt",
                              cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self, include_answers=False):
        d = {
            "id":             self.id,
            "quiz_id":        self.quiz_id,
            "quiz_title":     self.quiz.title if self.quiz else None,
            "student_id":     self.student_id,
            "student_name":   self.student.full_name if self.student else None,
            "started_at":     self.started_at.isoformat() if self.started_at else None,
            "submitted_at":   self.submitted_at.isoformat() if self.submitted_at else None,
            "score":          self.score,
            "max_score":      self.max_score,
            "percentage":     round(self.percentage, 1),
            "passed":         self.passed,
            "attempt_number": self.attempt_number,
            "status":         self.status,
        }
        if include_answers:
            d["answers"] = [a.to_dict() for a in self.answers.all()]
        return d


class QuizAnswer(db.Model):
    __tablename__ = "quiz_answers"

    id                 = db.Column(db.Integer, primary_key=True)
    attempt_id         = db.Column(db.Integer, db.ForeignKey("quiz_attempts.id"), nullable=False)
    question_id        = db.Column(db.Integer, db.ForeignKey("quiz_questions.id"), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey("quiz_options.id"),   nullable=True)
    is_correct         = db.Column(db.Boolean, default=False)
    points_earned      = db.Column(db.Float,   default=0)

    attempt  = db.relationship("QuizAttempt", back_populates="answers")
    question = db.relationship("QuizQuestion", back_populates="answers")
    selected_option = db.relationship("QuizOption")

    def to_dict(self):
        return {
            "id":                 self.id,
            "attempt_id":         self.attempt_id,
            "question_id":        self.question_id,
            "question_text":      self.question.question_text if self.question else None,
            "selected_option_id": self.selected_option_id,
            "selected_option_text": self.selected_option.option_text if self.selected_option else None,
            "is_correct":         self.is_correct,
            "points_earned":      self.points_earned,
        }
