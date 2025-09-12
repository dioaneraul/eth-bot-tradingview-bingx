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
        return jsonify({"error": "unauthorized"}), 401

    side = data.get("action").upper()
    symbol = data.get("symbol")
    leverage = int(data.get("leverage", 5))
    price = float(data.get("price", 0))
    sl = float(data.get("sl", 0))
    tp = float(data.get("tp", 0))

    # 🔥 Conversie quantity în contracte (integer)
    raw_qty = float(data.get("quantity", 1))
    qty = int(raw_qty / 0.01)   # pe KuCoin 1 contract = 0.01 ETH

    # setează levier
    endpoint_leverage = f"/api/v1/position/leverage"
    lev_body = json.dumps({"symbol": symbol, "leverage": leverage})
    res_lev = requests.post(BASE_URL + endpoint_leverage, headers=get_headers("POST", endpoint_leverage, lev_body), data=lev_body)

    # ordinele
    endpoint_order = "/api/v1/orders"

    # ordin principal MARKET
    main_body = {
        "symbol": symbol,
        "side": side.lower(),
        "type": "market",
        "size": qty
    }
    res_main = requests.post(BASE_URL + endpoint_order, headers=get_headers("POST", endpoint_order, json.dumps(main_body)), data=json.dumps(main_body))

    # adaugă TP și SL doar dacă au fost trimise
    tp_res, sl_res = None, None

    if tp > 0:
        tp_body = {
            "symbol": symbol,
            "side": "sell" if side == "BUY" else "buy",
            "type": "limit",
            "price": tp,
            "size": qty,
            "reduceOnly": True
        }
        tp_res = requests.post(BASE_URL + endpoint_order, headers=get_headers("POST", endpoint_order, json.dumps(tp_body)), data=json.dumps(tp_body))

    if sl > 0:
        sl_body = {
            "symbol": symbol,
            "side": "sell" if side == "BUY" else "buy",
            "type": "stop_market",
            "stopPrice": sl,
            "size": qty,
            "reduceOnly": True
        }
        sl_res = requests.post(BASE_URL + endpoint_order, headers=get_headers("POST", endpoint_order, json.dumps(sl_body)), data=json.dumps(sl_body))

    return jsonify({
        "status": "executed",
        "symbol": symbol,
        "side": side,
        "contracts": qty,
        "tp_response": tp_res.text if tp_res else "no tp",
        "sl_response": sl_res.text if sl_res else "no sl",
        "main_response": res_main.text
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
