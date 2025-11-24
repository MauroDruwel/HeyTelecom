import os
import json
from flask import Flask, jsonify
from heytelecom import HeyTelecomClient

app = Flask(__name__)

# Read config from Home Assistant options
try:
    with open('/data/options.json', 'r') as f:
        options = json.load(f)
    EMAIL = options.get('email')
    PASSWORD = options.get('password')
except FileNotFoundError:
    # Fallback to environment variables for testing outside HA
    EMAIL = os.environ.get('HEYTELECOM_EMAIL')
    PASSWORD = os.environ.get('HEYTELECOM_PASSWORD')


@app.route('/')
def get_account():
    """Single endpoint - returns complete account data"""
    try:
        with HeyTelecomClient(
            email=EMAIL,
            password=PASSWORD,
            user_data_dir='/data/hey_browser_data'
        ) as client:
            if EMAIL and PASSWORD:
                try:
                    client.login()
                except Exception as e:
                    return
            account_data = client.get_account_data()
            return jsonify(account_data.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if not EMAIL or not PASSWORD:
        print("WARNING: HEYTELECOM_EMAIL and HEYTELECOM_PASSWORD not set!")
    app.run(host='0.0.0.0', port=8099, debug=False)
