import os
import time
import json
import uuid
import hmac
import base64
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== KuCoin API Keys din Render Environment =====
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# ===== Funcție de semnătură =====
def sign_request(endpoint, method, body=""):
    now = int(time.time() * 1000)
    str_to_sign = str(now) + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    )
    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode(), API_PASSPHRASE.encode(), hashlib.sha256).digest()
    )
    headers = {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": signature.decode(),
        "KC-API-TIMESTAMP": str(now),
        "KC-API-PASSPHRASE": passphrase.decode(),
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }
    return headers

# ===== Webhook Trading =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Payload primit:", data, flush=True)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"status": "error", "msg": "Unauthorized"}), 401

    symbol = data.get("symbol")
    side = data.get("action").lower()  # "buy" sau "sell"
    qty = float(data.get("quantity"))
    leverage = int(data.get("leverage"))
    tp = float(data.get("tp"))
    sl = float(data.get("sl"))

    # ===== Ordin principal (Market) =====
    endpoint_order = "/api/v1/orders"
    url_order = BASE_URL + endpoint_order

    order_body = {
        "symbol": symbol,
        "side": side,
        "type": "market",
        "size": qty,
        "leverage": str(leverage),
        "clientOid": str(int(time.time() * 1000))
    }

    headers = sign_request(endpoint_order, "POST", json.dumps(order_body))
    res_order = requests.post(url_order, headers=headers, data=json.dumps(order_body))
    print("Main order response:", res_order.text, flush=True)

    # ===== Take Profit (Limit Order) =====
    tp_body = {
        "symbol": symbol,
        "side": "sell" if side == "buy" else "buy",
        "type": "limit",
        "price": tp,
        "size": qty,
        "reduceOnly": True,
        "clientOid": str(int(time.time() * 1000)) + "_tp"
    }
    res_tp = requests.post(url_order, headers=sign_request(endpoint_order, "POST", json.dumps(tp_body)),
                           data=json.dumps(tp_body))
    print("TP response:", res_tp.text, flush=True)

    # ===== Stop Loss (Stop Order) =====
    sl_body = {
        "symbol": symbol,
        "side": "sell" if side == "buy" else "buy",
        "type": "stop",
        "stopPrice": sl,
        "size": qty,
        "reduceOnly": True,
        "clientOid": str(int(time.time() * 1000)) + "_sl"
    }
    res_sl = requests.post(url_order, headers=sign_request(endpoint_order, "POST", json.dumps(sl_body)),
                           data=json.dumps(sl_body))
    print("SL response:", res_sl.text, flush=True)

    return jsonify({
        "status": "executed",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "tp": tp,
        "sl": sl
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
