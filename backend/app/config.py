"""Configuration par variables d'environnement (voir .env.example)."""
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_TZ = ZoneInfo("Europe/Paris")  # fuseau d'affichage et de la « date du jour » (RG05)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-secret-change-me"
    database_url: str = "sqlite:///./data/pilotage.db"
    admin_email: str = "admin@pilotage.local"  # email ou simple identifiant de connexion (ex. « admin »)
    admin_password: str = "admin1234"
    admin_first_name: str = "Admin"
    admin_last_name: str = "Tick’"
    # Comptes créés au démarrage s'ils n'existent pas (JSON) : [{"email", "first_name", "last_name", "role"}].
    # Sans mot de passe : un lien pour le définir leur est envoyé.
    initial_users: list[dict] = []
    password_link_hours: int = 72  # validité des liens d'activation et de réinitialisation
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "pilotage@pilotage.local"
    smtp_security: Literal["none", "starttls", "ssl"] = "none"  # none : Mailpit ou relais interne
    smtp_test_recipient: str = ""
    scheduler_enabled: bool = True  # tâches planifiées (retards, purge des fichiers)
    files_dir: str = "./data/files"  # fichiers déposés (lot 4), dans le volume en Docker
    files_purge_days: int = 30  # purge des fichiers N jours après le passage en « Livré »
    max_upload_mb: int = 10
    cookie_secure: bool = False  # true derrière HTTPS (production, Railway)
    app_base_url: str = "http://localhost:8080"
    # IA (lot 3) : mock (démonstration), anthropic (API), local (Ollama, vLLM : API compatible OpenAI)
    llm_provider: Literal["mock", "anthropic", "local"] = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    local_llm_url: str = "http://ollama:11434/v1"
    local_llm_model: str = "qwen2.5:7b-instruct"
    llm_timeout_seconds: int = 120  # par appel ; à augmenter pour un modèle local sans GPU
    llm_chunk_chars: int = 12000  # au-delà, la transcription est découpée en blocs analysés séparément
    due_soon_days: int = 7
    overdue_job_hour: int = 8
    done_hide_days: int = 30
    # Environnements de démonstration (Railway) : jeu de démo créé au démarrage, mot de passe non public
    seed_demo: bool = False
    demo_password: str = "demo1234"

    def unsafe_defaults(self) -> list[str]:
        """Variables restées à leur valeur de développement (publique dans le dépôt) alors que COOKIE_SECURE=true."""
        if not self.cookie_secure:
            return []
        unsafe = [name for name, value, default in (("SECRET_KEY", self.secret_key, "dev-secret-change-me"),
                                                    ("ADMIN_PASSWORD", self.admin_password, "admin1234"))
                  if value == default]
        if self.seed_demo and self.demo_password == "demo1234":
            unsafe.append("DEMO_PASSWORD")
        return unsafe


settings = Settings()
