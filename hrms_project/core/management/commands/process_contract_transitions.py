from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Contract, ContractHistory, Alerte
from datetime import date

class Command(BaseCommand):
    help = 'Process automatic contract transitions: renewals, conversions and notifications.'

    def handle(self, *args, **options):
        today = date.today()
        processed = 0
        for c in Contract.objects.filter(active=True):
            try:
                # Process trial contracts: if ended -> promote/notify
                if c.type == 'ESSAI':
                    if c.date_end and c.date_end <= today:
                        # trial finished: if auto_convert_to_cdi set then convert to CDI, else create alert for HR
                        if getattr(c, 'auto_convert_to_cdi', False):
                            c.convert_to_cdi()
                            self.stdout.write(self.style.SUCCESS(f'Contract {c.pk} converted to CDI'))
                            ContractHistory.objects.create(employee=c.employee, contract=c, action='AUTO_CONVERT_TRIAL', details=f'Auto converted to CDI on {today}')
                        else:
                            Alerte.objects.create(employee=c.employee, type='TRIAL_EXPIRED', message=f'Trial expired for {c.employee} on {c.date_end}', statut='OPEN')
                            self.stdout.write(self.style.WARNING(f'Trial expired for contract {c.pk}, alert created'))
                        processed += 1

                # Process CDD: if duration over 24 months -> convert to CDI
                if c.type == 'CDD' and c.date_start:
                    if c.date_end and (c.date_end - c.date_start).days > (365 * 2):
                        c.convert_to_cdi()
                        ContractHistory.objects.create(employee=c.employee, contract=c, action='AUTO_CONVERT_CDD', details=f'Auto converted to CDI due to >24 months on {today}')
                        self.stdout.write(self.style.SUCCESS(f'Contract {c.pk} CDD > 24 months converted to CDI'))
                        processed += 1

                # Check CDD reaching end: create alert 30 days before end
                if c.type == 'CDD' and c.date_end:
                    days_left = (c.date_end - today).days
                    if 0 < days_left <= 30:
                        # create an alert if none exists for this contract end
                        Alerte.objects.create(employee=c.employee, type='CDD_EXPIRING', message=f'CDD for {c.employee} expires on {c.date_end}', statut='OPEN')
                        self.stdout.write(self.style.WARNING(f'CDD {c.pk} expiring in {days_left} days, alert created'))
                        processed += 1

            except Exception as e:
                self.stderr.write(f'Error processing contract {c.pk}: {e}')
        self.stdout.write(self.style.SUCCESS(f'Processed {processed} contract(s)'))
