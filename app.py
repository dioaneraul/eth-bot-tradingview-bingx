from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os

app = Flask(__name__)

API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# ======================
# Helper pentru semnătură
# ======================
def get_headers(method, endpoint, body=""):
    now = str(int(time.time() * 1000))
    str_to_sign = now + method.upper() + endpoint + body
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

# ======================
# Webhook TradingView
# ======================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Payload primit:", data, flush=True)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        side = data.get("action").upper()   # BUY / SELL
        symbol = data.get("symbol")
        qty = str(data.get("quantity", 1))  # contracts
        leverage = str(data.get("leverage", 5))
        tp = data.get("tp")
        sl = data.get("sl")

        # ---- 1. Setăm leverage ----
        lev_endpoint = "/api/v1/position/leverage"
        lev_body = json.dumps({"symbol": symbol, "leverage": leverage})
        lev_headers = get_headers("POST", lev_endpoint, lev_body)
        res_lev = requests.post(BASE_URL + lev_endpoint, headers=lev_headers, data=lev_body)
        print("Leverage response:", res_lev.text, flush=True)

        # ---- 2. Ordin principal (Market) ----
        order_endpoint = "/api/v1/orders"
        order_body = json.dumps({
            "symbol": symbol,
            "side": side.lower(),
            "type": "market",
            "size": qty
        })
        order_headers = get_headers("POST", order_endpoint, order_body)
        res_order = requests.post(BASE_URL + order_endpoint, headers=order_headers, data=order_body)
        print("Main order response:", res_order.text, flush=True)
        main_status = res_order.json().get("msg", "success")

        # ---- 3. Stop Loss & Take Profit ----
        tp_status, sl_status = None, None

        if tp:
            tp_endpoint = "/api/v1/stopOrders"
            tp_body = json.dumps({
                "symbol": symbol,
                "side": "sell" if side == "BUY" else "buy",
                "type": "limit",
                "stop": "entry",
                "stopPrice": str(tp),
                "price": str(tp),
                "size": qty
            })
            tp_headers = get_headers("POST", tp_endpoint, tp_body)
            res_tp = requests.post(BASE_URL + tp_endpoint, headers=tp_headers, data=tp_body)
            print("TP response:", res_tp.text, flush=True)
            tp_status = res_tp.json().get("msg", "success")

        if sl:
            sl_endpoint = "/api/v1/stopOrders"
            sl_body = json.dumps({
                "symbol": symbol,
                "side": "sell" if side == "BUY" else "buy",
                "type": "limit",
                "stop": "loss",
                "stopPrice": str(sl),
                "price": str(sl),
                "size": qty
            })
            sl_headers = get_headers("POST", sl_endpoint, sl_body)
            res_sl = requests.post(BASE_URL + sl_endpoint, headers=sl_headers, data=sl_body)
            print("SL response:", res_sl.text, flush=True)
            sl_status = res_sl.json().get("msg", "success")

        # ---- 4. Returnăm status complet ----
        return jsonify({
            "status": "executed",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "main_order": main_status,
            "tp_order": tp_status,
            "sl_order": sl_status
        })

    except Exception as e:
        print("Error:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
