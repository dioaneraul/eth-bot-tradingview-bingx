from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os, uuid

app = Flask(__name__)

# ======================
# 1. Config din variabile de mediu
# ======================
API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"


# ======================
# 2. Funcție headers pentru semnătură
# ======================
def get_headers(method, endpoint, body=""):
    now = int(time.time() * 1000)
    str_to_sign = str(now) + method.upper() + endpoint + body
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
        "Content-Type": "application/json",
    }


# ======================
# 3. Webhook TradingView
# ======================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # validare secret
    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action").upper()  # BUY sau SELL
    symbol = data.get("symbol")
    price = data.get("price")
    sl = data.get("sl")
    tp = data.get("tp")
    qty = data.get("quantity")
    leverage = data.get("leverage", 5)

    print(f"Webhook received: {data}", flush=True)

    # ======================
    # 4. Setăm leverage
    # ======================
    endpoint_leverage = f"/api/v1/position/leverage"
    lev_body = {"symbol": symbol, "leverage": str(leverage)}
    headers = get_headers("POST", endpoint_leverage, json.dumps(lev_body))
    res_lev = requests.post(BASE_URL + endpoint_leverage, headers=headers, data=json.dumps(lev_body))
    print("Leverage response:", res_lev.text, flush=True)

    # ======================
    # 5. Trimitem ordin principal
    # ======================
    endpoint_order = "/api/v1/orders"
    order_body = {
        "clientOid": str(uuid.uuid4()),
        "symbol": symbol,
        "side": side.lower(),
        "type": "market",
        "size": str(qty)
    }
    headers = get_headers("POST", endpoint_order, json.dumps(order_body))
    res_order = requests.post(BASE_URL + endpoint_order, headers=headers, data=json.dumps(order_body))
    print("Main order response:", res_order.text, flush=True)

    # ======================
    # 6. Trimitem TP & SL ca stopOrders
    # ======================
    endpoint_stop = "/api/v1/stopOrders"

    if tp:
        tp_body = {
            "clientOid": str(uuid.uuid4()),
            "symbol": symbol,
            "side": "sell" if side == "BUY" else "buy",
            "type": "limit",
            "stop": "up" if side == "BUY" else "down",
            "stopPrice": str(tp),
            "price": str(tp),
            "reduceOnly": True,
            "closeOrder": True,
            "triggerType": "lastPrice"
        }
        headers = get_headers("POST", endpoint_stop, json.dumps(tp_body))
        res_tp = requests.post(BASE_URL + endpoint_stop, headers=headers, data=json.dumps(tp_body))
        print("TP response:", res_tp.text, flush=True)

    if sl:
        sl_body = {
            "clientOid": str(uuid.uuid4()),
            "symbol": symbol,
            "side": "sell" if side == "BUY" else "buy",
            "type": "market",
            "stop": "down" if side == "BUY" else "up",
            "stopPrice": str(sl),
            "reduceOnly": True,
            "closeOrder": True,
            "triggerType": "lastPrice"
        }
        headers = get_headers("POST", endpoint_stop, json.dumps(sl_body))
        res_sl = requests.post(BASE_URL + endpoint_stop, headers=headers, data=json.dumps(sl_body))
        print("SL response:", res_sl.text, flush=True)

    return jsonify({"status": "executed", "symbol": symbol, "side": side, "qty": qty, "sl": sl, "tp": tp})


# ======================
# 7. Rulează aplicația
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
