import os
import logging
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# -----------------------------
# Config logging
# -----------------------------
logging.basicConfig(level=logging.INFO)

# -----------------------------
# API KEYS din Environment
# -----------------------------
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# -----------------------------
# KuCoin Client
# -----------------------------
client = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    is_sandbox=False
)

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.info(f"Payload primit: {data}")

        # -----------------------------
        # Validare secret
        # -----------------------------
        if data.get("auth") != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 403

        # -----------------------------
        # Extragem parametrii
        # -----------------------------
        action = data.get("action", "").lower()
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        side = "buy" if action == "buy" else "sell"

        # -----------------------------
        # Market Order cu leverage 5x isolated
        # -----------------------------
        logging.info(f"Plasare market order: {side} {quantity} {symbol} lev={leverage} isolated")

        order = client.create_market_order(
            symbol=symbol,
            side=side,
            leverage=leverage,
            marginMode="isolated",
            size=quantity
        )

        logging.info(f"Market order executat: {order}")

        # -----------------------------
        # Atașăm Take Profit și Stop Loss
        # -----------------------------
        if tp_price > 0:
            client.create_limit_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                price=tp_price,
                size=quantity,
                leverage=leverage,
                marginMode="isolated",
                reduceOnly=True
            )
            logging.info(f"TP setat la {tp_price}")

        if sl_price > 0:
            client.create_stop_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                stop="down" if side == "buy" else "up",
                stopPrice=sl_price,
                size=quantity,
                leverage=leverage,
                marginMode="isolated",
                reduceOnly=True
            )
            logging.info(f"SL setat la {sl_price}")

        return jsonify({"status": "success", "market_order": order})

    except Exception as e:
        logging.error(f"Eroare la executie: {str(e)}")
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Run local (doar pentru test)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
