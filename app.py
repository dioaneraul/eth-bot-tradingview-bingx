from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os, uuid

app = Flask(__name__)

# ===============================
# ENV VARS (Render -> Environment)
# ===============================
API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# ===============================
# HELPERS
# ===============================
def get_headers(method, endpoint, body=""):
    now = str(int(time.time() * 1000))
    str_to_sign = now + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    )

    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode(), API_PASSPHRASE.encode(), hashlib.sha256).digest()
    )

    return {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": now,
        "KC-API-PASSPHRASE": passphrase.decode(),
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

# ===============================
# WEBHOOK ENTRY
# ===============================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Payload primit:", data, flush=True)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action").lower()   # buy / sell
    symbol = data.get("symbol")         # ex: ETHUSDTM
    qty = data.get("quantity")
    leverage = data.get("leverage", 5)
    tp = data.get("tp")
    sl = data.get("sl")

    # ============ 1. SET LEVERAGE ============
    endpoint_leverage = f"/api/v1/position/leverage"
    body_leverage = {
        "symbol": symbol,
        "leverage": str(leverage)
    }
    headers = get_headers("POST", endpoint_leverage, json.dumps(body_leverage))
    res_leverage = requests.post(BASE_URL + endpoint_leverage, headers=headers, data=json.dumps(body_leverage))
    print("Leverage response:", res_leverage.text, flush=True)

    # ============ 2. MAIN ORDER (MARKET) ============
    endpoint_order = "/api/v1/orders"
    main_body = {
        "clientOid": str(uuid.uuid4()),
        "symbol": symbol,
        "side": side,
        "type": "market",
        "size": str(int(qty))
    }
    headers = get_headers("POST", endpoint_order, json.dumps(main_body))
    res_main = requests.post(BASE_URL + endpoint_order, headers=headers, data=json.dumps(main_body))
    print("Main order response:", res_main.text, flush=True)

    # Dacă ordinul principal a fost executat corect
    if res_main.status_code == 200 and "orderId" in res_main.text:
        # ============ 3. STOP LOSS + TAKE PROFIT ============
        endpoint_stop = "/api/v1/orders"

        if side == "buy":
            # SL -> SELL dacă prețul scade
            sl_body = {
                "clientOid": str(uuid.uuid4()),
                "symbol": symbol,
                "side": "sell",
                "type": "limit",
                "price": str(sl),
                "size": str(int(qty)),
                "reduceOnly": True,
                "stop": "down",
                "stopPrice": str(sl)
            }

            # TP -> SELL dacă prețul urcă
            tp_body = {
                "clientOid": str(uuid.uuid4()),
                "symbol": symbol,
                "side": "sell",
                "type": "limit",
                "price": str(tp),
                "size": str(int(qty)),
                "reduceOnly": True,
                "stop": "up",
                "stopPrice": str(tp)
            }

        elif side == "sell":
            # SL -> BUY dacă prețul urcă
            sl_body = {
                "clientOid": str(uuid.uuid4()),
                "symbol": symbol,
                "side": "buy",
                "type": "limit",
                "price": str(sl),
                "size": str(int(qty)),
                "reduceOnly": True,
                "stop": "up",
                "stopPrice": str(sl)
            }

            # TP -> BUY dacă prețul scade
            tp_body = {
                "clientOid": str(uuid.uuid4()),
                "symbol": symbol,
                "side": "buy",
                "type": "limit",
                "price": str(tp),
                "size": str(int(qty)),
                "reduceOnly": True,
                "stop": "down",
                "stopPrice": str(tp)
            }

        # Trimitem ordinele SL & TP
        headers = get_headers("POST", endpoint_stop, json.dumps(sl_body))
        res_sl = requests.post(BASE_URL + endpoint_stop, headers=headers, data=json.dumps(sl_body))
        print("SL response:", res_sl.text, flush=True)

        headers = get_headers("POST", endpoint_stop, json.dumps(tp_body))
        res_tp = requests.post(BASE_URL + endpoint_stop, headers=headers, data=json.dumps(tp_body))
        print("TP response:", res_tp.text, flush=True)

    return jsonify({"status": "done", "symbol": symbol, "side": side, "qty": qty})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
