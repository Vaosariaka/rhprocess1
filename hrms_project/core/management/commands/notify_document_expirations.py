from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from core.models import Document, Alerte
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Scan documents and create alerts for documents expiring within N days (default 30)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Notify for documents expiring within DAYS')

    def handle(self, *args, **options):
        days = options.get('days', 30)
        today = date.today()
        cutoff = today + timedelta(days=days)
        qs = Document.objects.filter(valid_to__isnull=False, is_active=True)
        count = 0
        for doc in qs:
            if doc.valid_to and today <= doc.valid_to <= cutoff:
                # create an alert for the employee
                msg = f"Document '{doc.get_type_display()}' (file={doc.file_name}) will expire on {doc.valid_to.isoformat()}"
                Alerte.objects.create(employee=doc.employee, type='DOCUMENT_EXPIRY', message=msg, statut='OPEN')
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} alert(s) for documents expiring within {days} days'))
