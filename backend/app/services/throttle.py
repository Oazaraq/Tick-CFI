"""Limitation des tentatives (connexion, mot de passe oublié). En mémoire : l'application tourne en un seul
processus ; un redémarrage remet les compteurs à zéro."""
import time
from collections import defaultdict, deque
from threading import Lock


class Throttle:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit, self.window = limit, window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        return hits

    def wait_seconds(self, key: str) -> int:
        """0 si l'action est permise, sinon le nombre de secondes avant la prochaine tentative."""
        with self._lock:
            now = time.monotonic()
            hits = self._recent(key, now)
            return 0 if len(hits) < self.limit else int(hits[0] + self.window - now) + 1

    def hit(self, key: str) -> None:
        with self._lock:
            self._recent(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            self._hits.clear() if key is None else self._hits.pop(key, None)


LOGIN = Throttle(limit=5, window_seconds=15 * 60)  # 5 échecs par identifiant et par quart d'heure
FORGOT = Throttle(limit=3, window_seconds=15 * 60)  # 3 demandes de lien par adresse et par quart d'heure
