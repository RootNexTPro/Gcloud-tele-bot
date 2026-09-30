# DarkTunnel VLESS Cloud Run Bot

Un bot Telegram complet pour déployer automatiquement des conteneurs VLESS sur Google Cloud Run via des comptes Google Skills Boost.
Dispose d'un système de gestion de quotas, de crédits et de parrainage via SQLite.

## Installation et Déploiement

1. Clonez ce dépôt sur votre serveur (Ubuntu/Debian recommandé).
2. Rendez le script d'installation exécutable :
   ```bash
   chmod +x setup.sh
   ```
3. Exécutez le script d'installation :
   ```bash
   ./setup.sh
   ```
4. Suivez les instructions à l'écran pour saisir votre `BOT_TOKEN` (obtenu via BotFather sur Telegram) et votre `INITIAL_ADMIN_ID` (votre ID utilisateur Telegram).

Le script configurera automatiquement l'environnement virtuel, installera les dépendances (Playwright, etc.), et créera un service systemd (`cloudrun-bot.service`) pour s'assurer que le bot tourne 24h/24.

## Vérification

Pour vérifier les logs du bot :
```bash
journalctl -u cloudrun-bot -f
```

## Structure

* `bot.py` : Point d'entrée du bot.
* `database.py` : Gestion SQLite.
* `keyboards.py` : Menus interactifs en boutons.
* `cloudrun_worker.py` : Moteur Playwright pour interagir avec GCP.
* `vless_helper.py` : Générateur de lien VLESS et QR code.
