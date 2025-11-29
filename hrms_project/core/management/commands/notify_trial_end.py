from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from core.models import Contract, Alerte
from datetime import timedelta


class Command(BaseCommand):
    help = 'Create alerts for trial contracts ending within N days (default 15 days)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=15, help='Lookahead days')
        parser.add_argument('--send-email', action='store_true', help='Also send email notifications to employees')

    def handle(self, *args, **options):
        days = options['days']
        now = timezone.now().date()
        cutoff = now + timedelta(days=days)
        contracts = Contract.objects.filter(type='ESSAI', date_end__isnull=False, date_end__lte=cutoff, active=True)
        created = 0
        for c in contracts:
            msg = f"Contract trial for {c.employee} ends on {c.date_end}. Consider renewal/convert."
            Alerte.objects.create(employee=c.employee, type='TRIAL_END', message=msg)
            created += 1
            self.stdout.write(self.style.NOTICE(f'Alert created for {c.employee} trial end {c.date_end}'))

            if options.get('send_email'):
                # prepare email
                to_email = c.employee.email
                context = {'employee': c.employee, 'contract': c, 'cutoff': cutoff}
                subject = f'Votre période d\'essai se termine le {c.date_end}'
                text_body = render_to_string('core/emails/trial_end.txt', context)
                html_body = render_to_string('core/emails/trial_end.html', context)
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None) or 'no-reply@localhost'
                if to_email:
                    try:
                        msg_email = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=[to_email])
                        msg_email.attach_alternative(html_body, 'text/html')
                        msg_email.send(fail_silently=False)
                        self.stdout.write(self.style.NOTICE(f'Email sent to {to_email}'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Failed to send email to {to_email}: {e}'))
        self.stdout.write(self.style.SUCCESS(f'{created} trial-end alerts created'))
