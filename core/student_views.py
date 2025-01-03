from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Student

@login_required
def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    # Vérifier que l'utilisateur a le droit d'accéder aux détails de l'étudiant
    if not request.user.is_staff and (not hasattr(request.user, 'student') or request.user.student != student):
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette page.")
        return redirect('core:dashboard')
    
    context = {
        'student': student,
    }
    return render(request, 'core/student/detail.html', context)
