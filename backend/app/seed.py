"""Jeu de démonstration (`make seed`) : un compte par rôle, des projets dans chaque statut, des actions variées
(dont en retard), risques, planning, commentaire et lien. Dates relatives au jour du lancement. Idempotent."""
from datetime import timedelta

from sqlalchemy import select

from app import clock
from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.schemas import ActionCreate, LinkIn, PlanningIn, ProjectCreate, RiskIn, UserCreate
from app.services import actions, comments, links, planning, projects, risks, users

PASSWORD = settings.demo_password  # « demo1234 » en local ; aléatoire sur un environnement public
PEOPLE = {  # clé : (email, prénom, nom, rôle)
    "olivier": ("olivier.zimmer@demo.local", "Olivier", "Zimmer", "project_manager"),
    "alice": ("alice.martin@demo.local", "Alice", "Martin", "admin"),
    "eric": ("eric.moreau@demo.local", "Eric", "Moreau", "contributor"),
    "marie": ("marie.durand@demo.local", "Marie", "Durand", "contributor"),
    "marie_l": ("marie.lefevre@demo.local", "Marie", "Lefèvre", "reader"),
    "paul": ("paul.bernard@demo.local", "Paul", "Bernard", "contributor"),
}


def run() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == PEOPLE["olivier"][0])):
            print("Le jeu de démonstration est déjà présent.")
            return
        u = {key: users.create_user(db, UserCreate(email=e, first_name=f, last_name=n, role=r, password=PASSWORD))
             for key, (e, f, n, r) in PEOPLE.items()}
        cp = u["olivier"]

        def day(n: int):
            return clock.today() + timedelta(days=n)

        def project(title: str, owner: User, **fields):
            return projects.create_project(db, cp, ProjectCreate(title=title, owner_id=owner.id, **fields))

        def action(p, title, who=None, due=None, priority="medium", status="todo"):
            return actions.create_action(db, cp, p, ActionCreate(title=title, assignee_id=who.id if who else None,
                                                                 due_date=due, priority=priority, status=status))

        net = project("Migration Réseau Site A", cp, status_code="in_progress", priority="high",
                      member_ids=[u["eric"].id, u["marie"].id], start_date=day(-20), due_date=day(40),
                      description="Remplacement des commutateurs et du cœur de réseau du site A.")
        erp = project("Mise à jour ERP", u["eric"], status_code="in_progress",  # compartimentage : l'équipe porte les actions
                      member_ids=[cp.id, u["marie"].id, u["paul"].id],
                      start_date=day(-60), due_date=day(15))
        project("Refonte intranet", u["marie"], due_date=day(90))
        project("Déploiement Wi-Fi entrepôt", u["eric"], status_code="blocked", priority="critical",
                blocked_reason="Attente du devis opérateur")
        project("Audit sécurité", cp, status_code="done", start_date=day(-90))

        action(net, "Préparer planning", cp, day(2), "high")
        action(net, "Commander matériel", u["eric"], day(-2), "critical")
        action(net, "Valider architecture")
        action(net, "Réaliser recette", u["marie"], day(5))
        action(net, "Rédiger le cahier des charges", cp, day(-15), status="done")
        action(erp, "Tester la montée de version", u["eric"], day(-1), "high")
        action(erp, "Former les utilisateurs", u["marie"], day(10))
        action(erp, "Mettre à jour la documentation", u["paul"], day(20))
        u["paul"].is_active = False  # alimente la zone « responsable inactif » du dashboard
        db.commit()

        risks.create_risk(db, cp, net, RiskIn(title="Retard de livraison du matériel", probability="high", impact="medium",
                                              owner_id=u["eric"].id, mitigation="Commande anticipée, fournisseur de secours"))
        risks.create_risk(db, cp, net, RiskIn(title="Coupure réseau pendant la bascule", probability="medium", impact="high"))
        steps: dict = {}
        for label, kind, start, end, category, sold, consumed, after in [
            ("Étude et cadrage", "phase", -20, -6, "project_management", 5, 6, None),  # dépassement : barre orange
            ("Commande et livraison", "phase", -5, 10, "infrastructure", 3, 1.5, "Étude et cadrage"),
            ("Déploiement", "phase", 11, 30, "network", 12, 0, "Commande et livraison"),
            ("Mise en service", "milestone", 32, 32, None, None, None, "Déploiement"),
            ("Recette et garantie", "phase", 33, 40, "security", 4, 0, "Mise en service"),
        ]:
            steps[label] = planning.create_item(db, cp, net, PlanningIn(
                label=label, kind=kind, start_date=day(start), end_date=day(end), category=category,
                days_sold=sold, days_consumed=consumed, predecessor_ids=[steps[after].id] if after else []))
        actions.create_action(db, cp, net, ActionCreate(title="Câbler la baie réseau", assignee_id=u["eric"].id,
                                                        due_date=day(12), sourcing="external", subcontractor="Câblo SA"))
        comments.add_comment(db, u["eric"], net, "Le fournisseur annonce une livraison partielle la semaine prochaine.")
        links.add_link(db, cp, net, LinkIn(label="Schéma d'architecture", url="https://intranet.example/reseau-site-a"))

        shown = PASSWORD if PASSWORD == "demo1234" else "valeur de DEMO_PASSWORD"
        print(f"Jeu de démonstration créé. Mot de passe des comptes : {shown}")
        for email, first, last, role in PEOPLE.values():
            print(f"  {email:30} {first} {last} ({role})")


if __name__ == "__main__":
    run()
    from app.services import notifications
    notifications.flush()  # les alertes des données de démonstration partent avant la fin de la commande
