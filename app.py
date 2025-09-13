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
client = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE
)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action = data.get("action")       # buy sau sell
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        lever = int(data.get("lever", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # stabilim direcția
        side = "buy" if action.lower() == "buy" else "sell"

        # ============================
        # 1. Executăm ordinul Market
        # ============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=quantity,
            lever=lever,
            marginMode="cross",     # cross sau isolated
            positionMode="hedge"    # hedge activat
        )

        print("Market order:", order)

        # ============================
        # 2. Adăugăm TP și SL dacă există
        # ============================
        if tp_price > 0:
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                price=tp_price,
                size=quantity,
                lever=lever,
                marginMode="cross",
                positionMode="hedge"
            )
            print("Take Profit setat:", tp_order)

        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                stop="down" if side == "buy" else "up",
                stopPrice=sl_price,
                size=quantity,
                lever=lever,
                marginMode="cross",
                positionMode="hedge"
            )
            print("Stop Loss setat:", sl_order)

        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
