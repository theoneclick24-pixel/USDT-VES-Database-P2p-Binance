import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def obtener_p2p(trade_type="BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v1/friendly/c2c/ad/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "*/*"
    }
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
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        res_json = response.json()
        data = res_json.get("data", [])
        
        if not data:
            print(f"Advertencia: Binance no devolvió datos para {trade_type}")
            return 0.0, 0.0

        prices = [float(item["adv"]["price"]) for item in data if "adv" in item and "price" in item["adv"]]
        
        if not prices:
            return 0.0, 0.0

        avg_price = sum(prices) / len(prices)
        extreme_price = min(prices) if trade_type == "BUY" else max(prices)
        return round(avg_price, 4), round(extreme_price, 4)
    except Exception as e:
        print(f"Error consultando Binance P2P ({trade_type}): {e}")
        return 0.0, 0.0

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
    buy_avg, buy_min = obtener_p2p("BUY")
    sell_avg, sell_max = obtener_p2p("SELL")
    bcv = obtener_bcv()

    # Validar que obtuvimos precios válidos antes de insertar
    if buy_avg > 0 and sell_avg > 0:
        tick_data = {
            "p2p_buy_avg": buy_avg,
            "p2p_buy_min": buy_min,
            "p2p_sell_avg": sell_avg,
            "p2p_sell_max": sell_max,
            "bcv_rate": bcv,
            "sample_size": 10
        }

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("p2p_raw_ticks").insert(tick_data).execute()
        print("Tick registrado con éxito.")
    else:
        print("No se registraron datos en Supabase debido a respuesta vacía de Binance.")
