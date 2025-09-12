from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os, uuid

app = Flask(__name__)

API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

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

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action").upper()  # BUY / SELL
    symbol = data.get("symbol")
    leverage = data.get("leverage", 5)
    qty = data.get("quantity", 0.01)
    entry_price = data.get("price")
    tp = data.get("tp")
    sl = data.get("sl")

    # --- Set leverage ---
    endpoint_leverage = f"/api/v1/position/leverage"
    body_leverage = json.dumps({
        "symbol": symbol,
        "leverage": str(leverage)
    })
    headers = get_headers("POST", endpoint_leverage, body_leverage)
    res_leverage = requests.post(BASE_URL + endpoint_leverage, headers=headers, data=body_leverage)
    print("Leverage response:", res_leverage.text, flush=True)

    # --- Place main order ---
    endpoint_order = "/api/v1/orders"
    client_oid_main = str(uuid.uuid4())
    order_body = json.dumps({
        "clientOid": client_oid_main,
        "symbol": symbol,
        "type": "market",
        "side": side.lower(),
        "size": str(qty)
    })
    headers = get_headers("POST", endpoint_order, order_body)
    res_order = requests.post(BASE_URL + endpoint_order, headers=headers, data=order_body)
    print("Main order response:", res_order.text, flush=True)

    # --- Place SL order ---
    if sl:
        endpoint_stop = "/api/v1/stopOrders"
        client_oid_sl = str(uuid.uuid4())
        sl_body = json.dumps({
            "clientOid": client_oid_sl,
            "symbol": symbol,
            "side": "sell" if side == "BUY" else "buy",
            "type": "market",
            "stop": "loss",
            "stopPriceType": "TP",
            "stopPrice": str(sl),
            "size": str(qty)
        })
        headers = get_headers("POST", endpoint_stop, sl_body)
        res_sl = requests.post(BASE_URL + endpoint_stop, headers=headers, data=sl_body)
        print("SL response:", res_sl.text, flush=True)

    # --- Place TP order ---
    if tp:
        endpoint_stop = "/api/v1/stopOrders"
        client_oid_tp = str(uuid.uuid4())
        tp_body = json.dumps({
            "clientOid": client_oid_tp,
            "symbol": symbol,
            "side": "sell" if side == "BUY" else "buy",
            "type": "market",
            "stop": "entry",
            "stopPriceType": "TP",
            "stopPrice": str(tp),
            "size": str(qty)
        })
        headers = get_headers("POST", endpoint_stop, tp_body)
        res_tp = requests.post(BASE_URL + endpoint_stop, headers=headers, data=tp_body)
        print("TP response:", res_tp.text, flush=True)

    return jsonify({"status": "executed", "symbol": symbol, "side": side, "qty": qty, "tp": tp, "sl": sl})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
