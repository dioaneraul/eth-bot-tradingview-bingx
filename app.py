import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==========================
#  API KEYS din Render
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# Client trading
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

# ==========================
#  Webhook
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Payload primit:", data)

    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action   = data.get("action")
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
        # Take Profit
        # ==========================
        if tp_price > 0:
            try:
                tp_order = client.create_limit_order(
                    symbol=symbol,
                    side="sell" if side == "buy" else "buy",
                    price=str(tp_price),
                    size=quantity,
                    lever=str(leverage),
                    reduceOnly=True
                )
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        # ==========================
        # Stop Loss (corect cu create_stop_order)
        # ==========================
        if sl_price > 0:
            try:
                sl_order = client.create_stop_order(
                    symbol=symbol,
                    side="sell" if side == "buy" else "buy",
                    type="market",
                    size=quantity,
                    lever=str(leverage),
                    stop="loss",
                    stopPrice=str(sl_price),
                    stopPriceType="TP",
                    reduceOnly=True
                )
                print("Ordin SL creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", e)

        return jsonify({"success": True, "order": order})

    except Exception as e:
        print("Eroare la executie:", e)
        return jsonify({"error": str(e)}), 500

# ==========================
#  Pornire server Flask
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
