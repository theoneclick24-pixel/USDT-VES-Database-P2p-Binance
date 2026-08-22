import sys
import os
import requests as std_requests
from supabase import create_client
from curl_cffi import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip('/')
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

def consultar_binance_directo(trade_type="BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v1/friendly/c2c/ad/search"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Clienttype": "web",
        "Content-Type": "application/json",
        "Origin": "https://p2p.binance.com",
        "Referer": "https://p2p.binance.com/es/trade/sell/USDT?fiat=VES"
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
        r = requests.post(url, json=payload, headers=headers, impersonate="chrome120", timeout=15)
        print(f"Respuesta Binance ({trade_type}): HTTP Status {r.status_code}", flush=True)
        if r.status_code == 200:
            data = r.json().get("data", [])
            precios = [float(item["adv"]["price"]) for item in data if "adv" in item and item["adv"].get("price")]
            print(f"Ofertas procesadas ({trade_type}): {len(precios)}", flush=True)
            return precios
        else:
            print(f"Detalle de respuesta HTTP {r.status_code}: {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"Excepción de conexión ({trade_type}): {e}", flush=True)
        
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
    print("--- Iniciando extracción directa Binance vía curl_cffi ---", flush=True)
    precios_buy = consultar_binance_directo("BUY")
    precios_sell = consultar_binance_directo("SELL")
    bcv = obtener_bcv()

    if not precios_buy or not precios_sell:
        print("Error: No se obtuvieron anuncios de Binance P2P. Omitiendo inserción.", flush=True)
        sys.exit(1)

    buy_avg = sum(precios_buy) / len(precios_buy)
    buy_min = min(precios_buy)
    sell_avg = sum(precios_sell) / len(precios_sell)
    sell_max = max(precios_sell)
    sample_size = len(precios_buy) + len(precios_sell)

    tick_data = {
        "p2p_buy_avg": round(buy_avg, 4),
        "p2p_buy_min": round(buy_min, 4),
        "p2p_sell_avg": round(sell_avg, 4),
        "p2p_sell_max": round(sell_max, 4),
        "bcv_rate": bcv,
        "sample_size": sample_size
    }

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.table("p2p_ticks_binance").insert(tick_data).execute()
        print(f"¡Éxito! {sample_size} registros guardados en p2p_ticks_binance.", flush=True)
    except Exception as e:
        print(f"Error registrando en Supabase: {e}", flush=True)
        sys.exit(1)
