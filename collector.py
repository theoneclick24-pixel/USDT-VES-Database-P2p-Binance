import sys
import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def obtener_p2p():
    url = "https://criptoya.com/api/binancep2p/usdt/ves/100"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        ask = float(data.get("ask", 0))  # Compra
        bid = float(data.get("bid", 0))  # Venta
        
        if ask > 0 and bid > 0:
            return round(ask, 4), round(ask, 4), round(bid, 4), round(bid, 4), 10
            
    except Exception as e:
        print(f"Error consultando API P2P: {e}")
        
    return 0.0, 0.0, 0.0, 0.0, 0

def obtener_bcv():
    try:
        r = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if r.status_code == 200:
            return round(float(r.json().get("promedio", 0)), 4)
    except Exception:
        pass

    try:
        r = requests.get("https://www.bcv.org.ve", verify=False, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, 'html.parser')
        val_text = soup.find('div', id='dolar').find('strong').text.strip().replace(',', '.')
        return round(float(val_text), 4)
    except Exception as e:
        print(f"Error consultando BCV: {e}")
        return 0.0

if __name__ == "__main__":
    buy_avg, buy_min, sell_avg, sell_max, sample_size = obtener_p2p()
    bcv = obtener_bcv()

    if sample_size == 0 or buy_avg == 0:
        print("No se obtuvieron muestras válidas de P2P. Omitiendo inserción.")
        sys.exit(0)

    tick_data = {
        "p2p_buy_avg": buy_avg,
        "p2p_buy_min": buy_min,
        "p2p_sell_avg": sell_avg,
        "p2p_sell_max": sell_max,
        "bcv_rate": bcv,
        "sample_size": sample_size
    }

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("p2p_raw_ticks").insert(tick_data).execute()
        print("Tick registrado con éxito en Supabase.")
    except Exception as e:
        print(f"Error insertando en Supabase: {e}")
        sys.exit(1)
