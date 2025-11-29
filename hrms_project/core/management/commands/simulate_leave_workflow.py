from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from datetime import date, timedelta
from core.models import Employee, LeaveRequest, LeaveBalance


class Command(BaseCommand):
    help = 'Simulate creating a LeaveRequest and progressing it through request->dept->hr approval (used for testing).'

    def handle(self, *args, **options):
        # ensure at least one employee
        emp = Employee.objects.first()
        if not emp:
            emp = Employee.objects.create(matricule='TST1', first_name='Test', last_name='User')
            self.stdout.write(self.style.NOTICE(f'Created test employee {emp}'))

        # run accrual to give entitlement
        call_command('accrue_leaves')

        # create a leave request for 5 days starting tomorrow
        start = date.today() + timedelta(days=1)
        end = start + timedelta(days=4)
        lr = LeaveRequest.objects.create(employee=emp, start_date=start, end_date=end, leave_type='PAID', reason='Test leave')
        self.stdout.write(self.style.NOTICE(f'Created LeaveRequest id={lr.id} status={lr.status} days={lr.days}'))

        # mark requested
        lr.status = 'REQUESTED'
        lr.save()
        self.stdout.write(self.style.NOTICE(f'LeaveRequest id={lr.id} set to REQUESTED'))

        # mark dept approved
        lr.status = 'DEPT_APPROVED'
        lr.save()
        self.stdout.write(self.style.NOTICE(f'LeaveRequest id={lr.id} set to DEPT_APPROVED'))

        # attempt HR approve
        success, msg = lr.approve_by_hr()
        if success:
            self.stdout.write(self.style.SUCCESS(f'HR approval successful: {msg}'))
        else:
            self.stdout.write(self.style.ERROR(f'HR approval blocked: {msg}'))

        # show current leave balance
        lb = LeaveBalance.objects.filter(employee=emp, year=date.today().year).first()
        if lb:
            self.stdout.write(self.style.NOTICE(f'LeaveBalance year={lb.year} entitlement={lb.entitlement_days} used={lb.used_days} available={float(lb.entitlement_days - lb.used_days):.2f}'))
