import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action = data.get("action")  # "buy" sau "sell"
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        lever = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        side = "buy" if action.lower() == "buy" else "sell"

        # ==============================
        # 1. Market Order
        # ==============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            lever=lever,
            size=quantity
        )
        print("Ordin executat:", order)

        # ==============================
        # 2. TP și SL (folosim create_stop_order)
        # ==============================
        exit_side = "sell" if side == "buy" else "buy"

        if tp_price > 0:
            tp_order = client.create_stop_order(
                symbol=symbol,
                side=exit_side,
                stop="up" if side == "buy" else "down",
                stopPrice=tp_price,
                size=quantity
            )
            print("TP creat:", tp_order)

        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side=exit_side,
                stop="down" if side == "buy" else "up",
                stopPrice=sl_price,
                size=quantity
            )
            print("SL creat:", sl_order)

        return jsonify({"status": "success", "message": "Order + TP/SL executate"})

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
