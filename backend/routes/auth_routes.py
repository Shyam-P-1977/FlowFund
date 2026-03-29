from flask import Blueprint, request, jsonify
import bcrypt
import secrets
import string
from models.database import Database
from utils.auth import generate_token, token_required
from services.currency_service import CurrencyService

auth_bp = Blueprint('auth', __name__)


def _generate_company_code():
    """Generate a unique 6-character alphanumeric company code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(chars) for _ in range(6))
        existing = Database.execute_query(
            "SELECT id FROM companies WHERE company_code = %s", (code,), fetch_one=True)
        if not existing:
            return code


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Admin sign-up: auto-creates company + admin account in one step."""
    data = request.get_json()

    name         = data.get('name', '').strip()
    email        = data.get('email', '').strip().lower()
    password     = data.get('password', '')
    country      = data.get('country', '').strip()
    phone        = data.get('phone', '').strip()
    company_name = data.get('company_name', '').strip() or f"{name}'s Company"

    if not all([name, email, password, country]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    existing = Database.execute_query(
        "SELECT id FROM users WHERE email = %s", (email,), fetch_one=True)
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Determine currency from country
    currency     = CurrencyService.get_currency_for_country(country)
    company_code = _generate_company_code()

    # Create company
    company_id = Database.execute_query(
        "INSERT INTO companies (name, country, currency, company_code) VALUES (%s, %s, %s, %s)",
        (company_name, country, currency, company_code), commit=True)

    # Create admin user (auto-approved)
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = Database.execute_query(
        """INSERT INTO users (name, email, password, role, company_id, phone, is_approved)
           VALUES (%s, %s, %s, 'admin', %s, %s, TRUE)""",
        (name, email, hashed.decode('utf-8'), company_id, phone or None), commit=True)

    token = generate_token(user_id, 'admin', company_id)

    # ── Seed default approval rule ─────────────────────────────────────────
    # FlowFund Standard: Employee → Manager → Head Manager (100%, sequential)
    # Admin holds override authority via special_approver_auto_approve
    try:
        rule_id = Database.execute_query(
            """INSERT INTO approval_rules
               (company_id, name, min_percentage, is_sequential, is_manager_required,
                special_approver_id, special_approver_auto_approve, min_amount, max_amount, is_active)
               VALUES (%s, %s, 100.00, TRUE, TRUE, %s, TRUE, 0, NULL, TRUE)""",
            (company_id,
             'FlowFund Standard — Manager → Head Manager (100%, Sequential)',
             user_id),   # admin is the special approver with auto-approve
            commit=True
        )
    except Exception:
        pass  # Non-fatal: rule can be created manually later
    # ──────────────────────────────────────────────────────────────────────

    return jsonify({
        'message': 'Company and admin account created successfully',
        'token': token,
        'user': {
            'id': user_id, 'name': name, 'email': email, 'role': 'admin',
            'company_id': company_id, 'company_name': company_name,
            'currency': currency, 'company_code': company_code
        }
    }), 201


@auth_bp.route('/register/employee', methods=['POST'])
def register_employee():
    """Employee self-registration using company code."""
    data = request.get_json()

    name         = data.get('name', '').strip()
    email        = data.get('email', '').strip().lower()
    password     = data.get('password', '')
    phone        = data.get('phone', '').strip()
    department   = data.get('department', '').strip()
    company_code = data.get('company_code', '').strip().upper()

    if not all([name, email, password, company_code]):
        return jsonify({'error': 'Name, email, password, and company code are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Verify company code
    company = Database.execute_query(
        "SELECT id, name, currency FROM companies WHERE company_code = %s",
        (company_code,), fetch_one=True)
    if not company:
        return jsonify({'error': 'Invalid company code. Please ask your admin for the correct code.'}), 404

    existing = Database.execute_query(
        "SELECT id FROM users WHERE email = %s", (email,), fetch_one=True)
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = Database.execute_query(
        """INSERT INTO users (name, email, password, role, company_id, phone, department, is_approved)
           VALUES (%s, %s, %s, 'employee', %s, %s, %s, TRUE)""",
        (name, email, hashed.decode('utf-8'), company['id'],
         phone or None, department or None), commit=True)

    token = generate_token(user_id, 'employee', company['id'])

    return jsonify({
        'message': f'Registered successfully at {company["name"]}!',
        'token': token,
        'user': {
            'id': user_id, 'name': name, 'email': email, 'role': 'employee',
            'company_id': company['id'], 'company_name': company['name'],
            'currency': company['currency']
        }
    }), 201


@auth_bp.route('/register/manager', methods=['POST'])
def register_manager():
    """Manager self-registration using company code."""
    data = request.get_json()

    name         = data.get('name', '').strip()
    email        = data.get('email', '').strip().lower()
    password     = data.get('password', '')
    phone        = data.get('phone', '').strip()
    department   = data.get('department', '').strip()
    company_code = data.get('company_code', '').strip().upper()

    if not all([name, email, password, company_code]):
        return jsonify({'error': 'Name, email, password, and company code are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    company = Database.execute_query(
        "SELECT id, name, currency FROM companies WHERE company_code = %s",
        (company_code,), fetch_one=True)
    if not company:
        return jsonify({'error': 'Invalid company code.'}), 404

    existing = Database.execute_query(
        "SELECT id FROM users WHERE email = %s", (email,), fetch_one=True)
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = Database.execute_query(
        """INSERT INTO users (name, email, password, role, company_id, phone, department, is_approved)
           VALUES (%s, %s, %s, 'manager', %s, %s, %s, TRUE)""",
        (name, email, hashed.decode('utf-8'), company['id'],
         phone or None, department or None), commit=True)

    token = generate_token(user_id, 'manager', company['id'])

    return jsonify({
        'message': f'Registered successfully as Manager at {company["name"]}!',
        'token': token,
        'user': {
            'id': user_id, 'name': name, 'email': email, 'role': 'manager',
            'company_id': company['id'], 'company_name': company['name'],
            'currency': company['currency']
        }
    }), 201


@auth_bp.route('/company/info', methods=['GET'])
def get_company_by_code():
    """Get company name by company code (for registration preview)."""
    code = request.args.get('code', '').strip().upper()
    if not code:
        return jsonify({'error': 'Code required'}), 400
    company = Database.execute_query(
        "SELECT name, country, currency FROM companies WHERE company_code = %s",
        (code,), fetch_one=True)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    return jsonify({'company': company}), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not all([email, password]):
        return jsonify({'error': 'Email and password are required'}), 400

    user = Database.execute_query(
        """SELECT u.*, c.name as company_name, c.currency as company_currency,
                  c.company_code
           FROM users u
           LEFT JOIN companies c ON u.company_id = c.id
           WHERE u.email = %s AND u.is_active = TRUE""",
        (email,), fetch_one=True)

    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = generate_token(user['id'], user['role'], user['company_id'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'], 'name': user['name'], 'email': user['email'],
            'role': user['role'], 'company_id': user['company_id'],
            'company_name': user['company_name'], 'currency': user['company_currency'],
            'manager_id': user['manager_id'], 'company_code': user.get('company_code'),
            'is_head_manager': bool(user.get('is_head_manager'))
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current authenticated user profile."""
    user = Database.execute_query(
        """SELECT u.id, u.name, u.email, u.role, u.company_id, u.manager_id,
                  u.phone, u.department, u.is_head_manager,
                  c.name as company_name, c.currency as company_currency,
                  c.country, c.company_code
           FROM users u
           LEFT JOIN companies c ON u.company_id = c.id
           WHERE u.id = %s""",
        (request.current_user['id'],), fetch_one=True)
    if user and 'is_head_manager' in user:
        user['is_head_manager'] = bool(user['is_head_manager'])
    return jsonify({'user': user}), 200


@auth_bp.route('/countries', methods=['GET'])
def get_countries():
    countries = CurrencyService.get_countries_currencies()
    return jsonify({'countries': countries}), 200


@auth_bp.route('/currencies', methods=['GET'])
def get_currencies():
    currencies = CurrencyService.get_all_currencies()
    return jsonify({'currencies': currencies}), 200
