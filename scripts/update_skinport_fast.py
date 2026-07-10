"""
update_skinport_fast.py
========================
Version "rapide" : uniquement le dump Skinport (1 appel API pour tout le
marché) + l'historique. Pas d'appels Steam item par item, donc s'exécute en
quelques secondes — pensé pour tourner toutes les 15 minutes via
.github/workflows/update-skinport.yml, alors que update_prices.py (Steam,
~20 min) reste sur son cron 6h.
"""

import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "update_prices", os.path.join(os.path.dirname(__file__), "update_prices.py"))
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)

if __name__ == "__main__":
    data = _m.get_skinport_prices()
    _m.write_skinport_dump(data)
    _m.update_skinport_history(data)
