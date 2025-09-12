from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os

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

    side = data.get("action").lower()  # buy / sell
    symbol = data.get("symbol")        # ex: ETHUSDTM
    size = int(data.get("size"))       # număr contracte (NU quantity!)
    leverage = str(data.get("leverage", 5))
    tp = float(data.get("tp", 0))
    sl = float(data.get("sl", 0))

    # ===== Set Leverage =====
    endpoint_leverage = f"/api/v1/position/leverage"
    leverage_body = json.dumps({
        "symbol": symbol,
        "leverage": leverage
    })
    headers = get_headers("POST", endpoint_leverage, leverage_body)
    res_leverage = requests.post(BASE_URL + endpoint_leverage, headers=headers, data=leverage_body)
    print("Leverage response:", res_leverage.text, flush=True)

    # ===== Main Market Order =====
    endpoint_order = "/api/v1/orders"
    order_body = json.dumps({
        "symbol": symbol,
        "side": side,
        "type": "market",
        "size": size,
        "leverage": leverage,
        "clientOid": str(int(time.time() * 1000))
    })
    headers = get_headers("POST", endpoint_order, order_body)
    res_order = requests.post(BASE_URL + endpoint_order, headers=headers, data=order_body)
    print("Main order response:", res_order.text, flush=True)

    # ===== TP Order =====
    if tp > 0:
        tp_body = json.dumps({
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "limit",
            "price": tp,
            "size": size,
            "reduceOnly": True,
            "clientOid": str(int(time.time() * 1000)) + "_tp"
        })
        headers = get_headers("POST", endpoint_order, tp_body)
        res_tp = requests.post(BASE_URL + endpoint_order, headers=headers, data=tp_body)
        print("TP response:", res_tp.text, flush=True)

    # ===== SL Order =====
    if sl > 0:
        sl_body = json.dumps({
            "symbol": symbol,
            "side": "sell" if side == "buy" else "buy",
            "type": "stop",
            "stopPrice": sl,
            "size": size,
            "reduceOnly": True,
            "clientOid": str(int(time.time() * 1000)) + "_sl"
        })
        headers = get_headers("POST", endpoint_order, sl_body)
        res_sl = requests.post(BASE_URL + endpoint_order, headers=headers, data=sl_body)
        print("SL response:", res_sl.text, flush=True)

    return jsonify({
        "status": "executed",
        "symbol": symbol,
        "side": side,
        "size": size,
        "tp": tp,
        "sl": sl
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
