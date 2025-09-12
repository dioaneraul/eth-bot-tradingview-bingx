from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, json, os, requests

app = Flask(__name__)

# Chei API din Render Environment
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

    # verifică secret
    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    side = data.get("action").upper()   # BUY / SELL
    symbol = data.get("symbol")
    qty = str(data.get("quantity"))     # contracte
    leverage = str(data.get("leverage"))
    tp = str(data.get("tp"))
    sl = str(data.get("sl"))

    print(f"Payload primit: {data}", flush=True)

    # === ORDIN PRINCIPAL (MARKET) ===
    endpoint = "/api/v1/orders"
    method = "POST"
    headers = get_headers(method, endpoint)

    main_order = {
        "symbol": symbol,
        "side": side.lower(),          # buy / sell
        "type": "market",
        "size": qty,
        "leverage": leverage,
        "clientOid": str(int(time.time() * 1000)) + "_main"
    }

    res_main = requests.post(BASE_URL + endpoint, headers=headers, data=json.dumps(main_order))
    print("Main order response:", res_main.text, flush=True)

    # Dacă ordinul principal merge → trimitem TP & SL
    if res_main.status_code == 200:
        opposite_side = "sell" if side == "BUY" else "buy"

        # === Take Profit ===
        tp_order = {
            "symbol": symbol,
            "side": opposite_side,
            "type": "limit",
            "price": tp,
            "size": qty,
            "reduceOnly": True,
            "clientOid": str(int(time.time() * 1000)) + "_tp"
        }
        res_tp = requests.post(BASE_URL + endpoint, headers=headers, data=json.dumps(tp_order))
        print("TP response:", res_tp.text, flush=True)

        # === Stop Loss ===
        sl_order = {
            "symbol": symbol,
            "side": opposite_side,
            "type": "stop_market",
            "stopPrice": sl,
            "size": qty,
            "reduceOnly": True,
            "clientOid": str(int(time.time() * 1000)) + "_sl"
        }
        res_sl = requests.post(BASE_URL + endpoint, headers=headers, data=json.dumps(sl_order))
        print("SL response:", res_sl.text, flush=True)

    return jsonify({"status": "executed", "symbol": symbol, "side": side, "qty": qty, "tp": tp, "sl": sl})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
