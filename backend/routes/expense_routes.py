import os
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from models.database import Database
from utils.auth import token_required, role_required
from services.currency_service import CurrencyService
from services.approval_engine import ApprovalEngine
from services.ocr_service import OCRService
from config import Config

expense_bp = Blueprint('expenses', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@expense_bp.route('/', methods=['GET'])
@token_required
def list_expenses():
    """List expenses based on user role."""
    user = request.current_user
    role = user['role']
    company_id = user['company_id']

    if role == 'admin':
        # Admin sees all company expenses
        expenses = Database.execute_query(
            """SELECT e.*, u.name as employee_name, u.email as employee_email
               FROM expenses e
               JOIN users u ON e.user_id = u.id
               WHERE u.company_id = %s
               ORDER BY e.created_at DESC""",
            (company_id,),
            fetch_all=True
        )
    elif role == 'manager':
        # Manager sees team expenses
        expenses = Database.execute_query(
            """SELECT e.*, u.name as employee_name, u.email as employee_email
               FROM expenses e
               JOIN users u ON e.user_id = u.id
               WHERE (u.manager_id = %s OR e.user_id = %s)
               ORDER BY e.created_at DESC""",
            (user['id'], user['id']),
            fetch_all=True
        )
    else:
        # Employee sees only their own expenses
        expenses = Database.execute_query(
            """SELECT e.*, u.name as employee_name
               FROM expenses e
               JOIN users u ON e.user_id = u.id
               WHERE e.user_id = %s
               ORDER BY e.created_at DESC""",
            (user['id'],),
            fetch_all=True
        )

    # Convert date/datetime objects to strings
    for exp in expenses:
        for key, val in exp.items():
            if hasattr(val, 'isoformat'):
                exp[key] = val.isoformat()
            elif isinstance(val, bytes):
                exp[key] = val.decode('utf-8')
            elif hasattr(val, '__str__') and not isinstance(val, (str, int, float, type(None), bool)):
                exp[key] = str(val)

    return jsonify({'expenses': expenses}), 200


@expense_bp.route('/', methods=['POST'])
@token_required
def create_expense():
    """Submit a new expense."""
    user = request.current_user

    # Handle form data (with possible file upload)
    if request.content_type and 'multipart/form-data' in request.content_type:
        amount = request.form.get('amount')
        currency = request.form.get('currency', 'USD')
        category = request.form.get('category', '')
        description = request.form.get('description', '')
        expense_date = request.form.get('expense_date')
        paid_by = request.form.get('paid_by', 'cash')
        remarks = request.form.get('remarks', '')
        submit = request.form.get('submit', 'false') == 'true'
    else:
        data = request.get_json()
        amount = data.get('amount')
        currency = data.get('currency', 'USD')
        category = data.get('category', '')
        description = data.get('description', '')
        expense_date = data.get('expense_date')
        paid_by = data.get('paid_by', 'cash')
        remarks = data.get('remarks', '')
        submit = data.get('submit', False)

    if not all([amount, category, expense_date]):
        return jsonify({'error': 'Amount, category, and date are required'}), 400

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    # Get company currency
    company = Database.execute_query(
        "SELECT currency FROM companies WHERE id = %s",
        (user['company_id'],),
        fetch_one=True
    )
    company_currency = company['currency'] if company else 'USD'

    # Convert currency
    converted_amount = CurrencyService.convert_currency(amount, currency, company_currency)

    # Handle receipt upload
    receipt_path = None
    if request.files and 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{user['id']}_{file.filename}")
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            receipt_path = filename

    status = 'waiting_approval' if submit else 'draft'

    expense_id = Database.execute_query(
        """INSERT INTO expenses 
           (user_id, amount, currency, converted_amount, company_currency, category, description, 
            expense_date, paid_by, receipt_path, remarks, status) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (user['id'], amount, currency, converted_amount, company_currency, category,
         description, expense_date, paid_by, receipt_path, remarks, status),
        commit=True
    )

    # If submitting, create approval chain
    if submit and status == 'waiting_approval':
        ApprovalEngine.create_approval_chain(expense_id, user['id'], user['company_id'], amount)

    return jsonify({
        'message': 'Expense created successfully',
        'expense_id': expense_id,
        'converted_amount': converted_amount,
        'company_currency': company_currency
    }), 201


@expense_bp.route('/<int:expense_id>', methods=['GET'])
@token_required
def get_expense(expense_id):
    """Get expense details with approval history."""
    expense = Database.execute_query(
        """SELECT e.*, u.name as employee_name, u.email as employee_email
           FROM expenses e
           JOIN users u ON e.user_id = u.id
           WHERE e.id = %s""",
        (expense_id,),
        fetch_one=True
    )

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Convert special types
    for key, val in expense.items():
        if hasattr(val, 'isoformat'):
            expense[key] = val.isoformat()
        elif isinstance(val, bytes):
            expense[key] = val.decode('utf-8')
        elif hasattr(val, '__str__') and not isinstance(val, (str, int, float, type(None), bool)):
            expense[key] = str(val)

    # Get approval history
    history = ApprovalEngine.get_approval_history(expense_id)
    for h in history:
        for key, val in h.items():
            if hasattr(val, 'isoformat'):
                h[key] = val.isoformat()
            elif isinstance(val, bytes):
                h[key] = val.decode('utf-8')

    expense['approval_history'] = history

    return jsonify({'expense': expense}), 200


@expense_bp.route('/<int:expense_id>/submit', methods=['POST'])
@token_required
def submit_expense(expense_id):
    """Submit a draft expense for approval."""
    user = request.current_user

    expense = Database.execute_query(
        "SELECT * FROM expenses WHERE id = %s AND user_id = %s AND status = 'draft'",
        (expense_id, user['id']),
        fetch_one=True
    )

    if not expense:
        return jsonify({'error': 'Expense not found or already submitted'}), 404

    Database.execute_query(
        "UPDATE expenses SET status = 'waiting_approval' WHERE id = %s",
        (expense_id,),
        commit=True
    )

    ApprovalEngine.create_approval_chain(expense_id, user['id'], user['company_id'], float(expense['amount']))

    return jsonify({'message': 'Expense submitted for approval'}), 200


@expense_bp.route('/ocr', methods=['POST'])
@token_required
def process_ocr():
    """Process receipt image with OCR."""
    if 'receipt' not in request.files:
        return jsonify({'error': 'No receipt file provided'}), 400

    file = request.files['receipt']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Save temporarily
    filename = secure_filename(f"ocr_{request.current_user['id']}_{file.filename}")
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Process with OCR
    result = OCRService.extract_from_receipt(filepath)

    return jsonify({'ocr_result': result}), 200


@expense_bp.route('/receipt/<path:filename>', methods=['GET'])
@token_required
def get_receipt(filename):
    """Serve uploaded receipt file."""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)
