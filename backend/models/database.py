import mysql.connector
from mysql.connector import pooling
from config import Config

class Database:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="FlowFund_pool",
                pool_size=5,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                autocommit=False
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        return cls.get_pool().get_connection()

    @classmethod
    def execute_query(cls, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        conn = cls.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            if commit:
                conn.commit()
                result = cursor.lastrowid
            return result
        except Exception as e:
            if commit:
                conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def execute_many(cls, query, params_list, commit=True):
        conn = cls.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.executemany(query, params_list)
            if commit:
                conn.commit()
            return cursor.lastrowid
        except Exception as e:
            if commit:
                conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def init_db(cls):
        """Initialize the database and create tables if they don't exist."""
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cursor = conn.cursor()
        try:
            cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(Config.DB_NAME))
            cursor.execute("USE {}".format(Config.DB_NAME))

            # Companies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    country VARCHAR(100) NOT NULL,
                    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
                    company_code VARCHAR(10) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'manager', 'employee') NOT NULL DEFAULT 'employee',
                    manager_id INT NULL,
                    company_id INT NULL DEFAULT NULL,
                    phone VARCHAR(20) NULL,
                    department VARCHAR(100) NULL,
                    is_head_manager BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT TRUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                )
            """)

            # Expenses table
            cursor.execute("""
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
                )
            """)

            # Approval Rules table
            cursor.execute("""
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
                )
            """)

            # Approval Rule Steps
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approval_rule_steps (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    rule_id INT NOT NULL,
                    approver_id INT NOT NULL,
                    sequence_order INT NOT NULL DEFAULT 1,
                    role_required VARCHAR(50) NULL,
                    FOREIGN KEY (rule_id) REFERENCES approval_rules(id) ON DELETE CASCADE,
                    FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Approvals table
            cursor.execute("""
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
                )
            """)

            conn.commit()
            print("Database initialized successfully!")
        except Exception as e:
            conn.rollback()
            print(f"Error initializing database: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()
