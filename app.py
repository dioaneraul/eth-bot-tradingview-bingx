import os, uuid, time, hmac, base64, hashlib, json, requests
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

BASE_URL = "https://api-futures.kucoin.com"

client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "KuCoin TradingView Bot - LIVE"

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

def set_margin_mode(symbol, leverage, mode="ISOLATED"):
    payload = {
        "symbol": symbol,
        "leverage": str(leverage),
        "marginMode": mode
    }
    endpoint = "/api/v1/position/margin/setting"
    body_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    _, headers = _signed_headers("POST", endpoint, body_str)
    r = requests.post(BASE_URL + endpoint, headers=headers, data=body_str)
    print("Set Margin Mode Response:", r.text)
    return r.json()

def place_conditional_order(symbol, side, order_type, price, size, stop_price=None, stop_type=None):
    payload = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "size": str(int(size)),
        "reduceOnly": True,
        "closeOrder": True,
        "clientOid": str(uuid.uuid4())
    }
    if price:
        payload["price"] = str(price)
    if stop_price:
        payload["stopPrice"] = str(stop_price)
        payload["stopPriceType"] = "MP"
        payload["stop"] = stop_type

    endpoint = "/api/v1/orders"
    body_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    _, headers = _signed_headers("POST", endpoint, body_str)
    r = requests.post(BASE_URL + endpoint, headers=headers, data=body_str)
    print("Conditional Order Response:", r.text)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Payload primit:", data)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action   = data.get("action")
        symbol   = data.get("symbol", "ETHUSDTM")
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # Accepta 'contracts' sau fallback pe 'quantity'
        contracts = data.get("contracts")
        if contracts is None:
            quantity = float(data.get("quantity", 0.01))
            contracts = int(quantity)

        if contracts < 1:
            return jsonify({
                "error": "Cantitate prea mică. Trimite minim 1 contract. Poți seta 'contracts': 1 în alerta TradingView."
            }), 400

        side = "buy" if action.lower() == "buy" else "sell"

        try:
            margin_resp = set_margin_mode(symbol, leverage, mode="ISOLATED")
            print("Margin mode setat:", margin_resp)
        except Exception as e:
            print("Eroare setare margin mode:", e)

        try:
            cancel_result = client.cancel_all_limit_order(symbol=symbol)
            print("Ordine vechi anulate:", cancel_result)
        except Exception as e:
            print("Eroare anulare ordine vechi:", e)

        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=contracts,
            lever=str(leverage)
        )
        print("Ordin Market executat:", order)

        if tp_price > 0:
            try:
                tp_side = "sell" if side == "buy" else "buy"
                tp_order = place_conditional_order(symbol, tp_side, "limit", tp_price, contracts)
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        if sl_price > 0:
            try:
                sl_side = "sell" if side == "buy" else "buy"
                stop_type = "down" if side == "buy" else "up"
                sl_order = place_conditional_order(symbol, sl_side, "market", None, contracts,
                                                   stop_price=sl_price, stop_type=stop_type)
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", e)

        return jsonify({"success": True, "market_order": order})

    except Exception as e:
        print("Eroare execuție:", e)
        return jsonify({"error": str(e)}), 500
