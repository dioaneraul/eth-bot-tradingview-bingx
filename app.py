from flask import Flask, request, jsonify
from kucoin_futures.client import Trade
import os

app = Flask(__name__)

API_KEY = os.getenv("KUCOIN_API_KEY")
API_SECRET = os.getenv("KUCOIN_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "raulsecret123")

# client pentru futures trading
client = Trade(key=API_KEY, secret=API_SECRET, passphrase=API_PASSPHRASE, is_sandbox=False)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("Payload primit:", data)

        if data.get("auth") != WEBHOOK_SECRET:
            return jsonify({"error": "Auth invalid"}), 403

        action = data.get("action")
        symbol = data.get("symbol")
        quantity = data.get("quantity")
        leverage = data.get("leverage", 5)
        tp = data.get("tp")
        sl = data.get("sl")

        # intrare in pozitie (market order)
        if action == "buy":
            order = client.create_market_order(
                symbol=symbol,
                side="buy",
                lever=leverage,
                size=quantity
            )
            place_tp_sl(symbol, "buy", quantity, leverage, tp, sl)

        elif action == "sell":
            order = client.create_market_order(
                symbol=symbol,
                side="sell",
                lever=leverage,
                size=quantity
            )
            place_tp_sl(symbol, "sell", quantity, leverage, tp, sl)

        else:
            return jsonify({"error": "Actiune invalida"}), 400

        return jsonify({"message": "Ordin executat", "data": order})

    except Exception as e:
        print("Eroare la executie:", str(e))
        return jsonify({"error": str(e)}), 500


def place_tp_sl(symbol, side, quantity, leverage, tp=None, sl=None):
    """ Plaseaza ordine pentru Take Profit si Stop Loss """
    try:
        opposite = "sell" if side == "buy" else "buy"

        if tp:
            try:
                tp_order = client.create_limit_order(
                    symbol=symbol,
                    side=opposite,
                    lever=leverage,
                    price=str(tp),
                    size=quantity,
                    reduceOnly=True
                )
                print("TP setat:", tp_order)
            except Exception as e:
                print("Eroare TP:", str(e))

        if sl:
            try:
                sl_order = client.create_stop_order(
                    symbol=symbol,
                    side=opposite,
                    lever=leverage,
                    stopPrice=str(sl),
                    price=str(sl),
                    size=quantity,
                    reduceOnly=True
                )
                print("SL setat:", sl_order)
            except Exception as e:
                print("Eroare SL:", str(e))

    except Exception as e:
        print("Eroare generala TP/SL:", str(e))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
