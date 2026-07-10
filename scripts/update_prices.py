"""
update_prices.py
=================
Version "site public" du tracker : interroge Steam Market + Skinport,
écrit un fichier prices.json que le frontend statique (index.html) affiche,
et envoie une alerte Telegram si configuré (optionnel — le script fonctionne
très bien sans, pour l'usage "site" seul).

Pensé pour tourner via GitHub Actions (voir .github/workflows/update-prices.yml),
mais fonctionne identiquement en local : `python3 scripts/update_prices.py`
"""

import requests
import time
import json
import os
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

ITEMS_TO_TRACK = [
    {
        "id": "breakout",
        "name": "Operation Breakout Weapon Case",
        "display": "Operation Breakout",
        "status": "Gel des drops : déc. 2025",
        "blurb": "Contient le Couteau Papillon. Caisse d'opération discontinuée depuis 2016 ; "
                 "offre définitivement figée depuis le gel Valve de décembre 2025.",
    },
    {
        "id": "phoenix",
        "name": "Operation Phoenix Weapon Case",
        "display": "Operation Phoenix",
        "status": "Gel des drops : déc. 2025",
        "blurb": "Contient les 5 couteaux originaux (Karambit, M9 Bayonet, Bayonet, Flip, Gut) "
                 "en finitions Fade / Crimson Web / Case Hardened, plus AWP Asiimov et AK-47 Redline.",
    },
    {
        "id": "recoil",
        "name": "Recoil Case",
        "display": "Recoil Case",
        "status": "Sortie du pool actif : mars 2026",
        "blurb": "Partage le pool de gants d'Operation Broken Fang pour une fraction du prix. "
                 "Vient tout juste de sortir du pool actif — rareté toute récente.",
    },
    {
        "id": "glove",
        "name": "Glove Case",
        "display": "Glove Case (2016)",
        "status": "Référence",
        "blurb": "La toute première caisse de gants. Sert de point de comparaison : "
                 "plus chère que les autres, pas une caisse d'opération.",
    },
]

STEAM_APPID = 730
STEAM_CURRENCY = 3  # EUR
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "prices.json")
MAX_HISTORY_POINTS = 90  # ~1 point par run ; ajuste selon la fréquence du workflow

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# ============================================================
# STEAM
# ============================================================

def get_steam_price(market_hash_name: str):
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {"appid": STEAM_APPID, "currency": STEAM_CURRENCY, "market_hash_name": market_hash_name}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 429:
            print("[Steam] Rate limited (429).")
            return None
        data = r.json()
        if not data.get("success"):
            return None

        def _clean(v):
            if not v:
                return None
            v = v.strip()
            for sym in ("€", "$", "£"):
                v = v.replace(sym, "")
            v = v.strip().replace(".", "").replace(",", ".")
            try:
                return float(v)
            except ValueError:
                return None

        return {"lowest": _clean(data.get("lowest_price")), "median": _clean(data.get("median_price")),
                "volume": data.get("volume")}
    except Exception as e:
        print(f"[Steam] Erreur pour '{market_hash_name}': {e}")
        return None


# ============================================================
# SKINPORT
# ============================================================

def get_skinport_prices():
    url = "https://api.skinport.com/v1/items"
    params = {"app_id": STEAM_APPID, "currency": "EUR", "tradable": 0}
    headers = {"Accept-Encoding": "br", "Accept": "application/json"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"[Skinport] HTTP {r.status_code} — voir README (Cloudflare).")
            return {}
        items = r.json()
        return {item["market_hash_name"]: item for item in items}
    except Exception as e:
        print(f"[Skinport] Erreur : {e}")
        return {}


# ============================================================
# TELEGRAM (optionnel)
# ============================================================

def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # non configuré, on ignore silencieusement
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"[Telegram] Erreur : {e}")


# ============================================================
# GÉNÉRATION DU prices.json
# ============================================================

def load_existing():
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def main():
    existing = load_existing()
    existing_items = {it["id"]: it for it in existing.get("items", [])}

    skinport_data = get_skinport_prices()
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    output_items = []

    for item in ITEMS_TO_TRACK:
        steam = get_steam_price(item["name"])
        time.sleep(3)
        skinport = skinport_data.get(item["name"])

        current_price = None
        if steam and steam["lowest"]:
            current_price = steam["lowest"]
        elif skinport and skinport.get("min_price"):
            current_price = skinport["min_price"]

        prev = existing_items.get(item["id"], {})
        history = prev.get("history", [])
        if current_price is not None:
            history.append({"t": now_iso, "p": current_price})
            history = history[-MAX_HISTORY_POINTS:]

        record = {
            "id": item["id"],
            "name": item["name"],
            "display": item["display"],
            "status": item["status"],
            "blurb": item["blurb"],
            "steam_price": steam["lowest"] if steam else None,
            "steam_volume": steam.get("volume") if steam else None,
            "skinport_price": skinport.get("min_price") if skinport else None,
            "last_checked": now_iso,
            "history": history,
        }
        output_items.append(record)
        print(f"[{item['display']}] steam={record['steam_price']} skinport={record['skinport_price']}")

    output = {"generated_at": now_iso, "items": output_items}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"prices.json écrit ({len(output_items)} items).")


if __name__ == "__main__":
    main()
