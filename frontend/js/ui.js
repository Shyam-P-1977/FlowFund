/**
 * FlowFund - UI Utilities
 * Toast notifications, modals, loading states, and helpers
 */

class UI {
    // ========================
    // Toast Notifications
    // ========================
    static initToasts() {
        if (!document.querySelector('.toast-container')) {
            const container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
    }

    static toast(message, type = 'info', duration = 4000) {
        this.initToasts();
        const container = document.querySelector('.toast-container');

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    static success(msg) { this.toast(msg, 'success'); }
    static error(msg) { this.toast(msg, 'error', 6000); }
    static warning(msg) { this.toast(msg, 'warning'); }
    static info(msg) { this.toast(msg, 'info'); }

    // ========================
    // Modal
    // ========================
    static showModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    static hideModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    static closeAllModals() {
        document.querySelectorAll('.modal-backdrop.active').forEach(m => {
            m.classList.remove('active');
        });
        document.body.style.overflow = '';
    }

    // ========================
    // Loading States
    // ========================
    static showLoading(element) {
        if (!element) return;
        element.style.position = 'relative';
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        element.appendChild(overlay);
    }

    static hideLoading(element) {
        if (!element) return;
        const overlay = element.querySelector('.loading-overlay');
        if (overlay) overlay.remove();
    }

    static setButtonLoading(btn, loading = true) {
        if (!btn) return;
        if (loading) {
            btn.disabled = true;
            btn._originalText = btn.innerHTML;
            btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div>';
        } else {
            btn.disabled = false;
            if (btn._originalText) {
                btn.innerHTML = btn._originalText;
            }
        }
    }

    // ========================
    // Formatting Helpers
    // ========================
    static formatCurrency(amount, currency = 'USD') {
        const num = parseFloat(amount);
        if (isNaN(num)) return '—';
        try {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 2
            }).format(num);
        } catch {
            return `${currency} ${num.toFixed(2)}`;
        }
    }

    static formatDate(dateStr) {
        if (!dateStr) return '—';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch {
            return dateStr;
        }
    }

    static formatDateTime(dateStr) {
        if (!dateStr) return '—';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateStr;
        }
    }

    static statusBadge(status) {
        const map = {
            'draft': 'draft',
            'waiting_approval': 'waiting',
            'approved': 'approved',
            'rejected': 'rejected',
            'pending': 'pending'
        };
        const cls = map[status] || 'draft';
        const label = status ? status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Unknown';
        return `<span class="badge badge-${cls}">${label}</span>`;
    }

    static roleBadge(role) {
        const label = role ? role.charAt(0).toUpperCase() + role.slice(1) : 'User';
        return `<span class="badge badge-role">${label}</span>`;
    }

    static getInitials(name) {
        if (!name) return '?';
        return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    }

    // ========================
    // Sidebar
    // ========================
    static initSidebar() {
        const toggle = document.querySelector('.sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');

        if (toggle && sidebar) {
            toggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                if (overlay) overlay.classList.toggle('active');
            });
        }

        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            });
        }
    }

    static setActiveNav(page) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.page === page) {
                item.classList.add('active');
            }
        });
    }

    // ========================
    // Auth Guards
    // ========================
    static requireAuth() {
        if (!API.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    static requireRole(...roles) {
        const user = API.getUser();
        if (!user || !roles.includes(user.role)) {
            UI.error('You do not have permission to access this page.');
            return false;
        }
        return true;
    }

    // ========================
    // Page Setup
    // ========================
    static setupDashboardLayout(user) {
        // Set user info in sidebar
        const nameEl = document.querySelector('.user-name');
        const roleEl = document.querySelector('.user-role');
        const avatarEl = document.querySelector('.user-avatar');

        if (nameEl) nameEl.textContent = user.name;
        if (roleEl) roleEl.textContent = user.role;
        if (avatarEl) avatarEl.textContent = this.getInitials(user.name);

        // Show/hide nav items based on role
        document.querySelectorAll('[data-roles]').forEach(el => {
            const roles = el.dataset.roles.split(',');
            el.style.display = roles.includes(user.role) ? '' : 'none';
        });

        // Logout handler
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                API.clearAuth();
                window.location.href = 'login.html';
            });
        }

        this.initSidebar();
    }
}

window.UI = UI;
