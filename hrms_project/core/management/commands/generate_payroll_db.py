from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from core.models import Employee

class Command(BaseCommand):
    help = 'Generate payroll using DB stored procedure fn_generate_payroll for all employees for given month/year'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Year (e.g., 2025)')
        parser.add_argument('--month', type=int, help='Month (1-12)')
        parser.add_argument('--employee', type=int, help='Employee id (optional)')

    def handle(self, *args, **options):
        now = timezone.localdate()
        year = options.get('year') or now.year
        month = options.get('month') or now.month
        emp_id = options.get('employee')

        with connection.cursor() as cur:
            if emp_id:
                self.stdout.write(f'Generating payroll for employee {emp_id} for {month}/{year}')
                cur.execute("SELECT fn_generate_payroll(%s, %s, %s)", [emp_id, year, month])
            else:
                employees = Employee.objects.values_list('id', flat=True)
                total = employees.count()
                self.stdout.write(f'Generating payroll for {total} employees for {month}/{year}')
                for eid in employees:
                    cur.execute("SELECT fn_generate_payroll(%s, %s, %s)", [eid, year, month])
        self.stdout.write(self.style.SUCCESS('Payroll generation (DB) completed'))
