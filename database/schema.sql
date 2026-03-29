-- FlowFund Database Schema
-- MySQL

CREATE DATABASE IF NOT EXISTS FlowFund;
USE FlowFund;

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'manager', 'employee') NOT NULL DEFAULT 'employee',
    manager_id INT NULL,
    company_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Expenses table
CREATE TABLE IF NOT EXISTS expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    converted_amount DECIMAL(12, 2) NULL,
    company_currency VARCHAR(10) NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    expense_date DATE NOT NULL,
    paid_by ENUM('cash', 'card') NOT NULL DEFAULT 'cash',
    receipt_path VARCHAR(500) NULL,
    remarks TEXT NULL,
    status ENUM('draft', 'waiting_approval', 'approved', 'rejected') NOT NULL DEFAULT 'draft',
    current_approval_step INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Approval Rules table
CREATE TABLE IF NOT EXISTS approval_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    min_percentage DECIMAL(5,2) DEFAULT 100.00,
    is_sequential BOOLEAN DEFAULT TRUE,
    is_manager_required BOOLEAN DEFAULT TRUE,
    special_approver_id INT NULL,
    special_approver_auto_approve BOOLEAN DEFAULT FALSE,
    min_amount DECIMAL(12,2) DEFAULT 0,
    max_amount DECIMAL(12,2) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (special_approver_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Approval Rule Steps
CREATE TABLE IF NOT EXISTS approval_rule_steps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_id INT NOT NULL,
    approver_id INT NOT NULL,
    sequence_order INT NOT NULL DEFAULT 1,
    role_required VARCHAR(50) NULL,
    FOREIGN KEY (rule_id) REFERENCES approval_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Approvals table
CREATE TABLE IF NOT EXISTS approvals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_id INT NOT NULL,
    approver_id INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    comments TEXT NULL,
    sequence_order INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_users_company ON users(company_id);
CREATE INDEX idx_users_manager ON users(manager_id);
CREATE INDEX idx_expenses_user ON expenses(user_id);
CREATE INDEX idx_expenses_status ON expenses(status);
CREATE INDEX idx_approvals_expense ON approvals(expense_id);
CREATE INDEX idx_approvals_approver ON approvals(approver_id);
CREATE INDEX idx_approval_rules_company ON approval_rules(company_id);
