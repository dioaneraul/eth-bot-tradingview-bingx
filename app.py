from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json
import os

app = Flask(__name__)

# ---- CHEI API (din .env sau variabile Render) ----
API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"


# ---- HEADERE PENTRU AUTENTIFICARE KUCOIN ----
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


# ---- PRIMIRE ALERTĂ WEBHOOK DE LA TRADINGVIEW ----
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action", "").upper()  # BUY / SELL
    symbol = data.get("symbol")
    leverage = data.get("leverage", 5)
    size = data.get("quantity", 1)
    price = data.get("price")
    sl = data.get("sl")
    tp = data.get("tp")

    if None in [side, symbol, size, price, sl, tp]:
        return jsonify({"error": "Missing required fields"}), 400

    headers = get_headers("POST", "/api/v1/orders")
    endpoint = "/api/v1/orders"

    # 1️⃣ MARKET ENTRY ORDER
    entry_order = {
        "symbol": symbol,
        "side": side.lower(),  # buy / sell
        "type": "market",
        "leverage": leverage,
        "size": size
    }
    r_entry = requests.post(BASE_URL + endpoint, headers=headers, json=entry_order)

    if r_entry.status_code != 200:
        return jsonify({"error": "Entry failed", "details": r_entry.text}), 500

    # 2️⃣ TAKE PROFIT ORDER (LIMIT)
    tp_order = {
        "symbol": symbol,
        "side": "sell" if side.lower() == "buy" else "buy",
        "type": "limit",
        "price": tp,
        "size": size,
        "reduceOnly": True
    }
    r_tp = requests.post(BASE_URL + endpoint, headers=headers, json=tp_order)

    # 3️⃣ STOP LOSS ORDER (STOP-MARKET)
    sl_order = {
        "symbol": symbol,
        "side": "sell" if side.lower() == "buy" else "buy",
        "type": "market",
        "stop": "down" if side.lower() == "buy" else "up",
        "stopPrice": sl,
        "reduceOnly": True,
        "size": size
    }
    r_sl = requests.post(BASE_URL + endpoint, headers=headers, json=sl_order)

    return jsonify({
        "status": "executed",
        "entry": r_entry.json(),
        "tp": r_tp.json(),
        "sl": r_sl.json()
    })

