import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==============================
#  API KEYS din variabile ENV
# ==============================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Inițializare client corect (fără is_sandbox)
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action = data.get("action")  # buy / sell
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = data.get("quantity", 1)
        leverage = data.get("leverage", 5)
        tp_price = data.get("tp")
        sl_price = data.get("sl")

        # ==============================
        #   Market Order
        # ==============================
        if action.lower() == "buy":
            side = "buy"
        elif action.lower() == "sell":
            side = "sell"
        else:
            return jsonify({"error": "Action invalid"}), 400

        # Plasăm ordinul principal
        main_order = client.create_market_order(
            symbol=symbol,
            side=side,
            lever=leverage,
            size=quantity
        )
        print("Main order response:", main_order)

        # ==============================
        #   TP & SL (reduceOnly = True)
        # ==============================
        if tp_price:
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                price=str(tp_price),
                size=quantity,
                reduceOnly=True
            )
            print("TP order response:", tp_order)

        if sl_price:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                stop="down" if side == "buy" else "up",
                stopPrice=str(sl_price),
                size=quantity,
                reduceOnly=True
            )
            print("SL order response:", sl_order)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("Eroare:", str(e))
        return jsonify({"status": "error", "msg": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
