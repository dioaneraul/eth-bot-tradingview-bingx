import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==============================
# API KEYS din variabile ENV
# ==============================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Inițializare client KuCoin Futures
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        # Extragem datele din payload
        action = data.get("action")  # buy / sell
        symbol = data.get("symbol", "ETHUSDTM")  # default futures ETH
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # Direcția tranzacției
        side = "buy" if action.lower() == "buy" else "sell"

        # ==============================
        # 1. Executăm Market Order
        # ==============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=str(leverage),
            size=str(quantity)
        )
        print("Market order executat:", order)

        # ==============================
        # 2. Plasăm Take Profit (Limit Order)
        # ==============================
        if tp_price > 0:
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                leverage=str(leverage),
                size=str(quantity),
                price=str(tp_price)
            )
            print("Take profit plasat:", tp_order)

        # ==============================
        # 3. Plasăm Stop Loss (Stop Order)
        # ==============================
        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                leverage=str(leverage),
                size=str(quantity),
                stop="down" if side == "buy" else "up",
                stopPrice=str(sl_price)
            )
            print("Stop loss plasat:", sl_order)

        return jsonify({"status": "success", "message": "Order executat"}), 200

    except Exception as e:
        print("Eroare:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
