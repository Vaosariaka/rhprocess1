from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from core.models import Employee, Contract, LeaveBalance, LeaveAccrual


class Command(BaseCommand):
    help = 'Accrue monthly leave days (2.5 days per active employee per month). Records accruals to avoid duplicates.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Year to apply accrual (defaults to current year)')
        parser.add_argument('--month', type=int, help='Month to apply accrual (1-12, defaults to current month)')
        parser.add_argument('--days', type=str, help='Days to accrue per month (decimal), default 2.5', default='2.5')

    def handle(self, *args, **options):
        today = timezone.localdate()
        year = options.get('year') or today.year
        month = options.get('month') or today.month
        days = Decimal(options.get('days') or '2.5')

        self.stdout.write(f"Starting accrual for {year}-{month:02d}: {days} days per active employee")

        # Select employees that have at least one active contract overlapping this month
        import calendar
        first_day = timezone.datetime(year, month, 1).date()
        last_day = timezone.datetime(year, month, calendar.monthrange(year, month)[1]).date()

        employees = set()
        for contract in Contract.objects.filter(active=True):
            if contract.date_start and contract.date_start <= last_day and (not contract.date_end or contract.date_end >= first_day):
                employees.add(contract.employee)

        created = 0
        skipped = 0
        for emp in employees:
            # check if accrual already exists
            exists = LeaveAccrual.objects.filter(employee=emp, year=year, month=month).exists()
            if exists:
                skipped += 1
                continue
            # create/ensure leave balance for the year
            lb, _ = LeaveBalance.objects.get_or_create(employee=emp, year=year, defaults={'entitlement_days': 0, 'used_days': 0})
            lb.entitlement_days = Decimal(lb.entitlement_days) + days
            lb.save()
            LeaveAccrual.objects.create(employee=emp, year=year, month=month, days=days)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Accrual completed: created={created}, skipped={skipped}, total_employees={len(employees)}"))
