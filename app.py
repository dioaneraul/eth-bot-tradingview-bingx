import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# API KEYS
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Client KuCoin
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action = data.get("action")
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        side = "buy" if action.lower() == "buy" else "sell"

        # 1. Market order
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=leverage,
            size=quantity
        )
        print("Market order:", order)

        # 2. TP și SL
        if tp_price > 0:
            tp = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                price=tp_price,
                leverage=leverage,
                size=quantity,
                reduceOnly=True
            )
            print("Take Profit:", tp)

        if sl_price > 0:
            sl = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                stop="down" if side == "buy" else "up",
                stopPrice=sl_price,
                price=sl_price,
                leverage=leverage,
                size=quantity,
                reduceOnly=True
            )
            print("Stop Loss:", sl)

        return jsonify({"msg": "Ordin executat cu succes!"})

    except Exception as e:
        print("Eroare:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
