import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def obtener_proxies():
    """Obtiene una lista actualizada de proxies HTTP públicos."""
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=all"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return [p.strip() for p in r.text.strip().split("\r\n") if p.strip()]
    except Exception:
        pass
    return []

def consultar_binance_p2p(trade_type, lista_proxies):
    """Consulta las primeras 10 órdenes de Binance P2P rotando proxies."""
    url = "https://p2p.binance.com/bapi/c2c/v1/friendly/c2c/ad/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
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

    # Intentar primero conexión directa
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=4)
        if r.status_code == 200 and len(r.json().get("data", [])) > 0:
            return [float(ad["adv"]["price"]) for ad in r.json()["data"]]
    except Exception:
        pass

    # Rotar lista de proxies en caso de bloqueo
    for proxy in lista_proxies[:20]:
        try:
            px = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            r = requests.post(url, json=payload, headers=headers, proxies=px, timeout=4)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return [float(ad["adv"]["price"]) for ad in data]
        except Exception:
            continue

    return []

def obtener_p2p():
    proxies = obtener_proxies()
    
    precios_buy = consultar_binance_p2p("BUY", proxies)
    precios_sell = consultar_binance_p2p("SELL", proxies)

    if precios_buy and precios_sell:
        buy_avg = sum(precios_buy) / len(precios_buy)
        buy_min = min(precios_buy)
        sell_avg = sum(precios_sell) / len(precios_sell)
        sell_max = max(precios_sell)
        return buy_avg, buy_min, sell_avg, sell_max

    return 0.0, 0.0, 0.0, 0.0

def obtener_bcv():
    try:
        r = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if r.status_code == 200:
            return float(r.json().get("promedio", 0))
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
    buy_avg, buy_min, sell_avg, sell_max = obtener_p2p()
    bcv = obtener_bcv()

    if buy_avg > 0 and sell_avg > 0:
        tick_data = {
            "p2p_buy_avg": round(buy_avg, 4),
            "p2p_buy_min": round(buy_min, 4),
            "p2p_sell_avg": round(sell_avg, 4),
            "p2p_sell_max": round(sell_max, 4),
            "bcv_rate": round(bcv, 4),
            "sample_size": 10
        }

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("p2p_raw_ticks").insert(tick_data).execute()
        print("Muestras de Binance P2P registradas con éxito en Supabase.")
    else:
        print("Error: No se lograron obtener las órdenes de Binance P2P.")
