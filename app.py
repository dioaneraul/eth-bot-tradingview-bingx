import os
import time
import hmac
import base64
import hashlib
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Variabile din Render
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

BASE_URL = "https://api-futures.kucoin.com"


def sign_request(method, endpoint, body=""):
    now = int(time.time() * 1000)
    str_to_sign = str(now) + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode("utf-8"), str_to_sign.encode("utf-8"), hashlib.sha256).digest()
    )
    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode("utf-8"), API_PASSPHRASE.encode("utf-8"), hashlib.sha256).digest()
    )
    return now, signature.decode(), passphrase.decode()


def place_order(symbol, side, size, leverage=5, order_type="market", price=None, reduce_only=False):
    endpoint = "/api/v1/orders"
    url = BASE_URL + endpoint

    body = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "leverage": str(leverage),
        "size": str(size),
    }

    if price:
        body["price"] = str(price)
    if reduce_only:
        body["reduceOnly"] = True

    body_json = json.dumps(body)
    now, signature, passphrase = sign_request("POST", endpoint, body_json)

    headers = {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json",
    }

    r = requests.post(url, headers=headers, data=body_json)
    return r.json()


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    symbol = data.get("symbol", "ETHUSDTM")
    side = data.get("action", "buy")
    qty = str(data.get("quantity", 1))  # contracte
    lev = data.get("leverage", 5)
    tp = data.get("tp")
    sl = data.get("sl")

    # 1. Plasăm ordinul principal Market
    main_order = place_order(symbol, side, qty, lev, "market")
    print("Main order response:", main_order, flush=True)

    if "orderId" not in main_order.get("data", {}):
        return jsonify({"error": "Main order failed", "response": main_order}), 400

    # 2. TP și SL (reduceOnly)
    opposite_side = "sell" if side == "buy" else "buy"

    if tp:
        tp_order = place_order(symbol, opposite_side, qty, lev, "limit", price=tp, reduce_only=True)
        print("TP response:", tp_order, flush=True)

    if sl:
        sl_order = place_order(symbol, opposite_side, qty, lev, "stop_market", price=sl, reduce_only=True)
        print("SL response:", sl_order, flush=True)

    return jsonify({"status": "executed", "symbol": symbol, "side": side, "qty": qty, "tp": tp, "sl": sl})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
