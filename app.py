import os
from flask import Flask, request, jsonify
from kucoin.futures.client import Trade
import uuid

# API keys din Render
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Client KuCoin Futures
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE, is_sandbox=False)

app = Flask(__name__)

WEBHOOK_SECRET = "raulsecret123"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Payload primit:", data)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action = data.get("action")  # buy / sell
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = str(data.get("leverage", 5))  # KuCoin cere string
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        side = "buy" if action.lower() == "buy" else "sell"

        # === 1. Market Order ===
        market_order = client.create_order(
            symbol=symbol,
            side=side,
            type="market",
            marginMode="isolated",   # fortam Isolated
            leverage=leverage,
            size=quantity,
            clientOid=str(uuid.uuid4())
        )
        print("Ordin Market executat:", market_order)

        # === 2. Take Profit (daca e definit) ===
        if tp_price > 0:
            tp_side = "sell" if side == "buy" else "buy"
            try:
                tp_order = client.create_order(
                    symbol=symbol,
                    side=tp_side,
                    type="limit",
                    price=str(tp_price),
                    marginMode="isolated",
                    leverage=leverage,
                    size=quantity,
                    reduceOnly=True,  # important pentru TP
                    clientOid=str(uuid.uuid4())
                )
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        # === 3. Stop Loss (daca e definit) ===
        if sl_price > 0:
            sl_side = "sell" if side == "buy" else "buy"
            try:
                sl_order = client.create_order(
                    symbol=symbol,
                    side=sl_side,
                    type="stop_market",
                    stop="entry",              # tip de trigger
                    stopPrice=str(sl_price),   # pret de declansare
                    marginMode="isolated",
                    leverage=leverage,
                    size=quantity,
                    reduceOnly=True,  # important pentru SL
                    clientOid=str(uuid.uuid4())
                )
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", e)

        return jsonify({"status": "ok", "market_order": market_order})

    except Exception as e:
        print("Eroare la executie:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
