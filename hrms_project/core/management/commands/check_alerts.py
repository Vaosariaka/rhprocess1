from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone
from core.models import Leave, Alerte, Presence, Contract
from django.db.models import Q


class Command(BaseCommand):
    help = 'Scan for alert conditions (no-return from leave, repeated absences)'

    def handle(self, *args, **options):
        today = timezone.localdate()
        # Leaves approved with date_retour in past and no presence after date_retour
        leaves = Leave.objects.filter(status='APPROVED', end_date__lt=today)
        no_return_alerts = 0
        for l in leaves:
            if not l.end_date:
                continue
            expected_return = l.end_date + timedelta(days=1)
            # check if any presence recorded on or after expected return date
            if not Presence.objects.filter(employee=l.employee, date__gte=expected_return).exists():
                Alerte.objects.get_or_create(
                    employee=l.employee,
                    type='NO_RETURN',
                    message=f'Employee {l.employee} did not return from leave expected on {expected_return}',
                    defaults={'statut': 'OPEN'}
                )
                no_return_alerts += 1

        # Trial contracts currently active (Essai) without alert
        active_trials = Contract.objects.filter(
            type='ESSAI',
            active=True,
            date_start__lte=today
        ).filter(Q(date_end__isnull=True) | Q(date_end__gte=today))

        trial_alerts = 0
        for contract in active_trials:
            message = (
                f'Trial period active for {contract.employee} '
                f'(ends on {contract.date_end} if specified)'
            )
            alert, created = Alerte.objects.get_or_create(
                employee=contract.employee,
                type='TRIAL_ACTIVE',
                message=message,
                defaults={'statut': 'OPEN'}
            )
            if created:
                trial_alerts += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Alerts scan done. No-return alerts created: {no_return_alerts}. '
                f'Trial alerts created: {trial_alerts}'
            )
        )
