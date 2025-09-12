import os
import time
import uuid
import requests
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

app = Flask(__name__)

# ==========================
# API Keys din Render Env
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE, is_sandbox=False)

# ==========================
# Webhook endpoint
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Payload primit:", data)

    if data.get("auth") != "raulsecret123":
        return jsonify({"error": "Auth invalid"}), 403

    symbol = data.get("symbol", "ETHUSDTM")
    side = data.get("action", "buy").upper()  # BUY sau SELL
    qty = data.get("quantity", 1)
    leverage = int(data.get("leverage", 5))
    tp = float(data.get("tp", 0))
    sl = float(data.get("sl", 0))

    try:
        # ==========================
        # 1. Buy Market principal
        # ==========================
        client.set_leverage(symbol=symbol, leverage=leverage)
        order_id = str(uuid.uuid4())
        res = client.create_market_order(
            symbol=symbol,
            side=side,
            size=qty,
            clientOid=order_id
        )
        print("Main order response:", res)

        # ==========================
        # 2. TP (Sell Limit)
        # ==========================
        if tp > 0:
            tp_id = str(uuid.uuid4())
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "BUY" else "buy",
                size=qty,
                price=tp,
                reduceOnly=True,
                clientOid=tp_id
            )
            print("TP response:", tp_order)

        # ==========================
        # 3. SL (Stop Market)
        # ==========================
        if sl > 0:
            sl_id = str(uuid.uuid4())
            sl_order = client.create_market_order(
                symbol=symbol,
                side="sell" if side == "BUY" else "buy",
                size=qty,
                stop="down" if side == "BUY" else "up",
                stopPrice=sl,
                reduceOnly=True,
                clientOid=sl_id
            )
            print("SL response:", sl_order)

        return jsonify({"status": "executed", "symbol": symbol, "side": side, "qty": qty, "tp": tp, "sl": sl})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
