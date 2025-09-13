import os
import time
import base64
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==========================
#  API KEYS din Render
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# Client trading (SDK)
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

# Endpoint KuCoin Futures
BASE_URL = "https://api-futures.kucoin.com"

app = Flask(__name__)

# ==========================
#  Funcție pentru Stop Loss prin REST
# ==========================
def place_stop_loss(symbol, side, size, leverage, stop_price):
    try:
        endpoint = "/api/v1/orders"
        url = BASE_URL + endpoint

        now = int(time.time() * 1000)
        data = {
            "symbol": symbol,
            "side": side,
            "type": "market",
            "size": str(size),
            "leverage": str(leverage),
            "stop": "loss",
            "stopPrice": str(stop_price),
            "stopPriceType": "TP",
            "reduceOnly": True
        }

        str_to_sign = str(now) + "POST" + endpoint + str(data).replace("'", '"')
        signature = base64.b64encode(
            hmac.new(API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        )

        passphrase = base64.b64encode(
            hmac.new(API_SECRET.encode('utf-8'), API_PASSPHRASE.encode('utf-8'), hashlib.sha256).digest()
        )

        headers = {
            "KC-API-SIGN": signature.decode(),
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": API_KEY,
            "KC-API-PASSPHRASE": passphrase.decode(),
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        resp = requests.post(url, json=data, headers=headers)
        print("Stop Loss Response:", resp.text)
        return resp.json()
    except Exception as e:
        print("Eroare la crearea SL:", e)
        return None

# ==========================
#  Webhook
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action   = data.get("action")
        symbol   = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0)) or 0
        sl_price = float(data.get("sl", 0)) or 0

        side = "buy" if action.lower() == "buy" else "sell"

        # ==========================
        # Ordin Market principal
        # ==========================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=quantity,
            lever=str(leverage)
        )
        print("Ordin Market executat:", order)

        # ==========================
        # Take Profit
        # ==========================
        if tp_price > 0:
            try:
                tp_order = client.create_limit_order(
                    symbol=symbol,
                    side="sell" if side == "buy" else "buy",
                    price=str(tp_price),
                    size=quantity,
                    lever=str(leverage),
                    reduceOnly=True
                )
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        # ==========================
        # Stop Loss (via REST API)
        # ==========================
        if sl_price > 0:
            try:
                sl_order = place_stop_loss(
                    symbol,
                    "sell" if side == "buy" else "buy",
                    quantity,
                    leverage,
                    sl_price
                )
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", e)

        return jsonify({"success": True, "order": order})

    except Exception as e:
        print("Eroare la executie:", e)
        return jsonify({"error": str(e)}), 500

# ==========================
#  Pornire server Flask
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
