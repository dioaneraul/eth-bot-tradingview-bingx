import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade
import requests

# ==========================
#  API KEYS din Render
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# Endpoint KuCoin Futures pentru leverage
KUCOIN_FUTURES_URL = "https://api-futures.kucoin.com"

# Client trading
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE)

app = Flask(__name__)

# ==========================
#  Helper pentru leverage
# ==========================
def set_leverage(symbol, leverage):
    url = f"{KUCOIN_FUTURES_URL}/api/v1/position/leverage"
    headers = {"KC-API-KEY": API_KEY, "KC-API-PASSPHRASE": API_PASSPHRASE}
    # ⚠️ semnarea completă e necesară pentru REST call direct
    # aici e doar scheletul pentru explicare
    print(f"(Simulare) Setez leverage {leverage}x pentru {symbol} la isolated")
    return True


# ==========================
#  Webhook
# ==========================
@app.route("/webhook", methods=["POST"])
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

        # 1. Setare leverage (prin REST, aici doar simulat)
        set_leverage(symbol, leverage)

        # 2. Market order principal
        order = client.create_market_order(
            symbol=symbol,
            side=side,
            size=quantity
        )
        print("Ordin Market:", order)

        # 3. TP (limit order reduceOnly)
        if tp_price > 0:
            tp_order = client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                price=str(tp_price),
                size=quantity,
                reduceOnly=True
            )
            print("Ordin TP:", tp_order)

        # 4. SL (stop order reduceOnly)
        if sl_price > 0:
            sl_order = client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                stop="loss",
                stopPrice=str(sl_price),
                size=quantity,
                reduceOnly=True
            )
            print("Ordin SL:", sl_order)

        return jsonify({"success": True, "order": order})

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
