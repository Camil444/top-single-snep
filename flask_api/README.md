# SNEP Analytics API

Une API Flask légère pour interroger les données historiques du Top Singles SNEP (2020-2026). Cette API permet d'analyser les performances des artistes et des producteurs.

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.8+
- Les dépendances listées dans `requirements.txt` (notamment `flask`, `flask-cors`, `psycopg2-binary`, `python-dotenv`).

### Installation

1. Assurez-vous d'être à la racine du projet.
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

### Lancement

```bash
python flask_api/app.py
```

L'API sera accessible sur `http://localhost:5001`.

---

## 📡 Endpoints

### 1. Rechercher un Artiste ou Producteur

Récupère les statistiques, la liste des morceaux et les classements.

**URL** : `/api/artist/<nom>`
**Méthode** : `GET`
**Paramètres** :

- `type` (optionnel) : `artist` (défaut) ou `producer`.

**Exemples** :

- **Artiste** :
  ```bash
  curl "http://localhost:5001/api/artist/Jul"
  ```
- **Producteur** :
  ```bash
  curl "http://localhost:5001/api/artist/Maximum%20Beats?type=producer"
  ```

### 2. Politique de Confidentialité (GDPR)

Affiche les informations sur le traitement des données et les droits des utilisateurs.

**URL** : `/api/privacy`
**Méthode** : `GET`

### 3. Export de Données (Portabilité)

Endpoint dédié pour l'export complet des données d'une entité.

**URL** : `/api/gdpr/export/<nom>`
**Méthode** : `GET`

---

## 🛡️ Conformité RGPD (GDPR)

Cette API a été conçue en respectant les principes du Règlement Général sur la Protection des Données (RGPD/GDPR).

### 1. Transparence et Droit à l'Information

L'endpoint `/api/privacy` fournit une déclaration claire sur :

- La nature des données collectées (données publiques de classements musicaux).
- La finalité du traitement (analyse statistique).
- Les coordonnées du contrôleur de données.

### 2. Droit d'Accès

Tout utilisateur peut accéder librement aux données stockées concernant un artiste ou un producteur via les endpoints de recherche.

### 3. Droit à la Portabilité des Données

L'endpoint `/api/gdpr/export/<nom>` permet de récupérer l'intégralité des données associées à une personne (artiste ou producteur) dans un format structuré et lisible par machine (JSON), facilitant leur transfert.

### 4. Minimisation des Données

L'API ne renvoie que les informations strictement nécessaires à l'analyse musicale (Titre, Classement, Semaines). Aucune donnée sensible (vie privée, coordonnées, etc.) n'est traitée ou exposée.

### 5. Droit à l'Oubli et Rectification

Comme indiqué dans la politique de confidentialité, les demandes de suppression ou de rectification de données doivent être adressées à l'administrateur (voir `/api/privacy`). L'API étant une interface de lecture, les modifications sont effectuées au niveau de la base de données par le DPO.

### 6. Sécurité

- L'API fonctionne en lecture seule sur la base de données.
- Les identifiants de base de données sont gérés via des variables d'environnement (`.env`) et ne sont jamais exposés dans le code.
