import os
import sys
from flask import Flask, send_from_directory
from flask_cors import CORS
from config import Config
from models.database import Database
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.expense_routes import expense_bp
from routes.approval_routes import approval_bp
from routes.company_routes import company_bp


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(expense_bp, url_prefix='/api/expenses')
    app.register_blueprint(approval_bp, url_prefix='/api/approvals')
    app.register_blueprint(company_bp, url_prefix='/api/companies')

    # Serve frontend files
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')

    @app.route('/admin/dashboard')
    def admin_dashboard():
        return send_from_directory(frontend_dir, 'admin_dashboard.html')

    @app.route('/manager/dashboard')
    def manager_dashboard():
        return send_from_directory(frontend_dir, 'manager_dashboard.html')

    @app.route('/employee/dashboard')
    def employee_dashboard():
        return send_from_directory(frontend_dir, 'employee_dashboard.html')

    @app.route('/employee/register')
    def employee_register():
        return send_from_directory(frontend_dir, 'employee_register.html')

    @app.route('/manager/register')
    def manager_register():
        return send_from_directory(frontend_dir, 'manager_register.html')

    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        file_path = os.path.join(frontend_dir, path)
        if os.path.isfile(file_path):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, 'index.html')

    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return {'status': 'ok', 'message': 'FlowFund API is running'}, 200

    return app


if __name__ == "__main__":
    # Initialize database
    try:
        Database.init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
        print("The app will continue but database operations may fail.")

    app = create_app()
    print("🚀 FlowFund server starting on http://0.0.0.0:10000")
    app.run(host="0.0.0.0", port=10000)
