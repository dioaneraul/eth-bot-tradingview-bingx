import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==============================
# API KEYS din variabile ENV
# ==============================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Inițializare client
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action   = data.get("action")      # buy / sell
        symbol   = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # Default → isolated margin
        margin_mode = data.get("marginMode", "isolated")
        side = "buy" if action.lower() == "buy" else "sell"
        pos_side = "long" if side == "buy" else "short"

        # ========================
        # 1. Market order
        # ========================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=leverage,
            size=quantity,
            marginMode=margin_mode,   # FIX → explicit isolated
            positionSide=pos_side
        )
        print("Market order:", order)

        # ========================
        # 2. TP & SL (dacă există)
        # ========================
        if tp_price > 0:
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                size=quantity,
                price=tp_price,
                marginMode=margin_mode,
                positionSide=pos_side,
                reduceOnly=True
            )
            print("TP order:", tp_order)

        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                size=quantity,
                stop="down" if side == "buy" else "up",
                stopPrice=sl_price,
                marginMode=margin_mode,
                positionSide=pos_side,
                reduceOnly=True
            )
            print("SL order:", sl_order)

        return jsonify({"status": "success", "message": "Order executat"}), 200

    except Exception as e:
        print("Eroare:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
