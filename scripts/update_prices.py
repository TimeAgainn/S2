"""
update_prices.py
=================
Version "catalogue étendu" du tracker (façon csgoskins.gg) : interroge Steam
Market + Skinport pour ~200-250 items CS2 (caisses, couteaux, gants, skins
d'armes populaires), écrit prices.json que le frontend statique (index.html)
affiche, et envoie une alerte Telegram si configuré (optionnel).

Pensé pour tourner via GitHub Actions (voir .github/workflows/update-prices.yml),
mais fonctionne identiquement en local : `python3 scripts/update_prices.py`
"""

import re
import requests
import time
import json
import os
import unicodedata
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

STEAM_APPID = 730
STEAM_CURRENCY = 3  # EUR
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "prices.json")
CATALOG_FILE = os.path.join(os.path.dirname(__file__), "..", "catalog.json")
SKINPORT_DUMP_FILE = os.path.join(os.path.dirname(__file__), "..", "skinport_all.json")
MAX_HISTORY_POINTS = 90  # ~1 point par run ; ajuste selon la fréquence du workflow
REQUEST_DELAY = 3  # secondes entre deux appels Steam, pour éviter le rate-limit (429)

WEAR_SUFFIXES = (
    " (Factory New)", " (Minimal Wear)", " (Field-Tested)",
    " (Well-Worn)", " (Battle-Scarred)",
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text


# ============================================================
# CAISSES (actives + discontinuées)
# ============================================================
# status simplifié : "En pool actif" (encore dans le pool de drop) vs
# "Hors pool de drop" (ne tombe plus, mais reste achetable sur le marché).
# Les 4 entrées historiques (breakout/phoenix/recoil/glove) gardent leur
# id et leur blurb d'origine pour ne pas casser l'historique de prix déjà
# généré.

CASES = [
    {"id": "breakout", "name": "Operation Breakout Weapon Case", "display": "Operation Breakout",
     "category": "Caisses", "status": "Gel des drops : déc. 2025",
     "blurb": "Contient le Couteau Papillon. Caisse d'opération discontinuée depuis 2016 ; "
              "offre définitivement figée depuis le gel Valve de décembre 2025."},
    {"id": "phoenix", "name": "Operation Phoenix Weapon Case", "display": "Operation Phoenix",
     "category": "Caisses", "status": "Gel des drops : déc. 2025",
     "blurb": "Contient les 5 couteaux originaux (Karambit, M9 Bayonet, Bayonet, Flip, Gut) "
              "en finitions Fade / Crimson Web / Case Hardened, plus AWP Asiimov et AK-47 Redline."},
    {"id": "recoil", "name": "Recoil Case", "display": "Recoil Case",
     "category": "Caisses", "status": "Sortie du pool actif : mars 2026",
     "blurb": "Partage le pool de gants d'Operation Broken Fang pour une fraction du prix. "
              "Vient tout juste de sortir du pool actif — rareté toute récente."},
    {"id": "glove", "name": "Glove Case", "display": "Glove Case (2016)",
     "category": "Caisses", "status": "Référence",
     "blurb": "La toute première caisse de gants. Sert de point de comparaison : "
              "plus chère que les autres, pas une caisse d'opération."},

    {"id": "case-bravo", "name": "Operation Bravo Case", "display": "Operation Bravo Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse d'opération historique, l'une des plus rares du jeu."},
    {"id": "case-vanguard", "name": "Operation Vanguard Weapon Case", "display": "Operation Vanguard Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse d'opération contenant le Bowie Knife et le Butterfly Knife."},
    {"id": "case-chroma", "name": "Chroma Case", "display": "Chroma Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Première caisse de la série Chroma, gants non inclus (avant leur introduction)."},
    {"id": "case-chroma-2", "name": "Chroma 2 Case", "display": "Chroma 2 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Suite de la série Chroma, skins à finition colorée type Doppler/Gamma."},
    {"id": "case-chroma-3", "name": "Chroma 3 Case", "display": "Chroma 3 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Dernière caisse Chroma avant l'arrivée des gants sur le marché."},
    {"id": "case-falchion", "name": "Falchion Case", "display": "Falchion Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Falchion Knife."},
    {"id": "case-shadow", "name": "Shadow Case", "display": "Shadow Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit les Shadow Daggers."},
    {"id": "case-revolver", "name": "Revolver Case", "display": "Revolver Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Bowie Knife et le R8 Revolver."},
    {"id": "case-gamma", "name": "Gamma Case", "display": "Gamma Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Gamma Doppler et les couteaux finition Ultraviolet."},
    {"id": "case-gamma-2", "name": "Gamma 2 Case", "display": "Gamma 2 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Suite de la série Gamma."},
    {"id": "case-spectrum", "name": "Spectrum Case", "display": "Spectrum Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Première caisse sans vote communautaire, sélection Valve."},
    {"id": "case-spectrum-2", "name": "Spectrum 2 Case", "display": "Spectrum 2 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Suite de la série Spectrum."},
    {"id": "case-hydra", "name": "Operation Hydra Case", "display": "Operation Hydra Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Talon Knife et les Bloodhound Gloves."},
    {"id": "case-clutch", "name": "Clutch Case", "display": "Clutch Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Ursus Knife, votée par la communauté."},
    {"id": "case-horizon", "name": "Horizon Case", "display": "Horizon Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Navaja Knife et les Hand Wraps."},
    {"id": "case-danger-zone", "name": "Danger Zone Case", "display": "Danger Zone Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Nomad Knife, en lien avec le mode Danger Zone."},
    {"id": "case-prisma", "name": "Prisma Case", "display": "Prisma Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse d'entrée de gamme sans nouveau couteau."},
    {"id": "case-prisma-2", "name": "Prisma 2 Case", "display": "Prisma 2 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Suite de la série Prisma."},
    {"id": "case-cs20", "name": "CS20 Case", "display": "CS20 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse anniversaire des 20 ans de la licence Counter-Strike."},
    {"id": "case-shattered-web", "name": "Shattered Web Case", "display": "Shattered Web Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Paracord Knife et le Survival Knife."},
    {"id": "case-fracture", "name": "Fracture Case", "display": "Fracture Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Kukri Knife."},
    {"id": "case-broken-fang", "name": "Operation Broken Fang Case", "display": "Operation Broken Fang Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Skeleton Knife et les Hydra Gloves."},
    {"id": "case-snakebite", "name": "Snakebite Case", "display": "Snakebite Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Thématique infiltration, sans nouveau couteau."},
    {"id": "case-riptide", "name": "Operation Riptide Case", "display": "Operation Riptide Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Dernière caisse liée à une Operation payante."},
    {"id": "case-dreams-nightmares", "name": "Dreams & Nightmares Case", "display": "Dreams & Nightmares Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse à thème onirique, sans nouveau couteau."},
    {"id": "case-revolution", "name": "Revolution Case", "display": "Revolution Case",
     "category": "Caisses", "status": "En pool actif", "blurb": "L'une des caisses les plus récentes encore en circulation active."},
    {"id": "case-kilowatt", "name": "Kilowatt Case", "display": "Kilowatt Case",
     "category": "Caisses", "status": "En pool actif", "blurb": "Caisse récente à thème électrique, encore dans le pool de drop actuel."},
    {"id": "case-esports-2013", "name": "eSports 2013 Case", "display": "eSports 2013 Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Toute première caisse jamais sortie sur CS:GO."},
    {"id": "case-esports-2013-winter", "name": "eSports 2013 Winter Case", "display": "eSports 2013 Winter Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse hivernale historique, très rare."},
    {"id": "case-winter-offensive", "name": "Winter Offensive Weapon Case", "display": "Winter Offensive Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Caisse hivernale contenant le M9 Bayonet."},
    {"id": "case-huntsman", "name": "Huntsman Weapon Case", "display": "Huntsman Weapon Case",
     "category": "Caisses", "status": "Hors pool de drop", "blurb": "Introduit le Huntsman Knife."},
]

# ============================================================
# COUTEAUX (finition Vanilla — référence de prix hors patterns)
# ============================================================

KNIVES = [
    "Karambit", "M9 Bayonet", "Bayonet", "Flip Knife", "Gut Knife",
    "Huntsman Knife", "Falchion Knife", "Bowie Knife", "Butterfly Knife",
    "Shadow Daggers", "Navaja Knife", "Stiletto Knife", "Talon Knife",
    "Ursus Knife", "Classic Knife", "Paracord Knife", "Survival Knife",
    "Nomad Knife", "Skeleton Knife", "Kukri Knife",
]

# ============================================================
# GANTS (finition Vanilla)
# ============================================================

GLOVES = [
    "Sport Gloves", "Driver Gloves", "Specialist Gloves", "Moto Gloves",
    "Hand Wraps", "Bloodhound Gloves", "Hydra Gloves",
]

# ============================================================
# SKINS D'ARMES POPULAIRES (wear par défaut : Field-Tested)
# ============================================================

WEAPON_SKINS = {
    "AK-47": ["Redline", "Asiimov", "Fire Serpent", "Vulcan", "Bloodsport", "Wasteland Rebel",
              "Neon Rider", "Fuel Injector", "Point Disarray", "Case Hardened",
              "Frontside Misty", "The Empress", "Nightwish", "Legion of Anubis", "Jet Set"],
    "M4A4": ["Howl", "Asiimov", "Neo-Noir", "Poseidon", "Dragon King",
             "The Emperor", "Desolate Space", "In Living Color", "Buzz Kill"],
    "M4A1-S": ["Hyper Beast", "Printstream", "Golden Coil", "Icarus Fell",
               "Player Two", "Cyrex", "Knight", "Decimator", "Blue Phosphor"],
    "AWP": ["Dragon Lore", "Asiimov", "Lightning Strike", "Gungnir", "Neo-Noir",
            "Hyper Beast", "Wildfire", "Man-o'-war", "Redline", "Fever Dream",
            "Chromatic Aberration", "Elite Build"],
    "Desert Eagle": ["Blaze", "Printstream", "Code Red", "Kumicho Dragon",
                     "Ocean Drive", "Golden Koi", "Hypnotic", "Mecha Industries"],
    "Glock-18": ["Fade", "Water Elemental", "Neo-Noir", "Bullet Queen", "Moonrise", "Wasteland Rebel"],
    "USP-S": ["Kill Confirmed", "Neo-Noir", "Orion", "Printstream", "Cortex", "Ticket to Hell"],
    "P250": ["Asiimov", "Undertow", "Nuclear Threat", "Mehndi", "Iron Clad"],
    "Five-SeveN": ["Case Hardened", "Hyper Beast", "Monkey Business"],
    "Tec-9": ["Fuel Injector", "Nuclear Threat", "Bamboo Forest"],
    "CZ75-Auto": ["Tigris", "Victoria", "Xiangliu"],
    "P90": ["Asiimov", "Trigon", "Sunset Lily"],
    "MAC-10": ["Neon Rider", "Fade", "Stalker"],
    "MP9": ["Bulldozer", "Hydra", "Starlight Protector"],
    "UMP-45": ["Primal Saber", "Momentum"],
    "Galil AR": ["Chatterbox", "Cerberus", "Sugar Rush"],
    "FAMAS": ["Roll Cage", "Afterimage"],
    "SG 553": ["Integrale", "Tiger Moth"],
    "AUG": ["Chameleon", "Akihabara Accept", "Torque"],
    "SSG 08": ["Dragonfire", "Blood in the Water"],
    "G3SG1": ["Flux", "Orange Crash"],
    "SCAR-20": ["Cardiac", "Bloodsport"],
    "Nova": ["Hyper Beast", "Antique"],
    "XM1014": ["Seasons", "Tranquility"],
    "Sawed-Off": ["Kraken"],
    "MAG-7": ["Cinquedea", "Firestarter"],
    "M249": ["Nebula Crusher", "Emerald Poison Dart"],
    "P2000": ["Ocean Foam", "Fire Elemental"],
    "R8 Revolver": ["Fade", "Amber Fade"],
    "Dual Berettas": ["Cobra Strike", "Melondrama"],
    "MP7": ["Bloodsport", "Nemesis"],
    "MP5-SD": ["Lab Rats", "Phosphor"],
    "PP-Bizon": ["High Roller", "Osiris"],
    "Negev": ["Mjölnir"],
}

DEFAULT_WEAR = "Field-Tested"


def build_items():
    items = list(CASES)

    for name in KNIVES:
        items.append({
            "id": "knife-" + slugify(name),
            "name": f"★ {name}",
            "display": name,
            "category": "Couteaux",
            "status": "Vanilla",
            "blurb": f"Couteau {name}, finition Vanilla (sans pattern spécial) — sert de prix plancher pour ce type de couteau.",
        })

    for name in GLOVES:
        items.append({
            "id": "gloves-" + slugify(name),
            "name": f"★ {name}",
            "display": name,
            "category": "Gants",
            "status": "Vanilla",
            "blurb": f"Gants {name}, finition Vanilla — prix plancher pour ce modèle de gants.",
        })

    for weapon, skins in WEAPON_SKINS.items():
        for skin in skins:
            items.append({
                "id": "skin-" + slugify(f"{weapon}-{skin}"),
                "name": f"{weapon} | {skin} ({DEFAULT_WEAR})",
                "display": f"{weapon} | {skin}",
                "category": "Armes",
                "status": DEFAULT_WEAR,
                "blurb": f"Skin {skin} pour {weapon}, condition {DEFAULT_WEAR}.",
            })

    return items


ITEMS_TO_TRACK = build_items()


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


def base_name(market_hash_name: str) -> str:
    """'StatTrak™ AK-47 | Redline (Field-Tested)' -> 'AK-47 | Redline'"""
    n = market_hash_name
    for prefix in ("StatTrak™ ", "Souvenir ", "★ StatTrak™ "):
        if n.startswith(prefix):
            n = n[len(prefix):]
            if prefix == "★ StatTrak™ ":
                n = "★ " + n
    for suf in WEAR_SUFFIXES:
        if n.endswith(suf):
            return n[:-len(suf)]
    return n


def write_skinport_dump(skinport_data: dict):
    """Écrit skinport_all.json : le prix Skinport de TOUTES les variantes
    (chaque usure + StatTrak/Souvenir) des items présents dans catalog.json.
    C'est ce fichier qui permet d'afficher un prix sur chaque skin du site
    et le tableau de comparaison par usure sur les fiches."""
    if not skinport_data:
        print("[Skinport] Pas de données — skinport_all.json inchangé.")
        return
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[Skinport] catalog.json introuvable — dump non filtré ignoré.")
        return

    wanted = {s["n"] for s in catalog.get("skins", [])}
    wanted |= {c["n"] for c in catalog.get("cases", [])}

    prices = {}
    for name, item in skinport_data.items():
        if base_name(name) not in wanted:
            continue
        p = item.get("min_price")
        if p is not None:
            prices[name] = p

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": "EUR",
        "prices": prices,
    }
    with open(SKINPORT_DUMP_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)
    print(f"skinport_all.json écrit ({len(prices)} variantes d'items).")


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
    write_skinport_dump(skinport_data)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    output_items = []

    print(f"{len(ITEMS_TO_TRACK)} items à traiter...")

    for item in ITEMS_TO_TRACK:
        steam = get_steam_price(item["name"])
        time.sleep(REQUEST_DELAY)
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
            "category": item.get("category", ""),
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
