import os
import uuid
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==============================
# API KEYS din Render (Environment Variables)
# ==============================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# KuCoin Client
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

# ==============================
# Webhook Endpoint
# ==============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Payload primit:", data)

    # Validare secret
    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action   = data.get("action")        # buy / sell
        symbol   = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 0.01))  # ETH
        leverage = str(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # Direcție
        side = "buy" if action.lower() == "buy" else "sell"

        # ==============================
        # Conversie ETH → contracte
        # 1 contract ETHUSDTM = 0.01 ETH
        # ==============================
        contracts = int(quantity * 100)  # ex: 0.01 ETH → 1 contract
        if contracts < 1:
            return jsonify({"error": "Quantity prea mică pentru 1 contract"}), 400

        # ==============================
        # 1. Market Order Principal
        # ==============================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=contracts,
            lever=leverage
        )
        print("Ordin Market executat:", order)

        # ==============================
        # 2. TP + SL ca OCO Order
        # ==============================
        if tp_price > 0 and sl_price > 0:
            try:
                oco_order = client.create_stop_order(
                    symbol=symbol,
                    side="sell" if side == "buy" else "buy",
                    size=contracts,
                    lever=leverage,
                    stop="down" if side == "buy" else "up",
                    stopPrice=str(sl_price),
                    stopPriceType="TP",
                    reduceOnly=True,
                    closeOrder=True,
                    clientOid=str(uuid.uuid4()),
                    tpPrice=str(tp_price)
                )
                print("Ordin OCO (TP+SL) creat:", oco_order)
            except Exception as e:
                print("Eroare creare OCO:", e)

        return jsonify({"status": "ok", "market_order": order})

    except Exception as e:
        print("Eroare execuție:", e)
        return jsonify({"error": str(e)}), 500

# ==============================
# Run Flask App
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
