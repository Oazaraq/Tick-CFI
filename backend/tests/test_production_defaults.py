"""En production (COOKIE_SECURE=true), l'application refuse de démarrer avec les valeurs publiques du dépôt."""
from app.config import Settings

STRONG = "x" * 40


def test_local_defaults_are_allowed():
    assert Settings(cookie_secure=False).unsafe_defaults() == []


def test_production_refuses_public_defaults():
    unsafe = Settings(cookie_secure=True).unsafe_defaults()
    assert unsafe == ["SECRET_KEY", "ADMIN_PASSWORD"]
    assert Settings(cookie_secure=True, secret_key=STRONG, admin_password="autre", seed_demo=True).unsafe_defaults() == [
        "DEMO_PASSWORD"]


def test_production_with_own_values_starts():
    assert Settings(cookie_secure=True, secret_key=STRONG, admin_password="autre").unsafe_defaults() == []
