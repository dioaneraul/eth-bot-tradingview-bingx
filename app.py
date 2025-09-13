import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==============================
# API KEYS din Environment
# ==============================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Init KuCoin client
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
        leverage = int(data.get("leverage", 5))

        side = "buy" if action.lower() == "buy" else "sell"

        # ==============================
        # Market Order simplu
        # ==============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=leverage,
            size=quantity
        )

        print("Ordin executat:", order)
        return jsonify({"status": "success", "order": order})

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
