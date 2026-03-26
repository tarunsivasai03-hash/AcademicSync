/**
 * AcademicSync API Client  v2.0
 * JWT Bearer-token based wrapper for Flask backend.
 *
 * Usage (per page):
 *   const api = new AcademicSyncAPI('http://localhost:5000');
 *
 * A default global instance is also created at the bottom:
 *   window.api  ← ready to use immediately
 */
class AcademicSyncAPI {
  constructor() {
    this.baseUrl = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://localhost:5000'
      : 'https://academicsync-1.onrender.com';
    this.baseUrl = this.baseUrl.replace(/\/$/, '');
    this.TOKEN_KEY = 'academicsync_token';
    this.USER_KEY = 'academicsync_user';

    // Back-compat shims (old code read these directly)
    this.isAuthenticated = this.checkAuth();
    this.currentUser = this.getUserData();
  }

  // ─── Token / storage helpers ─────────────────────────────────────────────

  getToken() { return localStorage.getItem(this.TOKEN_KEY); }
  setToken(t) { localStorage.setItem(this.TOKEN_KEY, t); }
  clearToken() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    // back-compat keys used by older code
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('currentUser');
  }

  getUserData() {
    try {
      return JSON.parse(localStorage.getItem(this.USER_KEY))
        || JSON.parse(localStorage.getItem('currentUser'))
        || null;
    } catch { return null; }
  }

  setUserData(u) {
    localStorage.setItem(this.USER_KEY, JSON.stringify(u));
    localStorage.setItem('currentUser', JSON.stringify(u)); // back-compat
  }

  /** Returns true when a JWT token is present in localStorage. */
  checkAuth() { return !!this.getToken(); }

  // ─── Core fetch wrapper ──────────────────────────────────────────────────

  async request(method, path, body = null, isFormData = false) {
    const url = `${this.baseUrl}/api${path}`;

    const headers = {};
    const token = this.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (body && !isFormData) headers['Content-Type'] = 'application/json';

    const opts = { method, headers };
    if (body) opts.body = isFormData ? body : JSON.stringify(body);

    let res, data;
    try {
      res = await fetch(url, opts);
      data = await res.json().catch(() => ({}));
    } catch (err) {
      if (!navigator.onLine) {
        // Banner may not have fired yet — force-show it immediately
        const b = document.getElementById('academicsync-offline-banner');
        if (b) { b.style.transform = 'translateY(0)'; b.style.opacity = '1'; b.style.pointerEvents = 'auto'; }
        throw new Error('You are offline — please check your connection.');
      }
      console.error(`[api] network error ${method} ${path}:`, err);
      throw new Error('Network error – is the backend running?');
    }

    // Auto-logout on 401 (expired / invalid token after server restart)
    if (res.status === 401) {
      this.clearToken();
      const role = this._detectRoleFromPath();
      const loginPage = this._loginUrl(role);
      // Only redirect if not already on a login page to avoid redirect loops
      if (!window.location.pathname.includes('login')) {
        window.location.href = loginPage;
      }
      const msg = data.message || data.error || data.msg || 'Session expired. Please log in again.';
      throw new Error(msg);
    }

    if (!res.ok) {
      const msg = data.message || data.error || data.msg || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    // First successful response — dismiss the page-entry skeleton
    this._removePageLoadingOverlay();
    return data;
  }

  // Convenience verbs
  get(p) { return this.request('GET', p); }
  post(p, b) { return this.request('POST', p, b); }
  put(p, b) { return this.request('PUT', p, b); }
  del(p) { return this.request('DELETE', p); }
  postForm(p, fd) { return this.request('POST', p, fd, true); }
  putForm(p, fd) { return this.request('PUT', p, fd, true); }

  // ─── Health ──────────────────────────────────────────────────────────────

  checkHealth() { return this.get('/health'); }
  healthCheck() { return this.get('/health'); }

  // ─── Auth ────────────────────────────────────────────────────────────────

  async login(credentials) {
    const { user_id, password } = credentials;
    const data = await this.post('/auth/login', { user_id, password });
    if (data.access_token) {
      this.setToken(data.access_token);
      if (data.user) {
        this.setUserData(data.user);
        this.currentUser = data.user;
        this.isAuthenticated = true;
        // back-compat
        localStorage.setItem('isAuthenticated', 'true');
      }
    }
    return data;
  }

  async register(userData) {
    return this.post('/auth/register', userData);
  }

  async logout() {
    try { await this.post('/auth/logout', {}); } catch (_) { /* ignore */ }
    this.isAuthenticated = false;
    this.currentUser = null;
    this.clearToken();
  }

  getCurrentUser() { return this.get('/auth/me'); }

  async refreshUser() {
    try {
      const res = await this.getCurrentUser();
      const user = res.user || res;
      this.setUserData(user);
      this.currentUser = user;
      return user;
    } catch (_) { return this.getUserData(); }
  }

  // ─── Student ─────────────────────────────────────────────────────────────

  getDashboardStats() { return this.get('/student/dashboard'); }
  getCourses() { return this.get('/student/courses'); }
  getAvailableCourses() { return this.get('/student/courses'); }
  getCourse(id) { return this.get(`/student/courses/${id}`); }
  getCourseResources(id) { return this.get(`/student/courses/${id}/resources`); }
  getAssignments() { return this.get('/student/assignments'); }
  getAssignment(id) { return this.get(`/student/assignments/${id}`); }

  async submitAssignment(id, submissionData, file = null) {
    const fd = new FormData();
    if (submissionData?.text) fd.append('submission_text', submissionData.text);
    if (file) fd.append('file', file);
    return this.postForm(`/student/assignments/${id}/submit`, fd);
  }

  getResources() { return this.get('/student/resources'); }
  getSchedule() { return this.get('/student/schedule'); }
  getAttendance() { return this.get('/student/attendance'); }
  getProfile() { return this.get('/student/profile'); }
  updateProfile(data) {
    if (data instanceof FormData) return this.putForm('/student/profile', data);
    return this.put('/student/profile', data);
  }

  // Enroll / drop  (admin-managed in backend, graceful stubs)
  enrollCourse(id) { return this.post('/student/courses/enroll', { course_id: id }); }
  dropCourse(id) { return this.del(`/student/courses/${id}/drop`); }

  // ── Student Quizzes ─────────────────────────────────────────────────────
  getCourseQuizzes(courseId) { return this.get(`/student/courses/${courseId}/quizzes`); }
  getStudentQuiz(id) { return this.get(`/student/quizzes/${id}`); }
  startQuiz(id) { return this.post(`/student/quizzes/${id}/start`, {}); }
  submitQuiz(id, d) { return this.post(`/student/quizzes/${id}/submit`, d); }
  getQuizResult(id) { return this.get(`/student/quizzes/${id}/result`); }

  // ─── Faculty ─────────────────────────────────────────────────────────────

  getFacultyDashboardStats() { return this.get('/faculty/dashboard/stats'); }
  getFacultyCourses() { return this.get('/faculty/courses'); }
  getSemesters() { return this.get('/faculty/semesters'); }
  createCourse(d) { return this.post('/faculty/courses', d); }
  updateCourse(id, d) { return this.put(`/faculty/courses/${id}`, d); }
  deleteCourse(id) { return this.del(`/faculty/courses/${id}`); }
  getCourseStudents(id) { return this.get(`/faculty/courses/${id}/students`); }
  getFacultyAssignments() { return this.get('/faculty/assignments'); }
  createAssignment(d) { return this.post('/faculty/assignments', d); }
  updateAssignment(id, d) { return this.put(`/faculty/assignments/${id}`, d); }
  deleteAssignment(id) { return this.del(`/faculty/assignments/${id}`); }
  getAssignmentSubmissions(id) { return this.get(`/faculty/assignments/${id}/submissions`); }
  getSubmissions(id) { return this.get(`/faculty/assignments/${id}/submissions`); }
  gradeSubmission(id, d) { return this.put(`/faculty/grade/${id}`, d); }
  getFacultyStudents() { return this.get('/faculty/students'); }
  getFacultyResources() { return this.get('/faculty/resources'); }
  createFacultyResource(fd) { return this.postForm('/faculty/resources', fd); }
  deleteFacultyResource(id) { return this.del(`/faculty/resources/${id}`); }
  getFacultySchedule() { return this.get('/faculty/schedule'); }
  createScheduleSession(d) { return this.post('/faculty/schedule/sessions', d); }
  deleteScheduleSession(id) { return this.del(`/faculty/schedule/sessions/${id}`); }
  recordAttendance(d) { return this.post('/faculty/attendance', d); }
  bulkUpdateGrades(d) { return this.put('/faculty/grades/bulk', d); }
  getFacultyProfile() { return this.get('/faculty/profile'); }
  updateFacultyProfile(d) { return this.put('/faculty/profile', d); }

  // ── Faculty Quizzes ─────────────────────────────────────────────────────
  getFacultyQuizzes() { return this.get('/faculty/quizzes'); }
  createQuiz(d) { return this.post('/faculty/quizzes', d); }
  getFacultyQuiz(id) { return this.get(`/faculty/quizzes/${id}`); }
  updateQuiz(id, d) { return this.put(`/faculty/quizzes/${id}`, d); }
  deleteQuiz(id) { return this.del(`/faculty/quizzes/${id}`); }
  publishQuiz(id, pub) { return this.put(`/faculty/quizzes/${id}`, { is_published: pub }); }
  addQuizQuestion(quizId, d) { return this.post(`/faculty/quizzes/${quizId}/questions`, d); }
  updateQuizQuestion(qId, d) { return this.put(`/faculty/questions/${qId}`, d); }
  deleteQuizQuestion(qId) { return this.del(`/faculty/questions/${qId}`); }
  getQuizAttempts(quizId) { return this.get(`/faculty/quizzes/${quizId}/attempts`); }

  // ─── Admin ───────────────────────────────────────────────────────────────

  getAdminDashboardStats() { return this.get('/admin/dashboard/stats'); }
  getAdminActivities() { return this.get('/admin/audit-logs'); }
  getAdminSystemMetrics() { return this.get('/admin/settings'); }
  getAdminSettings() { return this.get('/admin/settings'); }
  updateAdminSettings(d) { return this.put('/admin/settings', d); }
  getAdminAnnouncements() { return this.get('/admin/announcements'); }
  postAdminAnnouncement(d) { return this.post('/admin/announcements', d); }
  deleteAdminAnnouncement(id) { return this.del(`/admin/announcements/${id}`); }
  postFacultyAnnouncement(d) { return this.post('/faculty/announcements', d); }
  changePassword(d) { return this.put('/auth/change-password', d); }

  getAdminUsers(p = {}) {
    const qs = new URLSearchParams(p).toString();
    return this.get(`/admin/users${qs ? '?' + qs : ''}`);
  }
  // aliases
  getAllUsers(p = {}) { return this.getAdminUsers(p); }
  getAdminUser(id) { return this.get(`/admin/users/${id}`); }
  createAdminUser(d) { return this.post('/admin/users', d); }
  createUser(d) { return this.post('/admin/users', d); }
  updateAdminUser(id, d) { return this.put(`/admin/users/${id}`, d); }
  updateUser(id, d) { return this.put(`/admin/users/${id}`, d); }
  activateAdminUser(id) { return this.put(`/admin/users/${id}`, { is_active: true }); }
  deactivateAdminUser(id) { return this.del(`/admin/users/${id}`); }
  deleteUser(id) { return this.del(`/admin/users/${id}`); }
  async resetAdminUserPassword(id, newPassword = null) {
    const body = newPassword ? { new_password: newPassword } : {};
    return this.post(`/admin/users/${id}/reset-password`, body);
  }

  getAdminCourses(p = {}) {
    const qs = new URLSearchParams(p).toString();
    return this.get(`/admin/courses${qs ? '?' + qs : ''}`);
  }
  getAllCourses(p = {}) { return this.getAdminCourses(p); }
  createAdminCourse(d) { return this.post('/admin/courses', d); }
  updateAdminCourse(id, d) { return this.put(`/admin/courses/${id}`, d); }
  deleteAdminCourse(id) { return this.del(`/admin/courses/${id}`); }
  assignCourseFaculty(cid, fid) { return this.put(`/admin/courses/${cid}/assign-faculty`, { faculty_id: fid }); }
  getAdminSemesters() { return this.get('/admin/semesters'); }
  getAcademicYears() { return this.get('/admin/academic-years'); }

  getAdminDepartments() { return this.get('/admin/departments'); }
  getDepartments() { return this.get('/admin/departments'); }
  createAdminDepartment(d) { return this.post('/admin/departments', d); }
  createDepartment(d) { return this.post('/admin/departments', d); }
  updateAdminDepartment(id, d) { return this.put(`/admin/departments/${id}`, d); }

  createStudent(d) { return this.post('/admin/create-student', d); }
  createFacultyMember(d) { return this.post('/admin/create-faculty', d); }
  /** @deprecated Use createAdminCourse() which calls /admin/courses */
  createAdminCourseLegacy(d) { return this.post('/admin/create-course', d); }

  // ── Admin Quizzes ────────────────────────────────────────────────────────
  getAdminQuizzes(p = {}) { const qs = new URLSearchParams(p).toString(); return this.get(`/admin/quizzes${qs ? '?' + qs : ''}`); }
  updateAdminQuiz(id, d) { return this.put(`/admin/quizzes/${id}`, d); }
  deleteAdminQuiz(id) { return this.del(`/admin/quizzes/${id}`); }
  getAdminQuizAttempts(id) { return this.get(`/admin/quizzes/${id}/attempts`); }

  getEnrollmentTrends() { return this.get('/admin/analytics/enrollment-trends'); }
  getGradeDistribution() { return this.get('/admin/analytics/grade-distribution'); }
  getAuditLogs(p = {}) {
    const qs = new URLSearchParams(p).toString();
    return this.get(`/admin/audit-logs${qs ? '?' + qs : ''}`);
  }

  // ─── Tasks  (any authenticated role) ─────────────────────────────────────

  getTasks() { return this.get('/tasks'); }
  createTask(d) { return this.post('/tasks', d); }
  updateTask(id, d) { return this.put(`/tasks/${id}`, d); }
  deleteTask(id) { return this.del(`/tasks/${id}`); }

  // ─── Notifications ────────────────────────────────────────────────────────

  getNotifications(unreadOnly = false, limit = null) {
    const params = [];
    if (unreadOnly) params.push('unread=true');
    if (limit)      params.push(`limit=${limit}`);
    const qs = params.length ? `?${params.join('&')}` : '';
    return this.get(`/notifications${qs}`);
  }
  markNotificationRead(id) { return this.post(`/notifications/${id}/read`, {}); }
  markAllNotificationsRead() { return this.post('/notifications/read-all', {}); }

  // ─── Real-time Notification Stream (SSE) ─────────────────────────────────

  /**
   * Opens a Server-Sent Events connection to /api/notifications/stream.
   * Fires  window.dispatchEvent(new CustomEvent('academicsync:notifications', { detail }))
   * whenever the server pushes an update.  Also shows a toast for new arrivals.
   *
   * EventSource auto-reconnects on network blips.
   * Call disconnectNotificationStream() on logout.
   */
  connectNotificationStream() {
    if (!this.checkAuth()) return;

    // Close any existing connection first
    if (this._sseSource) {
      this._sseSource.close();
      this._sseSource = null;
    }

    const token = this.getToken();
    const url   = `${this.baseUrl}/api/notifications/stream?token=${encodeURIComponent(token)}`;
    const source = new EventSource(url);
    this._sseSource       = source;
    this._sseLastUnread   = null;  // track previous count to detect new arrivals

    source.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const { unread_count, notifications = [] } = data;

        // Toast only when count increases (not on first connect or after marking read)
        if (this._sseLastUnread !== null && unread_count > this._sseLastUnread) {
          const latest = notifications[0];
          const label  = latest
            ? (latest.title || 'New notification')
            : `${unread_count - this._sseLastUnread} new notification(s)`;
          this.showNotification(`\uD83D\uDD14 ${label}`, 'info', 6000);
        }
        this._sseLastUnread = unread_count;

        // Broadcast to the current page
        window.dispatchEvent(new CustomEvent('academicsync:notifications', { detail: data }));
      } catch (_) {}
    };

    source.addEventListener('connected', () => {
      console.debug('[SSE] Notification stream connected');
    });

    source.onerror = () => {
      // EventSource handles reconnection automatically;
      // only null out our ref if the browser fully closed it.
      if (source.readyState === EventSource.CLOSED) {
        this._sseSource = null;
      }
    };

    return source;
  }

  disconnectNotificationStream() {
    if (this._sseSource) {
      this._sseSource.close();
      this._sseSource = null;
    }
  }

  // ─── Auth guards (page-level) ─────────────────────────────────────────────

  /**
   * Call at the top of any protected page.
   * Redirects to the matching login page if no valid token / wrong role.
   * Returns the stored user object if auth passes.
   */
  requireAuth(expectedRole = null, loginUrl = null) {
    if (!this.checkAuth()) {
      window.location.href = loginUrl || this._loginUrl(expectedRole);
      return null;
    }
    const user = this.getUserData();
    if (expectedRole && user && user.role !== expectedRole) {
      this.clearToken();
      window.location.href = loginUrl || this._loginUrl(expectedRole);
      return null;
    }
    return user;
  }

  requireRole(role) { return this.requireAuth(role); }

  _loginUrl(role) {
    const m = { student: 'student-login.html', faculty: 'faculty-login.html', admin: 'admin-login.html' };
    return m[role] || '../login.html';
  }

  /** Guess the role from the current page path so 401 redirects land on the right login. */
  _detectRoleFromPath() {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('/faculty/') || path.includes('faculty-')) return 'faculty';
    if (path.includes('/admin/')   || path.includes('admin-'))   return 'admin';
    if (path.includes('/student/') || path.includes('student-')) return 'student';
    // Fall back to stored user role if available
    const user = this.getUserData();
    return user?.role || null;
  }

  getFileUrl(filename) { return `${this.baseUrl}/api/uploads/${filename}`; }

  /**
   * Fetch a protected file with the JWT token and trigger a browser download.
   * Use this instead of a plain <a href> when the endpoint requires auth.
   */
  async downloadFile(filePath, originalFilename) {
    const token = this.getToken();
    const url = this.getFileUrl(filePath);
    const res = await fetch(url, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!res.ok) throw new Error(`Download failed: ${res.status} ${res.statusText}`);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = originalFilename || filePath.split('/').pop();
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(blobUrl); a.remove(); }, 10000);
  }

  // ─── UI helpers ───────────────────────────────────────────────────────────

  /** Populate [data-user-name], [data-user-role], [data-user-initials], [data-user-email] elements. */
  populateSidebar(user) {
    if (!user) return;
    const initials = (user.full_name || user.user_id || 'U')
      .split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    document.querySelectorAll('[data-user-name]').forEach(el => el.textContent = user.full_name || user.user_id || '—');
    document.querySelectorAll('[data-user-role]').forEach(el => el.textContent = user.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : '—');
    document.querySelectorAll('[data-user-initials]').forEach(el => el.textContent = initials);
    document.querySelectorAll('[data-user-email]').forEach(el => el.textContent = user.email || '—');
    document.querySelectorAll('[data-user-id]').forEach(el => el.textContent = user.user_id || '—');
  }

  /** Show a transient toast notification. */
  showNotification(message, type = 'info', durationMs = 3500) {
    const colours = { success: 'bg-green-500 text-white', error: 'bg-red-500 text-white', warning: 'bg-yellow-500 text-black', info: 'bg-gray-800 text-white' };
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    const el = document.createElement('div');
    el.className = `fixed top-4 right-4 px-5 py-3 rounded-xl shadow-xl z-[9999] text-sm font-semibold flex items-center gap-2 transition-opacity duration-300 ${colours[type] || colours.info}`;
    el.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 350); }, durationMs);
    return el;
  }

  // ─── Offline / Connection Banner ─────────────────────────────────────────

  /**
   * Injects a fixed top banner that slides down when the browser goes offline
   * and slides back up (with a toast) when connectivity is restored.
   * Safe to call multiple times — creates the banner only once.
   */
  _initOfflineBanner() {
    if (document.getElementById('academicsync-offline-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'academicsync-offline-banner';
    banner.setAttribute('role', 'alert');
    banner.setAttribute('aria-live', 'assertive');
    banner.style.cssText = [
      'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:10000',
      'background:#d97706', 'color:#fff', 'text-align:center',
      'padding:10px 16px', 'font-size:14px', 'font-weight:600',
      'display:flex', 'align-items:center', 'justify-content:center', 'gap:8px',
      'transform:translateY(-110%)',
      'transition:transform 0.3s cubic-bezier(0.4,0,0.2,1), opacity 0.3s ease',
      'opacity:0', 'pointer-events:none',
      'box-shadow:0 3px 10px rgba(0,0,0,0.3)'
    ].join(';');
    banner.innerHTML =
      '<span style="font-size:18px" aria-hidden="true">⚡</span>' +
      '<span>No internet connection — changes may not be saved</span>';
    document.body.prepend(banner);

    const show = () => {
      banner.style.transform = 'translateY(0)';
      banner.style.opacity = '1';
      banner.style.pointerEvents = 'auto';
    };
    const hide = () => {
      banner.style.transform = 'translateY(-110%)';
      banner.style.opacity = '0';
      banner.style.pointerEvents = 'none';
      this.showNotification('Connection restored', 'success', 3000);
    };

    if (!navigator.onLine) show();
    window.addEventListener('offline', show);
    window.addEventListener('online', hide);
  }

  // ─── Page-entry Skeleton Overlay ──────────────────────────────────────────────

  /**
   * Injects an animated skeleton overlay inside <main> immediately after the DOM
   * is ready. Skips login / auth pages (those whose <main> has the `p-0` class
   * or whose URL contains "login" / "register" / "index").
   * Safe to call multiple times — creates the overlay only once.
   */
  _initPageLoadingOverlay() {
    // Already initialised
    if (this._overlayDismissed || document.getElementById('as-page-skeleton')) return;

    const main = document.querySelector('main');
    if (!main) return;

    // Skip login / landing pages
    const path = window.location.pathname.toLowerCase();
    const skipPatterns = ['login', 'register', 'index.html', '/index'];
    if (skipPatterns.some(p => path.includes(p))) return;
    if (main.classList.contains('p-0')) return;

    // Inject shimmer keyframes + .as-skel class once per document
    if (!document.getElementById('as-skeleton-styles')) {
      const s = document.createElement('style');
      s.id = 'as-skeleton-styles';
      s.textContent = `
        @keyframes as-shimmer {
          0%   { background-position: -800px 0; }
          100% { background-position:  800px 0; }
        }
        .as-skel {
          background: linear-gradient(90deg, #e8e8e8 25%, #d0d0d0 50%, #e8e8e8 75%);
          background-size: 800px 100%;
          animation: as-shimmer 1.5s infinite linear;
          border-radius: 8px;
        }
        #as-page-skeleton {
          transition: opacity 0.35s ease;
        }
      `;
      document.head.appendChild(s);
    }

    // Make <main> the positioning context for the absolute overlay
    if (getComputedStyle(main).position === 'static') {
      main.style.position = 'relative';
    }

    const overlay = document.createElement('div');
    overlay.id = 'as-page-skeleton';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.cssText = [
      'position:absolute', 'inset:0', 'min-height:100%',
      'z-index:50', 'background:#f9fafb',
      'padding:24px', 'overflow:hidden', 'pointer-events:none'
    ].join(';');

    overlay.innerHTML = `
      <div class="as-skel" style="height:28px;width:38%;margin-bottom:28px;"></div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px;margin-bottom:28px;">
        <div class="as-skel" style="height:90px;"></div>
        <div class="as-skel" style="height:90px;"></div>
        <div class="as-skel" style="height:90px;"></div>
        <div class="as-skel" style="height:90px;"></div>
      </div>
      <div class="as-skel" style="height:190px;margin-bottom:20px;"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
        <div class="as-skel" style="height:120px;"></div>
        <div class="as-skel" style="height:120px;"></div>
      </div>
      <div class="as-skel" style="height:14px;width:72%;margin-bottom:12px;border-radius:4px;"></div>
      <div class="as-skel" style="height:14px;width:52%;border-radius:4px;"></div>
    `;

    main.prepend(overlay);

    // Safety net: auto-dismiss after 6 s even if no API call fires
    this._skeletonTimeout = setTimeout(() => this._removePageLoadingOverlay(), 6000);
  }

  /** Fade out and remove the page-entry skeleton overlay (idempotent). */
  _removePageLoadingOverlay() {
    if (this._overlayDismissed) return;
    this._overlayDismissed = true;
    clearTimeout(this._skeletonTimeout);
    const overlay = document.getElementById('as-page-skeleton');
    if (!overlay) return;
    overlay.style.opacity = '0';
    overlay.style.pointerEvents = 'none';
    setTimeout(() => overlay.remove(), 380);
  }
}

// ─── Utility Classes (kept for backwards compatibility) ───────────────────────

class UIHelpers {
  static showNotification(message, type = 'info', duration = 4000) {
    window.api?.showNotification(message, type, duration);
  }
  static formatDate(d) { return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); }
  static formatDateTime(d) { return new Date(d).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  static formatFileSize(b) { if (!b) return '0 B'; const k = 1024, sz = ['B', 'KB', 'MB', 'GB'], i = Math.floor(Math.log(b) / Math.log(k)); return (b / k ** i).toFixed(1) + ' ' + sz[i]; }
  static showLoading(el, show = true) {
    el.classList.toggle('opacity-50', show);
    el.classList.toggle('pointer-events-none', show);
  }
}

class FormValidator {
  static validateEmail(e) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e); }
  static validatePassword(p) { return p && p.length >= 6; }
  static validateRequired(v) { return v != null && v.toString().trim() !== ''; }
  static showFieldError(el, msg) {
    this.clearFieldError(el);
    el.classList.add('border-red-500', 'bg-red-50');
    const d = document.createElement('div');
    d.className = 'text-red-500 text-sm mt-1 field-error';
    d.textContent = msg;
    el.parentElement?.appendChild(d);
  }
  static clearFieldError(el) {
    el.classList.remove('border-red-500', 'bg-red-50');
    el.parentElement?.querySelector('.field-error')?.remove();
  }
}

// ─── Global singleton ──────────────────────────────────────────────────────────
// Use window.api (not const api) so pages that declare their own `const api`
// don't get a "already declared" SyntaxError from sharing the global lexical scope.
//
// Auto-detects the API host so LAN / Wi-Fi testing on a phone works without
// any manual config: when the page is opened via a LAN IP (e.g. 192.168.x.x)
// the API calls automatically go to that same IP on port 5000.
const _apiBase = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:5000'
  : `http://${window.location.hostname}:5000`;
window._apiBase = _apiBase;  // expose for pages that create their own AcademicSyncAPI instance
window.api = new AcademicSyncAPI(_apiBase);

// Auto-connect SSE stream on every authenticated page.
// Pages that need UI-specific reactions (dashboard, announcements) listen to
// the 'academicsync:notifications' custom event independently.
if (window.api.checkAuth()) {
  // Small delay so the page's own DOMContentLoaded runs first
  setTimeout(() => window.api.connectNotificationStream(), 800);
}

// Initialize the offline/online banner + page-entry skeleton on every page
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.api._initOfflineBanner();
    window.api._initPageLoadingOverlay();
  });
} else {
  window.api._initOfflineBanner();
  window.api._initPageLoadingOverlay();
}

window.UIHelpers = UIHelpers;
window.FormValidator = FormValidator;

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AcademicSyncAPI, UIHelpers, FormValidator };
}

