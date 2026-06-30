# AgendaPro - Gestionnaire d'Agenda Professionnel

Application de gestion d'agenda moderne et professionnelle développée en Python avec Tkinter.

## 🌟 Fonctionnalités

- **Gestion des rendez-vous** : Création, modification et suppression de rendez-vous
- **Vues multiples** : Affichage par jour, semaine ou mois
- **Catégorisation** : Organisation par catégories (Travail, Personnel, Santé, etc.)
- **Rappels** : Notifications personnalisables avant les rendez-vous
- **Récurrence** : Rendez-vous récurrents (quotidien, hebdomadaire, mensuel, annuel)
- **Partage** : Partage de rendez-vous avec d'autres utilisateurs
- **Synchronisation cloud** : Synchronisation automatique avec le cloud
- **Import/Export** : Export en JSON et iCalendar, import depuis JSON
- **Statistiques** : Graphiques et statistiques sur l'utilisation
- **Authentification** : Système d'authentification sécurisé avec bcrypt

## 📋 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

## 🚀 Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-username/Gestion_AgendaPro_Py.git
cd Gestion_AgendaPro_Py
```

2. Créer un environnement virtuel (recommandé) :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
cd Gestion_AgendaPro
cp .env.example .env
# Éditez .env avec vos configurations
```

## 🎯 Utilisation

Lancer l'application :
```bash
cd Gestion_AgendaPro
python main.py
```

### Première utilisation

1. Créer un compte via le bouton "Inscription"
2. Se connecter avec vos identifiants
3. Commencer à ajouter des rendez-vous

## 📁 Structure du projet

```
Gestion_AgendaPro/
├── main.py                 # Point d'entrée de l'application
├── auth_manager.py         # Gestion de l'authentification
├── database_manager.py     # Gestion de la base de données
├── gui_interface.py        # Interface utilisateur principale
├── notification_service.py # Service de notifications
├── cloud_sync_service.py   # Synchronisation cloud
├── sharing_manager.py      # Gestion du partage
├── statistics_view.py       # Affichage des statistiques
├── data_models.py          # Modèles de données
├── .env                    # Variables d'environnement (non versionné)
├── .env.example           # Exemple de configuration
└── requirements.txt        # Dépendances Python
```

## 🔐 Sécurité

- Les mots de passe sont hachés avec bcrypt
- Les données sensibles sont stockées dans `.env` (non versionné)
- La base de données SQLite est locale et non partagée

## 📝 Développement

### Ajout de fonctionnalités

Le projet est modulaire et chaque fichier a une responsabilité unique :
- `auth_manager.py` : Authentification et autorisation
- `database_manager.py` : Opérations sur la base de données
- `gui_interface.py` : Interface graphique
- `notification_service.py` : Notifications et rappels
- `cloud_sync_service.py` : Synchronisation avec le cloud
- `sharing_manager.py` : Partage de rendez-vous
- `statistics_view.py` : Statistiques et graphiques

### Tests

Pour tester les modifications :
```bash
python main.py
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commit vos modifications
4. Push vers la branche
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT.

## 👨‍💻 Auteur

Développé par Herve Brunel

## 🙏 Remerciements

- Tkinter pour l'interface graphique
- La communauté Python pour les excellentes bibliothèques utilisées
