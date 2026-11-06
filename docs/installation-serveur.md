# Installation sur un serveur (datacenter)

Le même code tourne du poste de recette au serveur : seule la configuration (`.env`) change. La base de production démarre vide ; aucune donnée de recette n'y est copiée.

## 1. Prérequis

- VM Linux 64 bits (Debian, Ubuntu ou RHEL) : 2 vCPU, 4 Go de mémoire, 20 Go de disque.
  - L'IA locale demande un serveur avec carte graphique, ou au moins 16 Go de mémoire (voir l'étape 7).
- Docker Engine et le greffon Docker Compose, `git`, `make`.
- Un nom DNS interne (ex. `tickson.mondomaine.local`) et le proxy HTTPS du datacenter, qui relaiera vers le port 8080 de la VM.
- Un relais SMTP interne (de préférence autorisé par adresse IP, sans mot de passe).

## 2. Installation

```bash
git clone https://github.com/Oazaraq/Tick-CFI.git && cd Tick-CFI
cp .env.example .env
```

## 3. Configuration (`.env`)

| Variable | Valeur en production |
|---|---|
| `SECRET_KEY` | longue chaîne aléatoire : `openssl rand -hex 32` (ne jamais la changer ensuite : elle déconnecterait tout le monde) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FIRST_NAME`, `ADMIN_LAST_NAME` | premier administrateur, créé au premier démarrage d'une base vide ; `ADMIN_EMAIL` peut être un simple identifiant (ex. `admin`) ; changez le mot de passe après la première connexion |
| `INITIAL_USERS` | facultatif : comptes à créer au démarrage, en JSON (`[{"email": …, "first_name": …, "last_name": …, "role": "project_manager"}]`) ; chacun reçoit un lien pour choisir son mot de passe |
| `APP_BASE_URL` | adresse publique, ex. `https://tickson.mondomaine.local` (liens des emails) |
| `COOKIE_SECURE` | `true` (application servie en HTTPS) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` | relais interne, ex. `smtp.mondomaine.local`, `25`, `tickson@mondomaine.fr` |
| `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASSWORD` | `none` pour un relais par adresse IP ; sinon `starttls` (587) ou `ssl` (465) avec identifiants |
| `SMTP_TEST_RECIPIENT` | vide en production (sinon tous les emails partent vers cette adresse) |
| `LLM_PROVIDER` | `local` (IA dans le datacenter, étape 7) ou `mock` en attendant |
| `SEED_DEMO` | absent ou `false` : jamais de données de démonstration en production |

Les autres variables gardent leurs valeurs par défaut (voir `.env.example`). Le fichier `.env` contient des secrets : droits `600`, jamais dans Git.

## 4. Démarrage

```bash
make up          # construit et démarre ; les migrations de la base s'appliquent seules
make logs        # suivi des journaux (Ctrl+C pour quitter)
```

- Contrôle de santé : `curl http://localhost:8080/api/health` doit renvoyer `{"status":"ok"}`.
- Mailpit (capture des emails de développement) n'est pas utile en production : `docker compose stop mailpit`. Il ne reçoit rien tant que `SMTP_HOST` pointe vers le relais.

## 5. HTTPS

Le proxy HTTPS du datacenter relaie `https://tickson.mondomaine.local` vers `http://<VM>:8080`, en transmettant les en-têtes `Host` et `X-Forwarded-Proto`. Avec `COOKIE_SECURE=true`, la connexion ne fonctionne plus qu'en HTTPS : c'est voulu.

## 6. Sauvegardes et restauration

- `make backup` crée `backups/tickson-AAAAMMJJ-HHMMSS.tar.gz` (base et fichiers déposés), application en marche.
- Planifiez-la chaque nuit et copiez le dossier `backups/` vers le stockage de sauvegarde du datacenter, par exemple :

  ```cron
  0 2 * * * cd /opt/TICKSON && make backup && find backups -name 'tickson-*.tar.gz' -mtime +30 -delete
  ```

- Restauration, qui remplace toutes les données actuelles : `make restore FILE=backups/tickson-AAAAMMJJ-HHMMSS.tar.gz`. Le backend est arrêté pendant l'opération.
- À tester une fois par trimestre sur une VM de recette.

## 7. IA locale (comptes-rendus de réunion)

Les transcriptions ne quittent pas le datacenter.

- **Serveur vLLM existant** : `LLM_PROVIDER=local`, `LOCAL_LLM_URL=http://<serveur>:8000/v1`, `LOCAL_LLM_MODEL=<nom du modèle servi>`, puis `make up`.
- **Ollama sur la VM** : `make ia-locale` (`MODEL=…` pour un autre modèle que celui par défaut), puis `LLM_PROVIDER=local` dans `.env` et `make up`. Sans carte graphique, augmentez `LLM_TIMEOUT_SECONDS` (600 ou plus).

## 8. Mise à jour

```bash
git pull && make up      # reconstruit, applique les migrations, redémarre
```

Faites un `make backup` juste avant.

## 9. Exploitation

- Tâches planifiées, intégrées au backend : alerte des retards chaque jour à `OVERDUE_JOB_HOUR` (8 h) et purge des fichiers des projets livrés depuis 30 jours (3 h 30). Une tâche manquée est rattrapée au redémarrage. Exécution manuelle de l'alerte des retards : `make overdue`.
- Journal des emails : menu **Emails** (administrateur).
- Un seul processus backend (`--workers 1`) : c'est voulu, les tâches planifiées ne doivent tourner qu'une fois.
