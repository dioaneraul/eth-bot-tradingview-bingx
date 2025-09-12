from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os

app = Flask(__name__)

API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# ---------------- AUTH HEADERS ---------------- #
def get_headers(method, endpoint, body=""):
    now = int(time.time() * 1000)
    str_to_sign = str(now) + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    ).decode()

    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode(), API_PASSPHRASE.encode(), hashlib.sha256).digest()
    ).decode()

    return {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

# ---------------- WEBHOOK ---------------- #
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    side = data.get("action").lower()  # buy / sell
    symbol = data.get("symbol", "ETHUSDTM")
    leverage = str(data.get("leverage", 5))
    qty = str(data.get("quantity", 0.01))

    price = data.get("price")  # dacă e None → market
    sl = data.get("sl")        # Stop Loss
    tp = data.get("tp")        # Take Profit

    # ------------ ORDER CREATION ------------ #
    order = {
        "symbol": symbol,
        "side": side,
        "type": "market" if price is None else "limit",
        "size": qty,
        "leverage": leverage
    }

    if price is not None:
        order["price"] = str(price)

    endpoint = "/api/v1/orders"
    url = BASE_URL + endpoint
    headers = get_headers("POST", endpoint, json.dumps(order))
    res = requests.post(url, headers=headers, data=json.dumps(order))
    print("Main order response:", res.text, flush=True)

    if res.status_code != 200:
        return jsonify({"error": "main_order_failed", "details": res.text}), 400

    res_json = res.json()
    order_id = res_json.get("data", {}).get("orderId")

    if not order_id:
        return jsonify({"error": "no_order_id", "details": res.text}), 400

    # ------------ TP / SL ORDERS ------------ #
    if sl:
        sl_order = {
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "stop_market",
            "stop": "loss",
            "stopPrice": str(sl),
            "size": qty,
            "reduceOnly": True
        }
        res_sl = requests.post(BASE_URL + "/api/v1/orders", headers=get_headers("POST", "/api/v1/orders", json.dumps(sl_order)), data=json.dumps(sl_order))
        print("SL response:", res_sl.text, flush=True)

    if tp:
        tp_order = {
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "stop_market",
            "stop": "entry",
            "stopPrice": str(tp),
            "size": qty,
            "reduceOnly": True
        }
        res_tp = requests.post(BASE_URL + "/api/v1/orders", headers=get_headers("POST", "/api/v1/orders", json.dumps(tp_order)), data=json.dumps(tp_order))
        print("TP response:", res_tp.text, flush=True)

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
