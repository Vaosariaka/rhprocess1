from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Seed demo data: employees, competencies, presences, payrolls, performance reviews'

    def handle(self, *args, **options):
        from core.models import Employee, Competency, EmployeeCompetency, Presence, Payroll, PerformanceReview, LeaveBalance
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # create demo user if none
        if not User.objects.filter(username='demo_hr').exists():
            User.objects.create_superuser('demo_hr', 'demo_hr@example.com', 'demo')

        # Create employees
        demo_employees = []
        today = date.today()
        for i in range(1, 6):
            matricule = f'E{i:03d}'
            emp, created = Employee.objects.get_or_create(
                matricule=matricule,
                defaults={
                    'first_name': f'Employee{i}',
                    'last_name': 'Demo',
                    'email': f'emp{i}@example.com',
                    'hire_date': today - timedelta(days=365 * (i % 4 + 1)),
                    'salary_base': 300000 + i * 50000,
                    'is_active': True,
                }
            )
            demo_employees.append(emp)

        # Competencies
        comps = ['Communication', 'Python', 'Management']
        comp_objs = {}
        for name in comps:
            c, _ = Competency.objects.get_or_create(name=name, defaults={'description': f'{name} skill'})
            comp_objs[name] = c

        # Assign competencies
        for idx, emp in enumerate(demo_employees):
            # Communication level varies
            EmployeeCompetency.objects.update_or_create(employee=emp, competency=comp_objs['Communication'], defaults={'level': (idx % 5) + 1})
            EmployeeCompetency.objects.update_or_create(employee=emp, competency=comp_objs['Python'], defaults={'level': (idx % 3) + 1})
            if idx % 2 == 0:
                EmployeeCompetency.objects.update_or_create(employee=emp, competency=comp_objs['Management'], defaults={'level': 2})

        # Presences: last 30 days
        for emp in demo_employees:
            for d in range(1, 21):
                dt = today - timedelta(days=d)
                # skip weekends to keep data simple
                if dt.weekday() >= 5:
                    continue
                Presence.objects.update_or_create(employee=emp, date=dt, defaults={
                    'time_in': timezone.datetime(2025,1,1,8,0).time(),
                    'time_out': timezone.datetime(2025,1,1,17,0).time(),
                    'minutes_late': 0,
                    'worked_minutes': 8 * 60,
                })

        # Payrolls: last 3 months
        for emp in demo_employees:
            for m in range(0, 3):
                d = today - timedelta(days=30 * m)
                month = d.month
                year = d.year
                Payroll.objects.update_or_create(employee=emp, month=month, year=year, defaults={
                    'salary_base': emp.salary_base,
                })

        # Leave balances for current year
        for emp in demo_employees:
            lb, _ = LeaveBalance.objects.get_or_create(employee=emp, year=today.year, defaults={'entitlement_days': 20, 'used_days': 2})

        # Performance reviews
        for idx, emp in enumerate(demo_employees):
            PerformanceReview.objects.update_or_create(employee=emp, review_date=today - timedelta(days=90), defaults={'score': 60 + idx * 5, 'comments': 'Demo review'})

        self.stdout.write(self.style.SUCCESS(f'Seeded demo data: {len(demo_employees)} employees, {len(comp_objs)} competencies.'))
