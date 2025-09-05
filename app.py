from flask import Flask, request, jsonify
import time, hmac, hashlib, requests, os

app = Flask(__name__)

API_KEY = os.environ.get("BINGX_API_KEY")
SECRET_KEY = os.environ.get("BINGX_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

BINGX_API_URL = "https://open-api.bingx.com/openApi/swap/v2/trade/order"

def generate_signature(query_string, secret_key):
    return hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if WEBHOOK_SECRET and data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    if 'action' not in data or 'symbol' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    symbol = data['symbol']
    side = "BUY" if data['action'] == "buy" else "SELL"
    quantity = str(data.get("quantity", 0.01))
    leverage = str(data.get("leverage", 5))

    timestamp = str(int(time.time() * 1000))
    params = f"timestamp={timestamp}&symbol={symbol}&side={side}&positionSide=BOTH&orderType=MARKET&quantity={quantity}&leverage={leverage}"
    signature = generate_signature(params, SECRET_KEY)
    headers = {"X-BX-APIKEY": API_KEY}
    url = f"{BINGX_API_URL}?{params}&signature={signature}"

    resp = requests.post(url, headers=headers)
    return jsonify(resp.json())
