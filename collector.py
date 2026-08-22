import sys
import time
import requests
from bs4 import BeautifulSoup
from supabase import create_client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def obtener_p2p(trade_type="BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v1/friendly/c2c/ad/search"
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "publisherType": None,
        "rows": 10,
        "tradeType": trade_type
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching P2P ({trade_type}): {e}")
        return 0.0, 0.0, 0  # avg, extreme, sample_size

    data = response.json().get("data", [])
    prices = []
    for item in data:
        try:
            if "adv" in item and item["adv"].get("price") is not None:
                prices.append(float(item["adv"]["price"]))
        except Exception:
            # skip malformed items
            continue

    sample_size = len(prices)
    if sample_size == 0:
        print(f"No P2P prices found for {trade_type}.")
        return 0.0, 0.0, 0

    avg_price = sum(prices) / sample_size
    extreme_price = min(prices) if trade_type == "BUY" else max(prices)
    return round(avg_price, 4), round(extreme_price, 4), sample_size

# obtener_bcv remains largely the same (optional: add similar guards)
def obtener_bcv():
    try:
        r = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if r.status_code == 200:
            return float(r.json().get("promedio"))
    except Exception:
        pass

    try:
        r = requests.get("https://www.bcv.org.ve", verify=False, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, 'html.parser')
        val_text = soup.find('div', id='dolar').find('strong').text.strip().replace(',', '.')
        return float(val_text)
    except Exception as e:
        print(f"Error consultando BCV: {e}")
        return 0.0

if __name__ == "__main__":
    buy_avg, buy_min, buy_sample = obtener_p2p("BUY")
    sell_avg, sell_max, sell_sample = obtener_p2p("SELL")
    bcv = obtener_bcv()

    total_sample = buy_sample + sell_sample

    if total_sample == 0:
        print("No P2P samples collected for BUY or SELL. Skipping DB insert.")
        sys.exit(0)  # exit cleanly (not an error state)

    tick_data = {
        "p2p_buy_avg": buy_avg,
        "p2p_buy_min": buy_min,
        "p2p_sell_avg": sell_avg,
        "p2p_sell_max": sell_max,
        "bcv_rate": bcv,
        "sample_size": total_sample
    }

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("p2p_raw_ticks").insert(tick_data).execute()
        print("Tick registrado con éxito.")
    except Exception as e:
        # don't crash the whole job; log the error
        print(f"Error inserting to Supabase: {e}")
        # optionally exit non-zero if you want the workflow to fail
        # sys.exit(1)
