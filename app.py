import os
import uuid
from flask import Flask, request, jsonify
from kucoin.futures.client import Trade

# ==========================
#  API KEYS din Render
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# Client KuCoin Futures
client = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    is_sandbox=False
)

# Flask app
app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Payload primit:", data)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Extragem parametrii
        action   = data.get("action")        # buy / sell
        symbol   = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0)) or 0
        sl_price = float(data.get("sl", 0)) or 0

        side = "buy" if action.lower() == "buy" else "sell"

        # ==========================
        # Ordin Market principal
        # ==========================
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=quantity,
            lever=str(leverage)
        )
        print("Ordin Market executat:", order)

        # ==========================
        # Take Profit (Conditional)
        # ==========================
        if tp_price > 0:
            try:
                tp_order = client.create_limit_order(
                    symbol=symbol,
                    side="sell" if side == "buy" else "buy",
                    price=str(tp_price),
                    size=quantity,
                    lever=str(leverage),
                    reduceOnly=True,
                    closeOrder=True,
                    clientOid=str(uuid.uuid4())
                )
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        # ==========================
        # Stop Loss (Conditional)
        # ==========================
        if sl_price > 0:
            try:
                stop_type = "down" if side == "buy" else "up"
                sl_order = client.create_order(
                    symbol=symbol,
                    side="sell" if side == "buy" else "buy",
                    type="market",
                    stop=stop_type,
                    stopPrice=str(sl_price),
                    stopPriceType="MP",  # MP = Mark Price
                    size=quantity,
                    reduceOnly=True,
                    closeOrder=True,
                    clientOid=str(uuid.uuid4())
                )
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", e)

        return jsonify({"success": True, "market_order": order})

    except Exception as e:
        print("Eroare la executie:", e)
        return jsonify({"error": str(e)}), 500


# ==========================
# Pornire server Flask
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
