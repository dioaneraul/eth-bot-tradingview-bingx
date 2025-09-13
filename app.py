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

# Flask app
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    try:
        action = data.get("action")        # buy / sell
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # BUY sau SELL
        side = "buy" if action.lower() == "buy" else "sell"

        # ============================
        # 1. Market Order principal
        # ============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=quantity,
            lever=leverage   # <-- corect, nu leverage
        )
        print("Market order executat:", order)

        # ============================
        # 2. TP / SL (dacă există)
        # ============================
        tp_order, sl_order = None, None

        if tp_price > 0:
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                size=quantity,
                price=tp_price,
                reduceOnly=True
            )
            print("TP setat:", tp_order)

        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                size=quantity,
                stop="down" if side == "buy" else "up",
                stopPrice=sl_price,
                reduceOnly=True
            )
            print("SL setat:", sl_order)

        return jsonify({
            "status": "success",
            "market_order": order,
            "tp_order": tp_order,
            "sl_order": sl_order
        })

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
