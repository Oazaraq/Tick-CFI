# Tick’

Outil interne de pilotage de projets : Kanban de projets, actions, planning (Gantt), comptes-rendus de réunion assistés par IA, alertes email et historique.

## Démarrer

Prérequis : Docker avec Compose (Docker Desktop, ou Rancher Desktop avec le moteur « dockerd »).
Sous Windows, ouvrez le terminal **WSL (Ubuntu)** : `git` et `make` y sont disponibles.

```bash
git clone https://github.com/Oazaraq/Tick-CFI.git && cd Tick-CFI
make up            # équivaut à : docker compose up --build -d
```

| Service | Adresse |
|---|---|
| Application | http://localhost:8080 |
| Documentation de l'API | http://localhost:8080/api/docs |
| Emails captés (Mailpit) | http://localhost:8025 |

Autres commandes : `make test`, `make logs`, `make down`, `make migrate`, `make overdue` (lot 4).

Données de démonstration : `make seed` (après `make up`) crée un compte par rôle (`olivier.zimmer@demo.local` chef de projet, `alice.martin@demo.local` admin, `eric.moreau@demo.local` contributeur, `marie.lefevre@demo.local` lecteur…), tous avec le mot de passe `demo1234`, et des projets dans chaque statut.

Configuration : copiez `.env.example` en `.env` (facultatif en démonstration, **obligatoire en production**). Chaque variable y est commentée : clé secrète et premier administrateur, base, relais SMTP, IA, fichiers déposés, cookie HTTPS.

Sauvegarde : `make backup` (base et fichiers, dans `backups/`) ; restauration : `make restore FILE=backups/…`.

Documentation : [guide utilisateur](docs/guide-utilisateur.md), [installation sur un serveur](docs/installation-serveur.md), [poste Windows de recette](docs/installation-windows.md), [décisions](DECISIONS.md).

## IA des comptes-rendus

Fiche projet, onglet **Réunions** : on importe une transcription (texte ou fichier `.txt` / `.vtt` Teams), l'IA propose un compte-rendu et des actions, rien n'est créé avant validation. Le lien « Charger la transcription de démonstration » permet d'essayer sans fichier.

| `LLM_PROVIDER` | Usage | Où partent les données |
|---|---|---|
| `mock` (défaut) | Démonstration et tests : règles simples, sans IA | Nulle part |
| `anthropic` | Qualité maximale ; renseigner `ANTHROPIC_API_KEY` | Service externe : transcriptions fictives uniquement |
| `local` | Modèle sur votre machine ou votre serveur (Ollama, vLLM) | Restent dans votre infrastructure |

IA locale sur le poste : `make ia-locale` (démarre Ollama et télécharge le modèle, environ 5 Go), puis `LLM_PROVIDER=local` et `LLM_TIMEOUT_SECONDS=600` dans `.env`, et `make up`. Prévoir au moins 8 Go de mémoire libre pour Docker ; sans carte graphique, une analyse prend plusieurs minutes. Sur un serveur vLLM : `LOCAL_LLM_URL=http://<serveur>:8000/v1` et `LOCAL_LLM_MODEL=<modèle servi>`.

## Avancement

| Lot | Contenu | État |
|---|---|---|
| 0 | Fondations | ✅ recetté |
| 1 | Socle : auth, Kanban, actions, historique | ✅ livré |
| 2 | Pilotage : dashboard, mes actions, risques, commentaires, liens, planning | ✅ livré, recette en attente |
| 2bis | J/h par phase, dépendances du planning, réalisation interne / externe | ✅ livré, recette en attente |
| 3 | IA : comptes-rendus de réunion (démonstration, Anthropic, IA locale) | ✅ livré, recette en attente |
| 3bis | Agent de réunion : transcriptions Teams via Microsoft Graph | V2 |
| 4 | Alertes email, journal des emails, tâche des retards, fichiers « en dur » (purge à 30 jours) | ✅ livré, recette en attente |
| 5 | Dashboard graphique, sécurité (CSRF, en-têtes, cookie), sauvegarde, documentation, charte graphique | ✅ livré, recette en attente |

Instance pilote en ligne (Railway, mode serverless ; adresse communiquée par le chef de projet), en service depuis le 05/11/2026 avec une base neuve ; la recette avec données de démonstration se fait sur le poste (`make seed`).
Emails de la recette : captés par Mailpit (accès protégé).
