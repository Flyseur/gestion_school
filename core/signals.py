from django.contrib.auth.models import User
from core.models import UserProfile

for user in User.objects.all():
    if not hasattr(user, 'userprofile'):
        UserProfile.objects.create(user=user)

for profile in UserProfile.objects.filter(fichier__isnull=True):
    profile.fichier = 'default.jpg'  # Chemin relatif dans le répertoire `media/`
    profile.save()