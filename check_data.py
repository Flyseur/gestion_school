import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from core.models import Student, Professor, Paiement, Classe
from django.contrib.auth.models import User

def check_data():
    print("\n=== Vérification des données ===")
    
    # Vérifier les étudiants
    students = Student.objects.select_related('user', 'classe').all()
    print("\nÉtudiants:")
    for student in students:
        print(f"- {student.user.first_name} {student.user.last_name} (Matricule: {student.matricule})")
        if student.classe:
            print(f"  Classe: {student.classe.nom}")
    
    # Vérifier les professeurs
    professors = Professor.objects.select_related('user').all()
    print("\nProfesseurs:")
    for prof in professors:
        print(f"- {prof.user.first_name} {prof.user.last_name} (Matricule: {prof.matricule})")
    
    # Vérifier les paiements
    payments = Paiement.objects.select_related('etudiant', 'etudiant__user').all()
    print("\nPaiements:")
    for payment in payments:
        print(f"- {payment.etudiant.user.first_name} {payment.etudiant.user.last_name}")
        print(f"  Montant: {payment.montant} FCFA")
        print(f"  Date: {payment.date_paiement}")
    
    # Vérifier les classes
    classes = Classe.objects.all()
    print("\nClasses:")
    for classe in classes:
        student_count = Student.objects.filter(classe=classe).count()
        print(f"- {classe.nom} ({student_count} étudiants)")

if __name__ == '__main__':
    check_data()
