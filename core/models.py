from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Count
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date
import uuid
from django.urls import reverse
import os
from datetime import datetime

def validate_date_naissance(value):
    age = (date.today() - value).days / 365.25
    if age < 5:
        raise ValidationError("L'étudiant doit avoir au moins 5 ans")
    if age > 100:
        raise ValidationError("La date de naissance n'est pas valide")

def user_directory_path(instance, filename):
    # Les fichiers seront uploadés dans MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.id}/{filename}'

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si c'est un nouveau user sans photo
        if not self.pk and not self.photo:
            self.photo = None
        
        # Si on change la photo, supprimer l'ancienne
        if self.pk:
            try:
                old_instance = CustomUser.objects.get(pk=self.pk)
                if old_instance.photo and self.photo != old_instance.photo:
                    old_instance.photo.delete(save=False)
            except CustomUser.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Supprimer la photo si elle existe
        if self.photo:
            try:
                self.photo.delete(save=False)
            except Exception as e:
                print(f"Erreur lors de la suppression de la photo: {e}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()}"

    def get_photo_url(self):
        if self.photo:
            return self.photo.url
        return None

    def get_unread_messages_count(self):
        return self.received_messages.filter(is_read=False).count()

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('student', 'Étudiant'),
        ('professor', 'Professeur'),
        ('administrator', 'Administrateur')
    ])

    def __str__(self):
        return f"Profil de {self.user.username}"

class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    matricule = models.CharField(
        max_length=20,
        unique=True
    )
    date_naissance = models.DateField(validators=[validate_date_naissance])
    adresse = models.TextField(
        help_text="Adresse complète de l'étudiant"
    )
    telephone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Le numéro de téléphone doit être au format '+243123456789'"
            )
        ]
    )
    photo = models.ImageField(
        upload_to='student_photos/',
        null=True,
        blank=True,
        help_text="Photo de profil de l'étudiant (format JPEG ou PNG)"
    )
    classe = models.ForeignKey(
        'Classe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etudiants'
    )
    date_inscription = models.DateField(
        default=timezone.now,
        help_text="Date d'inscription de l'étudiant"
    )
    actif = models.BooleanField(
        default=True,
        help_text="Indique si l'étudiant est actuellement inscrit"
    )

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.matricule})"

    def clean(self):
        # Validations personnalisées
        if self.date_inscription and self.date_naissance:
            date_inscription = self.date_inscription
            if isinstance(date_inscription, datetime):
                date_inscription = date_inscription.date()
            age_inscription = (date_inscription - self.date_naissance).days / 365.25
            if age_inscription < 5:
                raise ValidationError({
                    'date_inscription': "L'étudiant doit avoir au moins 5 ans à la date d'inscription"
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def age(self):
        if self.date_naissance:
            today = date.today()
            return today.year - self.date_naissance.year - (
                (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
            )
        return None

    @property
    def nom_complet(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Professor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=20, unique=True)
    specialite = models.CharField(max_length=100)
    telephone = models.CharField(max_length=15)
    matiere = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='professor_photos/', null=True, blank=True)
    classes = models.ManyToManyField('Classe', related_name='professeurs', blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.matiere}"

    def get_photo_url(self):
        if self.photo:
            return self.photo.url
        return None

    class Meta:
        verbose_name = "Professeur"
        verbose_name_plural = "Professeurs"

class Administrator(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    telephone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()} (Admin)"

class Classe(models.Model):
    nom = models.CharField(max_length=100)
    niveau = models.CharField(max_length=50)
    annee_scolaire = models.CharField(max_length=9)  # Format: 2023-2024
    professeur_principal = models.ForeignKey('Professor', on_delete=models.SET_NULL, null=True, related_name='classes_dirigees')
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire})"

class Matiere(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    coefficient = models.IntegerField(default=1)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.nom

class Cours(models.Model):
    JOURS_SEMAINE = [
        ('LUNDI', 'Lundi'),
        ('MARDI', 'Mardi'),
        ('MERCREDI', 'Mercredi'),
        ('JEUDI', 'Jeudi'),
        ('VENDREDI', 'Vendredi'),
        ('SAMEDI', 'Samedi'),
    ]
    
    matiere = models.CharField(max_length=100)
    professeur = models.ForeignKey(Professor, on_delete=models.CASCADE)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    jour = models.CharField(max_length=20)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    commentaire = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        ordering = ['jour', 'heure_debut']

    def __str__(self):
        return f"{self.matiere} - {self.professeur} - {self.classe} - {self.jour}"

class Note(models.Model):
    etudiant = models.ForeignKey(Student, on_delete=models.CASCADE)
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='notes')
    valeur = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    type_evaluation = models.CharField(
        max_length=20,
        choices=[
            ('DEVOIR', 'Devoir'),
            ('EXAMEN', 'Examen'),
            ('PROJET', 'Projet')
        ]
    )
    date = models.DateField()
    commentaire = models.TextField(blank=True)

    def __str__(self):
        return f"{self.etudiant} - {self.cours} - {self.valeur}/20"

class Absence(models.Model):
    etudiant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='absences')
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='absences', null=True, blank=True)
    date_absence = models.DateField()
    heure_debut = models.TimeField(default='08:00')
    heure_fin = models.TimeField(default='09:00')
    justifie = models.BooleanField(default=False)
    motif = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_absence']
        verbose_name = "Absence"
        verbose_name_plural = "Absences"

    def __str__(self):
        return f"Absence de {self.etudiant} le {self.date_absence} de {self.heure_debut} à {self.heure_fin}"

class Evenement(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    lieu = models.CharField(max_length=100)
    classes = models.ManyToManyField(Classe, blank=True)

    def __str__(self):
        return self.titre

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_sent']

    def __str__(self):
        return f"{self.subject} (De: {self.sender} À: {self.recipient})"

class Payment(models.Model):
    TYPES_PAIEMENT = [
        ('INSCRIPTION', 'Frais d\'inscription'),
        ('MENSUALITE', 'Mensualité'),
        ('EXAMEN', 'Frais d\'examen'),
        ('AUTRE', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('VALIDÉ', 'Validé'),
        ('ANNULÉ', 'Annulé'),
    ]
    
    etudiant = models.ForeignKey(Student, on_delete=models.CASCADE)
    type_paiement = models.CharField(max_length=20, choices=TYPES_PAIEMENT)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateField(default=timezone.now)
    reference = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    recu_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='paiements_recus')
    commentaire = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='EN_ATTENTE')
    
    class Meta:
        ordering = ['-date_paiement']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
    
    def __str__(self):
        return f"Paiement {self.reference} - {self.etudiant.nom_complet} ({self.montant} FCFA)"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = str(uuid.uuid4())
        super().save(*args, **kwargs)

class Document(models.Model):
    TYPES_DOCUMENT = [
        ('BULLETIN', 'Bulletin de notes'),
        ('CERTIFICAT', 'Certificat de scolarité'),
        ('ATTESTATION', 'Attestation'),
        ('AUTRE', 'Autre'),
    ]
    titre = models.CharField(max_length=200)
    type_document = models.CharField(max_length=20, choices=TYPES_DOCUMENT)
    fichier = models.FileField(upload_to='documents/')
    etudiant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    date_creation = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.titre} - {self.etudiant.user.get_full_name()}"

    def get_absolute_url(self):
        return reverse('core:download_document', args=[str(self.id)])

    def filename(self):
        return os.path.basename(self.fichier.name)

class Rapport(models.Model):
    TYPES_RAPPORT = [
        ('PRESENCE', 'Rapport de présence'),
        ('NOTE', 'Bulletin de notes'),
        ('PAIEMENT', 'État des paiements'),
    ]
    
    titre = models.CharField(max_length=200)
    type_rapport = models.CharField(max_length=20, choices=TYPES_RAPPORT)
    date_generation = models.DateTimeField(auto_now_add=True)
    classe = models.ForeignKey(Classe, on_delete=models.SET_NULL, null=True)
    fichier = models.FileField(upload_to='rapports/', null=True, blank=True)
    
    class Meta:
        ordering = ['-date_generation']
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"
    
    def __str__(self):
        return f"{self.get_type_rapport_display()} - {self.classe.nom if self.classe else 'Toutes les classes'} - {self.date_generation.strftime('%d/%m/%Y')}"

    def get_absolute_url(self):
        if self.fichier:
            return self.fichier.url
        return None

class Presence(models.Model):
    etudiant = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='presences')
    date = models.DateField(auto_now_add=True)
    heure_arrivee = models.TimeField(auto_now_add=True)
    classe = models.ForeignKey('Classe', on_delete=models.CASCADE, related_name='presences')
    
    class Meta:
        unique_together = ['etudiant', 'date']
        ordering = ['-date', 'etudiant__user__last_name']
        verbose_name = "Présence"
        verbose_name_plural = "Présences"

    def __str__(self):
        return f"{self.etudiant} - {self.date}"
