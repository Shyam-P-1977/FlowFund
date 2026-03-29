from flask import Blueprint, request, jsonify
import bcrypt
from models.database import Database
from utils.auth import token_required, role_required

user_bp = Blueprint('users', __name__)


@user_bp.route('/', methods=['GET'])
@token_required
@role_required('admin')
def list_users():
    """List all users in the company with full details."""
    company_id = request.current_user['company_id']
    users = Database.execute_query(
        """SELECT u.id, u.name, u.email, u.role, u.manager_id, u.is_active,
                  u.phone, u.department, u.is_head_manager, u.is_approved, u.created_at,
                  m.name as manager_name
           FROM users u
           LEFT JOIN users m ON u.manager_id = m.id
           WHERE u.company_id = %s
           ORDER BY u.role, u.created_at DESC""",
        (company_id,), fetch_all=True)

    for u in users:
        if 'is_head_manager' in u:
            u['is_head_manager'] = bool(u['is_head_manager'])
        if 'is_active' in u:
            u['is_active'] = bool(u['is_active'])
        if 'is_approved' in u:
            u['is_approved'] = bool(u['is_approved'])
        for key, val in u.items():
            if hasattr(val, 'isoformat'):
                u[key] = val.isoformat()

    return jsonify({'users': users}), 200


@user_bp.route('/', methods=['POST'])
@token_required
@role_required('admin')
def create_user():
    """Admin creates a user directly (without self-registration)."""
    data = request.get_json()
    company_id = request.current_user['company_id']

    name       = data.get('name', '').strip()
    email      = data.get('email', '').strip().lower()
    password   = data.get('password', '')
    role       = data.get('role', 'employee')
    manager_id = data.get('manager_id')
    phone      = data.get('phone', '').strip()
    department = data.get('department', '').strip()

    if not all([name, email, password]):
        return jsonify({'error': 'Name, email, and password are required'}), 400
    if role not in ('employee', 'manager'):
        return jsonify({'error': 'Role must be employee or manager'}), 400

    existing = Database.execute_query(
        "SELECT id FROM users WHERE email = %s", (email,), fetch_one=True)
    if existing:
        return jsonify({'error': 'Email already exists'}), 409

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = Database.execute_query(
        """INSERT INTO users (name, email, password, role, manager_id, company_id,
           phone, department, is_approved) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)""",
        (name, email, hashed.decode('utf-8'), role, manager_id, company_id,
         phone or None, department or None), commit=True)

    return jsonify({'message': 'User created successfully',
                    'user': {'id': user_id, 'name': name, 'email': email,
                             'role': role, 'manager_id': manager_id}}), 201


@user_bp.route('/<int:user_id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_user(user_id):
    """Update user details."""
    data = request.get_json()
    company_id = request.current_user['company_id']

    user = Database.execute_query(
        "SELECT id FROM users WHERE id = %s AND company_id = %s",
        (user_id, company_id), fetch_one=True)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    updates, params = [], []

    for field in ['name', 'department', 'phone']:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])

    if 'role' in data and data['role'] in ('employee', 'manager', 'admin'):
        updates.append("role = %s")
        params.append(data['role'])
    if 'manager_id' in data:
        updates.append("manager_id = %s")
        params.append(data['manager_id'])
    if 'is_active' in data:
        updates.append("is_active = %s")
        params.append(bool(data['is_active']))
    if 'is_head_manager' in data:
        updates.append("is_head_manager = %s")
        params.append(bool(data['is_head_manager']))
    if 'password' in data and data['password']:
        hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        updates.append("password = %s")
        params.append(hashed.decode('utf-8'))

    if not updates:
        return jsonify({'error': 'No fields to update'}), 400

    params.append(user_id)
    Database.execute_query(
        f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
        tuple(params), commit=True)

    return jsonify({'message': 'User updated successfully'}), 200


@user_bp.route('/<int:user_id>/assign-manager', methods=['POST'])
@token_required
@role_required('admin')
def assign_manager(user_id):
    """Assign a manager to an employee."""
    data = request.get_json()
    company_id = request.current_user['company_id']
    manager_id = data.get('manager_id')

    # Verify employee belongs to this company
    user = Database.execute_query(
        "SELECT id, role FROM users WHERE id = %s AND company_id = %s",
        (user_id, company_id), fetch_one=True)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if manager_id:
        # Verify manager belongs to company and is actually a manager
        mgr = Database.execute_query(
            "SELECT id FROM users WHERE id = %s AND company_id = %s AND role IN ('manager','admin')",
            (manager_id, company_id), fetch_one=True)
        if not mgr:
            return jsonify({'error': 'Manager not found in your company'}), 404

    Database.execute_query(
        "UPDATE users SET manager_id = %s WHERE id = %s",
        (manager_id, user_id), commit=True)

    return jsonify({'message': 'Manager assigned successfully'}), 200


@user_bp.route('/<int:user_id>/set-head-manager', methods=['POST'])
@token_required
@role_required('admin')
def set_head_manager(user_id):
    """Toggle head manager status for a manager."""
    data = request.get_json()
    company_id = request.current_user['company_id']
    is_head    = bool(data.get('is_head_manager', True))

    user = Database.execute_query(
        "SELECT id, role FROM users WHERE id = %s AND company_id = %s AND role = 'manager'",
        (user_id, company_id), fetch_one=True)
    if not user:
        return jsonify({'error': 'Manager not found'}), 404

    Database.execute_query(
        "UPDATE users SET is_head_manager = %s WHERE id = %s",
        (is_head, user_id), commit=True)

    return jsonify({'message': f"Head manager status {'set' if is_head else 'removed'}"}), 200


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@token_required
@role_required('admin')
def deactivate_user(user_id):
    """Deactivate a user."""
    company_id = request.current_user['company_id']
    if user_id == request.current_user['id']:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400
    Database.execute_query(
        "UPDATE users SET is_active = FALSE WHERE id = %s AND company_id = %s",
        (user_id, company_id), commit=True)
    return jsonify({'message': 'User deactivated'}), 200


@user_bp.route('/managers', methods=['GET'])
@token_required
@role_required('admin')
def list_managers():
    """List all managers in the company."""
    company_id = request.current_user['company_id']
    managers = Database.execute_query(
        """SELECT id, name, email, department, is_head_manager
           FROM users WHERE company_id = %s AND role IN ('manager','admin')
           AND is_active = TRUE ORDER BY name""",
        (company_id,), fetch_all=True)
    for m in managers:
        if 'is_head_manager' in m:
            m['is_head_manager'] = bool(m['is_head_manager'])
    return jsonify({'managers': managers}), 200


@user_bp.route('/team', methods=['GET'])
@token_required
@role_required('manager', 'admin')
def list_team():
    """List team members managed by current user."""
    user_id = request.current_user['id']
    team = Database.execute_query(
        "SELECT id, name, email, role, department FROM users WHERE manager_id = %s AND is_active = TRUE",
        (user_id,), fetch_all=True)
    return jsonify({'team': team}), 200
