import requests
from config import Config


class CurrencyService:
    _countries_cache = None
    _exchange_cache = {}

    @classmethod
    def get_countries_currencies(cls):
        """Fetch country-currency mapping from REST Countries API."""
        if cls._countries_cache:
            return cls._countries_cache

        try:
            response = requests.get(Config.COUNTRIES_API, timeout=10)
            if response.status_code == 200:
                data = response.json()
                result = []
                for country in data:
                    name = country.get('name', {}).get('common', '')
                    currencies = country.get('currencies', {})
                    for code, info in currencies.items():
                        result.append({
                            'country': name,
                            'currency_code': code,
                            'currency_name': info.get('name', ''),
                            'currency_symbol': info.get('symbol', '')
                        })
                cls._countries_cache = sorted(result, key=lambda x: x['country'])
                return cls._countries_cache
        except Exception as e:
            print(f"Error fetching countries: {e}")

        # Fallback data
        return [
            {'country': 'United States', 'currency_code': 'USD', 'currency_name': 'United States dollar', 'currency_symbol': '$'},
            {'country': 'United Kingdom', 'currency_code': 'GBP', 'currency_name': 'British pound', 'currency_symbol': '£'},
            {'country': 'India', 'currency_code': 'INR', 'currency_name': 'Indian rupee', 'currency_symbol': '₹'},
            {'country': 'Japan', 'currency_code': 'JPY', 'currency_name': 'Japanese yen', 'currency_symbol': '¥'},
            {'country': 'Germany', 'currency_code': 'EUR', 'currency_name': 'Euro', 'currency_symbol': '€'},
            {'country': 'Canada', 'currency_code': 'CAD', 'currency_name': 'Canadian dollar', 'currency_symbol': 'C$'},
            {'country': 'Australia', 'currency_code': 'AUD', 'currency_name': 'Australian dollar', 'currency_symbol': 'A$'},
        ]

    @classmethod
    def get_currency_for_country(cls, country_name):
        """Get default currency for a country."""
        countries = cls.get_countries_currencies()
        for entry in countries:
            if entry['country'].lower() == country_name.lower():
                return entry['currency_code']
        return 'USD'

    @classmethod
    def convert_currency(cls, amount, from_currency, to_currency):
        """Convert amount between currencies using exchange rate API."""
        if from_currency == to_currency:
            return float(amount)

        try:
            cache_key = f"{from_currency}_{to_currency}"
            if cache_key not in cls._exchange_cache:
                response = requests.get(f"{Config.EXCHANGE_RATE_API}{from_currency}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    rates = data.get('rates', {})
                    if to_currency in rates:
                        cls._exchange_cache[cache_key] = rates[to_currency]

            if cache_key in cls._exchange_cache:
                return round(float(amount) * cls._exchange_cache[cache_key], 2)
        except Exception as e:
            print(f"Error converting currency: {e}")

        return float(amount)

    @classmethod
    def get_all_currencies(cls):
        """Get unique list of all currencies."""
        countries = cls.get_countries_currencies()
        seen = set()
        currencies = []
        for entry in countries:
            code = entry['currency_code']
            if code not in seen:
                seen.add(code)
                currencies.append({
                    'code': code,
                    'name': entry['currency_name'],
                    'symbol': entry['currency_symbol']
                })
        return sorted(currencies, key=lambda x: x['code'])
