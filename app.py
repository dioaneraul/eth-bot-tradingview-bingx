import os
from flask import Flask, request, jsonify
from kucoin.futures.client import Trade
import uuid

# API keys din Render
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")

# Client KuCoin Futures
client = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    is_sandbox=False
)

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
        leverage = int(data.get("leverage", 5))  # int e corect aici
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        side = "buy" if action.lower() == "buy" else "sell"

        # === 0. Setăm leverage pe simbol (obligatoriu) ===
        try:
            client.change_margin_mode(symbol, "ISOLATED")  # sau CROSS dacă vrei
            client.set_leverage(symbol, leverage, "ISOLATED")
        except Exception as e:
            print("Eroare setare leverage/margin:", e)

        # === 1. Market Order ===
        market_order = client.create_order(
            symbol=symbol,
            side=side,
            type="market",
            size=quantity,
            clientOid=str(uuid.uuid4())
        )
        print("Ordin Market executat:", market_order)

        # === 2. Take Profit ===
        if tp_price > 0:
            tp_side = "sell" if side == "buy" else "buy"
            try:
                tp_order = client.create_order(
                    symbol=symbol,
                    side=tp_side,
                    type="limit",
                    price=str(tp_price),
                    size=quantity,
                    reduceOnly=True,
                    clientOid=str(uuid.uuid4())
                )
                print("Ordin TP creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", e)

        # === 3. Stop Loss ===
        if sl_price > 0:
            sl_side = "sell" if side == "buy" else "buy"
            stop_type = "down" if side == "buy" else "up"  # sens corect
            try:
                sl_order = client.create_order(
                    symbol=symbol,
                    side=sl_side,
                    type="market",
                    stop=stop_type,
                    stopPrice=str(sl_price),
                    stopPriceType="TP",  # sau "MP" pentru mark price
                    size=quantity,
                    reduceOnly=True,
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
