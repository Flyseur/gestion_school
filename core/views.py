from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from .models import Student, Professor, Classe, Matiere, Cours, Note, Absence, Message, Payment, Rapport, UserProfile, Presence
from .forms import StudentForm, ProfessorForm, ClasseForm, MessageForm, PaymentForm, AbsenceForm, NoteForm, CoursForm, MatiereForm, UserProfileForm
import uuid
import json
import time
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import os
from decimal import Decimal
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

# Create your views here.

@login_required
def dashboard(request):
    """Vue du tableau de bord"""
    import json
    from datetime import datetime, timedelta
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncMonth
    from decimal import Decimal

    # Statistiques générales
    total_students = Student.objects.count()
    total_classes = Classe.objects.count()
    total_payments = Payment.objects.aggregate(total=Sum('montant'))['total'] or 0
    
    # Calcul du taux de présence
    total_attendances = Presence.objects.count()
    total_possible = total_students * Classe.objects.count()  # Nombre total possible de présences
    attendance_rate = round((total_attendances / total_possible * 100) if total_possible > 0 else 0)

    # Données pour le graphique des paiements (12 derniers mois)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    monthly_payments = Payment.objects.filter(
        date_paiement__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('date_paiement')
    ).values('month').annotate(
        total=Sum('montant')
    ).order_by('month')

    payment_months = []
    payment_amounts = []
    
    # Remplir les données pour chaque mois
    current_date = start_date
    while current_date <= end_date:
        month_str = current_date.strftime('%B %Y')
        payment_months.append(month_str)
        
        # Chercher le montant pour ce mois
        month_payment = next(
            (float(p['total']) if p['total'] else 0 for p in monthly_payments if p['month'].strftime('%B %Y') == month_str),
            0
        )
        payment_amounts.append(month_payment)
        
        # Passer au mois suivant
        current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)

    # Données pour le graphique de répartition des étudiants par classe
    class_distribution = Classe.objects.annotate(
        student_count=Count('etudiants')
    ).values('nom', 'student_count')

    class_names = [c['nom'] for c in class_distribution]
    students_per_class = [c['student_count'] for c in class_distribution]

    # Activités récentes
    recent_activities = []
    # Ajouter les dernières inscriptions
    for student in Student.objects.order_by('-date_inscription')[:5]:
        recent_activities.append({
            'icon': 'fa-user-plus',
            'title': f'Nouvel étudiant inscrit',
            'description': f'{student.user.get_full_name()} a été inscrit',
            'timestamp': student.date_inscription
        })
    
    # Ajouter les derniers paiements
    for payment in Payment.objects.order_by('-date_paiement')[:5]:
        recent_activities.append({
            'icon': 'fa-money-bill-wave',
            'title': 'Nouveau paiement',
            'description': f'Paiement de {float(payment.montant)} FCFA par {payment.etudiant.user.get_full_name()}',
            'timestamp': payment.date_paiement
        })

    # Trier les activités par date
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]  # Garder les 5 plus récentes

    # Convertir les montants Decimal en float pour la sérialisation JSON
    if isinstance(total_payments, Decimal):
        total_payments = float(total_payments)

    # Récupérer les messages récents
    recent_messages = Message.objects.select_related('sender', 'recipient').order_by('-date_sent')[:5]

    context = {
        'total_students': total_students,
        'total_classes': total_classes,
        'total_payments': total_payments,
        'attendance_rate': attendance_rate,
        'payment_months': json.dumps(payment_months),
        'payment_amounts': json.dumps(payment_amounts),
        'class_names': json.dumps(class_names),
        'students_per_class': json.dumps(students_per_class),
        'recent_activities': recent_activities,
        'recent_messages': recent_messages,
    }

    return render(request, 'core/dashboard.html', context)

@login_required
def student_list(request):
    # Récupérer toutes les classes actives
    classes = Classe.objects.filter(active=True).order_by('nom')
    
    # Initialiser le queryset des étudiants
    students = Student.objects.all()
    
    # Filtre par classe
    classe_id = request.GET.get('classe')
    if classe_id:
        students = students.filter(classe_id=classe_id)
    
    # Filtre par recherche
    search_query = request.GET.get('search')
    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(matricule__icontains=search_query)
        )
    
    # Filtre par statut
    status = request.GET.get('status')
    if status == 'active':
        students = students.filter(actif=True)
    elif status == 'inactive':
        students = students.filter(actif=False)
    
    # Tri par nom de famille
    students = students.order_by('user__last_name', 'user__first_name')
    
    # Pagination
    paginator = Paginator(students, 10)  # 10 étudiants par page
    page = request.GET.get('page')
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)
    
    context = {
        'students': students,
        'classes': classes,
        'current_classe': classe_id,
        'search_query': search_query,
        'current_status': status
    }
    
    return render(request, 'core/student_list.html', context)

@login_required
def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    notes = Note.objects.filter(etudiant=student)
    absences = Absence.objects.filter(etudiant=student)
    payments = Payment.objects.filter(etudiant=student).order_by('-date_paiement')
    
    context = {
        'student': student,
        'notes': notes,
        'absences': absences,
        'payments': payments,
    }
    return render(request, 'core/student_detail.html', context)

@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            messages.success(request, 'Étudiant ajouté avec succès!')
            return redirect('core:student_list')
    else:
        form = StudentForm()
    return render(request, 'core/student_form.html', {'form': form})

@login_required
@staff_member_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    student.delete()
    messages.success(request, "L'étudiant a été supprimé avec succès.")
    return redirect('core:student_list')

@login_required
def professor_list(request):
    professors = Professor.objects.all().select_related('user')
    return render(request, 'core/professor_list.html', {'professors': professors})

@login_required
def professor_detail(request, professor_id):
    professor = get_object_or_404(Professor, id=professor_id)
    context = {
        'professor': professor
    }
    return render(request, 'core/professor_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_professor(request):
    if request.method == 'POST':
        form = ProfessorForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                professor = form.save()
                messages.success(request, f'Le professeur {professor.user.get_full_name()} a été ajouté avec succès.')
                return redirect('core:professor_list')
            except Exception as e:
                messages.error(request, f'Erreur lors de l\'ajout du professeur : {str(e)}')
    else:
        form = ProfessorForm()
    
    return render(request, 'core/add_professor.html', {'form': form})

@login_required
@staff_member_required
def delete_professor(request, professor_id):
    professor = get_object_or_404(Professor, id=professor_id)
    if professor.user:
        professor.user.delete()  # Supprime également le compte utilisateur associé
    professor.delete()
    messages.success(request, "Le professeur a été supprimé avec succès.")
    return redirect('core:professor_list')

@login_required
def class_list(request):
    classes = Classe.objects.all().order_by('niveau', 'nom')
    return render(request, 'core/class_list.html', {'classes': classes})

@login_required
def class_detail(request, class_id):
    classe = get_object_or_404(Classe, id=class_id)
    students = Student.objects.filter(classe=classe).select_related('user')
    cours = Cours.objects.filter(classe=classe).select_related('professeur', 'professeur__user')
    
    # Statistiques
    total_students = students.count()
    cours_count = cours.count()
    
    # Moyennes des notes par matière
    notes_by_matiere = {}
    for cours_item in cours:
        notes = Note.objects.filter(cours=cours_item)
        if notes.exists():
            moyenne = notes.aggregate(Avg('valeur'))['valeur__avg']
            notes_by_matiere[cours_item.matiere.nom] = round(moyenne, 2) if moyenne else None
    
    # Taux d'absences
    absences = Absence.objects.filter(etudiant__classe=classe)
    absences_count = absences.count()
    absences_justified = absences.filter(justifie=True).count()
    absence_rate = (absences_count / (total_students * cours_count)) * 100 if total_students and cours_count else 0
    
    context = {
        'classe': classe,
        'students': students,
        'cours': cours,
        'total_students': total_students,
        'cours_count': cours_count,
        'notes_by_matiere': notes_by_matiere,
        'absences_count': absences_count,
        'absences_justified': absences_justified,
        'absence_rate': round(absence_rate, 1)
    }
    
    return render(request, 'core/class_detail.html', context)

@login_required
def add_class(request):
    if request.method == 'POST':
        form = ClasseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Classe ajoutée avec succès!')
            return redirect('core:class_list')
    else:
        form = ClasseForm()
    return render(request, 'core/class_form.html', {'form': form})

@login_required
@staff_member_required
def delete_class(request, class_id):
    if request.method == 'POST':
        classe = get_object_or_404(Classe, id=class_id)
        nom_classe = classe.nom
        try:
            classe.delete()
            messages.success(request, f'La classe "{nom_classe}" a été supprimée avec succès.')
        except Exception as e:
            messages.error(request, f'Erreur lors de la suppression de la classe : {str(e)}')
    return redirect('core:class_list')

@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
    }
    
    if hasattr(user, 'student'):
        context['student'] = user.student
        context['payments'] = Payment.objects.filter(etudiant=user.student).order_by('-date_paiement')
        context['notes'] = Note.objects.filter(etudiant=user.student).order_by('-date')
        context['absences'] = Absence.objects.filter(etudiant=user.student).order_by('-date')
    elif hasattr(user, 'professor'):
        context['professor'] = user.professor
        context['cours'] = Cours.objects.filter(professeur=user.professor).order_by('jour', 'heure_debut')
    
    return render(request, 'core/profile.html', context)

def register(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
        
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Compte créé avec succès! Vous pouvez maintenant vous connecter.')
            return redirect('core:login')
    else:
        form = RegisterForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def inbox(request):
    messages_received = Message.objects.filter(recipient=request.user)
    return render(request, 'core/messages/inbox.html', {'messages': messages_received})

@login_required
def sent_messages(request):
    sent = Message.objects.filter(sender=request.user).order_by('-date_sent')
    return render(request, 'core/messages/sent_messages.html', {'messages': sent})

@login_required
def compose_message(request):
    recipient_id = request.GET.get('recipient')
    initial_data = {}
    
    if recipient_id:
        try:
            recipient = User.objects.get(id=recipient_id)
            initial_data['recipient'] = recipient
        except User.DoesNotExist:
            messages.error(request, "Destinataire non trouvé.")
            return redirect('core:received_messages')
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            messages.success(request, "Message envoyé avec succès.")
            return redirect('core:received_messages')
    else:
        form = MessageForm(initial=initial_data)
    
    return render(request, 'core/messages/compose.html', {
        'form': form,
        'recipient_id': recipient_id
    })

@login_required
def view_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    # Vérifier que l'utilisateur a le droit de voir ce message
    if message.recipient != request.user and message.sender != request.user:
        messages.error(request, "Vous n'avez pas accès à ce message.")
        return redirect('core:inbox')
    
    # Marquer comme lu si c'est le destinataire qui le lit
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
    
    return render(request, 'core/messages/view.html', {'message': message})

@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('core:login')

def login_view(request):
    # Si l'utilisateur est déjà connecté, rediriger vers le dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    return render(request, 'core/login.html')

from django.contrib.auth.decorators import user_passes_test

@login_required
def payment_list(request):
    payments = Payment.objects.select_related('etudiant', 'recu_par').all().order_by('-date_paiement')
    return render(request, 'core/payments/payment_list.html', {
        'payments': payments
    })

@login_required
@staff_member_required
def process_payment(request, student_id=None):
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        initial = {'etudiant': student}
    else:
        initial = {}

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.recu_par = request.user
            payment.status = 'VALIDÉ'  # Définir le statut comme VALIDÉ par défaut
            payment.save()
            messages.success(request, 'Le paiement a été enregistré avec succès.')
            return redirect('core:payment_list')
    else:
        form = PaymentForm(initial=initial)

    return render(request, 'core/payments/process_payment.html', {
        'form': form,
        'student_id': student_id
    })

@login_required
@staff_member_required
def process_payment_for_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    initial = {'etudiant': student}

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.recu_par = request.user
            payment.status = 'VALIDÉ'  # Définir le statut comme VALIDÉ par défaut
            payment.save()
            messages.success(request, 'Le paiement a été enregistré avec succès.')
            return redirect('core:student_detail', student_id=student_id)
    else:
        form = PaymentForm(initial=initial)

    return render(request, 'core/payments/process_payment.html', {
        'form': form,
        'student': student
    })

@login_required
@staff_member_required
def validate_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    payment.valide = True
    payment.save()
    messages.success(request, 'Le paiement a été validé avec succès.')
    return redirect('core:payment_list')

@login_required
@staff_member_required
def delete_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    payment.delete()
    messages.success(request, 'Le paiement a été supprimé avec succès.')
    return redirect('core:payment_list')

@login_required
def generate_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    return render(request, 'core/payments/receipt.html', {
        'payment': payment
    })

@login_required
@staff_member_required
def make_direct_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.date_paiement = timezone.now().date()
            payment.reference = str(uuid.uuid4())
            payment.recu_par = request.user
            payment.status = 'VALIDÉ'  # Définir le statut comme VALIDÉ par défaut
            payment.save()
            messages.success(request, "Le paiement a été enregistré avec succès.")
            return redirect('core:payment_list')
    else:
        form = PaymentForm()
    return render(request, 'core/payments/make_payment.html', {'form': form})

@login_required
def initiate_payment(request):
    if not request.user.groups.filter(name='Students').exists():
        messages.error(request, "Seuls les étudiants peuvent effectuer des paiements.")
        return redirect('core:payment_list')

    if request.method == 'POST':
        try:
            # Créer une session de paiement Stripe
            # checkout_session = stripe.checkout.Session.create(
            #     payment_method_types=['card'],
            #     line_items=[{
            #         'price_data': {
            #             'currency': 'eur',
            #             'unit_amount': int(float(request.POST.get('montant')) * 100),  # Stripe utilise les centimes
            #             'product_data': {
            #                 'name': request.POST.get('type_paiement'),
            #                 'description': f"Paiement pour {request.user.get_full_name()}",
            #             },
            #         },
            #         'quantity': 1,
            #     }],
            #     mode='payment',
            #     success_url=request.build_absolute_uri(reverse('core:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            #     cancel_url=request.build_absolute_uri(reverse('core:payment_cancel')),
            #     metadata={
            #         'student_id': request.user.student.id if hasattr(request.user, 'student') else None,
            #         'type_paiement': request.POST.get('type_paiement'),
            #     }
            # )
            # return JsonResponse({'sessionId': checkout_session.id})
            return JsonResponse({'error': 'Paiement non disponible'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            # Récupérer les informations de la session
            # session = stripe.checkout.Session.retrieve(session_id)
            
            # Créer un enregistrement de paiement
            # payment = Payment.objects.create(
            #     etudiant=request.user.student,
            #     type_paiement=session.metadata.get('type_paiement'),
            #     montant=session.amount_total / 100,  # Convertir les centimes en euros
            #     date_paiement=timezone.now(),
            #     methode_paiement='CARTE',
            #     reference=f"STRIPE-{session.payment_intent}",
            #     recu_par=request.user,
            #     description=f"Paiement en ligne via Stripe"
            # )
            messages.error(request, "Paiement non disponible")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement du paiement: {str(e)}")
    return redirect('core:payment_list')

@login_required
def payment_cancel(request):
    messages.warning(request, "Le paiement a été annulé.")
    return redirect('core:payment_list')

@login_required
def validate_payment(request, payment_id):
    if not request.user.is_staff:
        messages.error(request, "Seuls les administrateurs peuvent valider les paiements.")
        return redirect('core:payment_list')

    payment = get_object_or_404(Payment, id=payment_id)
    action = request.POST.get('action')
    
    if action == 'validate':
        payment.statut = 'VALIDÉ'
        payment.recu_par = request.user
        messages.success(request, "Le paiement a été validé avec succès.")
    elif action == 'reject':
        payment.statut = 'ANNULÉ'
        messages.warning(request, "Le paiement a été refusé.")
    
    payment.save()
    return redirect('core:payment_list')

@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, id=pk)
    
    # Vérifier si l'utilisateur a le droit de voir ce paiement
    if request.user.groups.filter(name='Students').exists():
        student = Student.objects.get(user=request.user)
        if payment.etudiant != student:
            messages.error(request, "Vous n'avez pas la permission de voir ce paiement.")
            return redirect('core:payment_list')
    
    return render(request, 'core/payments/payment_detail.html', {'payment': payment})

@login_required
def absence_list(request):
    absences = Absence.objects.select_related('etudiant', 'etudiant__user', 'cours').order_by('-date_absence')
    
    if not request.user.is_staff:
        if hasattr(request.user, 'student'):
            absences = absences.filter(etudiant=request.user.student)
        elif hasattr(request.user, 'professor'):
            absences = absences.filter(cours__professeur=request.user.professor)
        else:
            absences = Absence.objects.none()
    
    return render(request, 'core/absence/absence_list.html', {'absences': absences})

@login_required
def add_absence(request):
    if not request.user.is_staff:
        messages.error(request, "Seul le personnel administratif peut enregistrer des absences.")
        return redirect('core:absence_list')

    if request.method == 'POST':
        form = AbsenceForm(request.POST)
        if form.is_valid():
            absence = form.save()
            messages.success(request, "L'absence a été enregistrée avec succès.")
            return redirect('core:absence_list')
    else:
        # Pré-remplir l'étudiant si spécifié dans l'URL
        initial_data = {}
        student_id = request.GET.get('student')
        if student_id:
            try:
                student = Student.objects.get(id=student_id)
                initial_data['etudiant'] = student
            except Student.DoesNotExist:
                pass
        form = AbsenceForm(initial=initial_data)

    return render(request, 'core/absence/add_absence.html', {
        'form': form
    })

@login_required
def delete_absence(request, absence_id):
    if not request.user.is_staff:
        messages.error(request, "Seul le personnel administratif peut supprimer des absences.")
        return redirect('core:absence_list')

    absence = get_object_or_404(Absence, id=absence_id)
    absence.delete()
    messages.success(request, "L'absence a été supprimée avec succès.")
    return redirect('core:absence_list')

# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
#         )
#     except ValueError as e:
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError as e:
#         return HttpResponse(status=400)

#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']
#         # Vous pouvez ajouter ici une logique supplémentaire pour le traitement des paiements réussis

#     return HttpResponse(status=200)

@login_required
def generate_report(request):
    if request.method == 'POST':
        type_rapport = request.POST.get('type_rapport')
        classe_id = request.POST.get('classe')
        periode_debut = datetime.strptime(request.POST.get('periode_debut'), '%Y-%m-%d')
        periode_fin = datetime.strptime(request.POST.get('periode_fin'), '%Y-%m-%d')
        
        # Création du rapport
        rapport = Rapport.objects.create(
            titre=f"Rapport {dict(Rapport.TYPES_RAPPORT)[type_rapport].lower()} - {periode_debut.strftime('%d/%m/%Y')} au {periode_fin.strftime('%d/%m/%Y')}",
            type_rapport=type_rapport,
            periode_debut=periode_debut,
            periode_fin=periode_fin,
            classe_id=classe_id if classe_id else None
        )
        
        # Génération du fichier PDF (à implémenter)
        # TODO: Implémenter la génération du PDF selon le type de rapport
        
        messages.success(request, 'Le rapport a été généré avec succès.')
        return redirect('core:dashboard')
    
    return redirect('core:dashboard')

@login_required
@user_passes_test(lambda u: u.is_staff)
def generate_payment_receipt(request, pk):
    # Récupérer le paiement
    payment = get_object_or_404(Payment, id=pk)
    
    # Créer un buffer pour le PDF
    buffer = BytesIO()
    
    # Créer le PDF
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # En-tête
    p.setFont("Helvetica-Bold", 18)
    p.drawString(2*cm, height-3*cm, "REÇU DE PAIEMENT")
    
    # Logo et informations de l'école
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2*cm, height-5*cm, "ÉCOLE DE FORMATION")
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, height-5.7*cm, "Adresse: [Votre adresse]")
    p.drawString(2*cm, height-6.4*cm, "Tél: [Votre téléphone]")
    p.drawString(2*cm, height-7.1*cm, "Email: [Votre email]")
    
    # Informations du reçu
    p.setFont("Helvetica-Bold", 12)
    p.drawString(2*cm, height-9*cm, f"Reçu N°: {payment.reference}")
    p.drawString(12*cm, height-9*cm, f"Date: {payment.date_paiement.strftime('%d/%m/%Y')}")
    
    # Informations de l'étudiant
    p.setFont("Helvetica-Bold", 12)
    p.drawString(2*cm, height-11*cm, "REÇU DE:")
    p.setFont("Helvetica", 11)
    p.drawString(2*cm, height-12*cm, f"Nom: {payment.etudiant.user.get_full_name()}")
    p.drawString(2*cm, height-13*cm, f"Classe: {payment.etudiant.classe}")
    
    # Détails du paiement
    p.setFont("Helvetica-Bold", 12)
    p.drawString(2*cm, height-15*cm, "DÉTAILS DU PAIEMENT")
    
    # Tableau des détails
    p.setFont("Helvetica", 11)
    p.drawString(2*cm, height-16*cm, f"Type de paiement: {payment.get_type_paiement_display()}")
    p.drawString(2*cm, height-17*cm, f"Montant payé: {payment.montant} FCFA")
    if payment.commentaire:
        p.drawString(2*cm, height-18*cm, f"Commentaire: {payment.commentaire}")
    
    # Signature
    p.setFont("Helvetica-Bold", 11)
    p.drawString(12*cm, height-20*cm, "Signature et cachet")
    p.drawString(12*cm, height-22*cm, "_____________________")
    
    # Finaliser le PDF
    p.showPage()
    p.save()
    
    # Préparer la réponse
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recu_paiement_{payment.reference}.pdf"'
    
    return response

@login_required
def notes_list(request):
    # Filtrer par classe si spécifié
    classe_id = request.GET.get('classe')
    etudiant_id = request.GET.get('etudiant')
    
    # Base des notes
    notes = Note.objects.select_related('etudiant', 'cours', 'etudiant__classe').all()
    
    # Filtres
    if classe_id:
        notes = notes.filter(etudiant__classe_id=classe_id)
    if etudiant_id:
        notes = notes.filter(etudiant_id=etudiant_id)
    
    # Pour le formulaire de filtre
    classes = Classe.objects.filter(active=True)
    etudiants = Student.objects.all()
    
    # Calcul des moyennes par étudiant
    moyennes = {}
    for note in notes:
        if note.etudiant_id not in moyennes:
            moyennes[note.etudiant_id] = {
                'total': 0,
                'count': 0,
                'moyenne': 0
            }
        moyennes[note.etudiant_id]['total'] += float(note.valeur) * note.cours.matiere.coefficient
        moyennes[note.etudiant_id]['count'] += note.cours.matiere.coefficient
    
    # Calcul final des moyennes
    for etudiant_id in moyennes:
        if moyennes[etudiant_id]['count'] > 0:
            moyennes[etudiant_id]['moyenne'] = round(
                moyennes[etudiant_id]['total'] / moyennes[etudiant_id]['count'],
                2
            )
    
    context = {
        'notes': notes,
        'classes': classes,
        'etudiants': etudiants,
        'classe_selectionnee': classe_id,
        'etudiant_selectionne': etudiant_id,
        'moyennes': moyennes
    }
    
    return render(request, 'core/notes/notes_list.html', context)

@login_required
@staff_member_required
def add_note(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save()
            messages.success(request, "La note a été ajoutée avec succès.")
            return redirect('core:note_list')
    else:
        form = NoteForm()
    return render(request, 'core/note_form.html', {'form': form})

@login_required
def delete_note(request, note_id):
    if not request.user.is_staff:
        messages.error(request, "Seul le personnel administratif peut supprimer des notes.")
        return redirect('core:notes_list')

    note = get_object_or_404(Note, id=note_id)
    note.delete()
    messages.success(request, "La note a été supprimée avec succès.")
    return redirect('core:notes_list')

@login_required
@staff_member_required
def cours_list(request):
    cours = Cours.objects.all().order_by('jour', 'heure_debut')
    context = {
        'cours': cours,
        'section': 'cours'
    }
    return render(request, 'core/cours/cours_list.html', context)

@login_required
@staff_member_required
def add_cours(request):
    if request.method == 'POST':
        form = CoursForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le cours a été ajouté avec succès.')
            return redirect('core:cours_list')
    else:
        form = CoursForm()
    
    context = {
        'form': form,
        'section': 'cours',
        'action': 'Ajouter'
    }
    return render(request, 'core/cours/cours_form.html', context)

@login_required
@staff_member_required
def delete_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    if request.method == 'POST':
        cours.delete()
        messages.success(request, 'Le cours a été supprimé avec succès.')
        return redirect('core:cours_list')
    
    context = {
        'cours': cours,
        'section': 'cours'
    }
    return render(request, 'core/cours/cours_confirm_delete.html', context)

@login_required
def cours_detail(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    context = {
        'cours': cours,
        'section': 'cours'
    }
    return render(request, 'core/cours/cours_detail.html', context)

@login_required
@staff_member_required
def edit_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    if request.method == 'POST':
        form = CoursForm(request.POST, instance=cours)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le cours a été modifié avec succès.')
            return redirect('core:cours_list')
    else:
        form = CoursForm(instance=cours)
    
    context = {
        'form': form,
        'cours': cours,
        'section': 'cours',
        'action': 'Modifier'
    }
    return render(request, 'core/cours/cours_form.html', context)

@login_required
def send_message(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            messages.success(request, "Le message a été envoyé avec succès.")
            return redirect('core:sent_messages')
    else:
        form = MessageForm()
    return render(request, 'core/messages/send_message.html', {'form': form})

@login_required
def sent_messages(request):
    sent = Message.objects.filter(sender=request.user).order_by('-date_sent')
    return render(request, 'core/messages/sent_messages.html', {'messages': sent})

@login_required
def received_messages(request):
    received = Message.objects.filter(recipient=request.user).order_by('-date_sent')
    return render(request, 'core/messages/received_messages.html', {'messages': received})

@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    if message.sender == request.user or message.recipient == request.user:
        message.delete()
        messages.success(request, "Le message a été supprimé avec succès.")
    else:
        messages.error(request, "Vous n'avez pas la permission de supprimer ce message.")
    return redirect('core:sent_messages')

@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    if message.sender != request.user and message.recipient != request.user:
        messages.error(request, "Vous n'avez pas la permission de voir ce message.")
        return redirect('core:sent_messages')
    return render(request, 'core/messages/message_detail.html', {'message': message})

@login_required
def mark_as_read(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user)
    message.lu = True
    message.save()
    messages.success(request, "Le message a été marqué comme lu.")
    return redirect('core:received_messages')

@login_required
@staff_member_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student, edit_mode=True)
        if form.is_valid():
            form.save()
            messages.success(request, "L'étudiant a été modifié avec succès.")
            return redirect('core:student_list')
    else:
        form = StudentForm(instance=student, edit_mode=True)
    return render(request, 'core/student_form.html', {'form': form, 'edit': True})

@login_required
@staff_member_required
def edit_professor(request, professor_id):
    professor = get_object_or_404(Professor, id=professor_id)
    if request.method == 'POST':
        form = ProfessorForm(request.POST, request.FILES, instance=professor)
        if form.is_valid():
            professor = form.save()
            # Mise à jour des informations de l'utilisateur
            user = professor.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            
            messages.success(request, "Le professeur a été modifié avec succès.")
            return redirect('core:professor_list')
    else:
        # Pré-remplir le formulaire avec les informations existantes
        initial_data = {
            'first_name': professor.user.first_name,
            'last_name': professor.user.last_name,
            'email': professor.user.email,
            'specialite': professor.specialite,
            'matricule': professor.matricule,
        }
        form = ProfessorForm(instance=professor, initial=initial_data)
        
    return render(request, 'core/professor_form.html', {
        'form': form, 
        'edit': True,
        'professor': professor
    })

@login_required
@staff_member_required
def edit_class(request, class_id):
    classe = get_object_or_404(Classe, id=class_id)
    if request.method == 'POST':
        form = ClasseForm(request.POST, instance=classe)
        if form.is_valid():
            form.save()
            messages.success(request, "La classe a été modifiée avec succès.")
            return redirect('core:class_list')
    else:
        form = ClasseForm(instance=classe)
    return render(request, 'core/class_form.html', {'form': form, 'edit': True})

@login_required
@staff_member_required
def edit_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "La note a été modifiée avec succès.")
            return redirect('core:note_list')
    else:
        form = NoteForm(instance=note)
    return render(request, 'core/note_form.html', {'form': form, 'edit': True})

@login_required
@staff_member_required
def edit_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    if request.method == 'POST':
        form = AbsenceForm(request.POST, instance=absence)
        if form.is_valid():
            form.save()
            messages.success(request, "L'absence a été modifiée avec succès.")
            return redirect('core:absence_list')
    else:
        form = AbsenceForm(instance=absence)
    return render(request, 'core/absence_form.html', {'form': form, 'edit': True})

@login_required
@staff_member_required
def edit_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    if request.method == 'POST':
        form = CoursForm(request.POST, instance=cours)
        if form.is_valid():
            form.save()
            messages.success(request, "Le cours a été modifié avec succès.")
            return redirect('core:cours_list')
    else:
        form = CoursForm(instance=cours)
    return render(request, 'core/cours/edit_cours.html', {'form': form})

@login_required
def note_list(request):
    if request.user.is_staff:
        notes = Note.objects.all().select_related('etudiant', 'cours').order_by('-date')
    elif hasattr(request.user, 'student'):
        notes = Note.objects.filter(etudiant=request.user.student).select_related('cours').order_by('-date')
    elif hasattr(request.user, 'professor'):
        notes = Note.objects.filter(cours__professeur=request.user.professor).select_related('etudiant', 'cours').order_by('-date')
    else:
        notes = Note.objects.none()
    
    return render(request, 'core/note_list.html', {'notes': notes})

@login_required
@staff_member_required
def absence_list(request):
    if request.user.is_staff:
        absences = Absence.objects.all().select_related('etudiant', 'cours').order_by('-date_absence')
    elif hasattr(request.user, 'student'):
        absences = Absence.objects.filter(etudiant=request.user.student).select_related('cours').order_by('-date_absence')
    elif hasattr(request.user, 'professor'):
        absences = Absence.objects.filter(cours__professeur=request.user.professor).select_related('etudiant', 'cours').order_by('-date_absence')
    else:
        absences = Absence.objects.none()
    
    return render(request, 'core/absence_list.html', {'absences': absences})

@login_required
@staff_member_required
def payment_list(request):
    if request.user.is_staff:
        payments = Payment.objects.all().select_related('etudiant', 'recu_par').order_by('-date_paiement')
    elif hasattr(request.user, 'student'):
        payments = Payment.objects.filter(etudiant=request.user.student).select_related('recu_par').order_by('-date_paiement')
    else:
        payments = Payment.objects.none()
    
    return render(request, 'core/payment_list.html', {'payments': payments})

@login_required
def update_profile_photo(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    if 'photo' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'Aucune photo fournie'})
    
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    # Supprimer l'ancienne photo si elle existe
    if profile.fichier:
        try:
            old_file_path = profile.fichier.path
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        except Exception as e:
            print(f"Erreur lors de la suppression de l'ancienne photo : {e}")
    
    # Générer un nom de fichier unique
    photo = request.FILES['photo']
    ext = os.path.splitext(photo.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
        return JsonResponse({'success': False, 'error': 'Format de fichier non supporté'})
    
    filename = f"profile_photos/user_{request.user.id}_{uuid.uuid4().hex[:8]}{ext}"
    
    # S'assurer que le dossier existe
    os.makedirs('media/profile_photos', exist_ok=True)
    
    # Sauvegarder la nouvelle photo
    try:
        # Sauvegarder le fichier
        profile.fichier.save(filename, photo, save=False)
        # Sauvegarder explicitement le profil
        profile.save()
        
        # Vérifier que le fichier existe
        if not os.path.exists(profile.fichier.path):
            raise Exception("Le fichier n'a pas été sauvegardé correctement")
        
        # Retourner l'URL avec un timestamp pour éviter le cache
        photo_url = profile.fichier.url
        if '?' not in photo_url:
            photo_url += f'?t={int(time.time())}'
            
        return JsonResponse({
            'success': True,
            'photo_url': photo_url
        })
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la photo : {e}")
        if profile.fichier:
            try:
                profile.fichier.delete(save=False)
            except:
                pass
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de l\'upload : {str(e)}'
        })

@login_required
@staff_member_required
def matiere_list(request):
    matieres = Matiere.objects.all().order_by('nom')
    return render(request, 'core/matiere_list.html', {'matieres': matieres})

@login_required
@staff_member_required
def add_matiere(request):
    if request.method == 'POST':
        form = MatiereForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matière ajoutée avec succès!')
            return redirect('core:matiere_list')
    else:
        form = MatiereForm()
    return render(request, 'core/matiere_form.html', {'form': form})

@login_required
@staff_member_required
def edit_matiere(request, matiere_id):
    matiere = get_object_or_404(Matiere, id=matiere_id)
    if request.method == 'POST':
        form = MatiereForm(request.POST, instance=matiere)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matière modifiée avec succès!')
            return redirect('core:matiere_list')
    else:
        form = MatiereForm(instance=matiere)
    return render(request, 'core/matiere_form.html', {'form': form, 'matiere': matiere})

@login_required
@staff_member_required
def delete_matiere(request, matiere_id):
    matiere = get_object_or_404(Matiere, id=matiere_id)
    matiere.delete()
    messages.success(request, 'Matière supprimée avec succès!')
    return redirect('core:matiere_list')

@login_required
def presence_list(request):
    today = timezone.now().date()
    presences = Presence.objects.filter(date=today)
    classes = Classe.objects.all()
    
    selected_class = request.GET.get('classe')
    if selected_class:
        students = Student.objects.filter(classe_id=selected_class)
        present_students = presences.filter(classe_id=selected_class).values_list('etudiant_id', flat=True)
    else:
        students = []
        present_students = []
        
    context = {
        'presences': presences,
        'classes': classes,
        'selected_class': selected_class,
        'students': students,
        'present_students': present_students,
        'today': today,
    }
    return render(request, 'core/presence_list.html', context)

@login_required
def mark_presence(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        class_id = request.POST.get('class_id')
        
        try:
            student = Student.objects.get(id=student_id)
            classe = Classe.objects.get(id=class_id)
            
            # Vérifier si l'étudiant n'est pas déjà marqué présent aujourd'hui
            presence, created = Presence.objects.get_or_create(
                etudiant=student,
                date=timezone.now().date(),
                defaults={'classe': classe}
            )
            
            if created:
                messages.success(request, f"{student.user.get_full_name()} a été marqué présent.")
            else:
                messages.info(request, f"{student.user.get_full_name()} était déjà marqué présent.")
                
        except (Student.DoesNotExist, Classe.DoesNotExist):
            messages.error(request, "Étudiant ou classe non trouvé.")
            
    return redirect('core:presence_list')

@login_required
def remove_presence(request, presence_id):
    presence = get_object_or_404(Presence, id=presence_id)
    student_name = presence.etudiant.user.get_full_name()
    presence.delete()
    messages.success(request, f"La présence de {student_name} a été supprimée.")
    return redirect('core:presence_list')

@login_required
def profile_view(request):
    user = request.user
    user_profile = UserProfile.objects.get_or_create(user=user)[0]
    
    try:
        if hasattr(user, 'student'):
            specific_profile = user.student
            role = 'Étudiant'
            additional_info = {
                'Matricule': specific_profile.matricule,
                'Classe': specific_profile.classe.nom if specific_profile.classe else 'Non assigné',
                'Date d\'inscription': specific_profile.date_inscription,
                'Statut': 'Actif' if specific_profile.actif else 'Inactif'
            }
        elif hasattr(user, 'professor'):
            specific_profile = user.professor
            role = 'Professeur'
            classes = specific_profile.classes.all()
            additional_info = {
                'Matricule': specific_profile.matricule,
                'Spécialité': specific_profile.specialite,
                'Matière': specific_profile.matiere,
                'Classes': ', '.join([c.nom for c in classes]) if classes else 'Aucune classe assignée'
            }
        elif user.is_staff:
            role = 'Administrateur'
            additional_info = {
                'Statut': 'Staff' if user.is_staff else 'Normal',
                'Superutilisateur': 'Oui' if user.is_superuser else 'Non'
            }
        else:
            role = 'Utilisateur'
            additional_info = {}
    except Exception as e:
        role = 'Utilisateur'
        additional_info = {}
        print(f"Erreur lors de la récupération des informations spécifiques: {e}")

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            try:
                # Gérer la photo de profil
                if 'photo' in request.FILES:
                    # Si une ancienne photo existe, la supprimer
                    if user.photo:
                        try:
                            old_photo_path = user.photo.path
                            if os.path.exists(old_photo_path):
                                os.remove(old_photo_path)
                        except Exception as e:
                            print(f"Erreur lors de la suppression de l'ancienne photo: {e}")
                    
                    # Sauvegarder la nouvelle photo
                    photo_file = request.FILES['photo']
                    if photo_file.size > 5 * 1024 * 1024:  # 5MB limit
                        messages.error(request, 'La taille de la photo ne doit pas dépasser 5MB.')
                        return redirect('core:profile')
                    
                    if not photo_file.content_type.startswith('image/'):
                        messages.error(request, 'Le fichier doit être une image.')
                        return redirect('core:profile')
                    
                    user.photo = photo_file
                
                user.save()
                messages.success(request, 'Votre profil a été mis à jour avec succès.')
                return redirect('core:profile')
            except Exception as e:
                messages.error(request, f'Erreur lors de la mise à jour du profil: {str(e)}')
                print(f"Erreur lors de la sauvegarde du profil: {e}")
        else:
            messages.error(request, 'Erreur lors de la mise à jour du profil. Vérifiez les informations saisies.')
            print(f"Erreurs du formulaire: {form.errors}")
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
        'role': role,
        'additional_info': additional_info,
        'user_profile': user_profile,
        'photo_url': user.photo.url if user.photo else None,
    }
    
    return render(request, 'core/profile.html', context)

@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    # Vérifier que l'utilisateur est autorisé à voir ce message
    if message.recipient != request.user and message.sender != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à voir ce message.")
        return redirect('core:received_messages')
    
    # Marquer le message comme lu s'il ne l'est pas déjà
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
    
    return render(request, 'core/messages/message_detail.html', {'message': message})

@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    # Vérifier que l'utilisateur est autorisé à supprimer ce message
    if message.recipient != request.user and message.sender != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce message.")
        return redirect('core:received_messages')
    
    message.delete()
    messages.success(request, "Le message a été supprimé avec succès.")
    
    # Rediriger vers la boîte de réception ou la boîte d'envoi selon le contexte
    if message.recipient == request.user:
        return redirect('core:received_messages')
    else:
        return redirect('core:sent_messages')

@login_required
def cours_list(request):
    cours = Cours.objects.all()
    context = {
        'cours': cours,
        'section': 'cours'
    }
    return render(request, 'core/cours/cours_list.html', context)

@login_required
def add_cours(request):
    if request.method == 'POST':
        form = CoursForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le cours a été ajouté avec succès.')
            return redirect('core:cours_list')
    else:
        form = CoursForm()
    
    context = {
        'form': form,
        'section': 'cours',
        'action': 'Ajouter'
    }
    return render(request, 'core/cours/cours_form.html', context)

@login_required
def cours_detail(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    context = {
        'cours': cours,
        'section': 'cours'
    }
    return render(request, 'core/cours/cours_detail.html', context)

@login_required
def edit_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    if request.method == 'POST':
        form = CoursForm(request.POST, instance=cours)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le cours a été modifié avec succès.')
            return redirect('core:cours_list')
    else:
        form = CoursForm(instance=cours)
    
    context = {
        'form': form,
        'cours': cours,
        'section': 'cours',
        'action': 'Modifier'
    }
    return render(request, 'core/cours/cours_form.html', context)

@login_required
def delete_cours(request, cours_id):
    cours = get_object_or_404(Cours, id=cours_id)
    if request.method == 'POST':
        cours.delete()
        messages.success(request, 'Le cours a été supprimé avec succès.')
        return redirect('core:cours_list')
    
    context = {
        'cours': cours,
        'section': 'cours'
    }
    return render(request, 'core/cours/cours_confirm_delete.html', context)

@login_required
def payment_list(request):
    payments = Payment.objects.all()
    context = {
        'payments': payments,
        'section': 'payments'
    }
    return render(request, 'core/payment/payment_list.html', context)

@login_required
def add_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le paiement a été ajouté avec succès.')
            return redirect('core:payment_list')
    else:
        form = PaymentForm()
    
    context = {
        'form': form,
        'section': 'payments',
        'action': 'Ajouter'
    }
    return render(request, 'core/payment/payment_form.html', context)

@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, id=pk)
    context = {
        'payment': payment,
        'section': 'payments'
    }
    return render(request, 'core/payment/payment_detail.html', context)

@login_required
def edit_payment(request, pk):
    payment = get_object_or_404(Payment, id=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            messages.success(request, 'Paiement modifié avec succès.')
            return redirect('core:payment_detail', pk=payment.id)
    else:
        form = PaymentForm(instance=payment)
    
    context = {
        'form': form,
        'payment': payment,
        'section': 'payments'
    }
    return render(request, 'core/payment/payment_form.html', context)

@login_required
def delete_payment(request, pk):
    payment = get_object_or_404(Payment, id=pk)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, 'Paiement supprimé avec succès.')
        return redirect('core:payment_list')
    context = {
        'payment': payment,
        'section': 'payments'
    }
    return render(request, 'core/payment/payment_confirm_delete.html', context)

@login_required
def absence_list(request):
    absences = Absence.objects.all()
    context = {
        'absences': absences,
        'section': 'absences'
    }
    return render(request, 'core/absence/absence_list.html', context)

@login_required
def add_absence(request):
    if request.method == 'POST':
        form = AbsenceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'L\'absence a été ajoutée avec succès.')
            return redirect('core:absence_list')
    else:
        form = AbsenceForm()
    
    context = {
        'form': form,
        'section': 'absences',
        'action': 'Ajouter'
    }
    return render(request, 'core/absence/absence_form.html', context)

@login_required
def absence_detail(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    context = {
        'absence': absence,
        'section': 'absences'
    }
    return render(request, 'core/absence/absence_detail.html', context)

@login_required
def edit_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    if request.method == 'POST':
        form = AbsenceForm(request.POST, instance=absence)
        if form.is_valid():
            form.save()
            messages.success(request, 'L\'absence a été modifiée avec succès.')
            return redirect('core:absence_list')
    else:
        form = AbsenceForm(instance=absence)
    
    context = {
        'form': form,
        'absence': absence,
        'section': 'absences',
        'action': 'Modifier'
    }
    return render(request, 'core/absence/absence_form.html', context)

@login_required
def delete_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    if request.method == 'POST':
        absence.delete()
        messages.success(request, 'L\'absence a été supprimée avec succès.')
        return redirect('core:absence_list')
    
    context = {
        'absence': absence,
        'section': 'absences'
    }
    return render(request, 'core/absence/absence_confirm_delete.html', context)

@login_required
def message_list(request):
    received_messages = Message.objects.filter(recipient=request.user)
    sent_messages = Message.objects.filter(sender=request.user)
    context = {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
        'section': 'messages'
    }
    return render(request, 'core/message/message_list.html', context)