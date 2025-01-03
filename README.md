# Système de Gestion Scolaire

Une application web Django pour la gestion scolaire, permettant de gérer les étudiants, les professeurs, les cours, les paiements et les absences.

## Fonctionnalités

- Gestion des étudiants
- Gestion des professeurs
- Gestion des classes et cours
- Suivi des paiements
- Gestion des absences
- Système de messagerie interne
- Génération de rapports

## Installation

1. Cloner le repository
```bash
git clone https://github.com/votre-username/school_management.git
cd school_management
```

2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Installer les dépendances
```bash
pip install -r requirements.txt
```

4. Configurer la base de données
```bash
python manage.py migrate
```

5. Créer un super utilisateur
```bash
python manage.py createsuperuser
```

6. Lancer le serveur
```bash
python manage.py runserver
```

## Technologies utilisées

- Django
- Bootstrap
- SQLite (développement)
- PostgreSQL (production)
- Crispy Forms
- WhiteNoise
- Gunicorn
