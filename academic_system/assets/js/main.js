window.layout = function () {
    return {
        sidebarOpen: false,
        mobileMenuOpen: false,
        darkMode: localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches),

        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
        },

        toggleMobileMenu() {
            this.mobileMenuOpen = !this.mobileMenuOpen;
        },

        toggleDarkMode() {
            this.darkMode = !this.darkMode;
        },

        async logout() {
            try { await window.api?.logout(); } catch (_) {}
            const role = window.api?._detectRoleFromPath() || 'student';
            const urls = { student: 'student-login.html', faculty: 'faculty-login.html', admin: 'admin-login.html' };
            window.location.href = urls[role] || '../login.html';
        },

        init() {
            // Check initial dark mode preference
            if (this.darkMode) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }

            // Watch for dark mode changes
            this.$watch('darkMode', val => {
                localStorage.setItem('theme', val ? 'dark' : 'light');
                if (val) {
                    document.documentElement.classList.add('dark');
                } else {
                    document.documentElement.classList.remove('dark');
                }
            });

            // Close sidebar/mobile menu on resize to larger screens
            window.addEventListener('resize', () => {
                if (window.innerWidth >= 1024) { // lg breakpoint
                    this.sidebarOpen = false;
                    this.mobileMenuOpen = false;
                }
            });
        }
    };
};

document.addEventListener('alpine:init', () => {
    Alpine.data('layout', window.layout);
});
