import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'FlowFund-secret-key-2026')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'FlowFund-jwt-secret-2026')
    JWT_EXPIRATION_HOURS = 24

    # MySQL Configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Shyam@2006')
    DB_NAME = os.environ.get('DB_NAME', 'reimburseflow')

    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}

    # Tesseract Configuration
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')

    # External APIs
    COUNTRIES_API = 'https://restcountries.com/v3.1/all?fields=name,currencies'
    EXCHANGE_RATE_API = 'https://api.exchangerate-api.com/v4/latest/'
