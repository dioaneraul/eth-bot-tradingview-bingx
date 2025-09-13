import os
from flask import Flask, request, jsonify
from kucoin_futures.client import Trade

# ==========================
# API KEYS din Environment
# ==========================
API_KEY = os.getenv("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.getenv("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# ==========================
# Client KuCoin Futures
# ==========================
client = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    is_sandbox=False
)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Payload primit:", data)

    # ==========================
    # Validare secret
    # ==========================
    if data.get("auth") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        action = data.get("action")  # buy / sell
        symbol = data.get("symbol", "ETHUSDTM")
        quantity = float(data.get("quantity", 1))
        leverage = int(data.get("leverage", 5))
        tp_price = float(data.get("tp", 0))
        sl_price = float(data.get("sl", 0))

        # ==========================
        # Setăm leverage
        # ==========================
        try:
            client.change_leverage(symbol=symbol, leverage=leverage)
        except Exception as e:
            print("Eroare setare leverage:", str(e))

        # ==========================
        # Ordin principal Market
        # ==========================
        side = "buy" if action.lower() == "buy" else "sell"

        order = client.create_market_order(
            symbol=symbol,
            side=side,
            lever=leverage,
            size=quantity
        )
        print("Ordin executat:", order)

        # ==========================
        # TP și SL (reduceOnly=True)
        # ==========================
        if side == "buy":
            exit_side = "sell"
        else:
            exit_side = "buy"

        # Take Profit
        if tp_price > 0:
            try:
                tp_order = client.create_order(
                    symbol=symbol,
                    side=exit_side,
                    type="limit",
                    size=quantity,
                    price=tp_price,
                    reduceOnly=True
                )
                print("Take Profit creat:", tp_order)
            except Exception as e:
                print("Eroare TP:", str(e))

        # Stop Loss
        if sl_price > 0:
            try:
                sl_order = client.create_order(
                    symbol=symbol,
                    side=exit_side,
                    type="stop_market",
                    stop="down" if side == "buy" else "up",
                    stopPrice=sl_price,
                    size=quantity,
                    reduceOnly=True
                )
                print("Stop Loss creat:", sl_order)
            except Exception as e:
                print("Eroare SL:", str(e))

        return jsonify({"status": "success", "main_order": order})

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
