# Raccourcis Docker Compose. Sous Windows : à lancer dans le terminal WSL (Ubuntu).
.PHONY: up down logs test migrate seed overdue ia-locale backup restore

up:      ## Construit et démarre tout : http://localhost:8080 (emails : http://localhost:8025)
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend

test:    ## Tests backend, dans le conteneur, sur une base temporaire
	docker compose build backend
	docker compose run --rm --no-deps backend pytest -q

migrate:
	docker compose run --rm --no-deps backend alembic upgrade head

seed:    ## Données de démonstration (idempotent)
	docker compose exec backend python -m app.seed

overdue: ## Tâche des retards, exécution manuelle (sinon chaque jour à OVERDUE_JOB_HOUR)
	docker compose exec backend python -m app.jobs.overdue_job

MODEL ?= qwen2.5:7b-instruct
ia-locale: ## IA locale : démarre Ollama et télécharge le modèle (MODEL=… pour un autre) ; puis LLM_PROVIDER=local dans .env et make up
	docker compose --profile ia-locale up -d ollama
	docker compose exec ollama ollama pull $(MODEL)

backup: ## Sauvegarde la base et les fichiers dans ./backups (application en marche) ; à copier hors du serveur
	docker compose exec backend python -m app.backup create /backups

restore: ## Restaure une sauvegarde (efface les données actuelles) : make restore FILE=backups/tickson-….tar.gz
	@test -n "$(FILE)" || (echo "Préciser FILE=backups/tickson-….tar.gz" && exit 1)
	docker compose stop backend
	docker compose run --rm --no-deps backend python -m app.backup restore /backups/$(notdir $(FILE))
	docker compose start backend
