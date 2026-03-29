import os
import re
from config import Config

try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


class OCRService:
    @classmethod
    def is_available(cls):
        """Check if Tesseract OCR is available."""
        return TESSERACT_AVAILABLE

    @classmethod
    def extract_from_receipt(cls, image_path):
        """Extract text from receipt image and parse key fields."""
        result = {
            'raw_text': '',
            'amount': None,
            'date': None,
            'vendor': None,
            'success': False
        }

        if not TESSERACT_AVAILABLE:
            result['error'] = 'Tesseract OCR is not installed or configured'
            return result

        try:
            if not os.path.exists(image_path):
                result['error'] = 'Image file not found'
                return result

            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            result['raw_text'] = text
            result['success'] = True

            # Extract amount (look for currency patterns)
            amount_patterns = [
                r'(?:total|amount|sum|due|balance|grand\s*total)[:\s]*[\$€£₹¥]?\s*(\d+[.,]\d{2})',
                r'[\$€£₹¥]\s*(\d+[.,]\d{2})',
                r'(\d+[.,]\d{2})\s*(?:total|amount|due)',
                r'(?:total|amount)[:\s]*(\d+[.,]\d{2})',
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '.')
                    result['amount'] = float(amount_str)
                    break

            # Extract date
            date_patterns = [
                r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
                r'(\w{3,9}\s+\d{1,2},?\s+\d{4})',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result['date'] = match.group(1)
                    break

            # Extract vendor name (usually first non-empty line)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines:
                result['vendor'] = lines[0]

        except Exception as e:
            result['error'] = str(e)

        return result
