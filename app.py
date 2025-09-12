from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os

app = Flask(__name__)

API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# ---- Helper: creăm headers pentru autentificare ----
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

# ---- Endpoint pentru TradingView ----
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Payload primit:", data, flush=True)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        side = data.get("action").lower()   # buy / sell
        symbol = data.get("symbol")         # ex: ETHUSDTM
        price = float(data.get("price", 0))
        sl = float(data.get("sl", 0))
        tp = float(data.get("tp", 0))
        qty = str(data.get("quantity", 0.01))  # quantity in contracts
        leverage = int(data.get("leverage", 5))

        # ==== 1. Setăm leverage (trebuie separat în KuCoin) ====
        lev_endpoint = f"/api/v1/position/leverage"
        lev_body = json.dumps({"symbol": symbol, "leverage": leverage})
        lev_headers = get_headers("POST", lev_endpoint, lev_body)
        res_lev = requests.post(BASE_URL + lev_endpoint, headers=lev_headers, data=lev_body)
        print("Leverage response:", res_lev.text, flush=True)

        # ==== 2. Deschidem ordinul principal (Market) ====
        endpoint = "/api/v1/orders"
        order = {
            "symbol": symbol,
            "side": side,
            "type": "market",
            "size": qty
        }
        body = json.dumps(order)
        headers = get_headers("POST", endpoint, body)
        res = requests.post(BASE_URL + endpoint, headers=headers, data=body)
        print("Main order response:", res.text, flush=True)

        # ==== 3. Setăm SL ====
        if sl > 0:
            sl_order = {
                "symbol": symbol,
                "side": "sell" if side == "buy" else "buy",
                "type": "market",
                "stop": "loss",
                "stopPrice": str(sl),
                "size": qty
            }
            sl_body = json.dumps(sl_order)
            sl_headers = get_headers("POST", "/api/v1/stopOrders", sl_body)
            res_sl = requests.post(BASE_URL + "/api/v1/stopOrders", headers=sl_headers, data=sl_body)
            print("SL response:", res_sl.text, flush=True)

        # ==== 4. Setăm TP ====
        if tp > 0:
            tp_order = {
                "symbol": symbol,
                "side": "sell" if side == "buy" else "buy",
                "type": "market",
                "stop": "entry",
                "stopPrice": str(tp),
                "size": qty
            }
            tp_body = json.dumps(tp_order)
            tp_headers = get_headers("POST", "/api/v1/stopOrders", tp_body)
            res_tp = requests.post(BASE_URL + "/api/v1/stopOrders", headers=tp_headers, data=tp_body)
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
        print("Error:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
