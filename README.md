# AcademicSync

**AcademicSync** is a Smart Academic Management System built with a modern decoupled architecture — an Alpine.js + Tailwind CSS frontend with a Flask REST API backend.

## Features

### Student Portal
- Dashboard with upcoming deadlines & stats
- Assignment submission (file + text) with status tracking
- Attendance records & grade book
- Quiz taking, course resources, schedules
- Personal task manager & announcements

### Faculty Portal
- Assignment creation, management & grading
- Submission viewer (file preview, inline grading)
- Export submissions report as CSV/Excel
- Attendance marking, grade book, quiz builder
- Course resources management & class schedules

### Admin Portal
- System-wide dashboard & analytics
- User management (students, faculty, admins)
- Course & department management
- Post announcements & system settings

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Alpine.js 3.13.3 + Tailwind CSS |
| Icons | Remix Icons + LineIcons |
| Backend | Flask 3.1.0 (Python) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (flask-jwt-extended) |
| Migrations | Flask-Migrate |

## Project Structure

```
smart_academic_system/
├── academic_system/        # Frontend (HTML + Alpine.js)
│   ├── student/            # Student pages
│   ├── faculty/            # Faculty pages
│   ├── admin/              # Admin pages
│   └── assets/             # CSS, JS, fonts
├── backend/                # Flask REST API
│   ├── app/
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routes/         # API blueprints
│   │   ├── services/       # Business logic
│   │   └── utils/          # Helpers & validators
│   ├── config.py
│   ├── run.py
│   └── requirements.txt
└── start.bat               # One-click dev server launcher
```

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
flask db upgrade
python run.py
```

### Frontend
Open `academic_system/index.html` in a browser, or serve via a local server.

The frontend connects to `http://localhost:5000` by default.

## License
MIT
