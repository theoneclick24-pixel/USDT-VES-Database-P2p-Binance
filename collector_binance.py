import sys
import os
import requests as std_requests
from bs4 import BeautifulSoup
from supabase import create_client
from curl_cffi import requests as c_requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip('/')
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

def consultar_binance(trade_type="BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v1/friendly/c2c/ad/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Clienttype": "web",
        "Content-Type": "application/json"
    }
    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "rows": 10,
        "tradeType": trade_type
    }
    try:
        r = c_requests.post(url, json=payload, headers=headers, impersonate="chrome120", timeout=12)
        if r.status_code == 200:
            data = r.json().get("data", [])
            return [float(item["adv"]["price"]) for item in data if "adv" in item and item["adv"].get("price")]
    except Exception as e:
        print(f"Error Binance: {e}")
    return []

def obtener_bcv():
    try:
        r = std_requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if r.status_code == 200:
            return round(float(r.json().get("promedio", 0)), 4)
    except Exception:
        pass
    return 0.0

if __name__ == "__main__":
    buy = consultar_binance("BUY")
    sell = consultar_binance("SELL")
    bcv = obtener_bcv()

    if not buy or not sell:
        sys.exit(0)

    tick_data = {
        "p2p_buy_avg": round(sum(buy) / len(buy), 4),
        "p2p_buy_min": round(min(buy), 4),
        "p2p_sell_avg": round(sum(sell) / len(sell), 4),
        "p2p_sell_max": round(max(sell), 4),
        "bcv_rate": bcv,
        "sample_size": len(buy) + len(sell)
    }

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("p2p_ticks_binance").insert(tick_data).execute()
        print("Registrado en p2p_ticks_binance con éxito.")
    except Exception as e:
        print(f"Error Supabase Binance: {e}")
        sys.exit(1)
