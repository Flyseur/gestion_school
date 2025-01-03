from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Student, Professor, Classe, Presence

@login_required
def dashboard(request):
    try:
        # Statistiques globales
        students = Student.objects.select_related('user', 'classe').order_by('-date_inscription')[:5]
        professors = Professor.objects.select_related('user').all()[:5]
        classes = Classe.objects.select_related('professeur_principal', 'professeur_principal__user').all()[:5]
        
        total_students = Student.objects.count()
        total_professors = professors.model.objects.count()
        total_classes = Classe.objects.count()
        
        # Présences du jour
        today = timezone.now().date()
        presences = Presence.objects.filter(date=today).select_related('etudiant__user', 'classe').order_by('-heure_arrivee')[:5]
        presences_today = presences.count()
        
        context = {
            'total_students': total_students,
            'total_professors': total_professors,
            'total_classes': total_classes,
            'presences_today': presences_today,
            'students': students,
            'professors': professors,
            'classes': classes,
            'presences': presences,
        }
        
        return render(request, 'core/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur s'est produite : {str(e)}")
        return render(request, 'core/dashboard.html', {
            'total_students': 0,
            'total_professors': 0,
            'total_classes': 0,
            'presences_today': 0,
            'students': [],
            'professors': [],
            'classes': [],
            'presences': [],
        })
