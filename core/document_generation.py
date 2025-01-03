from django.utils import timezone
from django.db.models import Avg
from django.conf import settings
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from .models import Student, Note, Matiere, Document
from django.core.files.base import ContentFile

def get_appreciation(moyenne):
    if moyenne >= 16:
        return "Excellent"
    elif moyenne >= 14:
        return "Très Bien"
    elif moyenne >= 12:
        return "Bien"
    elif moyenne >= 10:
        return "Assez Bien"
    else:
        return "Insuffisant"

def calculate_student_rank(student):
    classe_students = Student.objects.filter(classe=student.classe)
    moyennes = []
    
    for s in classe_students:
        notes = Note.objects.filter(etudiant=s)
        if notes.exists():
            moyenne = notes.aggregate(Avg('valeur'))['valeur__avg']
            moyennes.append((s.id, moyenne))
    
    moyennes.sort(key=lambda x: x[1], reverse=True)
    for rank, (student_id, _) in enumerate(moyennes, 1):
        if student_id == student.id:
            return rank
    return len(moyennes)

def generate_bulletin_pdf(student, periode="Premier Semestre"):
    # Créer un buffer pour le PDF
    buffer = BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # En-tête
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Centre
    )
    elements.append(Paragraph("BULLETIN DE NOTES", title_style))
    elements.append(Paragraph(f"Période : {periode}", title_style))
    
    # Informations de l'étudiant
    elements.append(Paragraph(f"Nom et Prénom : {student.user.get_full_name()}", styles['Normal']))
    elements.append(Paragraph(f"Matricule : {student.matricule}", styles['Normal']))
    elements.append(Paragraph(f"Classe : {student.classe.nom}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Notes et moyennes
    notes = Note.objects.filter(etudiant=student)
    matieres = Matiere.objects.filter(cours__notes__etudiant=student).distinct()
    
    # Tableau des notes
    table_data = [['Matière', 'Coefficient', 'Moyenne', 'Appréciation']]
    total_points = 0
    total_coeff = 0
    
    for matiere in matieres:
        notes_matiere = notes.filter(cours__matiere=matiere)
        if notes_matiere.exists():
            moyenne = notes_matiere.aggregate(Avg('valeur'))['valeur__avg']
            total_points += moyenne * matiere.coefficient
            total_coeff += matiere.coefficient
            
            table_data.append([
                matiere.nom,
                str(matiere.coefficient),
                f"{moyenne:.2f}/20",
                get_appreciation(moyenne)
            ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Moyenne générale
    moyenne_generale = total_points / total_coeff if total_coeff > 0 else 0
    elements.append(Paragraph(f"Moyenne Générale : {moyenne_generale:.2f}/20", styles['Heading2']))
    elements.append(Paragraph(f"Rang : {calculate_student_rank(student)}/{Student.objects.filter(classe=student.classe).count()}", styles['Normal']))
    elements.append(Paragraph(f"Appréciation Générale : {get_appreciation(moyenne_generale)}", styles['Normal']))
    
    # Générer le PDF
    doc.build(elements)
    
    # Créer le document dans la base de données
    document = Document.objects.create(
        titre=f'Bulletin - {student.user.get_full_name()} - {timezone.now().strftime("%d/%m/%Y")}',
        type_document='BULLETIN',
        etudiant=student,
        description=f'Bulletin de notes généré le {timezone.now().strftime("%d/%m/%Y")}'
    )
    
    # Sauvegarder le fichier PDF
    buffer.seek(0)
    document.fichier.save(
        f'bulletin_{student.matricule}_{timezone.now().strftime("%Y%m%d")}.pdf',
        ContentFile(buffer.read()),
        save=True
    )
    
    return document

def update_certificat_scolarite_pdf(document, ville="Kinshasa", informations_supplementaires=""):
    student = document.etudiant
    # Créer un buffer pour le PDF
    buffer = BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # En-tête
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Centre
    )
    elements.append(Paragraph("CERTIFICAT DE SCOLARITÉ", title_style))
    elements.append(Spacer(1, 20))
    
    # Contenu principal
    text = f"""
    Je soussigné(e), Directeur(trice) de l'École de Formation, certifie que :
    
    L'élève {student.user.get_full_name()}
    Né(e) le {student.date_naissance.strftime('%d/%m/%Y')}
    Matricule : {student.matricule}
    
    est régulièrement inscrit(e) dans notre établissement en classe de {student.classe.nom} 
    pour l'année scolaire {student.classe.annee_scolaire}.
    """
    
    # Ajouter les informations supplémentaires si présentes
    if informations_supplementaires:
        text += f"\n\n{informations_supplementaires}"
    
    text += "\n\nCe certificat est délivré à l'intéressé(e) pour servir et valoir ce que de droit."
    
    for line in text.split('\n'):
        if line.strip():
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 12))
    
    # Date et signature
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Fait à {ville}, le {timezone.now().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("Le Directeur de l'École", styles['Normal']))
    
    # Générer le PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Supprimer l'ancien fichier
    if document.fichier:
        try:
            document.fichier.delete(save=False)
        except Exception:
            pass
    
    # Mettre à jour la description
    document.description = informations_supplementaires
    
    # Sauvegarder le nouveau fichier PDF
    document.fichier.save(
        f'certificat_{student.matricule}_{timezone.now().strftime("%Y%m%d")}.pdf',
        ContentFile(buffer.read()),
        save=True
    )
    
    return document

def generate_certificat_scolarite_pdf(student, ville="Kinshasa", informations_supplementaires=""):
    # Créer un buffer pour le PDF
    buffer = BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # En-tête
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Centre
    )
    elements.append(Paragraph("CERTIFICAT DE SCOLARITÉ", title_style))
    elements.append(Spacer(1, 20))
    
    # Contenu principal
    text = f"""
    Je soussigné(e), Directeur(trice) de l'École de Formation, certifie que :
    
    L'élève {student.user.get_full_name()}
    Né(e) le {student.date_naissance.strftime('%d/%m/%Y')}
    Matricule : {student.matricule}
    
    est régulièrement inscrit(e) dans notre établissement en classe de {student.classe.nom} 
    pour l'année scolaire {student.classe.annee_scolaire}.
    """
    
    # Ajouter les informations supplémentaires si présentes
    if informations_supplementaires:
        text += f"\n\n{informations_supplementaires}"
    
    text += "\n\nCe certificat est délivré à l'intéressé(e) pour servir et valoir ce que de droit."
    
    for line in text.split('\n'):
        if line.strip():
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 12))
    
    # Date et signature
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Fait à {ville}, le {timezone.now().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("Le Directeur de l'École", styles['Normal']))
    
    # Générer le PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Créer un nouveau document
    document = Document.objects.create(
        titre=f'Certificat de Scolarité - {student.user.get_full_name()}',
        type_document='CERTIFICAT',
        etudiant=student,
        description=informations_supplementaires
    )
    
    # Sauvegarder le fichier PDF
    document.fichier.save(
        f'certificat_{student.matricule}_{timezone.now().strftime("%Y%m%d")}.pdf',
        ContentFile(buffer.read()),
        save=True
    )
    
    return document
