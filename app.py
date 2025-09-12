import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ================================
# API KEYS din Render ENV
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# ================================
# Client KuCoin Futures
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action = data.get("action")      # buy / sell
        symbol = data.get("symbol")      # ETHUSDTM
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # ======================
        # 1. MARKET ORDER
        side = "buy" if action.lower() == "buy" else "sell"
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=leverage,
            size=quantity
        )
        print("Market order:", order)

        # ======================
        # 2. STOP LOSS
        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                size=quantity,
                stop="loss",
                stop_price=sl_price,
                leverage=leverage
            )
            print("Stop Loss order:", sl_order)

        # ======================
        # 3. TAKE PROFIT
        if tp_price > 0:
            tp_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                size=quantity,
                stop="entry",
                stop_price=tp_price,
                leverage=leverage
            )
            print("Take Profit order:", tp_order)

        return jsonify({"status": "success", "order": order})

    except Exception as e:
        print("Eroare:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
