from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os, uuid

app = Flask(__name__)

API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

# Dimensiuni contracte pentru simboluri
CONTRACT_SIZES = {
    "ETHUSDTM": 0.01,   # 1 contract = 0.01 ETH
    "BTCUSDTM": 0.001,  # 1 contract = 0.001 BTC
    "PAXGUSDTM": 0.001, # 1 contract = 0.001 PAXG
    "SOLUSDTM": 1       # 1 contract = 1 SOL
}

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

    side = data.get("action").upper()
    symbol = data.get("symbol")
    price = float(data.get("price"))
    sl = float(data.get("sl"))
    tp = float(data.get("tp"))
    qty = float(data.get("quantity"))
    leverage = int(data.get("leverage", 5))

    # Contract size lookup
    contract_size = CONTRACT_SIZES.get(symbol, 1)
    contracts = int(qty / contract_size)

    if contracts < 1:
        return jsonify({"error": "Quantity too small for contract size"}), 400

    print(f"Placing order => {side} {symbol}, qty={qty}, contracts={contracts}, lev={leverage}, tp={tp}, sl={sl}", flush=True)

    # 1) Set leverage
    endpoint_leverage = f"/api/v1/position/leverage"
    lev_body = json.dumps({"symbol": symbol, "leverage": str(leverage)})
    headers = get_headers("POST", endpoint_leverage, lev_body)
    res_lev = requests.post(BASE_URL + endpoint_leverage, headers=headers, data=lev_body)
    print("Leverage response:", res_lev.text, flush=True)

    # 2) Place main market order
    client_oid_main = str(uuid.uuid4())
    endpoint_order = "/api/v1/orders"
    order_body = json.dumps({
        "clientOid": client_oid_main,
        "symbol": symbol,
        "type": "market",
        "side": side.lower(),
        "size": str(contracts)
    })
    headers = get_headers("POST", endpoint_order, order_body)
    res_order = requests.post(BASE_URL + endpoint_order, headers=headers, data=order_body)
    print("Main order response:", res_order.text, flush=True)

    # Dacă ordinul nu a mers, oprim execuția
    if res_order.status_code != 200:
        return jsonify({"error": "Order failed", "details": res_order.text}), 400

    # 3) Adaugă TP și SL
    opp_side = "sell" if side == "BUY" else "buy"

    # SL order
    client_oid_sl = str(uuid.uuid4())
    sl_body = json.dumps({
        "clientOid": client_oid_sl,
        "symbol": symbol,
        "type": "market",
        "side": opp_side,
        "size": str(contracts),
        "stop": "down" if side == "BUY" else "up",
        "stopPrice": str(sl),
        "reduceOnly": True
    })
    headers = get_headers("POST", endpoint_order, sl_body)
    res_sl = requests.post(BASE_URL + endpoint_order, headers=headers, data=sl_body)
    print("SL response:", res_sl.text, flush=True)

    # TP order
    client_oid_tp = str(uuid.uuid4())
    tp_body = json.dumps({
        "clientOid": client_oid_tp,
        "symbol": symbol,
        "type": "limit",
        "side": opp_side,
        "size": str(contracts),
        "price": str(tp),
        "reduceOnly": True
    })
    headers = get_headers("POST", endpoint_order, tp_body)
    res_tp = requests.post(BASE_URL + endpoint_order, headers=headers, data=tp_body)
    print("TP response:", res_tp.text, flush=True)

    return jsonify({"status": "executed", "symbol": symbol, "side": side, "contracts": contracts, "tp": tp, "sl": sl})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
