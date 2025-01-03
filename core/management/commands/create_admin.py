from django.core.management.base import BaseCommand
from core.models import CustomUser, Administrator

class Command(BaseCommand):
    help = 'Creates a superuser and administrator'

    def handle(self, *args, **options):
        try:
            # Créer le superutilisateur
            admin = CustomUser.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            
            # Créer le profil administrateur
            Administrator.objects.create(
                user=admin,
                telephone='123456789'
            )
            
            self.stdout.write(self.style.SUCCESS('Superuser créé avec succès!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur: {str(e)}'))
