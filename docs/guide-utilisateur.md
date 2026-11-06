# Guide utilisateur – Tick’

Une section par écran. Les boutons affichés dépendent de votre rôle : **Administrateur**, **Chef de projet**, **Contributeur** ou **Lecteur** (consultation seule).

**Qui voit quoi** : vous ne voyez que les projets dont vous êtes responsable ou participant, avec leurs actions, risques, fichiers et emails. L'administrateur voit tous les projets. Pour donner accès à un projet, ajoutez la personne aux participants.

## Connexion et compte

- Connectez-vous avec votre adresse email (ou votre identifiant) et votre mot de passe. La session dure 7 jours. Après 5 échecs, la connexion est bloquée 15 minutes.
- **Mot de passe oublié ?** sur l'écran de connexion : un lien pour choisir un nouveau mot de passe est envoyé par email (valable 72 heures, une seule utilisation). Un nouveau compte reçoit le même type de lien pour choisir son premier mot de passe.
- Menu à votre nom, en haut à droite :
  - **Recevoir les alertes email** : décochez pour ne plus recevoir d'emails (vous ne recevez jamais d'email pour vos propres actions) ;
  - **Changer le mot de passe** : déconnecte vos autres sessions ;
  - **Déconnexion**.

## Dashboard

- **Tuiles** : projets actifs, actions ouvertes, actions en retard, projets bloqués, mes actions. Un clic ouvre la liste correspondante.
- **État du jour** : quatre graphiques ; « Voir les données » affiche les valeurs en tableau.
  - Projets par statut, en barres ou en répartition.
  - Actions ouvertes par priorité.
  - Actions en retard par projet : un clic ouvre le projet.
  - Charge des projets non livrés : j/h vendus et consommés, en nuage de points ou en barres. Un point au-dessus de la diagonale signale un projet qui a consommé plus que vendu.
- **Zones d'alerte** : échéances proches, projets bloqués, actions sans responsable, responsable inactif. On peut réaffecter directement depuis la zone.
- **Tous / Mes projets** (administrateur) limite l'ensemble à vos projets (responsable ou participant).

## Projets (Kanban et liste)

- Quatre colonnes : Avant-vente, En cours, Bloqué, Livré. Glissez une carte pour changer son statut :
  - Bloqué demande un motif ;
  - Livré demande une confirmation s'il reste des actions ouvertes ;
  - la colonne Livré masque les projets livrés depuis plus de 30 jours (« Voir tout » pour les afficher).
- Filtres : recherche, responsable, priorité, bloqués, avec retards (et mes projets pour l'administrateur). La vue **Liste** présente les mêmes projets en tableau.
- **Nouveau projet** : Administrateur et Chef de projet. Choisissez le responsable et les participants : eux seuls verront le projet. Si vous n'êtes ni l'un ni l'autre, vous êtes ajouté aux participants.

## Fiche projet

En-tête : statut, responsable, priorité, boutons Modifier et Supprimer selon vos droits. **Modifier** gère aussi les participants ; une personne qui porte encore une action ou un risque ouverts ne peut être retirée qu'après leur réaffectation. Les onglets :

- **Général** : informations du projet, charge en j/h, liens (adresses http/https) et **fichiers**.
  - Fichiers acceptés : PDF, Word, Excel, PowerPoint, OpenDocument, images, texte ; 10 Mo au maximum.
  - Ils sont supprimés définitivement 30 jours après le passage en « Livré » ; la date est affichée sur la fiche.
- **Actions** : création rapide (titre, responsable choisi dans l'équipe du projet, échéance, priorité), changement de statut direct, réalisation interne ou externe (sous-traitant). Un clic sur une action ouvre son volet d'édition. Les échéances dépassées sont en rouge, les échéances proches en orange. La corbeille en bout de ligne supprime l'action après confirmation (Administrateur et Chef de projet) : elle disparaît des listes, l'historique du projet la conserve.
- **Planning** : phases et jalons, catégories de charge, j/h vendus et consommés, dépendances.
  - Le Gantt trace les dépendances et le remplissage de la consommation (orange en cas de dépassement).
  - **Exporter en .png** produit une image du Gantt.
- **Risques** : probabilité × impact, criticité calculée, mesures, responsable (membre de l'équipe), statut.
- **Réunions** :
  - **Nouvelle réunion (IA)** : collez la transcription ou déposez le fichier .txt / .vtt exporté de Teams (« Charger la transcription de démonstration » pour essayer), puis **Analyser**.
  - L'écran de validation propose un compte-rendu modifiable et des actions, avec le responsable et l'échéance déjà calculés. Les lignes sans responsable ou sans échéance sont surlignées ; décochez, corrigez ou ajoutez des lignes.
  - **Créer les actions sélectionnées** crée les actions ; rien n'est créé avant. **Tout rejeter** n'en crée aucune.
  - En cas d'échec de l'IA, **Relancer** refait l'analyse sans nouvelle saisie.
- **Commentaires** : fil de discussion ; chacun modifie ou supprime ses propres commentaires.
- **Historique** : journal non modifiable de tout ce qui s'est passé, avec filtres par type, auteur et période.

## Mes actions

Vos actions, retards d'abord, puis par échéance et priorité. Le statut se change en un clic ; la corbeille supprime une action (Administrateur et Chef de projet). Filtres : statut, priorité, projet ; les actions terminées et annulées sont masquées par défaut.

## Utilisateurs (Administrateur)

Création des comptes (sans mot de passe : la personne reçoit un lien pour le choisir), rôle, activation et désactivation. **Réinitialiser le mot de passe** envoie un lien par email et l'affiche, pour le transmettre par un autre moyen si l'email n'arrive pas. Un compte désactivé ne peut plus se connecter ; ses actions apparaissent dans la zone « Responsable inactif » du dashboard.

## Emails (Administrateur)

Journal des 300 derniers emails, avec leur statut (Envoyé, Échec) et l'erreur éventuelle. Un clic sur l'objet ouvre le projet.

Les alertes partent à la création ou modification d'un projet, au changement de statut d'un projet ou d'une action, à l'ajout d'une action ou d'un commentaire, à la réaffectation d'une action, et chaque matin pour les actions passées en retard.
