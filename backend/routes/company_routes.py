from flask import Blueprint, request, jsonify
from models.database import Database
from utils.auth import token_required, role_required, generate_token

company_bp = Blueprint('companies', __name__)

@company_bp.route('/', methods=['POST'])
@token_required
@role_required('admin')
def create_company():
    """Create a new company and link the current admin user to it.
    Returns a fresh JWT token with the company_id embedded so the frontend
    doesn't need to re-login.
    """
    data = request.get_json()
    name = data.get('name', '').strip()
    country = data.get('country', '').strip()
    currency = data.get('currency', 'USD').strip()

    if not all([name, country, currency]):
        return jsonify({'error': 'Name, country, and currency are required'}), 400

    # Ensure user doesn't already have a company
    if request.current_user.get('company_id'):
        return jsonify({'error': 'You already belong to a company'}), 400

    company_id = Database.execute_query(
        "INSERT INTO companies (name, country, currency) VALUES (%s, %s, %s)",
        (name, country, currency),
        commit=True
    )

    Database.execute_query(
        "UPDATE users SET company_id = %s WHERE id = %s",
        (company_id, request.current_user['id']),
        commit=True
    )

    # Issue a fresh token with company_id embedded so subsequent API calls work
    new_token = generate_token(request.current_user['id'], 'admin', company_id)

    return jsonify({
        'message': 'Company created successfully',
        'token': new_token,
        'company': {
            'id': company_id,
            'name': name,
            'country': country,
            'currency': currency
        },
        'user': {
            'id': request.current_user['id'],
            'name': request.current_user['name'],
            'email': request.current_user['email'],
            'role': 'admin',
            'company_id': company_id,
            'company_name': name,
            'currency': currency
        }
    }), 201
