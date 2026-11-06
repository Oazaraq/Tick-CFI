from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import SessionLocal
from app.permissions import Forbidden
from app.security import COOKIE
from app.jobs import scheduler
from app.routers import (actions, auth, comments, dashboard, emails, files, health, links, meetings, planning,
                         projects, risks, statuses, users)
from app.services import meetings as meetings_service
from app.services import notifications
from app.services import users as users_service
from app.services.errors import ServiceError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    unsafe = settings.unsafe_defaults()
    if unsafe:  # en production (HTTPS), les valeurs publiques du dépôt ne doivent jamais servir
        raise RuntimeError("Démarrage refusé : valeurs par défaut à remplacer dans l'environnement : " + ", ".join(unsafe))
    with SessionLocal() as db:
        users_service.ensure_admin(db)
        for user in users_service.bootstrap_users(db):  # INITIAL_USERS : lien d'activation envoyé
            notifications.send_password_link(user, users_service.password_link(user), invitation=True)
        meetings_service.recover_interrupted(db)
    if settings.seed_demo:  # environnement de démonstration uniquement (idempotent)
        from app import seed
        seed.run()
    scheduler.start()  # retards (OVERDUE_JOB_HOUR) et purge des fichiers, avec rattrapage au démarrage
    yield
    scheduler.shutdown()


app = FastAPI(title="Tick’", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)

for module in (health, auth, users, statuses, projects, actions, dashboard, risks, comments, links, planning, meetings,
               files, emails):
    app.include_router(module.router, prefix="/api")


CSRF_HEADER, CSRF_VALUE = "x-requested-with", "tickson"


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """Protection CSRF, en plus du cookie SameSite=Lax : toute écriture accompagnée du cookie de session doit porter
    l'en-tête X-Requested-With, qu'un autre site ne peut pas poser sans autorisation CORS (jamais accordée)."""
    if (request.method not in ("GET", "HEAD", "OPTIONS") and COOKIE in request.cookies
            and request.headers.get(CSRF_HEADER) != CSRF_VALUE):
        return JSONResponse({"detail": "Requête refusée (protection CSRF) : rechargez la page, l'application a été mise à jour."}, status_code=403)
    return await call_next(request)


@app.exception_handler(ServiceError)
async def service_error(_request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse({"detail": exc.message, **exc.extra}, status_code=exc.status_code)


@app.exception_handler(Forbidden)
async def forbidden(_request: Request, _exc: Forbidden) -> JSONResponse:
    return JSONResponse({"detail": "Droits insuffisants"}, status_code=403)
