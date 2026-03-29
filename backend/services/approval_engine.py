from models.database import Database


class ApprovalEngine:
    """Handles multi-level, conditional, and hybrid approval workflows."""

    @classmethod
    def get_applicable_rule(cls, company_id, amount):
        """Find the applicable approval rule for a given expense amount."""
        rules = Database.execute_query(
            """SELECT * FROM approval_rules 
               WHERE company_id = %s AND is_active = TRUE 
               AND (min_amount <= %s) 
               AND (max_amount IS NULL OR max_amount >= %s)
               ORDER BY min_amount DESC LIMIT 1""",
            (company_id, amount, amount),
            fetch_one=True
        )
        return rules

    @classmethod
    def create_approval_chain(cls, expense_id, user_id, company_id, amount):
        """Create the approval chain for an expense based on rules."""
        rule = cls.get_applicable_rule(company_id, amount)

        # Get the employee's manager
        employee = Database.execute_query(
            "SELECT manager_id FROM users WHERE id = %s",
            (user_id,),
            fetch_one=True
        )
        manager_id = employee.get('manager_id') if employee else None

        # Get Head Managers for the company dynamically
        head_managers = Database.execute_query(
            "SELECT id FROM users WHERE company_id = %s AND is_head_manager = TRUE AND is_active = TRUE",
            (company_id,),
            fetch_all=True
        )

        approvers = []
        sequence = 1

        if rule:
            # If manager is required, add manager first
            if rule['is_manager_required'] and manager_id:
                approvers.append({
                    'approver_id': manager_id,
                    'sequence_order': sequence
                })
                sequence += 1

            # Get rule steps
            steps = Database.execute_query(
                """SELECT * FROM approval_rule_steps 
                   WHERE rule_id = %s ORDER BY sequence_order""",
                (rule['id'],),
                fetch_all=True
            )

            for step in steps:
                # Don't duplicate manager
                if step['approver_id'] != manager_id:
                    approvers.append({
                        'approver_id': step['approver_id'],
                        'sequence_order': sequence
                    })
                    sequence += 1

            # Dynamically insert Head Managers into the chain
            if head_managers:
                head_manager_added = False
                for hm in head_managers:
                    # Prevent duplicates if Head Manager is the same as Direct Manager or already in steps
                    if not any(a['approver_id'] == hm['id'] for a in approvers):
                        approvers.append({
                            'approver_id': hm['id'],
                            'sequence_order': sequence
                        })
                        head_manager_added = True
                if head_manager_added:
                    sequence += 1

            # Add special approver if defined
            if rule.get('special_approver_id'):
                already_added = any(a['approver_id'] == rule['special_approver_id'] for a in approvers)
                if not already_added:
                    approvers.append({
                        'approver_id': rule['special_approver_id'],
                        'sequence_order': sequence
                    })

        elif manager_id:
            # No rule defined? Just use the direct manager
            approvers.append({
                'approver_id': manager_id,
                'sequence_order': 1
            })
            
            # Followed by Head Managers
            if head_managers:
                head_manager_added = False
                for hm in head_managers:
                    if hm['id'] != manager_id:
                        approvers.append({
                            'approver_id': hm['id'],
                            'sequence_order': 2
                        })
                        head_manager_added = True
                if head_manager_added:
                    sequence = 3
            else:
                sequence = 2

        # Create approval records
        for approver in approvers:
            Database.execute_query(
                """INSERT INTO approvals (expense_id, approver_id, status, sequence_order) 
                   VALUES (%s, %s, 'pending', %s)""",
                (expense_id, approver['approver_id'], approver['sequence_order']),
                commit=True
            )

        # Update expense status
        if approvers:
            Database.execute_query(
                "UPDATE expenses SET status = 'waiting_approval', current_approval_step = 1 WHERE id = %s",
                (expense_id,),
                commit=True
            )

        return approvers

    @classmethod
    def process_approval(cls, expense_id, approver_id, status, comments=None):
        """Process an approval action and determine next steps."""
        # Update this approval
        Database.execute_query(
            """UPDATE approvals 
               SET status = %s, comments = %s, updated_at = NOW() 
               WHERE expense_id = %s AND approver_id = %s AND status = 'pending'""",
            (status, comments, expense_id, approver_id),
            commit=True
        )

        # Get the expense
        expense = Database.execute_query(
            "SELECT * FROM expenses WHERE id = %s",
            (expense_id,),
            fetch_one=True
        )
        if not expense:
            return {'error': 'Expense not found'}

        # Get the employee's company
        employee = Database.execute_query(
            "SELECT company_id FROM users WHERE id = %s",
            (expense['user_id'],),
            fetch_one=True
        )
        company_id = employee['company_id'] if employee else None

        # Get applicable rule
        rule = cls.get_applicable_rule(company_id, float(expense['amount'])) if company_id else None

        if status == 'rejected':
            # Any rejection = expense rejected
            Database.execute_query(
                "UPDATE expenses SET status = 'rejected' WHERE id = %s",
                (expense_id,),
                commit=True
            )
            return {'status': 'rejected', 'message': 'Expense rejected'}

        # Status is 'approved' — check if more approvals needed
        all_approvals = Database.execute_query(
            "SELECT * FROM approvals WHERE expense_id = %s ORDER BY sequence_order",
            (expense_id,),
            fetch_all=True
        )

        total = len(all_approvals)
        approved_count = sum(1 for a in all_approvals if a['status'] == 'approved')

        # Check special approver auto-approve
        if rule and rule.get('special_approver_auto_approve') and rule.get('special_approver_id'):
            special_approved = any(
                a['approver_id'] == rule['special_approver_id'] and a['status'] == 'approved'
                for a in all_approvals
            )
            if special_approved:
                Database.execute_query(
                    "UPDATE expenses SET status = 'approved' WHERE id = %s",
                    (expense_id,),
                    commit=True
                )
                # Auto-approve remaining pending approvals
                Database.execute_query(
                    "UPDATE approvals SET status = 'approved', comments = 'Auto-approved by special approver' WHERE expense_id = %s AND status = 'pending'",
                    (expense_id,),
                    commit=True
                )
                return {'status': 'approved', 'message': 'Auto-approved by special approver'}

        # Check percentage rule
        if rule and rule.get('min_percentage'):
            required_pct = float(rule['min_percentage'])
            current_pct = (approved_count / total * 100) if total > 0 else 0

            if current_pct >= required_pct:
                Database.execute_query(
                    "UPDATE expenses SET status = 'approved' WHERE id = %s",
                    (expense_id,),
                    commit=True
                )
                return {'status': 'approved', 'message': f'Approved ({current_pct:.0f}% of approvals received)'}

        # Check if all approved (100% case or no rule)
        if approved_count == total:
            Database.execute_query(
                "UPDATE expenses SET status = 'approved' WHERE id = %s",
                (expense_id,),
                commit=True
            )
            return {'status': 'approved', 'message': 'All approvals received'}

        # Sequential mode: advance to next step
        if rule and rule.get('is_sequential'):
            next_step = expense['current_approval_step'] + 1
            Database.execute_query(
                "UPDATE expenses SET current_approval_step = %s WHERE id = %s",
                (next_step, expense_id),
                commit=True
            )
            return {'status': 'pending', 'message': f'Advanced to step {next_step}'}

        return {'status': 'pending', 'message': 'Awaiting more approvals'}

    @classmethod
    def get_pending_approvals(cls, approver_id):
        """Get all pending approvals for an approver."""
        approvals = Database.execute_query(
            """SELECT a.*, e.amount, e.currency, e.converted_amount, e.company_currency,
                      e.category, e.description, e.expense_date, e.paid_by, 
                      e.receipt_path, e.remarks, e.status as expense_status,
                      e.current_approval_step, u.name as employee_name, u.email as employee_email
               FROM approvals a
               JOIN expenses e ON a.expense_id = e.id
               JOIN users u ON e.user_id = u.id
               WHERE a.approver_id = %s AND a.status = 'pending'
               AND e.status = 'waiting_approval'
               ORDER BY a.created_at DESC""",
            (approver_id,),
            fetch_all=True
        )

        # For sequential mode, only show current step
        filtered = []
        for approval in approvals:
            if approval['sequence_order'] <= approval['current_approval_step']:
                filtered.append(approval)

        return filtered

    @classmethod
    def get_approval_history(cls, expense_id):
        """Get full approval history for an expense."""
        return Database.execute_query(
            """SELECT a.*, u.name as approver_name, u.email as approver_email
               FROM approvals a
               JOIN users u ON a.approver_id = u.id
               WHERE a.expense_id = %s
               ORDER BY a.sequence_order, a.created_at""",
            (expense_id,),
            fetch_all=True
        )
