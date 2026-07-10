# CS2 Price Tracker — Site public

Site statique qui affiche le prix de caisses CS2 discontinuées, mis à jour
automatiquement toutes les 4h par un workflow GitHub Actions.

**Structure :**
```
index.html                        → la page (lit prices.json)
prices.json                       → les données affichées (regénéré automatiquement)
scripts/update_prices.py          → le script qui va chercher les prix
.github/workflows/update-prices.yml → l'automatisation
```

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
d'attendre le prochain créneau de 4h.

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
une exécution immédiate (en plus du cron toutes les 4h) grâce au `push:` dans
le workflow.

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
