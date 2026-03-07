"""
Seed script — populates the database with realistic sample data.

Run with:
    cd backend
    python seed.py

Safe to run multiple times; existing data will be preserved.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, StudentProfile, FacultyProfile, AdminProfile, Department, SystemSetting
from app.models.course import AcademicYear, Semester, Course, Enrollment
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.attendance import Attendance
from app.models.resource import Resource
from app.models.schedule import CourseSession
from app.models.task import Task
from app.models.notification import Notification

app = create_app("development")


def seed():
    with app.app_context():
        db.create_all()
        print("Tables created.")

        # ── Departments ────────────────────────────────────────────────────
        dept_data = [
            ("Computer Science", "CS"),
            ("Mathematics",      "MTH"),
            ("Physics",          "PHY"),
            ("Business Admin",   "BBA"),
            ("Electrical Eng.",  "EE"),
        ]
        depts = {}
        for name, code in dept_data:
            d = Department.query.filter_by(code=code).first()
            if not d:
                d = Department(name=name, code=code)
                db.session.add(d)
                db.session.flush()
                print(f"  Dept: {name}")
            depts[code] = d
        db.session.commit()

        # ── Academic Year & Semester ───────────────────────────────────────
        ay = AcademicYear.query.filter_by(year_label="2025-2026").first()
        if not ay:
            ay = AcademicYear(
                year_label = "2025-2026",
                start_date = date(2025, 9, 1),
                end_date   = date(2026, 6, 30),
                is_current = True,
            )
            db.session.add(ay)
            db.session.flush()
            print("  AcademicYear: 2025-2026")

        sem = Semester.query.filter_by(name="Fall 2025").first()
        if not sem:
            sem = Semester(
                name             = "Fall 2025",
                semester_type    = "fall",
                academic_year_id = ay.id,
                start_date       = date(2025, 9, 1),
                end_date         = date(2026, 1, 15),
                is_current       = True,
            )
            db.session.add(sem)
            db.session.flush()
            print("  Semester: Fall 2025")
        db.session.commit()

        # ── Admin ──────────────────────────────────────────────────────────
        admin = User.query.filter_by(user_id="ADM001").first()
        if not admin:
            admin = User(
                user_id="ADM001", full_name="Michael Rodriguez",
                email="admin@academic.edu", role="admin",
                department="Administration",
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.flush()
            db.session.add(AdminProfile(
                user_id      = admin.id,
                access_level = "super",
                notes        = "System administrator",
            ))
            print("  Admin: ADM001 / admin123")
        db.session.commit()

        # ── Faculty ────────────────────────────────────────────────────────
        faculty_data = [
            ("FAC001", "Dr. Sarah Thompson",    "s.thompson@academic.edu",  "CS",  "Algorithms & AI"),
            ("FAC002", "Prof. James Wilson",    "j.wilson@academic.edu",    "MTH", "Calculus & Linear Algebra"),
            ("FAC003", "Dr. Emily Chen",        "e.chen@academic.edu",      "PHY", "Quantum Mechanics"),
            ("FAC004", "Prof. Robert Martinez", "r.martinez@academic.edu",  "BBA", "Finance & Economics"),
        ]
        faculty_objs = {}
        for uid, name, email, dept_code, spec in faculty_data:
            f = User.query.filter_by(user_id=uid).first()
            if not f:
                f = User(
                    user_id=uid, full_name=name, email=email,
                    role="faculty",
                    department=depts[dept_code].name,
                    department_id=depts[dept_code].id,
                )
                f.set_password("faculty123")
                db.session.add(f)
                db.session.flush()
                db.session.add(FacultyProfile(user_id=f.id, specialization=spec))
                print(f"  Faculty: {uid}")
            faculty_objs[uid] = f
        db.session.commit()

        # ── Students ───────────────────────────────────────────────────────
        student_data = [
            ("STU001", "Alice Johnson",   "a.johnson@student.edu",  "CS",  1),
            ("STU002", "Bob Williams",    "b.williams@student.edu", "CS",  2),
            ("STU003", "Clara Davis",     "c.davis@student.edu",    "MTH", 1),
            ("STU004", "Daniel Moore",    "d.moore@student.edu",    "PHY", 3),
            ("STU005", "Eva Martinez",    "e.martinez@student.edu", "BBA", 2),
            ("STU006", "Frank Taylor",    "f.taylor@student.edu",   "CS",  3),
            ("STU007", "Grace Anderson",  "g.anderson@student.edu", "EE",  1),
            ("STU008", "Henry Thomas",    "h.thomas@student.edu",   "CS",  4),
            ("STU009", "Isabella Brown",  "i.brown@student.edu",    "MTH", 2),
            ("STU010", "James Wilson Jr", "j.wilson2@student.edu",  "PHY", 1),
        ]
        student_objs = {}
        for uid, name, email, dept_code, year in student_data:
            s = User.query.filter_by(user_id=uid).first()
            if not s:
                s = User(
                    user_id=uid, full_name=name, email=email,
                    role="student",
                    department=depts[dept_code].name,
                    department_id=depts[dept_code].id,
                    phone=f"+1555{uid[-3:]}000",
                )
                s.set_password("student123")
                db.session.add(s)
                db.session.flush()
                db.session.add(StudentProfile(user_id=s.id, year=year, gpa=3.2, attendance_pct=85.0))
                print(f"  Student: {uid}")
            student_objs[uid] = s
        db.session.commit()

        # ── Courses ────────────────────────────────────────────────────────
        course_data = [
            ("CS101", "Introduction to Programming",     "CS",  3, "FAC001"),
            ("CS201", "Data Structures & Algorithms",    "CS",  4, "FAC001"),
            ("MTH101","Calculus I",                      "MTH", 3, "FAC002"),
            ("PHY201","Classical Mechanics",             "PHY", 3, "FAC003"),
            ("BBA101","Principles of Management",        "BBA", 3, "FAC004"),
        ]
        course_objs = {}
        for code, name, dept_code, credits, fac_uid in course_data:
            c = Course.query.filter_by(course_code=code).first()
            fac = faculty_objs.get(fac_uid)
            if not c:
                c = Course(
                    course_code  = code,
                    course_name  = name,
                    credits      = credits,
                    department   = depts[dept_code].name,
                    department_id= depts[dept_code].id,
                    faculty_id   = fac.id if fac else None,
                    semester_id  = sem.id,
                    description  = f"Core {name} course for undergraduate students.",
                )
                db.session.add(c)
                db.session.flush()
                print(f"  Course: {code}")
            else:
                if fac:
                    c.faculty_id = fac.id
                c.semester_id = sem.id
            course_objs[code] = c
        db.session.commit()

        # ── Course Sessions ────────────────────────────────────────────────
        session_data = [
            ("CS101",  "Monday",    "09:00", "10:30", "Room 101", "lecture"),
            ("CS101",  "Wednesday", "09:00", "10:30", "Room 101", "lecture"),
            ("CS201",  "Tuesday",   "11:00", "12:30", "Room 205", "lecture"),
            ("CS201",  "Thursday",  "11:00", "12:30", "Room 205", "lab"),
            ("MTH101", "Monday",    "14:00", "15:30", "Room 302", "lecture"),
            ("MTH101", "Friday",    "14:00", "15:30", "Room 302", "tutorial"),
            ("PHY201", "Tuesday",   "09:00", "10:30", "Lab A",    "lecture"),
            ("PHY201", "Thursday",  "09:00", "10:30", "Lab A",    "lab"),
            ("BBA101", "Wednesday", "13:00", "14:30", "Room 110", "lecture"),
            ("BBA101", "Friday",    "13:00", "14:30", "Room 110", "lecture"),
        ]
        for code, day, start, end, room, stype in session_data:
            course = course_objs.get(code)
            if not course:
                continue
            exists = CourseSession.query.filter_by(
                course_id=course.id, day_of_week=day, start_time=start
            ).first()
            if not exists:
                db.session.add(CourseSession(
                    course_id    = course.id,
                    day_of_week  = day,
                    start_time   = start,
                    end_time     = end,
                    room         = room,
                    session_type = stype,
                ))
        db.session.commit()
        print("  Course sessions created.")

        # ── Enrollments ────────────────────────────────────────────────────
        enrollment_map = {
            "STU001": ["CS101", "CS201", "MTH101"],
            "STU002": ["CS101", "CS201"],
            "STU003": ["MTH101", "PHY201"],
            "STU004": ["PHY201", "MTH101"],
            "STU005": ["BBA101"],
            "STU006": ["CS201", "CS101"],
            "STU007": ["CS101", "MTH101"],
            "STU008": ["CS201", "BBA101"],
            "STU009": ["MTH101"],
            "STU010": ["PHY201", "CS101"],
        }
        for uid, codes in enrollment_map.items():
            student = student_objs.get(uid)
            if not student:
                continue
            for code in codes:
                course = course_objs.get(code)
                if not course:
                    continue
                exists = Enrollment.query.filter_by(
                    student_id=student.id, course_id=course.id
                ).first()
                if not exists:
                    grade = "A" if uid in ("STU001", "STU003") else (
                            "B+" if uid in ("STU002", "STU006") else "B")
                    db.session.add(Enrollment(
                        student_id  = student.id,
                        course_id   = course.id,
                        grade       = grade,
                        grade_points= {"A": 4.0, "B+": 3.3, "B": 3.0}.get(grade, 3.0),
                    ))
        db.session.commit()
        print("  Enrollments created.")

        # ── Assignments ────────────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        assignment_data = [
            ("CS101",  "Hello World Project",       "homework", now + timedelta(days=7),  100),
            ("CS101",  "Variables & Control Flow",  "homework", now + timedelta(days=14), 100),
            ("CS201",  "Linked List Implementation","project",  now + timedelta(days=10), 150),
            ("CS201",  "Binary Search Tree",        "project",  now + timedelta(days=21), 150),
            ("MTH101", "Limits Quiz",               "quiz",     now + timedelta(days=5),   50),
            ("MTH101", "Derivatives Assignment",    "homework", now + timedelta(days=12), 100),
            ("PHY201", "Newton's Laws Essay",       "homework", now + timedelta(days=8),  100),
            ("BBA101", "Management Case Study",     "project",  now + timedelta(days=15), 200),
        ]
        assign_objs = []
        for code, title, atype, due, points in assignment_data:
            course = course_objs.get(code)
            if not course or not course.faculty_id:
                continue
            exists = Assignment.query.filter_by(title=title, course_id=course.id).first()
            if not exists:
                a = Assignment(
                    title           = title,
                    course_id       = course.id,
                    faculty_id      = course.faculty_id,
                    assignment_type = atype,
                    due_date        = due,
                    total_points    = points,
                    description     = f"Please complete the {title} task as instructed.",
                )
                db.session.add(a)
                assign_objs.append((a, code))
        db.session.commit()
        print("  Assignments created.")

        # ── Auto-tasks for enrolled students ───────────────────────────────
        for a, code in assign_objs:
            course = course_objs.get(code)
            if not course:
                continue
            enrolled = [
                e.student_id for e in
                Enrollment.query.filter_by(course_id=course.id, status="active").all()
            ]
            for sid in enrolled:
                exists = Task.query.filter_by(user_id=sid, assignment_id=a.id).first()
                if not exists:
                    db.session.add(Task(
                        user_id       = sid,
                        assignment_id = a.id,
                        title         = a.title,
                        description   = f"Complete assignment for {course.course_name}",
                        due_date      = a.due_date,
                        priority      = "medium",
                    ))
        db.session.commit()
        print("  Auto-tasks created for students.")

        # ── Resources ──────────────────────────────────────────────────────
        resource_data = [
            ("CS101",  "Python Basics Slides",    "slides",   "FAC001", "enrolled"),
            ("CS101",  "Week 1 Lecture Notes",    "pdf",      "FAC001", "enrolled"),
            ("CS201",  "DSA Reference Guide",     "document", "FAC001", "all"),
            ("MTH101", "Calculus Textbook Ch.1",  "pdf",      "FAC002", "enrolled"),
            ("PHY201", "Physics Formula Sheet",   "document", "FAC003", "all"),
            ("BBA101", "Management Theories PDF", "pdf",      "FAC004", "enrolled"),
        ]
        for code, title, rtype, fac_uid, visibility in resource_data:
            course = course_objs.get(code)
            fac    = faculty_objs.get(fac_uid)
            if not course or not fac:
                continue
            exists = Resource.query.filter_by(title=title, course_id=course.id).first()
            if not exists:
                db.session.add(Resource(
                    title       = title,
                    course_id   = course.id,
                    faculty_id  = fac.id,
                    resource_type = rtype,
                    visibility  = visibility,
                    description = f"Course material: {title}",
                ))
        db.session.commit()
        print("  Resources created.")

        # ── Attendance Records (past 8 weeks) ─────────────────────────────
        import random
        random.seed(42)   # deterministic run
        today = date.today()
        # Simulate 8 weeks of class days (Mon/Wed or Tue/Thu depending on course)
        class_weekdays = {
            "CS101":  [0, 2],   # Mon, Wed
            "CS201":  [1, 3],   # Tue, Thu
            "MTH101": [0, 4],   # Mon, Fri
            "PHY201": [1, 3],   # Tue, Thu
            "BBA101": [2, 4],   # Wed, Fri
        }
        attendance_weights = {
            # (present_prob, absent_prob, late_prob)
            "STU001": (0.92, 0.04, 0.04),
            "STU002": (0.85, 0.10, 0.05),
            "STU003": (0.95, 0.03, 0.02),
            "STU004": (0.78, 0.15, 0.07),
            "STU005": (0.88, 0.08, 0.04),
            "STU006": (0.82, 0.12, 0.06),
            "STU007": (0.90, 0.06, 0.04),
            "STU008": (0.75, 0.18, 0.07),
            "STU009": (0.93, 0.04, 0.03),
            "STU010": (0.80, 0.14, 0.06),
        }
        for uid, codes in enrollment_map.items():
            student = student_objs.get(uid)
            if not student:
                continue
            weights = attendance_weights.get(uid, (0.85, 0.10, 0.05))
            statuses = ["present", "absent", "late"]
            for code in codes:
                course = course_objs.get(code)
                if not course:
                    continue
                weekdays = class_weekdays.get(code, [0, 2])
                # Go back 8 weeks
                for week in range(8, 0, -1):
                    for wd in weekdays:
                        # Find the date of that weekday in that week
                        days_back = (today.weekday() - wd) % 7 + (week - 1) * 7
                        class_date = today - timedelta(days=days_back)
                        if class_date >= today:
                            continue
                        exists = Attendance.query.filter_by(
                            student_id=student.id,
                            course_id=course.id,
                            date=class_date
                        ).first()
                        if not exists:
                            status = random.choices(statuses, weights=weights)[0]
                            db.session.add(Attendance(
                                student_id  = student.id,
                                course_id   = course.id,
                                date        = class_date,
                                status      = status,
                                recorded_by = course.faculty_id,
                            ))
        db.session.commit()
        print("  Attendance records created.")

        # ── Sample Submissions ─────────────────────────────────────────────
        # STU001 submits all their assignments; others submit some
        all_assignments = Assignment.query.all()
        for a in all_assignments:
            enrolled_students = [
                e.student_id for e in
                Enrollment.query.filter_by(course_id=a.course_id, status="active").all()
            ]
            for sid in enrolled_students:
                student = db.session.get(User, sid)
                if not student:
                    continue
                uid = student.user_id
                # STU001 always submits; others 60% chance
                if uid != "STU001" and random.random() > 0.60:
                    continue
                exists = Submission.query.filter_by(
                    assignment_id=a.id, student_id=sid
                ).first()
                if not exists:
                    score = round(random.uniform(70, 100) / 100 * a.total_points, 1)
                    db.session.add(Submission(
                        assignment_id   = a.id,
                        student_id      = sid,
                        submission_text = f"Submission for {a.title} by {student.full_name}.",
                        grade           = score,
                        status          = "graded",
                        submitted_at    = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5)),
                        graded_at       = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 2)),
                        feedback        = "Good work! Keep it up.",
                    ))
        db.session.commit()
        print("  Sample submissions created.")

        # ── Sample Notifications for STU001 ───────────────────────────────
        stu1 = student_objs.get("STU001")
        if stu1 and stu1.notifications.count() == 0:
            db.session.add(Notification(
                user_id           = stu1.id,
                title             = "Welcome to AcademicSync!",
                message           = "Your student account is ready. Explore your dashboard.",
                notification_type = "info",
            ))
            db.session.add(Notification(
                user_id           = stu1.id,
                title             = "Assignment Due Soon",
                message           = "Hello World Project is due in 7 days.",
                notification_type = "assignment",
            ))
        db.session.commit()

        # ── System Settings ────────────────────────────────────────────────
        SystemSetting.set_many({
            "institution_name":   "AcademicSync University",
            "academic_year":      "2025-2026",
            "current_semester":   "Fall 2025",
            "max_enrollment":     "50",
            "gpa_scale":          "4.0",
            "late_submission":    "true",
            "email_notifications":"true",
        })
        db.session.commit()
        print("  Settings seeded.")

        print("\n" + "="*50)
        print("  Seed complete!")
        print("="*50)
        print("\n  Login credentials:")
        print("  Admin:   ADM001 / admin123")
        print("  Faculty: FAC001 / faculty123")
        print("  Student: STU001 / student123")
        print()


if __name__ == "__main__":
    seed()