import os, uuid, time, hmac, base64, hashlib, json, requests
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==========================
#  API KEYS din Render
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

BASE_URL = "https://api-futures.kucoin.com"

client = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    is_sandbox=False
)

app = Flask(__name__)

# ==========================
#  Funcții semnătură + ordine
# ==========================
def _signed_headers(method: str, endpoint: str, body_str: str):
    now = str(int(time.time() * 1000))
    msg = f"{now}{method}{endpoint}{body_str}"
    sign = base64.b64encode(hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).digest()).decode()
    pph = base64.b64encode(hmac.new(API_SECRET.encode(), API_PASSPHRASE.encode(), hashlib.sha256).digest()).decode()
    return now, {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": sign,
        "KC-API-TIMESTAMP": now,
        "KC-API-PASSPHRASE": pph,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

def place_conditional_order(symbol, side, order_type, price, size, stop_price=None, stop_type=None):
    payload = {
        "symbol": symbol,
        "side": side,
        "type": order_type,        # "limit" sau "market"
        "size": str(int(size)),    # KuCoin cere int, nu float
        "reduceOnly": True,
        "closeOrder": True,
        "clientOid": str(uuid.uuid4())
    }
    if price:
        payload["price"] = str(price)
    if stop_price:
        payload["stopPrice"] = str(stop_price)
        payload["stopPriceType"] = "MP"   # Mark Price
        payload["stop"] = stop_type

    endpoint = "/api/v1/orders"
    body_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    _, headers = _signed_headers("POST", endpoint, body_str)
    r = requests.post(BASE_URL + endpoint, headers=headers, data=body_str)
    print("Conditional Order Response:", r.text)
    return r.json()

# ==========================
#  Webhook TradingView
# ==========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Payload primit:", data)
    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action   = data.get("action")        # buy / sell
        symbol   = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0)) or 0
        sl_price = float(data.get("sl", 0)) or 0

        side = "buy" if action.lower() == "buy" else "sell"

        # 0) Setăm margin mode + leverage pentru simbol
        try:
            client.change_margin_mode(symbol, "ISOLATED")
            client.set_leverage(symbol, str(leverage), "ISOLATED")
            print(f"{symbol}: Isolated {leverage}x setat")
        except Exception as e:
            print("Eroare setare margin/leverage:", e)

        # 1) Curățare ordine vechi (TP/SL rămase)
        try:
            cancel_result = client.cancel_all_limit_order(symbol=symbol)
            print("Ordine vechi anulate:", cancel_result)
        except Exception as e:
            print("Eroare anulare ordine vechi:", e)

        # 2) Market order (SDK)
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=str(int(quantity)),
            lever=str(leverage)
        )
        print("Ordin Market executat:", order)

        # 3) Take Profit (conditional limit)
        if tp_price > 0:
            try:
                tp_side = "sell" if side == "buy" else "buy"
                tp_order = place_conditional_order(
                    symbol, tp_side, "limit", tp_price, quantity
                )
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        # 4) Stop Loss (conditional market)
        if sl_price > 0:
            try:
                sl_side = "sell" if side == "buy" else "buy"
                stop_type = "down" if side == "buy" else "up"
                sl_order = place_conditional_order(
                    symbol, sl_side, "market", None, quantity,
                    stop_price=sl_price, stop_type=stop_type
                )
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", e)

        return jsonify({"success": True, "market_order": order})

    except Exception as e:
        print("Eroare la executie:", e)
        return jsonify({"error": str(e)}), 500

# ==========================
#  Pornire server
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
