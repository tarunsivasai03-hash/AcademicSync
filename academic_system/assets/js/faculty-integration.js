/**
 * Faculty Dashboard Integration
 * Sample JavaScript code showing how to integrate faculty backend APIs
 */

// Use the global api instance created by api.js (window.api)
// DO NOT re-declare 'const api' here — api.js already sets window.api

/**
 * Faculty Dashboard Functions
 */
async function loadFacultyDashboard() {
    try {
        const stats = await api.getFacultyDashboardStats();

        // Update dashboard cards
        document.getElementById('total-courses').textContent = stats.courses_count;
        document.getElementById('total-students').textContent = stats.students_count;
        document.getElementById('total-assignments').textContent = stats.assignments?.total ?? 0;
        document.getElementById('pending-grading').textContent = stats.pending_grading ?? 0;

        // Load course statistics
        loadCourseStats(stats.course_stats);

        // Load recent activities
        loadRecentActivities(stats.recent_activities);

    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Failed to load dashboard data', 'error');
    }
}

function loadCourseStats(courseStats) {
    const container = document.getElementById('course-stats');
    container.innerHTML = '';

    courseStats.forEach(course => {
        const courseCard = `
            <div class="bg-white p-4 rounded-lg shadow">
                <h3 class="font-semibold">${course.course_code}</h3>
                <p class="text-gray-600">${course.course_name}</p>
                <div class="mt-2 text-sm text-gray-500">
                    <p>Students: ${course.enrolled_students}</p>
                    <p>Assignments: ${course.assignments_count}</p>
                    <p>Avg Grade: ${course.avg_grade ? course.avg_grade.toFixed(1) : 'N/A'}</p>
                </div>
            </div>
        `;
        container.innerHTML += courseCard;
    });
}

function loadRecentActivities(activities) {
    const container = document.getElementById('recent-activities');
    container.innerHTML = '';

    activities.forEach(activity => {
        const activityItem = `
            <div class="flex justify-between items-center p-3 border-b">
                <div>
                    <p class="font-medium">${activity.student_name}</p>
                    <p class="text-sm text-gray-600">${activity.item_title}</p>
                    <p class="text-xs text-gray-500">${activity.course_code}</p>
                </div>
                <div class="text-right">
                    <span class="px-2 py-1 text-xs rounded-full ${getStatusColor(activity.status)}">
                        ${activity.status}
                    </span>
                    <p class="text-xs text-gray-500 mt-1">
                        ${new Date(activity.activity_date).toLocaleDateString()}
                    </p>
                </div>
            </div>
        `;
        container.innerHTML += activityItem;
    });
}

/**
 * Course Management Functions
 */
async function loadFacultyCourses() {
    try {
        const courses = await api.getFacultyCourses();
        displayCourses(courses);
    } catch (error) {
        console.error('Error loading courses:', error);
        showNotification('Failed to load courses', 'error');
    }
}

function displayCourses(courses) {
    const container = document.getElementById('courses-container');
    container.innerHTML = '';

    courses.forEach(course => {
        const courseCard = `
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-semibold">${course.course_code}</h3>
                        <h4 class="text-gray-600">${course.course_name}</h4>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="editCourse(${course.id})" class="text-blue-600 hover:text-blue-800">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button onclick="viewCourseDetails(${course.id})" class="text-green-600 hover:text-green-800">
                            <i class="bi bi-eye"></i>
                        </button>
                    </div>
                </div>
                <p class="text-gray-700 mb-3">${course.description}</p>
                <div class="grid grid-cols-3 gap-4 text-sm">
                    <div>
                        <span class="text-gray-500">Students:</span>
                        <span class="font-medium">${course.enrolled_students}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Assignments:</span>
                        <span class="font-medium">${course.assignments_count}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Resources:</span>
                        <span class="font-medium">${course.resources_count}</span>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += courseCard;
    });
}

async function createNewCourse() {
    const formData = {
        course_code: document.getElementById('course-code').value,
        course_name: document.getElementById('course-name').value,
        description: document.getElementById('course-description').value,
        credits: parseInt(document.getElementById('course-credits').value),
        department: document.getElementById('course-department').value,
        semester: document.getElementById('course-semester').value,
        max_students: parseInt(document.getElementById('max-students').value)
    };

    try {
        await api.createCourse(formData);
        showNotification('Course created successfully', 'success');
        loadFacultyCourses(); // Refresh course list
        closeModal('create-course-modal');
    } catch (error) {
        console.error('Error creating course:', error);
        showNotification(error.message, 'error');
    }
}

/**
 * Assignment Management Functions
 */
async function loadFacultyAssignments() {
    try {
        const assignments = await api.getFacultyAssignments();
        displayAssignments(assignments);
    } catch (error) {
        console.error('Error loading assignments:', error);
        showNotification('Failed to load assignments', 'error');
    }
}

function displayAssignments(assignments) {
    const container = document.getElementById('assignments-container');
    container.innerHTML = '';

    assignments.forEach(assignment => {
        const dueDate = new Date(assignment.due_date);
        const isOverdue = dueDate < new Date();

        const assignmentCard = `
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-semibold">${assignment.title}</h3>
                        <p class="text-gray-600">${assignment.course_code} - ${assignment.course_name}</p>
                    </div>
                    <span class="px-3 py-1 text-sm rounded-full ${isOverdue ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                        ${isOverdue ? 'Past Due' : 'Active'}
                    </span>
                </div>
                <p class="text-gray-700 mb-3">${assignment.description}</p>
                <div class="grid grid-cols-2 gap-4 mb-4 text-sm">
                    <div>
                        <span class="text-gray-500">Due Date:</span>
                        <span class="font-medium">${dueDate.toLocaleDateString()}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Total Points:</span>
                        <span class="font-medium">${assignment.total_points}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Submissions:</span>
                        <span class="font-medium">${assignment.submissions_count}/${assignment.total_students}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Avg Grade:</span>
                        <span class="font-medium">${assignment.avg_grade ? assignment.avg_grade.toFixed(1) : 'N/A'}</span>
                    </div>
                </div>
                <div class="flex space-x-3">
                    <button onclick="viewSubmissions(${assignment.id})" 
                            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        View Submissions
                    </button>
                    <button onclick="editAssignment(${assignment.id})" 
                            class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
                        Edit
                    </button>
                </div>
            </div>
        `;
        container.innerHTML += assignmentCard;
    });
}

async function viewSubmissions(assignmentId) {
    try {
        const submissions = await api.getAssignmentSubmissions(assignmentId);
        displaySubmissions(submissions);
        openModal('submissions-modal');
    } catch (error) {
        console.error('Error loading submissions:', error);
        showNotification('Failed to load submissions', 'error');
    }
}

function displaySubmissions(submissions) {
    const container = document.getElementById('submissions-container');
    container.innerHTML = '';

    submissions.forEach(submission => {
        const submissionRow = `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${submission.student_name}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">${new Date(submission.submitted_at).toLocaleString()}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <input type="number" value="${submission.grade || ''}" 
                           id="grade-${submission.id}" 
                           class="w-20 px-2 py-1 border rounded" 
                           max="${submission.total_points}" min="0">
                </td>
                <td class="px-6 py-4">
                    <textarea id="feedback-${submission.id}" 
                              class="w-full px-2 py-1 border rounded" 
                              placeholder="Enter feedback...">${submission.feedback || ''}</textarea>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="gradeSubmission(${submission.id})" 
                            class="text-indigo-600 hover:text-indigo-900">Grade</button>
                    ${submission.file_path ? `<a href="/api/uploads/${submission.file_path}" target="_blank" class="text-green-600 hover:text-green-900 ml-2">View</a>` : ''}
                </td>
            </tr>
        `;
        container.innerHTML += submissionRow;
    });
}

async function gradeSubmission(submissionId) {
    const grade = document.getElementById(`grade-${submissionId}`).value;
    const feedback = document.getElementById(`feedback-${submissionId}`).value;

    if (!grade) {
        showNotification('Please enter a grade', 'warning');
        return;
    }

    try {
        await api.gradeSubmission(submissionId, { grade: parseFloat(grade), feedback });
        showNotification('Submission graded successfully', 'success');
    } catch (error) {
        console.error('Error grading submission:', error);
        showNotification(error.message, 'error');
    }
}

/**
 * Resource Management Functions
 */
async function uploadResource() {
    const form = document.getElementById('resource-form');
    const formData = new FormData(form);

    try {
        await api.createFacultyResource(formData);
        showNotification('Resource uploaded successfully', 'success');
        loadFacultyResources(); // Refresh resource list
        form.reset();
        closeModal('upload-resource-modal');
    } catch (error) {
        console.error('Error uploading resource:', error);
        showNotification(error.message, 'error');
    }
}

/**
 * Student Management Functions
 */
async function loadCourseStudents(courseId) {
    try {
        const students = await api.getCourseStudents(courseId);
        displayCourseStudents(students);
    } catch (error) {
        console.error('Error loading students:', error);
        showNotification('Failed to load students', 'error');
    }
}

async function recordAttendance() {
    const courseId = document.getElementById('attendance-course').value;
    const date = document.getElementById('attendance-date').value;
    const attendanceData = {
        course_id: courseId,
        date: date,
        attendance: []
    };

    // Collect attendance data from checkboxes
    document.querySelectorAll('.attendance-checkbox').forEach(checkbox => {
        attendanceData.attendance.push({
            student_id: checkbox.dataset.studentId,
            status: checkbox.checked ? 'present' : 'absent'
        });
    });

    try {
        await api.recordAttendance(attendanceData);
        showNotification('Attendance recorded successfully', 'success');
    } catch (error) {
        console.error('Error recording attendance:', error);
        showNotification(error.message, 'error');
    }
}

/**
 * Utility Functions
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${getNotificationColor(type)}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function getNotificationColor(type) {
    const colors = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-black',
        info: 'bg-blue-500 text-white'
    };
    return colors[type] || colors.info;
}

function getStatusColor(status) {
    const colors = {
        submitted: 'bg-blue-100 text-blue-800',
        graded: 'bg-green-100 text-green-800',
        late: 'bg-red-100 text-red-800',
        draft: 'bg-gray-100 text-gray-800'
    };
    return colors[status] || colors.draft;
}

function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

/**
 * Initialize faculty portal when page loads
 */
document.addEventListener('DOMContentLoaded', function () {
    // Check authentication
    if (!api.checkAuth() || api.currentUser?.role !== 'faculty') {
        window.location.href = 'faculty-login.html';
        return;
    }

    // Load dashboard data based on current page
    const currentPage = window.location.pathname;

    if (currentPage.includes('faculty-dashboard.html')) {
        loadFacultyDashboard();
    } else if (currentPage.includes('faculty-courses.html')) {
        loadFacultyCourses();
    } else if (currentPage.includes('faculty-assignments.html')) {
        loadFacultyAssignments();
    }
});

// Export functions for global use
window.facultyPortal = {
    loadFacultyDashboard,
    loadFacultyCourses,
    createNewCourse,
    loadFacultyAssignments,
    viewSubmissions,
    gradeSubmission,
    uploadResource,
    recordAttendance,
    showNotification
};