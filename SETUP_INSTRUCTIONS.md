# AcademicSync Setup Instructions

Complete setup guide for running the AcademicSync system with Flask backend and frontend integration.

## 📋 Prerequisites

### Required Software
- **Python 3.8+** - Download from [python.org](https://python.org)
- **Web Browser** - Chrome, Firefox, Safari, or Edge
- **Code Editor** (Optional) - VS Code, Sublime Text, or any editor

### System Requirements
- **Operating System:** Windows 10+, macOS 10.14+, or Linux
- **RAM:** 2GB minimum (4GB recommended)
- **Storage:** 1GB free space
- **Network:** Internet connection for initial setup

## 🚀 Quick Start (Automated Setup)

### Windows Users
1. **Navigate to backend directory:**
   ```cmd
   cd backend
   ```

2. **Run the setup script:**
   ```cmd
   setup.bat
   ```

### Mac/Linux Users
1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Make the script executable and run:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

## 🛠️ Manual Setup

### Step 1: Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or for Python 3 specifically:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Initialize database with sample data:**
   ```bash
   python database.py
   ```

4. **Start the Flask server:**
   ```bash
   python run.py
   ```

   The server will start at: `http://localhost:5000`

### Step 2: Frontend Setup

1. **Open any web browser**

2. **Navigate to the frontend files:**
   - Open `academic_system/index.html` in your browser
   - Or use Live Server extension in VS Code
   - Or serve via any local web server

### Step 3: Test the Integration

1. **Open the API example page:**
   - Navigate to `academic_system/student/api-example.html`
   - This page tests backend connectivity

2. **Test user login:**
   - Use sample credentials (see below)
   - Verify dashboard stats load correctly

## 👥 Sample User Accounts

The system comes pre-populated with test accounts:

### Students
- **STU001** through **STU011** — Password: `student123`

### Faculty
- **FAC001** through **FAC004** — Password: `faculty123`

### Admin
- **ADM001** — Password: `admin123`

## 🌐 Accessing the System

### Student Portal
1. **Open:** `http://localhost:3000/student/student-login.html`
2. **Login with:** Any student account (STU001–STU011)
3. **Password:** `student123`
4. **Explore:** Dashboard, Courses, Assignments, Resources, Schedule

### Faculty Portal
1. **Open:** `http://localhost:3000/faculty/faculty-login.html`
2. **Login with:** Any faculty account (FAC001–FAC004)
3. **Password:** `faculty123`
4. **Explore:** Dashboard, Courses, Students, Resources, Grades

### Admin Portal
1. **Open:** `http://localhost:3000/admin/admin-login.html`
2. **Login with:** `ADM001`
3. **Password:** `admin123`

## 🔧 Configuration

### Backend Configuration
- **Config file:** `backend/config.py`
- **Database:** SQLite file `backend/academic_system.db`
- **Upload directory:** `backend/uploads/`
- **Default port:** 5000

### Frontend Configuration
- **API client:** `academic_system/assets/js/api.js`
- **Default API URL:** `http://localhost:5000`
- **Styles:** `academic_system/assets/css/`

## 📊 Available Features

### Student Features
✅ **Authentication** - Login/logout with session management  
✅ **Dashboard** - GPA, attendance, course statistics  
✅ **Courses** - View enrolled courses and details  
✅ **Assignments** - View, submit, track deadlines  
✅ **Resources** - Access course materials  
✅ **Schedule** - Class timetables and calendar  
✅ **Profile** - Update personal information  

### Faculty Features
✅ **Course Management** - Create and manage courses  
✅ **Resource Sharing** - Upload and organize materials  
✅ **Assignment Creation** - Create and grade assignments  
✅ **Student Tracking** - Monitor student progress  
✅ **Grade Management** - Record and update grades  

### Technical Features
✅ **REST API** - Complete RESTful backend  
✅ **File Upload** - Assignment submission support  
✅ **Dark Mode** - Light/dark theme toggle  
✅ **Responsive Design** - Mobile-friendly interface  
✅ **Real-time Updates** - Dynamic content loading  

## 🐛 Troubleshooting

### Common Issues

#### "Python not found"
**Solution:** Install Python from [python.org](https://python.org) and add to PATH

#### "pip not found"
**Solution:** 
```bash
python -m pip install -r requirements.txt
```

#### "Port 5000 already in use"
**Solution:** Kill existing process or change port in `run.py`

#### "CORS errors in browser"
**Solution:** 
- Ensure backend is running on localhost:5000
- Check browser console for specific errors
- Verify API base URL in frontend

#### "Database locked"
**Solution:** 
```bash
# Delete and recreate database
rm academic_system.db
python database.py
```

#### "API connection failed"
**Solution:** 
1. Verify backend is running: http://localhost:5000/api/health
2. Check browser network tab for request errors
3. Ensure CORS is properly configured

### Debug Mode

To run in debug mode with detailed logging:
```bash
export FLASK_DEBUG=1  # Linux/Mac
set FLASK_DEBUG=1     # Windows
python run.py
```

### Reset Everything

To completely reset the system:
```bash
# Backend
rm academic_system.db uploads/*
python database.py

# Frontend - Clear browser cache and localStorage
```

## 📱 Browser Compatibility

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Full Support |
| Firefox | 88+ | ✅ Full Support |
| Safari | 14+ | ✅ Full Support |
| Edge | 90+ | ✅ Full Support |

## 🔒 Security Notes

- **Development Only:** Current setup is for development/demo only
- **Change Credentials:** Update default passwords in production
- **HTTPS:** Use SSL certificates in production
- **Database:** Use PostgreSQL/MySQL in production
- **Secret Key:** Update Flask secret key

## 📚 Next Steps

1. **Explore the Interface:** Try different user accounts and features
2. **Review the Code:** Understand the architecture and components
3. **Customize:** Modify styling, add features, or integrate with other systems
4. **Deploy:** Set up for production use with proper security

## 🆘 Getting Help

### Documentation
- **Backend API:** Check `backend/README.md`
- **Frontend Examples:** See `student/api-example.html`
- **Database Schema:** Review `backend/database.py`

### Support Resources
- **Flask Documentation:** [flask.palletsprojects.com](https://flask.palletsprojects.com)
- **Tailwind CSS:** [tailwindcss.com](https://tailwindcss.com)
- **Alpine.js:** [alpinejs.dev](https://alpinejs.dev)

---

**🎉 Congratulations!** You now have a fully functional Academic Management System with Flask backend and modern frontend integration.