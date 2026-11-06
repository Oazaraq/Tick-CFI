# Installer et recetter l'application sur un PC Windows (en partant de zéro)

Durée : environ 45 minutes, téléchargements compris. Il faut Windows 10 (22H2) ou 11, 8 Go de RAM minimum (16 conseillés), 15 Go libres et les droits administrateur.

> ⚠ Sur un PC personnel, utilisez uniquement les données de démonstration : aucune vraie transcription, aucune clé IA de la société.

## 1. Installer WSL (Linux dans Windows)
1. Menu Démarrer : tapez « PowerShell », clic droit, **Exécuter en tant qu'administrateur**.
2. Tapez `wsl --install` puis Entrée. **Redémarrez** le PC quand c'est demandé.
3. Au redémarrage, la fenêtre **Ubuntu** s'ouvre. Choisissez un nom d'utilisateur et un mot de passe Linux, et notez-les. Le mot de passe ne s'affiche pas pendant la frappe : c'est normal.

Si un message parle de virtualisation, activez-la dans le BIOS (« Intel VT-x » ou « AMD-V / SVM »), puis recommencez.

## 2. Installer Docker
Choisissez selon la licence :
- usage personnel, ou société de **moins de 250 salariés et moins de 10 M$** de chiffre d'affaires : **Docker Desktop** (gratuit) ;
- sinon : **Rancher Desktop** (gratuit dans tous les cas).

**Docker Desktop** : téléchargez-le sur docker.com et installez-le en laissant « Use WSL 2 » coché. Lancez-le et acceptez les conditions ; la connexion à un compte Docker est facultative. Ensuite, dans **Settings → Resources → WSL integration**, activez **Ubuntu**, puis *Apply & restart*.

**Rancher Desktop** : au premier lancement, choisissez le moteur **dockerd (moby)** et décochez Kubernetes. Ensuite, dans **Preferences → WSL**, cochez **Ubuntu**.

Docker doit être **lancé** chaque fois que vous utilisez l'application.

## 3. Préparer Ubuntu
Ouvrez **Ubuntu** depuis le menu Démarrer, puis tapez ces commandes une par une :
```bash
sudo apt update && sudo apt install -y git make gh
docker compose version        # doit afficher un numéro de version
gh auth login                 # choisissez GitHub.com, HTTPS, Login with a web browser
```
`gh auth login` affiche un code : saisissez-le dans le navigateur où vous êtes connecté à GitHub.

## 4. Récupérer et lancer l'application
```bash
cd ~
gh repo clone Oazaraq/Tick-CFI
cd TICKSON
make up                       # premier lancement : 5 à 10 minutes
docker compose ps             # attendu : 3 services en marche, backend « healthy »
```
Restez dans `~`, le disque Linux, et non dans `/mnt/c/…` : c'est nettement plus rapide et ça évite les problèmes de fins de ligne Windows.

## 5. Recette du jalon 0
| # | Vérification | Résultat attendu |
|---|---|---|
| 1 | Ouvrir http://localhost:8080 dans le navigateur Windows | « État de l'API : opérationnelle » |
| 2 | Ouvrir http://localhost:8080/api/docs | La documentation de l'API s'affiche |
| 3 | Ouvrir http://localhost:8025 | L'interface Mailpit s'affiche (vide) |
| 4 | Lancer `make test` dans Ubuntu | La dernière ligne indique `48 passed` |

Pour arrêter : `make down` (les données sont conservées). Pour relancer : `make up`.

## En cas de problème
| Symptôme | Remède |
|---|---|
| `docker: command not found` dans Ubuntu | Docker n'est pas lancé, ou Ubuntu n'est pas coché dans l'intégration WSL (étape 2) |
| `permission denied … docker.sock` | Fermez Ubuntu, tapez `wsl --shutdown` dans PowerShell, relancez Docker puis Ubuntu |
| `port is already allocated` (8080 ou 8025) | Un autre logiciel occupe ce port : signalez-le, je rendrai le port réglable |
| `make up` échoue | Copiez les 20 dernières lignes affichées, ou la sortie de `docker compose logs backend`, et envoyez-les-moi |
