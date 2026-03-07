/**
 * Admin Portal Integration
 * Complete JavaScript code for admin system management
 */

// Use the global api instance created by api.js (window.api)
// DO NOT re-declare 'const api' here — api.js already sets window.api

/**
 * Admin Dashboard Functions
 */
async function loadAdminDashboard() {
    try {
        const stats = await api.getAdminDashboardStats();

        // Update dashboard overview cards
        document.getElementById('total-users').textContent =
            Object.values(stats.users).reduce((sum, count) => sum + count, 0);
        document.getElementById('total-courses').textContent = stats.courses.total_courses;
        document.getElementById('total-assignments').textContent = stats.assignments.total_assignments;
        document.getElementById('system-storage').textContent =
            `${(stats.resources.total_storage_kb / 1024).toFixed(1)} MB`;

        // Update role-specific counts
        document.getElementById('student-count').textContent = stats.users.student || 0;
        document.getElementById('faculty-count').textContent = stats.users.faculty || 0;
        document.getElementById('admin-count').textContent = stats.users.admin || 0;

        // Load system metrics
        loadSystemMetrics(stats);

        // Load recent activities
        loadSystemActivities(stats.recent_activities);

        // Load performance indicators
        loadPerformanceIndicators(stats);

    } catch (error) {
        console.error('Error loading admin dashboard:', error);
        showNotification('Failed to load dashboard data', 'error');
    }
}

function loadSystemMetrics(stats) {
    // Course distribution chart data
    const courseMetrics = {
        totalCourses: stats.courses.total_courses,
        activeFaculty: stats.courses.active_faculty,
        departments: stats.courses.departments,
        avgEnrollment: stats.courses.avg_enrollment?.toFixed(1) || 'N/A'
    };

    // Update metrics display
    document.getElementById('active-faculty').textContent = courseMetrics.activeFaculty;
    document.getElementById('departments-count').textContent = courseMetrics.departments;
    document.getElementById('avg-enrollment').textContent = courseMetrics.avgEnrollment;

    // Assignment metrics
    document.getElementById('pending-grading').textContent = stats.assignments.pending_grading;
    document.getElementById('avg-system-grade').textContent =
        stats.assignments.avg_grade ? stats.assignments.avg_grade.toFixed(1) : 'N/A';

    // Attendance metrics
    document.getElementById('attendance-rate').textContent =
        `${stats.attendance.attendance_rate}%`;
}

function loadSystemActivities(activities) {
    const container = document.getElementById('system-activities');
    container.innerHTML = '';

    activities.forEach(activity => {
        const activityItem = `
            <div class="flex items-center justify-between p-3 border-b border-gray-200">
                <div class="flex items-center space-x-3">
                    <div class="p-1 rounded-full ${getActivityIconColor(activity.type)}">
                        <i class="bi bi-${getActivityIcon(activity.type)} text-white text-xs"></i>
                    </div>
                    <div>
                        <p class="font-medium text-gray-900">${activity.user_name}</p>
                        <p class="text-sm text-gray-600">${activity.description}</p>
                        <p class="text-xs text-gray-500">${activity.item_name}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-xs text-gray-500">
                        ${new Date(activity.activity_date).toLocaleString()}
                    </p>
                </div>
            </div>
        `;
        container.innerHTML += activityItem;
    });
}

function loadPerformanceIndicators(stats) {
    // Calculate system health score
    const healthFactors = [
        stats.attendance.attendance_rate / 100, // Attendance rate
        Math.min(stats.assignments.avg_grade / 90, 1) || 0, // Grade performance
        Math.min(stats.courses.avg_enrollment / 25, 1) || 0, // Enrollment efficiency
        Math.min(stats.resources.total_resources / 100, 1) || 0 // Resource availability
    ];

    const healthScore = (healthFactors.reduce((sum, factor) => sum + factor, 0) / healthFactors.length * 100).toFixed(1);

    document.getElementById('system-health-score').textContent = `${healthScore}%`;
    document.getElementById('system-health-bar').style.width = `${healthScore}%`;

    // Set health color
    const healthBar = document.getElementById('system-health-bar');
    if (healthScore >= 80) {
        healthBar.className = 'h-2 bg-green-500 rounded-full transition-all duration-300';
    } else if (healthScore >= 60) {
        healthBar.className = 'h-2 bg-yellow-500 rounded-full transition-all duration-300';
    } else {
        healthBar.className = 'h-2 bg-red-500 rounded-full transition-all duration-300';
    }
}

/**
 * User Management Functions
 */
async function loadUserManagement() {
    try {
        const result = await api.getAllUsers({ limit: 50, offset: 0 });
        displayUsers(result.users);
        updateUserPagination(result.total, result.limit, result.offset);
    } catch (error) {
        console.error('Error loading users:', error);
        showNotification('Failed to load users', 'error');
    }
}

function displayUsers(users) {
    const container = document.getElementById('users-table-body');
    container.innerHTML = '';

    users.forEach(user => {
        const userRow = `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="h-8 w-8 rounded-full ${getRoleColor(user.role)} flex items-center justify-center">
                            <span class="text-white text-xs font-medium">
                                ${user.full_name.charAt(0).toUpperCase()}
                            </span>
                        </div>
                        <div class="ml-3">
                            <div class="text-sm font-medium text-gray-900">${user.full_name}</div>
                            <div class="text-sm text-gray-500">${user.user_id}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">${user.email}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 text-xs font-semibold rounded-full ${getRoleBadgeColor(user.role)}">
                        ${user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${user.department || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(user.status)}">
                        ${user.status || 'active'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="editUser('${user.user_id}')" 
                            class="text-indigo-600 hover:text-indigo-900 mr-3">Edit</button>
                    <button onclick="confirmDeleteUser('${user.user_id}')" 
                            class="text-red-600 hover:text-red-900">Delete</button>
                </td>
            </tr>
        `;
        container.innerHTML += userRow;
    });
}

async function createNewUser() {
    const form = document.getElementById('create-user-form');
    const formData = new FormData(form);

    const userData = {
        user_id: formData.get('user_id'),
        full_name: formData.get('full_name'),
        email: formData.get('email'),
        password: formData.get('password'),
        role: formData.get('role'),
        department: formData.get('department'),
        year: formData.get('year') ? parseInt(formData.get('year')) : null,
        phone: formData.get('phone')
    };

    try {
        await api.createUser(userData);
        showNotification('User created successfully', 'success');
        loadUserManagement(); // Refresh user list
        closeModal('create-user-modal');
        form.reset();
    } catch (error) {
        console.error('Error creating user:', error);
        showNotification(error.message, 'error');
    }
}

async function editUser(userId) {
    try {
        // Get user details (you might need to add a getUserById method to API)
        // For now, we'll open the modal with empty fields
        openModal('edit-user-modal');
        document.getElementById('edit-user-id').value = userId;

        // In production, populate form with current user data
        showNotification('Edit user functionality ready', 'info');
    } catch (error) {
        console.error('Error editing user:', error);
        showNotification(error.message, 'error');
    }
}

async function confirmDeleteUser(userId) {
    if (confirm(`Are you sure you want to deactivate user ${userId}? This action cannot be undone.`)) {
        try {
            await api.deleteUser(userId);
            showNotification('User deactivated successfully', 'success');
            loadUserManagement(); // Refresh user list
        } catch (error) {
            console.error('Error deleting user:', error);
            showNotification(error.message, 'error');
        }
    }
}

async function searchUsers() {
    const searchTerm = document.getElementById('user-search').value;
    const roleFilter = document.getElementById('role-filter').value;

    try {
        const filters = {};
        if (searchTerm) filters.search = searchTerm;
        if (roleFilter) filters.role = roleFilter;

        const result = await api.getAllUsers(filters);
        displayUsers(result.users);
        updateUserPagination(result.total, result.limit, result.offset);
    } catch (error) {
        console.error('Error searching users:', error);
        showNotification('Search failed', 'error');
    }
}

/**
 * Course Management Functions
 */
async function loadCourseManagement() {
    try {
        const courses = await api.getAllCourses();
        displayAllCourses(courses);
    } catch (error) {
        console.error('Error loading courses:', error);
        showNotification('Failed to load courses', 'error');
    }
}

function displayAllCourses(courses) {
    const container = document.getElementById('admin-courses-container');
    container.innerHTML = '';

    courses.forEach(course => {
        const courseCard = `
            <div class="bg-white p-6 rounded-lg shadow-md border">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">${course.course_code}</h3>
                        <h4 class="text-gray-600">${course.course_name}</h4>
                        <p class="text-sm text-gray-500 mt-1">${course.department}</p>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="reassignFaculty(${course.id})" 
                            class="text-blue-600 hover:text-blue-800" title="Reassign Faculty">
                        <i class="bi bi-person-gear"></i>
                    </button>
                    <button onclick="console.log('Analytics for course', ${course.id})" 
                            class="text-green-600 hover:text-green-800" title="View Analytics">
                        <i class="bi bi-graph-up"></i>
                    </button>
                    </div>
                </div>
                
                <div class="mb-3">
                    <p class="text-sm text-gray-700">${course.description}</p>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-3 text-sm">
                    <div>
                        <span class="text-gray-500">Faculty:</span>
                        <span class="font-medium ml-1">${course.faculty_name || 'Unassigned'}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Credits:</span>
                        <span class="font-medium ml-1">${course.credits}</span>
                    </div>
                </div>
                
                <div class="grid grid-cols-3 gap-4 text-sm">
                    <div class="text-center p-2 bg-blue-50 rounded">
                        <div class="font-semibold text-blue-800">${course.enrolled_students}</div>
                        <div class="text-blue-600 text-xs">Students</div>
                    </div>
                    <div class="text-center p-2 bg-green-50 rounded">
                        <div class="font-semibold text-green-800">${course.assignments_count}</div>
                        <div class="text-green-600 text-xs">Assignments</div>
                    </div>
                    <div class="text-center p-2 bg-purple-50 rounded">
                        <div class="font-semibold text-purple-800">${course.resources_count}</div>
                        <div class="text-purple-600 text-xs">Resources</div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += courseCard;
    });
}

async function reassignFaculty(courseId) {
    // Open faculty assignment modal
    openModal('assign-faculty-modal');
    document.getElementById('assign-course-id').value = courseId;

    // Load faculty members
    try {
        const result = await api.getAllUsers({ role: 'faculty' });
        const facultySelect = document.getElementById('faculty-select');
        facultySelect.innerHTML = '<option value="">Select Faculty</option>';

        result.users.forEach(faculty => {
            const option = `<option value="${faculty.user_id}">${faculty.full_name} (${faculty.department})</option>`;
            facultySelect.innerHTML += option;
        });
    } catch (error) {
        console.error('Error loading faculty:', error);
        showNotification('Failed to load faculty members', 'error');
    }
}

async function assignFaculty() {
    const courseId = document.getElementById('assign-course-id').value;
    const facultyId = document.getElementById('faculty-select').value;

    if (!facultyId) {
        showNotification('Please select a faculty member', 'warning');
        return;
    }

    try {
        await api.assignCourseFaculty(courseId, facultyId);
        showNotification('Faculty assigned successfully', 'success');
        loadCourseManagement(); // Refresh course list
        closeModal('assign-faculty-modal');
    } catch (error) {
        console.error('Error assigning faculty:', error);
        showNotification(error.message, 'error');
    }
}

/**
 * Department Management Functions
 */
async function loadDepartmentManagement() {
    try {
        const departments = await api.getDepartments();
        displayDepartments(departments);
    } catch (error) {
        console.error('Error loading departments:', error);
        showNotification('Failed to load departments', 'error');
    }
}

function displayDepartments(departments) {
    const container = document.getElementById('departments-container');
    container.innerHTML = '';

    departments.forEach(dept => {
        const deptCard = `
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">${dept.department}</h3>
                <div class="grid grid-cols-3 gap-4">
                    <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600">${dept.faculty_count}</div>
                        <div class="text-sm text-gray-500">Faculty</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-green-600">${dept.student_count}</div>
                        <div class="text-sm text-gray-500">Students</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600">${dept.course_count}</div>
                        <div class="text-sm text-gray-500">Courses</div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += deptCard;
    });
}

/**
 * System Settings Functions
 */
async function loadSystemSettings() {
    try {
        const settings = await api.getAdminSettings();
        populateSettingsForm(settings);
    } catch (error) {
        console.error('Error loading settings:', error);
        showNotification('Failed to load system settings', 'error');
    }
}

function populateSettingsForm(settings) {
    document.getElementById('academic-year').value = settings.academic_year;
    document.getElementById('current-semester').value = settings.current_semester;
    document.getElementById('enrollment-open').checked = settings.enrollment_open;
    document.getElementById('max-enrollment').value = settings.max_course_enrollment;

    // Populate notification settings
    document.getElementById('email-notifications').checked = settings.notification_settings.email_notifications;
    document.getElementById('grade-notifications').checked = settings.notification_settings.grade_release_notifications;
    document.getElementById('assignment-reminders').checked = settings.notification_settings.assignment_reminders;

    // Display maintenance info
    document.getElementById('last-backup').textContent =
        new Date(settings.system_maintenance.last_backup).toLocaleString();
    document.getElementById('next-maintenance').textContent =
        new Date(settings.system_maintenance.next_maintenance).toLocaleString();
}

async function saveSystemSettings() {
    const settings = {
        academic_year: document.getElementById('academic-year').value,
        current_semester: document.getElementById('current-semester').value,
        enrollment_open: document.getElementById('enrollment-open').checked,
        max_course_enrollment: parseInt(document.getElementById('max-enrollment').value),
        notification_settings: {
            email_notifications: document.getElementById('email-notifications').checked,
            grade_release_notifications: document.getElementById('grade-notifications').checked,
            assignment_reminders: document.getElementById('assignment-reminders').checked
        }
    };

    try {
        await api.updateAdminSettings(settings);
        showNotification('System settings updated successfully', 'success');
    } catch (error) {
        console.error('Error updating settings:', error);
        showNotification(error.message, 'error');
    }
}

/**
 * Analytics Functions
 */
async function loadSystemAnalytics() {
    try {
        const [enrollmentTrends, gradeDistribution] = await Promise.all([
            api.getEnrollmentTrends(),
            api.getGradeDistribution()
        ]);

        displayEnrollmentTrends(enrollmentTrends);
        displayGradeDistribution(gradeDistribution);

    } catch (error) {
        console.error('Error loading analytics:', error);
        showNotification('Failed to load analytics data', 'error');
    }
}

function displayEnrollmentTrends(trends) {
    const container = document.getElementById('enrollment-trends');
    container.innerHTML = '<h4 class="font-semibold mb-3">Recent Enrollment Trends</h4>';

    // Group by date for better visualization
    const trendsByDate = trends.reduce((acc, trend) => {
        if (!acc[trend.date]) {
            acc[trend.date] = { date: trend.date, total: 0, departments: {} };
        }
        acc[trend.date].total += trend.enrollments;
        acc[trend.date].departments[trend.department] = trend.enrollments;
        return acc;
    }, {});

    Object.values(trendsByDate).slice(0, 10).forEach(dayTrend => {
        const trendItem = `
            <div class="flex justify-between items-center p-3 border-b">
                <div>
                    <div class="font-medium">${new Date(dayTrend.date).toLocaleDateString()}</div>
                    <div class="text-sm text-gray-500">
                        ${Object.entries(dayTrend.departments).map(([dept, count]) => `${dept}: ${count}`).join(', ')}
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-lg font-semibold">${dayTrend.total}</span>
                    <div class="text-xs text-gray-500">enrollments</div>
                </div>
            </div>
        `;
        container.innerHTML += trendItem;
    });
}

function displayGradeDistribution(distribution) {
    const container = document.getElementById('grade-distribution');
    container.innerHTML = '<h4 class="font-semibold mb-3">Grade Distribution</h4>';

    // Group by department
    const byDepartment = distribution.reduce((acc, item) => {
        if (!acc[item.department]) {
            acc[item.department] = {};
        }
        acc[item.department][item.grade_letter] = item.count;
        return acc;
    }, {});

    Object.entries(byDepartment).forEach(([department, grades]) => {
        const total = Object.values(grades).reduce((sum, count) => sum + count, 0);

        const deptSection = `
            <div class="mb-4 p-3 border rounded">
                <h5 class="font-medium mb-2">${department}</h5>
                <div class="grid grid-cols-5 gap-2 text-sm">
                    ${['A', 'B', 'C', 'D', 'F'].map(grade => {
            const count = grades[grade] || 0;
            const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
            return `
                            <div class="text-center p-2 bg-gray-50 rounded">
                                <div class="font-semibold">${grade}</div>
                                <div class="text-xs">${count} (${percentage}%)</div>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
        container.innerHTML += deptSection;
    });
}

/**
 * Audit Logs Functions
 */
async function loadAuditLogs() {
    try {
        const logs = await api.getAuditLogs({ limit: 50 });
        displayAuditLogs(logs);
    } catch (error) {
        console.error('Error loading audit logs:', error);
        showNotification('Failed to load audit logs', 'error');
    }
}

function displayAuditLogs(logs) {
    const container = document.getElementById('audit-logs-table');
    container.innerHTML = '';

    logs.forEach(log => {
        const logRow = `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${new Date(log.timestamp).toLocaleString()}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm font-medium">${log.user_id}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 text-xs font-semibold rounded-full ${getActionBadgeColor(log.action)}">
                        ${log.action.replace('_', ' ')}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${log.target}
                </td>
                <td class="px-6 py-4 text-sm text-gray-500">
                    ${log.details}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${log.ip_address}
                </td>
            </tr>
        `;
        container.innerHTML += logRow;
    });
}

/**
 * Utility Functions
 */
function getRoleColor(role) {
    const colors = {
        admin: 'bg-red-500',
        faculty: 'bg-blue-500',
        student: 'bg-green-500'
    };
    return colors[role] || 'bg-gray-500';
}

function getRoleBadgeColor(role) {
    const colors = {
        admin: 'bg-red-100 text-red-800',
        faculty: 'bg-blue-100 text-blue-800',
        student: 'bg-green-100 text-green-800'
    };
    return colors[role] || 'bg-gray-100 text-gray-800';
}

function getStatusColor(status) {
    const colors = {
        active: 'bg-green-100 text-green-800',
        inactive: 'bg-red-100 text-red-800',
        suspended: 'bg-yellow-100 text-yellow-800'
    };
    return colors[status] || 'bg-green-100 text-green-800';
}

function getActivityIconColor(type) {
    const colors = {
        enrollment: 'bg-blue-500',
        submission: 'bg-green-500',
        course_created: 'bg-purple-500',
        user_created: 'bg-orange-500'
    };
    return colors[type] || 'bg-gray-500';
}

function getActivityIcon(type) {
    const icons = {
        enrollment: 'person-plus',
        submission: 'file-earmark-arrow-up',
        course_created: 'book',
        user_created: 'person-add'
    };
    return icons[type] || 'activity';
}

function getActionBadgeColor(action) {
    const colors = {
        user_created: 'bg-green-100 text-green-800',
        user_updated: 'bg-blue-100 text-blue-800',
        user_deleted: 'bg-red-100 text-red-800',
        course_created: 'bg-purple-100 text-purple-800',
        course_updated: 'bg-blue-100 text-blue-800'
    };
    return colors[action] || 'bg-gray-100 text-gray-800';
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${getNotificationColor(type)}`;
    notification.textContent = message;
    document.body.appendChild(notification);

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

function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
    document.body.style.overflow = 'auto';
}

function updateUserPagination(total, limit, offset) {
    const currentPage = Math.floor(offset / limit) + 1;
    const totalPages = Math.ceil(total / limit);

    document.getElementById('pagination-info').textContent =
        `Showing ${offset + 1}-${Math.min(offset + limit, total)} of ${total} users`;

    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;

    prevBtn.onclick = () => {
        if (currentPage > 1) {
            loadUsersPage(currentPage - 1);
        }
    };

    nextBtn.onclick = () => {
        if (currentPage < totalPages) {
            loadUsersPage(currentPage + 1);
        }
    };
}

async function loadUsersPage(page) {
    const limit = 50;
    const offset = (page - 1) * limit;

    try {
        const result = await api.getAllUsers({ limit, offset });
        displayUsers(result.users);
        updateUserPagination(result.total, result.limit, result.offset);
    } catch (error) {
        console.error('Error loading users page:', error);
        showNotification('Failed to load users', 'error');
    }
}

/**
 * Initialize admin portal when page loads
 */
document.addEventListener('DOMContentLoaded', function () {
    // Check authentication
    if (!api.checkAuth() || api.currentUser?.role !== 'admin') {
        window.location.href = 'admin-login.html';
        return;
    }

    // Load content based on current page
    const currentPage = window.location.pathname;

    if (currentPage.includes('admin-dashboard.html')) {
        loadAdminDashboard();
    } else if (currentPage.includes('manage-users.html')) {
        loadUserManagement();
    } else if (currentPage.includes('system-settings.html')) {
        loadSystemSettings();
    }

    // Set up search functionality
    const userSearchInput = document.getElementById('user-search');
    if (userSearchInput) {
        userSearchInput.addEventListener('input', debounce(searchUsers, 300));
    }

    const roleFilter = document.getElementById('role-filter');
    if (roleFilter) {
        roleFilter.addEventListener('change', searchUsers);
    }
});

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global use
window.adminPortal = {
    loadAdminDashboard,
    loadUserManagement,
    createNewUser,
    editUser,
    confirmDeleteUser,
    searchUsers,
    loadCourseManagement,
    reassignFaculty,
    assignFaculty,
    loadDepartmentManagement,
    loadSystemSettings,
    saveSystemSettings,
    loadSystemAnalytics,
    loadAuditLogs,
    showNotification
};