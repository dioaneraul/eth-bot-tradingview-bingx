from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os, uuid

app = Flask(__name__)

# API keys din Render (Environment)
API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# === Helper semnătură ===
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

# === Route principal webhook ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Payload primit:", data, flush=True)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action").lower()   # buy/sell
    symbol = data.get("symbol")
    qty = data.get("quantity")
    price = data.get("price")
    sl = data.get("sl")
    tp = data.get("tp")
    leverage = data.get("leverage", 5)

    try:
        # === SETARE LEVIER ===
        endpoint_leverage = f"/api/v1/positions/margin/leverage"
        body_leverage = {"symbol": symbol, "leverage": str(leverage)}
        headers = get_headers("POST", endpoint_leverage, json.dumps(body_leverage))
        res_lev = requests.post(BASE_URL + endpoint_leverage, headers=headers, data=json.dumps(body_leverage))
        print("Leverage response:", res_lev.text, flush=True)

        # === ORDIN PRINCIPAL (market) ===
        endpoint_order = "/api/v1/orders"
        order_body = {
            "clientOid": str(uuid.uuid4()),
            "symbol": symbol,
            "side": side,
            "type": "market",
            "size": str(int(qty))
        }
        headers = get_headers("POST", endpoint_order, json.dumps(order_body))
        res_order = requests.post(BASE_URL + endpoint_order, headers=headers, data=json.dumps(order_body))
        print("Main order response:", res_order.text, flush=True)

        # === STOP LOSS ===
        sl_body = {
            "clientOid": str(uuid.uuid4()),
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "limit",
            "price": str(sl),
            "size": str(int(qty)),
            "reduceOnly": True,
            "stop": "loss",
            "stopPrice": str(sl)
        }
        headers = get_headers("POST", endpoint_order, json.dumps(sl_body))
        res_sl = requests.post(BASE_URL + endpoint_order, headers=headers, data=json.dumps(sl_body))
        print("SL response:", res_sl.text, flush=True)

        # === TAKE PROFIT ===
        tp_body = {
            "clientOid": str(uuid.uuid4()),
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "limit",
            "price": str(tp),
            "size": str(int(qty)),
            "reduceOnly": True,
            "stop": "entry",
            "stopPrice": str(tp)
        }
        headers = get_headers("POST", endpoint_order, json.dumps(tp_body))
        res_tp = requests.post(BASE_URL + endpoint_order, headers=headers, data=json.dumps(tp_body))
        print("TP response:", res_tp.text, flush=True)

        return jsonify({
            "status": "executed",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "tp": tp,
            "sl": sl
        })

    except Exception as e:
        print("Eroare:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
