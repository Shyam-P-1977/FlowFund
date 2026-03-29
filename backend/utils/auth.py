import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from config import Config
from models.database import Database


def generate_token(user_id, role, company_id):
    """Generate JWT token for authenticated user."""
    payload = {
        'user_id': user_id,
        'role': role,
        'company_id': company_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')


def decode_token(token):
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        payload = decode_token(token)
        if payload is None:
            return jsonify({'error': 'Token is invalid or expired'}), 401

        # Get user from database
        user = Database.execute_query(
            """SELECT id, name, email, role, company_id, manager_id, is_head_manager
               FROM users WHERE id = %s AND is_active = TRUE""",
            (payload['user_id'],), fetch_one=True
        )
        if not user:
            return jsonify({'error': 'User not found or inactive'}), 401

        if 'is_head_manager' in user:
            user['is_head_manager'] = bool(user['is_head_manager'])

        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Decorator to require specific role(s)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            if request.current_user['role'] not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
