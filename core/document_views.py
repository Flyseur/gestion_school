from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import FileResponse, Http404
import os
from .models import Document, Student, Note, Matiere
from .document_generation import (
    generate_bulletin_pdf, generate_certificat_scolarite_pdf,
    update_certificat_scolarite_pdf, get_appreciation
)

@staff_member_required
def edit_bulletin(request, document_id):
    document = get_object_or_404(Document, id=document_id, type_document='BULLETIN')
    student = document.etudiant
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            periode = request.POST.get('periode', 'Premier Semestre')
            appreciation_generale = request.POST.get('appreciation_generale', '')
            
            # Mettre à jour les notes
            matieres = Matiere.objects.filter(cours__notes__etudiant=student).distinct()
            for matiere in matieres:
                note_value = request.POST.get(f'note_{matiere.id}')
                if note_value:
                    note = Note.objects.filter(etudiant=student, cours__matiere=matiere).first()
                    if note:
                        note.valeur = float(note_value)
                        note.save()
            
            # Générer le nouveau bulletin
            document = generate_bulletin_pdf(student, periode)
            messages.success(request, "Le bulletin a été modifié avec succès.")
            return redirect('core:student_detail', student_id=student.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification du bulletin : {str(e)}")
    
    # Préparer les données pour le template
    matieres_data = []
    notes = Note.objects.filter(etudiant=student)
    matieres = Matiere.objects.filter(cours__notes__etudiant=student).distinct()
    
    for matiere in matieres:
        note = notes.filter(cours__matiere=matiere).first()
        matieres_data.append({
            'id': matiere.id,
            'nom': matiere.nom,
            'coefficient': matiere.coefficient,
            'note': note.valeur if note else None,
            'appreciation': get_appreciation(note.valeur) if note else None
        })
    
    context = {
        'document': document,
        'matieres': matieres_data,
        'appreciation_generale': document.description,
        'periode': 'Premier Semestre'  # À adapter selon vos besoins
    }
    
    return render(request, 'core/documents/edit_bulletin.html', context)

@staff_member_required
def edit_certificat(request, document_id):
    document = get_object_or_404(Document, id=document_id, type_document='CERTIFICAT')
    student = document.etudiant
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            ville = request.POST.get('ville', 'Kinshasa')
            informations_supplementaires = request.POST.get('informations_supplementaires', '')
            
            # Mettre à jour le certificat existant
            update_certificat_scolarite_pdf(
                document,
                ville=ville,
                informations_supplementaires=informations_supplementaires
            )
            
            messages.success(request, "Le certificat a été modifié avec succès.")
            return redirect('core:student_detail', student_id=student.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification du certificat : {str(e)}")
    
    context = {
        'document': document,
        'ville': 'Kinshasa',
        'informations_supplementaires': document.description
    }
    
    return render(request, 'core/documents/edit_certificat.html', context)

@staff_member_required
def delete_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    student_id = document.etudiant.id
    
    try:
        # Supprimer le fichier physique
        if document.fichier:
            if os.path.exists(document.fichier.path):
                os.remove(document.fichier.path)
        
        # Supprimer l'entrée de la base de données
        document.delete()
        messages.success(request, "Le document a été supprimé avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression du document : {str(e)}")
    
    return redirect('core:student_detail', student_id=student_id)

@staff_member_required
def generate_bulletin(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    try:
        document = generate_bulletin_pdf(student)
        messages.success(request, "Le bulletin a été généré avec succès.")
        return redirect('core:student_detail', student_id=student_id)
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du bulletin : {str(e)}")
        return redirect('core:student_detail', student_id=student_id)

@staff_member_required
def generate_certificat(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    try:
        document = generate_certificat_scolarite_pdf(student)
        messages.success(request, "Le certificat de scolarité a été généré avec succès.")
        return redirect('core:student_detail', student_id=student_id)
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du certificat : {str(e)}")
        return redirect('core:student_detail', student_id=student_id)

@login_required
def download_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    
    # Vérifier que l'utilisateur a le droit d'accéder au document
    if not request.user.is_staff and (not hasattr(request.user, 'student') or document.etudiant != request.user.student):
        messages.error(request, "Vous n'avez pas la permission d'accéder à ce document.")
        return redirect('core:dashboard')
    
    try:
        if not document.fichier or not os.path.exists(document.fichier.path):
            raise Http404("Le fichier n'existe pas")
        
        response = FileResponse(document.fichier.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{document.filename()}"'
        return response
    
    except Exception as e:
        messages.error(request, f"Erreur lors du téléchargement : {str(e)}")
        return redirect('core:student_detail', student_id=document.etudiant.id)
