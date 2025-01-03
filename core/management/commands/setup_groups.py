from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from django.db import transaction
from core.models import Administrator, Professor, Student

class Command(BaseCommand):
    help = 'Configure les groupes initiaux et crée un superutilisateur'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # Créer les groupes
            administrators_group, _ = Group.objects.get_or_create(name='Administrators')
            professors_group, _ = Group.objects.get_or_create(name='Professors')
            students_group, _ = Group.objects.get_or_create(name='Students')

            self.stdout.write(self.style.SUCCESS('Groupes créés avec succès'))

            # Créer un superutilisateur s'il n'existe pas
            if not User.objects.filter(username='admin').exists():
                admin_user = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User'
                )
                
                # Ajouter l'utilisateur au groupe Administrators
                administrators_group.user_set.add(admin_user)
                
                # Créer un profil Administrator
                Administrator.objects.create(user=admin_user)
                
                self.stdout.write(self.style.SUCCESS('Superutilisateur créé avec succès'))
            else:
                self.stdout.write(self.style.WARNING('Le superutilisateur existe déjà'))
