"""Le jeu de démonstration (make seed) passe par les services : il doit respecter les règles en vigueur."""
from sqlalchemy import func, select

from app import seed
from app.models import Action, Project


def test_demo_seed_runs_with_current_rules(db):
    seed.run()
    assert db.scalar(select(func.count()).select_from(Project)) == 5
    assert db.scalar(select(func.count()).select_from(Action)) == 9
