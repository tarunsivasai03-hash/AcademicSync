"""
Demo Quiz Seed Script
Adds 3 published demo quizzes (with questions & options) to the database.

Run with:
    cd backend
    python seed_quiz.py

Safe to run multiple times – skips quizzes that already exist by title+course.
Requires the main seed.py to have been run first (needs faculty + courses).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.course import Course
from app.models.quiz import Quiz, QuizQuestion, QuizOption

app = create_app("development")

# ─────────────────────────────────────────────────────────────────────────────
# Demo quiz data
# ─────────────────────────────────────────────────────────────────────────────
DEMO_QUIZZES = [
    {
        "title":              "Week 1 Quiz: Intro to Programming",
        "description":        "Basic programming concepts — variables, data types, and operators.",
        "course_code":        "CS101",
        "faculty_user_id":    "FAC001",
        "time_limit_minutes": 10,
        "max_attempts":       2,
        "pass_score":         60.0,
        "show_answers_after": True,
        "is_published":       True,
        "questions": [
            {
                "question_text": "What is the correct way to declare a variable in Python?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "Python uses simple assignment: x = 5 (no type keyword needed).",
                "options": [
                    {"option_text": "x = 5",          "is_correct": True},
                    {"option_text": "int x = 5;",     "is_correct": False},
                    {"option_text": "var x = 5",      "is_correct": False},
                    {"option_text": "declare x = 5",  "is_correct": False},
                ],
            },
            {
                "question_text": "Which data type stores True or False values?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "The Boolean (bool) type holds True or False.",
                "options": [
                    {"option_text": "int",     "is_correct": False},
                    {"option_text": "string",  "is_correct": False},
                    {"option_text": "bool",    "is_correct": True},
                    {"option_text": "float",   "is_correct": False},
                ],
            },
            {
                "question_text": "Python is a compiled language.",
                "question_type": "true_false",
                "points": 1,
                "explanation": "Python is an interpreted language, not compiled.",
                "options": [
                    {"option_text": "True",  "is_correct": False},
                    {"option_text": "False", "is_correct": True},
                ],
            },
            {
                "question_text": "What does the % operator do in most programming languages?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "% is the modulus operator — it returns the remainder of division.",
                "options": [
                    {"option_text": "Divides two numbers",          "is_correct": False},
                    {"option_text": "Returns the remainder",        "is_correct": True},
                    {"option_text": "Converts to percentage",       "is_correct": False},
                    {"option_text": "Multiplies two numbers",       "is_correct": False},
                ],
            },
            {
                "question_text": "A function is a reusable block of code.",
                "question_type": "true_false",
                "points": 1,
                "explanation": "Correct — functions allow code reuse and modularity.",
                "options": [
                    {"option_text": "True",  "is_correct": True},
                    {"option_text": "False", "is_correct": False},
                ],
            },
        ],
    },
    {
        "title":              "Data Structures Quiz: Arrays & Lists",
        "description":        "Test your knowledge of arrays, linked lists, and basic complexity.",
        "course_code":        "CS201",
        "faculty_user_id":    "FAC001",
        "time_limit_minutes": 15,
        "max_attempts":       1,
        "pass_score":         70.0,
        "show_answers_after": True,
        "is_published":       True,
        "questions": [
            {
                "question_text": "What is the time complexity of accessing an element in an array by index?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "Array access by index is O(1) — constant time regardless of size.",
                "options": [
                    {"option_text": "O(1)",      "is_correct": True},
                    {"option_text": "O(n)",      "is_correct": False},
                    {"option_text": "O(log n)",  "is_correct": False},
                    {"option_text": "O(n²)",     "is_correct": False},
                ],
            },
            {
                "question_text": "A stack follows FIFO (First In, First Out) order.",
                "question_type": "true_false",
                "points": 2,
                "explanation": "Wrong — a Stack is LIFO (Last In First Out). A Queue is FIFO.",
                "options": [
                    {"option_text": "True",  "is_correct": False},
                    {"option_text": "False", "is_correct": True},
                ],
            },
            {
                "question_text": "Which operation is most expensive in a singly linked list?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "Accessing an element by index requires O(n) traversal from the head.",
                "options": [
                    {"option_text": "Insert at head",             "is_correct": False},
                    {"option_text": "Access element by index",    "is_correct": True},
                    {"option_text": "Delete from head",           "is_correct": False},
                    {"option_text": "Check if list is empty",     "is_correct": False},
                ],
            },
            {
                "question_text": "Arrays are stored in contiguous memory locations.",
                "question_type": "true_false",
                "points": 1,
                "explanation": "Correct — arrays occupy sequential memory, enabling O(1) index access.",
                "options": [
                    {"option_text": "True",  "is_correct": True},
                    {"option_text": "False", "is_correct": False},
                ],
            },
            {
                "question_text": "What does 'Big O notation' measure?",
                "question_type": "mcq",
                "points": 3,
                "explanation": "Big O describes the upper-bound (worst-case) growth of algorithm time/space.",
                "options": [
                    {"option_text": "Memory usage only",                        "is_correct": False},
                    {"option_text": "Exact execution time in milliseconds",     "is_correct": False},
                    {"option_text": "Algorithm efficiency as input grows",      "is_correct": True},
                    {"option_text": "Number of lines of code",                  "is_correct": False},
                ],
            },
        ],
    },
    {
        "title":              "Calculus I — Limits & Derivatives",
        "description":        "Fundamental concepts of limits, continuity, and basic differentiation.",
        "course_code":        "MTH101",
        "faculty_user_id":    "FAC002",
        "time_limit_minutes": 20,
        "max_attempts":       3,
        "pass_score":         60.0,
        "show_answers_after": True,
        "is_published":       True,
        "questions": [
            {
                "question_text": "What is the derivative of f(x) = x² ?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "Using the power rule: d/dx [xⁿ] = n·xⁿ⁻¹, so d/dx[x²] = 2x.",
                "options": [
                    {"option_text": "2x",   "is_correct": True},
                    {"option_text": "x",    "is_correct": False},
                    {"option_text": "2",    "is_correct": False},
                    {"option_text": "x²",   "is_correct": False},
                ],
            },
            {
                "question_text": "The derivative of a constant is zero.",
                "question_type": "true_false",
                "points": 1,
                "explanation": "A constant has no rate of change, so its derivative is always 0.",
                "options": [
                    {"option_text": "True",  "is_correct": True},
                    {"option_text": "False", "is_correct": False},
                ],
            },
            {
                "question_text": "What does the limit lim(x→0) sin(x)/x equal?",
                "question_type": "mcq",
                "points": 3,
                "explanation": "This is a fundamental trigonometric limit: lim(x→0) sin(x)/x = 1.",
                "options": [
                    {"option_text": "0",        "is_correct": False},
                    {"option_text": "1",        "is_correct": True},
                    {"option_text": "∞",        "is_correct": False},
                    {"option_text": "Undefined", "is_correct": False},
                ],
            },
            {
                "question_text": "If f'(x) > 0 on an interval, the function is decreasing on that interval.",
                "question_type": "true_false",
                "points": 2,
                "explanation": "Wrong — a positive derivative means the function is INCREASING.",
                "options": [
                    {"option_text": "True",  "is_correct": False},
                    {"option_text": "False", "is_correct": True},
                ],
            },
            {
                "question_text": "What is the derivative of f(x) = sin(x)?",
                "question_type": "mcq",
                "points": 2,
                "explanation": "The derivative of sin(x) is cos(x) — a standard result.",
                "options": [
                    {"option_text": "cos(x)",   "is_correct": True},
                    {"option_text": "-cos(x)",  "is_correct": False},
                    {"option_text": "tan(x)",   "is_correct": False},
                    {"option_text": "-sin(x)",  "is_correct": False},
                ],
            },
        ],
    },
]


def seed_quizzes():
    with app.app_context():
        db.create_all()
        created = 0

        for qdata in DEMO_QUIZZES:
            # ── Resolve faculty ────────────────────────────────────────────
            faculty = User.query.filter_by(user_id=qdata["faculty_user_id"]).first()
            if not faculty:
                print(f"  SKIP: faculty {qdata['faculty_user_id']} not found — run seed.py first")
                continue

            # ── Resolve course ─────────────────────────────────────────────
            course = Course.query.filter_by(course_code=qdata["course_code"]).first()
            if not course:
                print(f"  SKIP: course {qdata['course_code']} not found — run seed.py first")
                continue

            # ── Skip if quiz already exists ────────────────────────────────
            existing = Quiz.query.filter_by(
                title=qdata["title"], course_id=course.id
            ).first()
            if existing:
                print(f"  EXISTS: '{qdata['title']}' — skipping")
                continue

            # ── Create quiz ────────────────────────────────────────────────
            quiz = Quiz(
                title               = qdata["title"],
                description         = qdata["description"],
                course_id           = course.id,
                faculty_id          = faculty.id,
                time_limit_minutes  = qdata["time_limit_minutes"],
                max_attempts        = qdata["max_attempts"],
                pass_score          = qdata["pass_score"],
                show_answers_after  = qdata["show_answers_after"],
                is_published        = qdata["is_published"],
            )
            db.session.add(quiz)
            db.session.flush()   # get quiz.id

            # ── Add questions & options ────────────────────────────────────
            for qi, qitem in enumerate(qdata["questions"]):
                question = QuizQuestion(
                    quiz_id       = quiz.id,
                    question_text = qitem["question_text"],
                    question_type = qitem["question_type"],
                    points        = qitem["points"],
                    order_index   = qi,
                    explanation   = qitem.get("explanation", ""),
                )
                db.session.add(question)
                db.session.flush()   # get question.id

                for oi, opt in enumerate(qitem["options"]):
                    db.session.add(QuizOption(
                        question_id = question.id,
                        option_text = opt["option_text"],
                        is_correct  = opt["is_correct"],
                        order_index = oi,
                    ))

            db.session.commit()
            total_pts = sum(q["points"] for q in qdata["questions"])
            status = "PUBLISHED" if qdata["is_published"] else "draft"
            print(f"  [{status}] '{qdata['title']}' — {len(qdata['questions'])} questions, {total_pts} pts  ({qdata['course_code']})")
            created += 1

        print(f"\nDone. {created} demo quiz(es) created.")


if __name__ == "__main__":
    seed_quizzes()
