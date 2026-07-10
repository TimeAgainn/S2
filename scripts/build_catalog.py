"""
build_catalog.py
=================
Génère catalog.json à partir de l'API communautaire ByMykel/CSGO-API
(https://github.com/ByMykel/CSGO-API) : la liste complète des skins,
couteaux, gants et caisses CS2 avec leurs images officielles (CDN Steam),
raretés, collections et float ranges.

À lancer une fois de temps en temps (nouvelle caisse / nouvelle collection),
pas à chaque run de prix : `python3 scripts/build_catalog.py`
Le workflow .github/workflows/update-catalog.yml le fait aussi chaque semaine.
"""

import json
import os

import requests

BASE = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "catalog.json")

# Traductions des catégories de l'API (en anglais) vers ce qu'affiche le site.
CATEGORY_FR = {
    "Rifles": "Fusils",
    "Pistols": "Pistolets",
    "SMGs": "Mitraillettes",
    "Heavy": "Armes lourdes",
    "Knives": "Couteaux",
    "Gloves": "Gants",
    "Equipment": "Équipement",
}


def fetch(path):
    r = requests.get(f"{BASE}/{path}", timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    print("Téléchargement skins.json ...")
    skins_raw = fetch("skins.json")
    print(f"  {len(skins_raw)} skins")
    print("Téléchargement crates.json ...")
    crates_raw = fetch("crates.json")
    print(f"  {len(crates_raw)} crates (tous types)")

    collections = {}  # name -> image

    skins = []
    for s in skins_raw:
        cat_en = s.get("category", {}).get("name", "")
        cat = CATEGORY_FR.get(cat_en, cat_en)
        col_names = []
        for col in s.get("collections") or []:
            col_names.append(col["name"])
            collections.setdefault(col["name"], col.get("image"))
        crate_names = [c["name"] for c in (s.get("crates") or [])]
        rarity = s.get("rarity") or {}
        skins.append({
            "i": s["id"],
            "n": s["name"],                      # nom marché sans wear, ex. "AK-47 | Redline"
            "w": s.get("weapon", {}).get("name", ""),
            "c": cat,
            "r": rarity.get("name", ""),
            "rc": rarity.get("color", "#7A8290"),
            "col": col_names,
            "cr": crate_names,
            "img": s.get("image", ""),
            "f0": s.get("min_float"),
            "f1": s.get("max_float"),
            "st": bool(s.get("stattrak")),
        })

    cases = []
    for c in crates_raw:
        if c.get("type") != "Case":
            continue
        cases.append({
            "i": c["id"],
            "n": c["name"],
            "img": c.get("image", ""),
            "d": c.get("first_sale_date") or "",
        })
    cases.sort(key=lambda x: x["d"] or "9999")

    output = {
        "skins": skins,
        "cases": cases,
        "collections": [{"n": k, "img": v} for k, v in sorted(collections.items())],
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)

    size_mb = os.path.getsize(OUTPUT_FILE) / 1e6
    print(f"catalog.json écrit : {len(skins)} skins, {len(cases)} caisses, "
          f"{len(collections)} collections ({size_mb:.1f} Mo)")


if __name__ == "__main__":
    main()
