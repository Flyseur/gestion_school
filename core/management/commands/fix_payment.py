from django.core.management.base import BaseCommand
from core.models import Payment
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Fix payment status and display total'

    def handle(self, *args, **kwargs):
        # Afficher tous les paiements
        self.stdout.write("Liste des paiements:")
        for payment in Payment.objects.all():
            self.stdout.write(f"ID: {payment.id}, Montant: {payment.montant}, Status: {payment.status}")

        # Mettre à jour tous les paiements non validés
        Payment.objects.all().update(status='VALIDÉ')
        
        # Afficher le total
        total = Payment.objects.aggregate(total=Sum('montant'))['total'] or 0
        self.stdout.write(f"\nTotal des paiements: {total} FCFA")
