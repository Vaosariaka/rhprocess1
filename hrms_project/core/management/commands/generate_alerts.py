from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date

from core.models import Contract, LeaveRequest, Absence, Alerte


class Command(BaseCommand):
    help = 'Generate automatic HR alerts (contract end, unvalidated leaves, repeated absences)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, nargs='*', default=[90, 30, 15],
                            help='Days before contract end to generate alerts (default: 90 30 15)')
        parser.add_argument('--leave-age-days', type=int, default=7,
                            help='Create alerts for LeaveRequest in REQUESTED state older than this many days (default: 7)')
        parser.add_argument('--absence-count', type=int, default=3,
                            help='Number of un-justified absences within window to consider a repetition (default: 3)')
        parser.add_argument('--absence-window-days', type=int, default=30,
                            help='Time window (days) to count repeated absences (default: 30)')

    def handle(self, *args, **options):
        today = date.today()
        days_list = sorted(set(options.get('days') or [90, 30, 15]), reverse=True)
        leave_age = options.get('leave_age_days', 7)
        absence_count = options.get('absence_count', 3)
        absence_window = options.get('absence_window_days', 30)

        created = 0
        # 1) Contracts ending soon
        for d in days_list:
            target = today + timedelta(days=d)
            contracts = Contract.objects.filter(date_end__isnull=False, date_end=target, active=True)
            # also include those that end on that date (exact match)
            for c in contracts.select_related('employee'):
                # avoid duplicates: check if an open alert of same type exists in recent period
                exists = Alerte.objects.filter(employee=c.employee, type='CONTRACT_END', statut='OPEN',
                                               message__contains=str(c.date_end)).exists()
                if exists:
                    continue
                msg = f'Contract ending on {c.date_end.isoformat()} (in {d} days)'
                Alerte.objects.create(employee=c.employee, type='CONTRACT_END', message=msg, statut='OPEN')
                created += 1

        # 2) LeaveRequests in REQUESTED state older than threshold
        cutoff = timezone.now() - timedelta(days=leave_age)
        old_requests = LeaveRequest.objects.filter(status__in=['REQUESTED', 'DEPT_APPROVED']).filter(requested_at__lte=cutoff)
        for r in old_requests.select_related('employee'):
            exists = Alerte.objects.filter(employee=r.employee, type='LEAVE_UNVALIDATED', statut='OPEN',
                                           message__contains=str(r.pk)).exists()
            if exists:
                continue
            msg = f'Leave request #{r.pk} requested at {r.requested_at.isoformat()} still not validated (status={r.status})'
            Alerte.objects.create(employee=r.employee, type='LEAVE_UNVALIDATED', message=msg, statut='OPEN')
            created += 1

        # 3) Repeated un-justified absences in the given window
        window_start = today - timedelta(days=absence_window)
        # aggregate per employee
        emp_ids = Absence.objects.filter(justified=False, date__gte=window_start).values_list('employee', flat=True)
        from collections import Counter

        cnt = Counter(emp_ids)
        for emp_id, num in cnt.items():  
            if num >= absence_count:
                # ensure we don't spam duplicates: check for recent OPEN alert
                latest_abs = Absence.objects.filter(employee_id=emp_id, justified=False, date__gte=window_start).order_by('-date').first()
                employee = latest_abs.employee if latest_abs else None
                if not employee:
                    continue
                exists = Alerte.objects.filter(employee=employee, type='ABSENCE_REPETITION', statut='OPEN',
                                               message__contains=str(window_start)).exists()
                if exists:
                    continue
                msg = f'{num} un-justified absences between {window_start.isoformat()} and {today.isoformat()}'
                Alerte.objects.create(employee=employee, type='ABSENCE_REPETITION', message=msg, statut='OPEN')
                created += 1

        self.stdout.write(self.style.SUCCESS(f'generate_alerts: created {created} alert(s)'))