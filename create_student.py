from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from core.models import Student
from django.utils import timezone
import re

def validate_phone(phone):
    pattern = r'^\+243[0-9]{9}$'  # Format spécifique pour les numéros RDC
    if not re.match(pattern, phone):
        raise ValidationError("Le numéro de téléphone doit être au format +243XXXXXXXXX")

def validate_matricule(matricule):
    pattern = r'^[A-Z]{3}\d{3}$'  # Format requis: ABC123
    if not re.match(pattern, matricule):
        raise ValidationError("Le matricule doit être au format 'ABC123'")

def create_student(
    username,
    password,
    email,
    first_name,
    last_name,
    date_naissance,
    adresse,
    telephone,
    matricule
):
    try:
        # Validation des données
        validate_email(email)
        validate_phone(telephone)
        validate_matricule(matricule)
        
        # Vérification de l'âge minimum
        age = (timezone.now().date() - date_naissance).days / 365.25
        if age < 5:
            raise ValidationError("L'étudiant doit avoir au moins 5 ans")
        
        if User.objects.filter(username=username).exists():
            raise ValidationError(f"Un utilisateur avec le nom {username} existe déjà")
        
        if Student.objects.filter(matricule=matricule).exists():
            raise ValidationError(f"Un étudiant avec le matricule {matricule} existe déjà")
        
        if not password or len(password) < 8:
            raise ValidationError("Le mot de passe doit contenir au moins 8 caractères")
            
        # Créer le nouvel utilisateur
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # Ajouter l'utilisateur au groupe Students
        student_group, _ = Group.objects.get_or_create(name='Students')
        user.groups.add(student_group)
        
        # Créer le profil étudiant
        student = Student.objects.create(
            user=user,
            date_naissance=date_naissance,
            adresse=adresse,
            telephone=telephone,
            matricule=matricule,
            date_inscription=timezone.now()
        )
        
        print(f"\nCompte étudiant créé avec succès !")
        print(f"Nom d'utilisateur : {username}")
        print(f"Email : {email}")
        return student
        
    except ValidationError as e:
        print(f"Erreur de validation : {e}")
        raise
    except Exception as e:
        print(f"Une erreur s'est produite : {e}")
        raise

if __name__ == '__main__':
    import os
    import django
    from datetime import date
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
    django.setup()
    
    try:
        student = create_student(
            username='etudiant1',
            password='Etudiant@123',  # Utiliser un mot de passe plus sécurisé
            email='etudiant1@example.com',
            first_name='Jean',
            last_name='Dupont',
            date_naissance=date(2000, 1, 1),  # Date de naissance réelle
            adresse='123 Rue Example',
            telephone='+243123456789',
            matricule='STD001'
        )
        print("Étudiant créé avec succès !")
    except Exception as e:
        print(f"Erreur lors de la création de l'étudiant : {e}")
