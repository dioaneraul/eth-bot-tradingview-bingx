from flask import Flask, request, jsonify
import time, base64, hmac, hashlib, requests, json, os, traceback

app = Flask(__name__)

# Variabile din Environment (Render)
API_KEY = os.environ.get("KUCOIN_FUTURES_API_KEY")
API_SECRET = os.environ.get("KUCOIN_FUTURES_API_SECRET")
API_PASSPHRASE = os.environ.get("KUCOIN_FUTURES_API_PASSPHRASE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

BASE_URL = "https://api-futures.kucoin.com"

def get_headers(method, endpoint, body=""):
    now = str(int(time.time() * 1000))
    str_to_sign = now + method.upper() + endpoint + body
    signature = base64.b64encode(
        hmac.new(API_SECRET.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    )
    passphrase = base64.b64encode(
        hmac.new(API_SECRET.encode(), API_PASSPHRASE.encode(), hashlib.sha256).digest()
    )

    return {
        "KC-API-KEY": API_KEY,
        "KC-API-SIGN": signature.decode(),
        "KC-API-TIMESTAMP": now,
        "KC-API-PASSPHRASE": passphrase.decode(),
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("Webhook received:", data, flush=True)

        if data.get("auth") != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401

        side = data.get("action").upper()      # BUY sau SELL
        symbol = data.get("symbol")            # ex. ETHUSDTM
        leverage = str(data.get("leverage", 5))
        price = data.get("price")
        tp = data.get("tp")
        sl = data.get("sl")

        # ======================
        # Conversie în contracte
        # ======================
        contracts_per_coin = {
            "ETHUSDTM": 0.01,   # 1 contract = 0.01 ETH
            "XBTUSDTM": 0.001,  # 1 contract = 0.001 BTC
            "SOLUSDTM": 1,      # 1 contract = 1 SOL
            "ADAUSDTM": 10,     # 1 contract = 10 ADA
            "XRPUSDTM": 10,     # 1 contract = 10 XRP
            "DOGEUSDTM": 100,   # 1 contract = 100 DOGE
            "PAXGUSDTM": 0.01,  # 1 contract = 0.01 PAXG
        }

        qty_input = float(data.get("quantity"))  # ce trimiți tu (în monede)
        contract_size = contracts_per_coin.get(symbol, 1)  # fallback = 1
        qty = int(qty_input / contract_size)  # conversie în contracte (integer)

        print(f"Placing order -> {side} {symbol}, qty_input={qty_input}, contracts={qty}, lev={leverage}, TP={tp}, SL={sl}", flush=True)

        # 1. Setează leverage
        endpoint_lev = f"/api/v1/position/setLeverage"
        lev_body = {"symbol": symbol, "leverage": leverage}
        headers = get_headers("POST", endpoint_lev, json.dumps(lev_body))
        res_lev = requests.post(BASE_URL + endpoint_lev, headers=headers, data=json.dumps(lev_body))
        print("Leverage response:", res_lev.text, flush=True)

        # 2. Creează ordin principal (market)
        endpoint_order = "/api/v1/orders"
        order_body = {
            "symbol": symbol,
            "side": side,
            "type": "market",
            "size": qty,
            "leverage": leverage
        }
        headers = get_headers("POST", endpoint_order, json.dumps(order_body))
        res_order = requests.post(BASE_URL + endpoint_order, headers=headers, data=json.dumps(order_body))
        print("Order response:", res_order.text, flush=True)

        order_id = None
        try:
            order_id = res_order.json().get("data", {}).get("orderId")
        except:
            pass

        # 3. Adaugă TP și SL dacă există
        if order_id and (tp or sl):
            endpoint_oco = "/api/v1/stopOrders"
            stop_body = {
                "symbol": symbol,
                "side": "sell" if side == "BUY" else "buy",  # invers pentru exit
                "type": "limit",
                "size": qty,
                "reduceOnly": True
            }
            if tp:
                stop_body["stopPrice"] = str(tp)
                stop_body["price"] = str(tp)
                stop_body["stop"] = "up" if side == "BUY" else "down"
                headers = get_headers("POST", endpoint_oco, json.dumps(stop_body))
                res_tp = requests.post(BASE_URL + endpoint_oco, headers=headers, data=json.dumps(stop_body))
                print("TP response:", res_tp.text, flush=True)

            if sl:
                stop_body["stopPrice"] = str(sl)
                stop_body["price"] = str(sl)
                stop_body["stop"] = "down" if side == "BUY" else "up"
                headers = get_headers("POST", endpoint_oco, json.dumps(stop_body))
                res_sl = requests.post(BASE_URL + endpoint_oco, headers=headers, data=json.dumps(stop_body))
                print("SL response:", res_sl.text, flush=True)

        return jsonify({
            "status": "executed",
            "symbol": symbol,
            "side": side,
            "contracts": qty,
            "tp": tp,
            "sl": sl
        })

    except Exception as e:
        print("ERROR:", str(e), flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
