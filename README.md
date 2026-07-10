# CS2 Price Tracker — Site public

Base de données + tracker de prix CS2 : ~2100 skins, 42 caisses et 94
collections avec images officielles (CDN Steam), pages par catégorie / arme /
collection, fiches détaillées avec effet d'inspection 3D, et suivi de prix
Steam Market & Skinport (~190 items suivis, mis à jour toutes les 6h par
GitHub Actions).

**Structure :**
```
index.html                          → SPA à routing par hash (toutes les pages)
catalog.json                        → catalogue complet skins/caisses/collections + images
prices.json                         → prix suivis (regénéré automatiquement toutes les 6h)
scripts/update_prices.py            → script de récupération des prix
scripts/build_catalog.py            → régénération du catalogue (source : ByMykel/CSGO-API)
.github/workflows/update-prices.yml → cron prix (6h)
.github/workflows/update-catalog.yml→ cron catalogue (hebdo)
```

**Pages du site** (routing par hash, compatible GitHub Pages) :
`#/` accueil · `#/caisses` · `#/cat/<catégorie>` · `#/arme/<arme>` ·
`#/collections` · `#/collection/<nom>` · `#/item/<id>` (fiche avec inspection
3D, float range, liens Steam par usure) · `#/recherche/<texte>`.

**Images & données catalogue** : API communautaire
[ByMykel/CSGO-API](https://github.com/ByMykel/CSGO-API), images © Valve
servies par le CDN Steam. Le site n'est pas affilié à Valve.

---

## Déploiement en 10 minutes

### 1. Créer le dépôt
Sur GitHub : **New repository** → nomme-le comme tu veux (ex. `cs2-tracker`) →
mets tous les fichiers de ce projet dedans (via l'interface web "upload files",
ou en local avec `git init && git add . && git commit -m "init" && git push`).

### 2. Activer GitHub Pages
Dans le dépôt : **Settings → Pages → Source : Deploy from a branch → Branch : main / (root)**.
Ton site sera en ligne en 1-2 minutes à une adresse du type
`https://ton-pseudo.github.io/cs2-tracker/`.

### 3. Vérifier que le workflow tourne
Onglet **Actions** du dépôt → tu dois voir "Update CS2 prices" → clique
**Run workflow** pour le lancer une première fois manuellement plutôt que
d'attendre le prochain créneau de 6h. Avec ~190 items et 3s de délai entre
deux appels Steam, un run complet prend 15-20 minutes.

### 4. (Optionnel) Garder les alertes Telegram
Si tu veux que ce même script t'envoie aussi des alertes Telegram (comme le
bot précédent) : **Settings → Secrets and variables → Actions → New repository
secret**, ajoute `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`. Sans ça, le script
tourne quand même très bien, il ignore juste l'envoi Telegram.

### 5. (Optionnel) Domaine personnalisé
Une fois que tu as un nom de domaine (Namecheap, OVH...), **Settings → Pages →
Custom domain**, et suis les instructions DNS affichées.

---

## Modifier ce qui est suivi

Ouvre `scripts/update_prices.py`, la liste `ITEMS_TO_TRACK` en haut du fichier.
Chaque entrée a besoin d'un `id` (unique, utilisé en interne), du `name` exact
Steam Market, d'un `display` (nom affiché), d'un `status` et d'un `blurb`
(le texte descriptif affiché sous le nom — c'est ce genre de contenu écrit,
répété sur plusieurs pages, qui aide au référencement Google).

Après une modification du script, le push sur `main` déclenche automatiquement
une exécution immédiate (en plus du cron toutes les 6h) grâce au `push:` dans
le workflow.

Les items sont regroupés par `category` (`Caisses`, `Couteaux`, `Gants`,
`Armes`) — c'est ce champ qui alimente les filtres sur la page. Pour ajouter
un nouveau skin d'arme, ajoute simplement une entrée dans le dict
`WEAPON_SKINS` du script.

## Activer les publicités (AdSense)

Le site a deux emplacements pub prêts (`#ad-slot-top` et `#ad-slot-bottom`
dans `index.html`), vides par défaut. Une fois ta candidature Google AdSense
approuvée :

1. Dans AdSense, crée une unité publicitaire et récupère le snippet
   `<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXX">`
   → colle-le dans `<head>` de `index.html`.
2. Remplace le contenu de `#ad-slot-top` / `#ad-slot-bottom` par le bloc
   `<ins class="adsbygoogle">...</ins>` fourni par AdSense, suivi de
   `<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>`.
3. Édite `ads.txt` à la racine du repo : remplace le commentaire par la
   ligne exacte donnée dans AdSense → Sites → "ads.txt" (contient ton
   vrai `pub-XXXXXXXXXXXXXXXX`). Sans ce fichier correct, AdSense refuse
   de servir des annonces sur le domaine.

## Prochaines étapes réalistes

- **Contenu** : une page par caisse (historique, contexte, comparaisons) plutôt
  que tout sur une seule page — c'est ce qui fait venir le trafic de recherche,
  pas le design.
- **AdSense** : candidater une fois qu'il y a du contenu réel et un peu
  d'ancienneté (voir la discussion sur les délais réalistes).
- **Vercel/Netlify** au lieu de GitHub Pages si tu veux un déploiement un peu
  plus flexible (preview par branche, redirections faciles) — le repo
  fonctionne tel quel avec les deux, il suffit de le connecter depuis leur
  interface, aucune modification de code nécessaire.
