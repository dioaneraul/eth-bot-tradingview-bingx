import os
import time
import hmac
import base64
import hashlib
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# KuCoin API Keys din Environment Variables (Render → Environment)
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# ========= Funcție pentru semnătură =========
def get_headers(method, endpoint, body=""):
    now = int(time.time() * 1000)
    str_to_sign = str(now) + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode("utf-8"), str_to_sign.encode("utf-8"), hashlib.sha256).digest()
    )
    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode("utf-8"), API_PASSPHRASE.encode("utf-8"), hashlib.sha256).digest()
    )

    return {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": API_KEY,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

# ========= Endpoint Webhook =========
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data, flush=True)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action", "").lower()  # buy sau sell
    symbol = data.get("symbol", "ETHUSDTM")
    qty = float(data.get("quantity", 0))
    leverage = int(data.get("leverage", 5))
    tp = float(data.get("tp", 0))
    sl = float(data.get("sl", 0))

    # ========= Plasare ordin principal =========
    endpoint_order = "/api/v1/orders"
    main_body = json.dumps({
        "symbol": symbol,
        "side": side,
        "type": "market",
        "size": qty,
        "leverage": leverage,
        "clientOid": str(int(time.time() * 1000)) + "_main"
    })

    headers = get_headers("POST", endpoint_order, main_body)
    res_main = requests.post(BASE_URL + endpoint_order, headers=headers, data=main_body)
    print("Main order response:", res_main.text, flush=True)

    # ========= Plasare TP =========
    if tp > 0:
        tp_body = json.dumps({
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "limit",
            "price": tp,
            "stop": "up" if side == "buy" else "down",
            "stopPrice": tp,
            "size": qty,
            "reduceOnly": True,
            "clientOid": str(int(time.time() * 1000)) + "_tp"
        })
        headers = get_headers("POST", endpoint_order, tp_body)
        res_tp = requests.post(BASE_URL + endpoint_order, headers=headers, data=tp_body)
        print("TP response:", res_tp.text, flush=True)

    # ========= Plasare SL =========
    if sl > 0:
        sl_body = json.dumps({
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "limit",
            "price": sl,
            "stop": "down" if side == "buy" else "up",
            "stopPrice": sl,
            "size": qty,
            "reduceOnly": True,
            "clientOid": str(int(time.time() * 1000)) + "_sl"
        })
        headers = get_headers("POST", endpoint_order, sl_body)
        res_sl = requests.post(BASE_URL + endpoint_order, headers=headers, data=sl_body)
        print("SL response:", res_sl.text, flush=True)

    return jsonify({"status": "executed", "symbol": symbol, "side": side, "qty": qty, "tp": tp, "sl": sl})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
