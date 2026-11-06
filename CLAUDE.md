# CLAUDE.md – « Tick’ »

Lu en premier par tout assistant de développement.

- **Référence** : DFB v2 (voir `docs/`) ; sa Partie 0 fixe la stack, les conventions et la méthode. Elle prévaut sur toute autre version.
- **Décisions et avenants** : `DECISIONS.md`, à lire avant de coder.
- **Méthode** : un lot à la fois (DFB Partie 7), `make test` vert avant le lot suivant, un commit par lot. Point ambigu : option la plus simple, tracée dans `DECISIONS.md`.
- **Règles d'or** : métier dans `services/` ; droits uniquement via `permissions.py` ; chaque écriture métier passe par un service qui historise et notifie ; code en anglais, interface en français (`frontend/src/i18n/fr.json`).
- **Avancement** : section « Avancement » du `README.md`.
