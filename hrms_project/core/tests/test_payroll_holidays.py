from django.test import TestCase
from django.conf import settings
from datetime import date
from ..models import Employee, Presence, Contract
from ..payroll import compute_payroll_for_employee


class PayrollHolidayTests(TestCase):
    def setUp(self):
        # ensure HR_HOLIDAYS contains a known date for the test year
        settings.HR_HOLIDAYS = ['01-01']
        self.emp = Employee.objects.create(matricule='TST1', first_name='Test', last_name='User', salary_base=100000)
        # create an active contract so payroll computation has a salary base
        Contract.objects.create(employee=self.emp, type='CDI', date_start=date(2024, 1, 1), salary=100000, active=True)

    def test_presence_on_holiday_counts_as_holiday_minutes(self):
        # Create a presence on Jan 1st of 2025 (holiday)
        p = Presence.objects.create(employee=self.emp, date=date(2025, 1, 1), worked_minutes=8*60, holiday_minutes=0)
        # compute payroll for January 2025
        result = compute_payroll_for_employee(self.emp, 2025, 1, dry_run=True)
        # the details should include holiday_premium > 0 because presence on holiday was inferred
        details = result.get('details', {})
        holiday_premium = details.get('holiday_premium', 0)
        self.assertGreater(float(holiday_premium), 0.0, 'Holiday premium should be applied when working on a configured holiday')
