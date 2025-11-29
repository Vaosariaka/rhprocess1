from django.core.management.base import BaseCommand
from datetime import timedelta, date
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from core.models import Employee, Absence, Alerte


class Command(BaseCommand):
    help = 'Detect employees with repeated unjustified absences in a window and create alerts.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90, help='Window in days to scan')
        parser.add_argument('--threshold', type=int, default=3, help='Number of unjustified absences to trigger alert')
        parser.add_argument('--send-email', action='store_true', help='Also send email notifications to employees/HR')

    def handle(self, *args, **options):
        days = options['days']
        threshold = options['threshold']
        since = (timezone.now() - timedelta(days=days)).date()
        employees = Employee.objects.filter(is_active=True)
        created = 0
        for emp in employees:
            count = Absence.objects.filter(employee=emp, justified=False, date__gte=since).count()
            if count >= threshold:
                msg = f"Employee {emp} has {count} unjustified absences since {since} (threshold {threshold})."
                Alerte.objects.create(employee=emp, type='REPEATED_ABSENCE', message=msg)
                created += 1
                self.stdout.write(self.style.NOTICE(msg))
                if options.get('send_email'):
                    # render email templates
                    to_email = emp.email
                    context = {'employee': emp, 'count': count, 'since': since, 'threshold': threshold}
                    subject = f'Alert: repeated absences ({count})'
                    text_body = render_to_string('core/emails/repeated_absence.txt', context)
                    html_body = render_to_string('core/emails/repeated_absence.html', context)
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None) or 'no-reply@localhost'
                    recipients = []
                    if to_email:
                        recipients.append(to_email)
                    # optionally notify HR emails if configured
                    hr_list = getattr(settings, 'HR_NOTIFICATION_EMAILS', [])
                    if hr_list:
                        recipients.extend(hr_list)
                    if recipients:
                        try:
                            msg_email = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=recipients)
                            msg_email.attach_alternative(html_body, 'text/html')
                            msg_email.send(fail_silently=False)
                            self.stdout.write(self.style.NOTICE(f'Email sent to {recipients}'))
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Failed to send emails to {recipients}: {e}'))
        self.stdout.write(self.style.SUCCESS(f'{created} repeated-absence alerts created'))
