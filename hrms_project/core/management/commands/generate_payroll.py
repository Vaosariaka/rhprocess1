from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Employee, Payroll
from core.payroll import compute_payroll_for_employee


class Command(BaseCommand):
    help = 'Generate payroll for all employees for a given month/year (defaults to previous month)'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Year (e.g., 2025)')
        parser.add_argument('--month', type=int, help='Month (1-12)')

    def handle(self, *args, **options):
        now = timezone.localdate()
        year = options.get('year') or now.year
        month = options.get('month') or now.month
        self.stdout.write(f'Generating payroll for {month}/{year}')
        employees = Employee.objects.filter()
        created = 0
        for e in employees:
            data = compute_payroll_for_employee(e, year, month, dry_run=False)
            # create or update Payroll record: we persist salary_base and deductions
            # but gross/net are considered computed values and not authoritative.
            defaults = {
                'salary_base': data.get('salary_base', 0),
                'deductions': data.get('deductions', 0),
                'etat_paie': 'MAJ',
                'notes': str(data.get('details', {})),
            }
            obj, created_flag = Payroll.objects.update_or_create(employee=e, year=year, month=month, defaults=defaults)
            if created_flag:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Payroll generation done. Records created/updated: {employees.count()}'))
