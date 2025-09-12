import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ===============================
# API KEYS din variabile ENV
# ===============================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# ===============================
# Inițializare client
# ===============================
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    # ===============================
    # Validare date
    # ===============================
    if not data or data.get("auth") != "raulsecret123":
        return jsonify({"error": "Auth invalid"}), 403

    try:
        action = data.get("action")  # buy/sell
        symbol = data.get("symbol", "ETHUSDTM")  # default ETH futures
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        side = "buy" if action.lower() == "buy" else "sell"
        positionSide = "LONG" if side == "buy" else "SHORT"

        # ===============================
        # Execută ordinul Market
        # ===============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=leverage,
            size=quantity,
            positionSide=positionSide,
            tp=tp_price if tp_price > 0 else None,
            sl=sl_price if sl_price > 0 else None
        )

        print("Ordin executat:", order)
        return jsonify({"status": "success", "order": order})

    except Exception as e:
        print("Eroare la execuție:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
