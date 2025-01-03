from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .document_views import download_document, generate_bulletin, generate_certificat, edit_bulletin, edit_certificat, delete_document
from .student_views import student_detail
from django.conf import settings
from django.conf.urls.static import static

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/photo/update/', views.update_profile_photo, name='update_profile_photo'),
    
    # Étudiants
    path('etudiants/', views.student_list, name='student_list'),
    path('etudiants/ajouter/', views.add_student, name='add_student'),
    path('etudiants/<int:student_id>/', views.student_detail, name='student_detail'),
    path('etudiants/<int:student_id>/modifier/', views.edit_student, name='edit_student'),
    path('etudiants/<int:student_id>/supprimer/', views.delete_student, name='delete_student'),
    
    # Professeurs
    path('professeurs/', views.professor_list, name='professor_list'),
    path('professeurs/ajouter/', views.add_professor, name='add_professor'),
    path('professeurs/<int:professor_id>/', views.professor_detail, name='professor_detail'),
    path('professeurs/<int:professor_id>/modifier/', views.edit_professor, name='edit_professor'),
    path('professeurs/<int:professor_id>/supprimer/', views.delete_professor, name='delete_professor'),
    
    # Classes
    path('classes/', views.class_list, name='class_list'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),
    path('classes/ajouter/', views.add_class, name='add_class'),
    path('classes/<int:class_id>/modifier/', views.edit_class, name='edit_class'),
    path('classes/<int:class_id>/supprimer/', views.delete_class, name='delete_class'),
    
    # Cours
    path('cours/', views.cours_list, name='cours_list'),
    path('cours/ajouter/', views.add_cours, name='add_cours'),
    path('cours/<int:cours_id>/', views.cours_detail, name='cours_detail'),
    path('cours/<int:cours_id>/modifier/', views.edit_cours, name='edit_cours'),
    path('cours/<int:cours_id>/supprimer/', views.delete_cours, name='delete_cours'),
    
    # Paiements
    path('paiements/', views.payment_list, name='payment_list'),
    path('paiements/ajouter/', views.add_payment, name='add_payment'),
    path('paiements/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('paiements/<int:pk>/recu/', views.generate_payment_receipt, name='payment_receipt'),
    path('paiements/<int:pk>/modifier/', views.edit_payment, name='edit_payment'),
    path('paiements/<int:pk>/supprimer/', views.delete_payment, name='delete_payment'),
    
    # Absences
    path('absences/', views.absence_list, name='absence_list'),
    path('absences/ajouter/', views.add_absence, name='add_absence'),
    path('absences/<int:absence_id>/', views.absence_detail, name='absence_detail'),
    path('absences/<int:absence_id>/modifier/', views.edit_absence, name='edit_absence'),
    path('absences/<int:absence_id>/supprimer/', views.delete_absence, name='delete_absence'),
    
    # Messages
    path('messages/', views.message_list, name='message_list'),
    path('messages/recus/', views.received_messages, name='received_messages'),
    path('messages/envoyes/', views.sent_messages, name='sent_messages'),
    path('messages/composer/', views.compose_message, name='compose_message'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),
    path('messages/<int:message_id>/supprimer/', views.delete_message, name='delete_message'),
    
    # Documents
    path('documents/<int:document_id>/download/', download_document, name='download_document'),
    path('documents/bulletin/generate/<int:student_id>/', generate_bulletin, name='generate_bulletin'),
    path('documents/certificat/generate/<int:student_id>/', generate_certificat, name='generate_certificat'),
    path('document/<int:document_id>/edit-bulletin/', edit_bulletin, name='edit_bulletin'),
    path('document/<int:document_id>/edit-certificat/', edit_certificat, name='edit_certificat'),
    path('document/<int:document_id>/delete/', delete_document, name='delete_document'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
