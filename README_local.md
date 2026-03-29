# ReimburseFlow – Smart Expense Reimbursement System

A complete full-stack web application for automated expense reimbursement with multi-level approvals, OCR receipt scanning, and currency conversion.

![ReimburseFlow](https://img.shields.io/badge/ReimburseFlow-v1.0-6366f1?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-Flask-green?style=flat-square)
![MySQL](https://img.shields.io/badge/Database-MySQL-blue?style=flat-square)

## ✨ Features

- **Authentication**: JWT-based signup/login with auto company creation
- **Role-Based Access**: Admin, Manager, Employee dashboards
- **Expense Management**: Submit, track, and manage expenses
- **Multi-Level Approvals**: Sequential & parallel workflows with conditional rules
- **OCR Receipt Scanning**: Auto-extract amount, date, vendor from receipts (Tesseract)
- **Currency Conversion**: Live exchange rates via external API
- **Admin Panel**: User management & approval rule configuration
- **Dark Theme UI**: Modern SaaS dashboard with responsive design

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Flask |
| Database | MySQL |
| Frontend | HTML5, CSS3, Vanilla JS |
| OCR | Tesseract (pytesseract) |
| Auth | JWT (PyJWT + bcrypt) |
| APIs | restcountries.com, exchangerate-api.com |

## 📦 Prerequisites

- **Python 3.8+**
- **MySQL 8.0+**
- **Tesseract OCR** (optional, for receipt scanning)

## 🚀 Setup & Run

### 1. Clone & Navigate
```bash
cd project-directory
```

### 2. Setup MySQL
```bash
# Log into MySQL and create the database
mysql -u root -p < database/schema.sql
```

Or let the app auto-create tables on startup.

### 3. Configure Environment
Edit `backend/config.py` or set environment variables:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=reimburseflow
```

### 4. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 5. Run the Server
```bash
python app.py
```

### 6. Open in Browser
Navigate to: **http://localhost:5000**

## 📁 Project Structure

```
project/
├── frontend/
│   ├── index.html          # Landing page
│   ├── login.html          # Login page
│   ├── signup.html         # Registration page
│   ├── dashboard.html      # Role-based dashboard
│   ├── expense.html        # Expense submission + OCR
│   ├── admin.html          # Admin panel (users + rules)
│   ├── css/
│   │   └── styles.css      # Complete design system
│   └── js/
│       ├── api.js          # API client
│       └── ui.js           # UI utilities
├── backend/
│   ├── app.py              # Flask application
│   ├── config.py           # Configuration
│   ├── requirements.txt    # Python dependencies
│   ├── routes/
│   │   ├── auth_routes.py      # Authentication
│   │   ├── user_routes.py      # User management
│   │   ├── expense_routes.py   # Expense CRUD + OCR
│   │   └── approval_routes.py  # Approval workflow
│   ├── models/
│   │   └── database.py     # MySQL connection pool
│   ├── services/
│   │   ├── approval_engine.py  # Multi-level approval logic
│   │   ├── currency_service.py # Currency conversion
│   │   └── ocr_service.py     # Tesseract OCR
│   └── utils/
│       └── auth.py         # JWT utilities
├── database/
│   └── schema.sql          # MySQL schema
├── uploads/                # Receipt uploads
└── README.md
```

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Register + auto-create company |
| POST | `/api/auth/login` | Login and get JWT token |
| GET | `/api/auth/me` | Get current user profile |
| GET | `/api/auth/countries` | List countries & currencies |
| GET | `/api/auth/currencies` | List all currencies |

### Users (Admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/` | List all users |
| POST | `/api/users/` | Create user |
| PUT | `/api/users/:id` | Update user |
| DELETE | `/api/users/:id` | Deactivate user |
| GET | `/api/users/managers` | List managers |

### Expenses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/expenses/` | List expenses (role-based) |
| POST | `/api/expenses/` | Create expense (with receipt) |
| GET | `/api/expenses/:id` | Get expense details |
| POST | `/api/expenses/:id/submit` | Submit draft for approval |
| POST | `/api/expenses/ocr` | Process receipt OCR |

### Approvals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/approvals/pending` | Get pending approvals |
| POST | `/api/approvals/:id/approve` | Approve expense |
| POST | `/api/approvals/:id/reject` | Reject expense |
| GET | `/api/approvals/:id/history` | Get approval history |
| GET | `/api/approvals/rules` | List approval rules |
| POST | `/api/approvals/rules` | Create rule |
| PUT | `/api/approvals/rules/:id` | Update rule |
| DELETE | `/api/approvals/rules/:id` | Delete rule |
| POST | `/api/approvals/override/:id` | Admin override |

## 🔄 Workflow

1. **Signup** → Company + Admin auto-created with country-based currency
2. **Admin** → Creates employees and managers
3. **Admin** → Configures approval rules (sequence + conditions)
4. **Employee** → Submits expense (with optional OCR scan)
5. **System** → Routes to manager (if required)
6. **System** → Moves through approval chain
7. **System** → Applies percentage / special approver rules
8. **Final** → Approved ✅ or Rejected ❌
9. **Audit** → Full approval history with timestamps

## 📝 License

MIT License
