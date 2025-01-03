from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Professor, Student, Classe, Message, Payment, Absence, Note, Cours, Matiere, CustomUser
import uuid
from django.utils import timezone

class ProfessorForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label='Prénom')
    last_name = forms.CharField(max_length=30, required=True, label='Nom')
    email = forms.EmailField(required=True, label='Email')
    password = forms.CharField(widget=forms.PasswordInput(), label='Mot de passe')
    telephone = forms.CharField(max_length=15, required=True, label='Téléphone')
    matiere = forms.CharField(max_length=100, required=True, label='Matière')
    specialite = forms.CharField(max_length=100, required=True, label='Spécialité')
    photo = forms.ImageField(required=False, label='Photo', help_text='Format recommandé : JPG, PNG. Taille max : 2MB')

    class Meta:
        model = Professor
        fields = ['specialite', 'telephone', 'matiere', 'photo']

    def generate_unique_matricule(self):
        # Générer un matricule unique basé sur PROF + numéro séquentiel
        prefix = 'PROF'
        last_prof = Professor.objects.order_by('-matricule').first()
        
        if last_prof and last_prof.matricule.startswith(prefix):
            try:
                last_num = int(last_prof.matricule[4:])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
            
        return f'{prefix}{new_num:04d}'

    def save(self, commit=True):
        # Générer un nom d'utilisateur unique basé sur le prénom et le nom
        first_name = self.cleaned_data['first_name'].lower()
        last_name = self.cleaned_data['last_name'].lower()
        base_username = f"{first_name}.{last_name}"
        username = base_username
        
        # Vérifier si le nom d'utilisateur existe déjà et ajouter un suffixe si nécessaire
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Créer l'utilisateur
        user = CustomUser.objects.create_user(
            username=username,
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )

        # Créer le professeur
        professor = super().save(commit=False)
        professor.user = user
        professor.telephone = self.cleaned_data['telephone']
        professor.matricule = self.generate_unique_matricule()
        professor.photo = self.cleaned_data.get('photo')
        
        if commit:
            professor.save()

        return professor

class StudentForm(forms.ModelForm):
    first_name = forms.CharField(label='Prénom', max_length=30)
    last_name = forms.CharField(label='Nom', max_length=30)
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput, required=False)
    classe = forms.ModelChoiceField(
        queryset=Classe.objects.filter(active=True).order_by('nom'),
        label='Classe',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Sélectionnez une classe'
        }),
        required=False,
        empty_label="Sélectionnez une classe"
    )
    date_inscription = forms.DateField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Student
        fields = ['matricule', 'date_naissance', 'adresse', 'telephone', 'photo', 'date_inscription', 'classe']
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'matricule': 'Matricule',
            'date_naissance': 'Date de naissance',
            'adresse': 'Adresse',
            'telephone': 'Téléphone',
            'photo': 'Photo',
            'classe': 'Classe'
        }

    def __init__(self, *args, **kwargs):
        self.edit_mode = kwargs.pop('edit_mode', False)
        super().__init__(*args, **kwargs)
        
        # Mettre à jour la liste des classes
        self.fields['classe'].queryset = Classe.objects.filter(active=True).order_by('nom')
        
        if self.edit_mode:
            self.fields['password'].required = False
            if self.instance and self.instance.user:
                self.fields['first_name'].initial = self.instance.user.first_name
                self.fields['last_name'].initial = self.instance.user.last_name
                self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        student = super().save(commit=False)
        
        if not self.edit_mode:
            # Création d'un nouvel utilisateur uniquement lors de l'ajout
            user = CustomUser.objects.create_user(
                username=self.cleaned_data['email'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name']
            )
            student.user = user
        else:
            # Mise à jour de l'utilisateur existant
            user = student.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            user.save()

        if not student.date_inscription:
            student.date_inscription = timezone.now().date()
            
        if commit:
            student.save()
            
        return student

class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = ['nom', 'niveau', 'annee_scolaire', 'professeur_principal', 'active']
        labels = {
            'nom': 'Nom de la classe',
            'niveau': 'Niveau',
            'annee_scolaire': 'Année scolaire',
            'professeur_principal': 'Professeur principal',
            'active': 'Classe active'
        }
        widgets = {
            'professeur_principal': forms.Select(attrs={'class': 'form-select'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class RegisterForm(UserCreationForm):
    email = forms.EmailField(label='Email', required=True)
    role = forms.ChoiceField(
        label='Rôle',
        choices=[
            ('admin', 'Administrateur'),
            ('professor', 'Professeur'),
            ('student', 'Étudiant')
        ],
        required=True
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'role']
        labels = {
            'username': "Nom d'utilisateur",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Créer le profil selon le rôle
            role = self.cleaned_data['role']
            if role == 'admin':
                user.is_staff = True
                user.is_superuser = True
                user.save()
            elif role == 'professor':
                Professor.objects.create(
                    user=user,
                    matricule=user.username
                )
            elif role == 'student':
                Student.objects.create(
                    user=user,
                    matricule=user.username
                )
        return user

class MessageForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=CustomUser.objects.all(),
        label='Destinataire'
    )

    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'content']

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['etudiant', 'type_paiement', 'montant', 'date_paiement', 'commentaire']
        widgets = {
            'date_paiement': forms.DateInput(attrs={'type': 'date'}),
            'commentaire': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'etudiant': 'Étudiant',
            'type_paiement': 'Type de paiement',
            'montant': 'Montant',
            'date_paiement': 'Date du paiement',
            'commentaire': 'Commentaire (optionnel)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['etudiant'].queryset = Student.objects.select_related('user').order_by('user__last_name', 'user__first_name')
        self.fields['montant'].widget.attrs['min'] = '0'
        self.fields['montant'].widget.attrs['step'] = '0.01'

class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ['etudiant', 'date_absence', 'heure_debut', 'heure_fin', 'justifie', 'motif']
        widgets = {
            'date_absence': forms.DateInput(attrs={'type': 'date'}),
            'heure_debut': forms.TimeInput(attrs={'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'type': 'time'}),
            'motif': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['etudiant'].queryset = Student.objects.all().order_by('user__last_name')
        self.fields['etudiant'].label = "Étudiant"
        self.fields['date_absence'].label = "Date de l'absence"
        self.fields['justifie'].label = "Absence justifiée"
        self.fields['motif'].label = "Motif de l'absence (optionnel)"

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['etudiant', 'cours', 'valeur', 'type_evaluation', 'date', 'commentaire']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'valeur': forms.NumberInput(attrs={'min': '0', 'max': '20', 'step': '0.25'}),
            'commentaire': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Amélioration de l'affichage des étudiants
        self.fields['etudiant'].queryset = Student.objects.select_related('user', 'classe').order_by('user__last_name')
        self.fields['etudiant'].label = "Étudiant"
        
        # Amélioration de l'affichage des cours
        self.fields['cours'].queryset = Cours.objects.select_related('matiere', 'professeur', 'classe')
        self.fields['cours'].label = "Cours"
        
        # Labels en français
        self.fields['valeur'].label = "Note sur 20"
        self.fields['type_evaluation'].label = "Type d'évaluation"
        self.fields['date'].label = "Date"
        self.fields['commentaire'].label = "Commentaire (optionnel)"

class CoursForm(forms.ModelForm):
    matiere = forms.CharField(
        max_length=100,
        required=True,
        label='Matière',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le nom de la matière'
        })
    )
    professeur = forms.ModelChoiceField(
        queryset=Professor.objects.all(),
        required=True,
        label='Professeur',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    classe = forms.ModelChoiceField(
        queryset=Classe.objects.all(),
        required=True,
        label='Classe',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    jour = forms.ChoiceField(
        choices=[('Lundi', 'Lundi'), ('Mardi', 'Mardi'), ('Mercredi', 'Mercredi'), ('Jeudi', 'Jeudi'), ('Vendredi', 'Vendredi'), ('Samedi', 'Samedi'), ('Dimanche', 'Dimanche')],
        required=True,
        label='Jour',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    heure_debut = forms.TimeField(
        required=True,
        label='Heure de début',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    heure_fin = forms.TimeField(
        required=True,
        label='Heure de fin',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    commentaire = forms.CharField(
        required=False,
        label='Commentaire (optionnel)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ajoutez un commentaire si nécessaire'
        })
    )

    class Meta:
        model = Cours
        fields = ['matiere', 'professeur', 'classe', 'jour', 'heure_debut', 'heure_fin', 'commentaire']

class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ['nom', 'code', 'coefficient', 'description']
        labels = {
            'nom': 'Nom de la matière',
            'code': 'Code de la matière',
            'coefficient': 'Coefficient',
            'description': 'Description (optionnel)'
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        label='Prénom',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True, 
        label='Nom',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True, 
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    telephone = forms.CharField(
        max_length=15,
        required=False,
        label='Téléphone',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    photo = forms.ImageField(
        required=False, 
        label='Photo de profil',
        help_text='Format recommandé : JPG, PNG. Taille max : 2MB',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'telephone', 'photo']
