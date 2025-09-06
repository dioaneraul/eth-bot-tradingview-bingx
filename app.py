from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json
import os

app = Flask(__name__)

API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

def get_headers(method, endpoint, body=""):
    now = str(int(time.time() * 1000))
    str_to_sign = now + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    ).decode()

    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode(), API_PASSPHRASE.encode(), hashlib.sha256).digest()
    ).decode()

    return {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": now,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data["action"].upper()      # BUY or SELL
    symbol = data["symbol"]            # ex: ETHUSDM
    leverage = data.get("leverage", 5)
    size = data.get("quantity", 1)     # contract size

    endpoint = "/api/v1/orders"
    url = BASE_URL + endpoint

    body = {
        "symbol": symbol,
        "side": side,
        "leverage": leverage,
        "type": "market",
        "size": size
    }

    headers = get_headers("POST", endpoint, json.dumps(body))
    response = requests.post(url, headers=headers, data=json.dumps(body))

    return jsonify(response.json())
