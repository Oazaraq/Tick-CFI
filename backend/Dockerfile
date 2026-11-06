FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Migrations à chaque démarrage, puis un seul worker (SQLite + APScheduler, voir DECISIONS.md).
# Par défaut (HOST vide), écoute sur toutes les interfaces en IPv4 et IPv6 : Railway joint le backend
# en IPv6 sur son réseau privé et en IPv4 pour son contrôle de santé (« :: » seul n'écoute qu'en IPv6).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host \"${HOST:-}\" --port 8000 --workers 1"]
