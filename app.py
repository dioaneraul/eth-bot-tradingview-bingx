import os
import uuid
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==========================
# Config API KuCoin Futures
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE, is_sandbox=False)

app = Flask(__name__)

# ==========================
# Funcție creare Market Order
# ==========================
def place_market_order(symbol, side, quantity, leverage):
    return client.create_market_order(
        symbol=symbol,
        side=side,
        lever=str(leverage),
        marginMode="isolated",
        size=str(quantity)
    )

# ==========================
# Funcție creare Limit Order (TP)
# ==========================
def place_tp_order(symbol, side, quantity, leverage, tp_price):
    return client.create_limit_order(
        symbol=symbol,
        side=side,
        lever=str(leverage),
        marginMode="isolated",
        size=str(quantity),
        price=str(tp_price),
        reduceOnly=True  # Închide poziția existentă
    )

# ==========================
# Funcție creare Stop Order (SL)
# ==========================
def place_sl_order(symbol, side, quantity, leverage, sl_price, action):
    return client.create_limit_order(
        symbol=symbol,
        side=side,
        lever=str(leverage),
        marginMode="isolated",
        size=str(quantity),
        stop="down" if action == "buy" else "up",  # stop pentru long/short
        stopPrice=str(sl_price),
        reduceOnly=True
    )

# ==========================
# Endpoint webhook TradingView
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    print("Payload primit:", data)

    if not data or data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"code": "error", "msg": "Unauthorized"}), 401

    try:
        action = data.get("action")  # buy / sell
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = data.get("quantity", 1)
        leverage = data.get("leverage", 5)
        tp_price = data.get("tp")
        sl_price = data.get("sl")

        side = "buy" if action == "buy" else "sell"

        # ==========================
        # Execută Market Order
        # ==========================
        market_order = place_market_order(symbol, side, quantity, leverage)
        print("Ordin Market executat:", market_order)

        # ==========================
        # Creează TP
        # ==========================
        if tp_price:
            try:
                tp_side = "sell" if action == "buy" else "buy"
                tp_order = place_tp_order(symbol, tp_side, quantity, leverage, tp_price)
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", str(e))

        # ==========================
        # Creează SL
        # ==========================
        if sl_price:
            try:
                sl_side = "sell" if action == "buy" else "buy"
                sl_order = place_sl_order(symbol, sl_side, quantity, leverage, sl_price, action)
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", str(e))

        return jsonify({"code": "success", "msg": "Ordin executat"}), 200

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"code": "error", "msg": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
