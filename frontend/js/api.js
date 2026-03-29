/**
 * FlowFund - Core API Client
 * Handles all HTTP requests to the backend
 */

// Update API_BASE to point to the correct port (Flask default is 5000)
const API_BASE = 'https://flowfund-2dt5.onrender.com/api';

class API {
    static getToken() {
        return localStorage.getItem('rf_token');
    }

    static setToken(token) {
        localStorage.setItem('rf_token', token);
    }

    static clearAuth() {
        localStorage.removeItem('rf_token');
        localStorage.removeItem('rf_user');
    }

    static getUser() {
        const data = localStorage.getItem('rf_user');
        return data ? JSON.parse(data) : null;
    }

    static setUser(user) {
        localStorage.setItem('rf_user', JSON.stringify(user));
    }

    static isAuthenticated() {
        return !!this.getToken();
    }

    static async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = options.headers || {};

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (response.status === 401) {
                this.clearAuth();
                if (!window.location.pathname.includes('login') && !window.location.pathname.includes('signup')) {
                    window.location.href = 'login.html';
                }
                throw new Error(data.error || 'Authentication expired');
            }

            if (!response.ok) {
                throw new Error(data.error || `Request failed: ${response.status}`);
            }

            return data;
        } catch (error) {
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                throw new Error('Unable to connect to server. Please ensure the backend is running.');
            }
            throw error;
        }
    }

    static get(endpoint) {
        return this.request(endpoint);
    }

    static post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    static async upload(endpoint, formData) {
        return this.request(endpoint, {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type with boundary
        });
    }

    // Auth endpoints
    static signup(data) { return this.post('/auth/signup', data); }
    static login(data) { return this.post('/auth/login', data); }
    static getMe() { return this.get('/auth/me'); }
    static getCountries() { return this.get('/auth/countries'); }
    static getCurrencies() { return this.get('/auth/currencies'); }
    static registerEmployee(data) { return this.post('/auth/register/employee', data); }
    static registerManager(data) { return this.post('/auth/register/manager', data); }
    static getCompanyByCode(code) { return this.get(`/auth/company/info?code=${code}`); }

    // User endpoints
    static listUsers() { return this.get('/users/'); }
    static createUser(data) { return this.post('/users/', data); }
    static updateUser(id, data) { return this.put(`/users/${id}`, data); }
    static deleteUser(id) { return this.delete(`/users/${id}`); }
    static listManagers() { return this.get('/users/managers'); }
    static assignManager(userId, managerId) { return this.post(`/users/${userId}/assign-manager`, { manager_id: managerId }); }
    static setHeadManager(userId, isHead) { return this.post(`/users/${userId}/set-head-manager`, { is_head_manager: isHead }); }

    // Expense endpoints
    static listExpenses() { return this.get('/expenses/'); }
    static getExpense(id) { return this.get(`/expenses/${id}`); }
    static createExpense(formData) { return this.upload('/expenses/', formData); }
    static submitExpense(id) { return this.post(`/expenses/${id}/submit`); }
    static processOCR(formData) { return this.upload('/expenses/ocr', formData); }

    // Approval endpoints
    static getPendingApprovals() { return this.get('/approvals/pending'); }
    static approveExpense(id, comments) { return this.post(`/approvals/${id}/approve`, { comments }); }
    static rejectExpense(id, comments) { return this.post(`/approvals/${id}/reject`, { comments }); }
    static getApprovalHistory(id) { return this.get(`/approvals/${id}/history`); }
    static listRules() { return this.get('/approvals/rules'); }
    static createRule(data) { return this.post('/approvals/rules', data); }
    static updateRule(id, data) { return this.put(`/approvals/rules/${id}`, data); }
    static deleteRule(id) { return this.delete(`/approvals/rules/${id}`); }
    static overrideApproval(id, data) { return this.post(`/approvals/override/${id}`, data); }
}

window.API = API;
