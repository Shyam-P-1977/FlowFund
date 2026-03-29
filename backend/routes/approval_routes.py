from flask import Blueprint, request, jsonify
from models.database import Database
from utils.auth import token_required, role_required
from services.approval_engine import ApprovalEngine

approval_bp = Blueprint('approvals', __name__)


@approval_bp.route('/pending', methods=['GET'])
@token_required
@role_required('manager', 'admin')
def get_pending():
    """Get pending approvals. Head manager sees ALL company expenses."""
    user = request.current_user
    is_head = bool(user.get('is_head_manager'))

    if is_head:
        # Head manager: fetch all waiting-approval expenses in the company
        approvals = Database.execute_query(
            """SELECT e.id as expense_id, e.amount, e.currency, e.converted_amount,
                      e.company_currency, e.category, e.description, e.expense_date,
                      e.paid_by, e.receipt_path, e.remarks, e.status as expense_status,
                      e.current_approval_step, u.name as employee_name, u.email as employee_email,
                      1 as sequence_order
               FROM expenses e
               JOIN users u ON e.user_id = u.id
               WHERE u.company_id = %s AND e.status = 'waiting_approval'
               ORDER BY e.created_at DESC""",
            (user['company_id'],), fetch_all=True)
    else:
        approvals = ApprovalEngine.get_pending_approvals(user['id'])

    for a in approvals:
        for key, val in a.items():
            if hasattr(val, 'isoformat'):
                a[key] = val.isoformat()
            elif isinstance(val, bytes):
                a[key] = val.decode('utf-8')
            elif hasattr(val, '__str__') and not isinstance(val, (str, int, float, type(None), bool)):
                a[key] = str(val)

    return jsonify({'approvals': approvals, 'is_head_manager': is_head}), 200


@approval_bp.route('/<int:expense_id>/approve', methods=['POST'])
@token_required
@role_required('manager', 'admin')
def approve_expense(expense_id):
    """Approve an expense. Head manager and Admin approval is final."""
    data = request.get_json() or {}
    comments = data.get('comments', '')
    user = request.current_user
    is_head = bool(user.get('is_head_manager'))
    is_admin = user.get('role') == 'admin'

    if is_head or is_admin:
        role_label = "Admin" if is_admin else "Head Manager"
        # Admin or Head manager direct final approval
        Database.execute_query(
            "UPDATE expenses SET status = 'approved' WHERE id = %s",
            (expense_id,), commit=True)
        Database.execute_query(
            "UPDATE approvals SET status = 'approved', comments = %s WHERE expense_id = %s AND status = 'pending'",
            (comments or f'Directly approved by {role_label}', expense_id), commit=True)
        return jsonify({'status': 'approved', 'message': f'Directly approved by {role_label}'}), 200

    result = ApprovalEngine.process_approval(expense_id, user['id'], 'approved', comments)
    return jsonify(result), 200


@approval_bp.route('/<int:expense_id>/reject', methods=['POST'])
@token_required
@role_required('manager', 'admin')
def reject_expense(expense_id):
    """Reject an expense."""
    data = request.get_json() or {}
    comments = data.get('comments', '')
    user = request.current_user

    if not comments:
        return jsonify({'error': 'Comments are required when rejecting'}), 400

    is_head = bool(user.get('is_head_manager'))
    is_admin = user.get('role') == 'admin'

    if is_head or is_admin:
        role_label = "Admin" if is_admin else "Head Manager"
        Database.execute_query(
            "UPDATE expenses SET status = 'rejected' WHERE id = %s",
            (expense_id,), commit=True)
        Database.execute_query(
            "UPDATE approvals SET status = 'rejected', comments = %s WHERE expense_id = %s AND status = 'pending'",
            (comments, expense_id), commit=True)
        return jsonify({'status': 'rejected', 'message': f'Rejected by {role_label}'}), 200

    result = ApprovalEngine.process_approval(expense_id, user['id'], 'rejected', comments)
    return jsonify(result), 200


@approval_bp.route('/<int:expense_id>/history', methods=['GET'])
@token_required
def get_history(expense_id):
    """Get approval history for an expense."""
    history = ApprovalEngine.get_approval_history(expense_id)

    for h in history:
        for key, val in h.items():
            if hasattr(val, 'isoformat'):
                h[key] = val.isoformat()
            elif isinstance(val, bytes):
                h[key] = val.decode('utf-8')

    return jsonify({'history': history}), 200


@approval_bp.route('/rules', methods=['GET'])
@token_required
@role_required('admin')
def list_rules():
    """List all approval rules for the company."""
    company_id = request.current_user['company_id']

    rules = Database.execute_query(
        """SELECT ar.*, u.name as special_approver_name
           FROM approval_rules ar
           LEFT JOIN users u ON ar.special_approver_id = u.id
           WHERE ar.company_id = %s
           ORDER BY ar.min_amount""",
        (company_id,),
        fetch_all=True
    )

    for rule in rules:
        # Get steps for each rule
        steps = Database.execute_query(
            """SELECT ars.*, u.name as approver_name, u.email as approver_email
               FROM approval_rule_steps ars
               JOIN users u ON ars.approver_id = u.id
               WHERE ars.rule_id = %s
               ORDER BY ars.sequence_order""",
            (rule['id'],),
            fetch_all=True
        )
        rule['steps'] = steps

        for key, val in rule.items():
            if hasattr(val, 'isoformat'):
                rule[key] = val.isoformat()
            elif isinstance(val, bytes):
                rule[key] = val.decode('utf-8')
            elif hasattr(val, '__str__') and not isinstance(val, (str, int, float, type(None), bool)):
                rule[key] = str(val)

    return jsonify({'rules': rules}), 200


@approval_bp.route('/rules', methods=['POST'])
@token_required
@role_required('admin')
def create_rule():
    """Create a new approval rule."""
    data = request.get_json()
    company_id = request.current_user['company_id']

    name = data.get('name', '').strip()
    min_percentage = data.get('min_percentage', 100.0)
    is_sequential = data.get('is_sequential', True)
    is_manager_required = data.get('is_manager_required', True)
    special_approver_id = data.get('special_approver_id')
    special_approver_auto_approve = data.get('special_approver_auto_approve', False)
    min_amount = data.get('min_amount', 0)
    max_amount = data.get('max_amount')
    steps = data.get('steps', [])

    if not name:
        return jsonify({'error': 'Rule name is required'}), 400

    rule_id = Database.execute_query(
        """INSERT INTO approval_rules 
           (company_id, name, min_percentage, is_sequential, is_manager_required,
            special_approver_id, special_approver_auto_approve, min_amount, max_amount) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (company_id, name, min_percentage, is_sequential, is_manager_required,
         special_approver_id, special_approver_auto_approve, min_amount, max_amount),
        commit=True
    )

    # Create steps
    for step in steps:
        Database.execute_query(
            """INSERT INTO approval_rule_steps (rule_id, approver_id, sequence_order, role_required)
               VALUES (%s, %s, %s, %s)""",
            (rule_id, step['approver_id'], step.get('sequence_order', 1), step.get('role_required')),
            commit=True
        )

    return jsonify({'message': 'Approval rule created', 'rule_id': rule_id}), 201


@approval_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_rule(rule_id):
    """Update an approval rule."""
    data = request.get_json()
    company_id = request.current_user['company_id']

    # Verify rule belongs to company
    rule = Database.execute_query(
        "SELECT id FROM approval_rules WHERE id = %s AND company_id = %s",
        (rule_id, company_id),
        fetch_one=True
    )
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    updates = []
    params = []

    for field in ['name', 'min_percentage', 'is_sequential', 'is_manager_required',
                  'special_approver_id', 'special_approver_auto_approve', 'min_amount', 'max_amount', 'is_active']:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])

    if updates:
        params.append(rule_id)
        Database.execute_query(
            f"UPDATE approval_rules SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
            commit=True
        )

    # Update steps if provided
    if 'steps' in data:
        Database.execute_query(
            "DELETE FROM approval_rule_steps WHERE rule_id = %s",
            (rule_id,),
            commit=True
        )
        for step in data['steps']:
            Database.execute_query(
                """INSERT INTO approval_rule_steps (rule_id, approver_id, sequence_order, role_required)
                   VALUES (%s, %s, %s, %s)""",
                (rule_id, step['approver_id'], step.get('sequence_order', 1), step.get('role_required')),
                commit=True
            )

    return jsonify({'message': 'Rule updated'}), 200


@approval_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_rule(rule_id):
    """Delete an approval rule."""
    company_id = request.current_user['company_id']

    Database.execute_query(
        "DELETE FROM approval_rules WHERE id = %s AND company_id = %s",
        (rule_id, company_id),
        commit=True
    )

    return jsonify({'message': 'Rule deleted'}), 200


@approval_bp.route('/override/<int:expense_id>', methods=['POST'])
@token_required
@role_required('admin')
def override_approval(expense_id):
    """Admin override - instantly approve or reject an expense at any stage.
    The admin's action is recorded in the approval trail for full audit visibility.
    """
    data = request.get_json() or {}
    action = data.get('action', 'approve')
    comments = data.get('comments', 'Admin override')
    admin_id = request.current_user['id']

    # Check if admin already has an approvals row for this expense
    existing = Database.execute_query(
        "SELECT id FROM approvals WHERE expense_id = %s AND approver_id = %s",
        (expense_id, admin_id),
        fetch_one=True
    )

    if action == 'approve':
        target_status = 'approved'
        auto_comment = comments or 'Admin instant approval — override authority'
    else:
        target_status = 'rejected'
        auto_comment = comments or 'Admin rejection — override authority'

    # Update expense status
    Database.execute_query(
        f"UPDATE expenses SET status = '{target_status}' WHERE id = %s",
        (expense_id,),
        commit=True
    )
    # Mark all pending approval steps as resolved
    Database.execute_query(
        f"UPDATE approvals SET status = '{target_status}', comments = %s WHERE expense_id = %s AND status = 'pending'",
        (auto_comment, expense_id),
        commit=True
    )

    # Log admin's override action so it appears in the trail
    if not existing:
        # Find the highest sequence_order to place admin at end
        max_seq = Database.execute_query(
            "SELECT COALESCE(MAX(sequence_order), 0) as max_seq FROM approvals WHERE expense_id = %s",
            (expense_id,),
            fetch_one=True
        )
        next_seq = (max_seq['max_seq'] if max_seq else 0) + 1
        Database.execute_query(
            """INSERT INTO approvals (expense_id, approver_id, status, comments, sequence_order)
               VALUES (%s, %s, %s, %s, %s)""",
            (expense_id, admin_id, target_status, f'⚡ {auto_comment}', next_seq),
            commit=True
        )
    else:
        Database.execute_query(
            "UPDATE approvals SET status = %s, comments = %s WHERE expense_id = %s AND approver_id = %s",
            (target_status, f'⚡ {auto_comment}', expense_id, admin_id),
            commit=True
        )

    return jsonify({'message': f'Expense {action}d by admin override', 'status': target_status}), 200
