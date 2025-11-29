from decimal import Decimal
from datetime import date

from django.test import TestCase

from ..models import Employee, Contract, Presence
from ..payroll import compute_payroll_for_employee, DEFAULTS


class PayrollOvertimeTests(TestCase):
    def setUp(self):
        self.salary_base = Decimal('1000000')
        self.emp = Employee.objects.create(
            matricule='OVT1',
            first_name='Over',
            last_name='Time',
            salary_base=self.salary_base,
        )
        Contract.objects.create(
            employee=self.emp,
            type='CDI',
            date_start=date(2024, 1, 1),
            salary=self.salary_base,
            active=True,
        )
        self.reference_minutes = int((Decimal('200') * Decimal('60')))  # ensure worked minutes exceed expected hours

    def _make_presence(self, overtime_hours):
        Presence.objects.create(
            employee=self.emp,
            date=date(2025, 1, 15),
            worked_minutes=self.reference_minutes,
            overtime_minutes=int(Decimal(overtime_hours) * Decimal('60')),
        )

    def _expected_progressive_amount(self, overtime_hours):
        hours_per_month = DEFAULTS['HOURS_PER_MONTH']['NON_AGRI']
        hourly = self.salary_base / hours_per_month
        capped = min(Decimal(overtime_hours), Decimal('20'))
        first_8 = min(capped, Decimal('8'))
        pay_first = (first_8 * hourly * Decimal('1.3')).quantize(Decimal('0.01'))
        remaining = max(Decimal('0'), capped - Decimal('8'))
        next_12 = min(remaining, Decimal('12'))
        pay_next = (next_12 * hourly * Decimal('1.5')).quantize(Decimal('0.01'))
        return float((pay_first + pay_next).quantize(Decimal('0.01')))

    def test_overtime_progressive_majoration_applied(self):
        self._make_presence(Decimal('12'))
        result = compute_payroll_for_employee(self.emp, 2025, 1, dry_run=True)
        overtime_pay = result.get('details', {}).get('overtime_pay', 0.0)
        expected = self._expected_progressive_amount(Decimal('12'))
        self.assertAlmostEqual(overtime_pay, expected, places=2)

    def test_overtime_capped_to_twenty_hours(self):
        self._make_presence(Decimal('30'))
        result = compute_payroll_for_employee(self.emp, 2025, 1, dry_run=True)
        overtime_pay = result.get('details', {}).get('overtime_pay', 0.0)
        expected = self._expected_progressive_amount(Decimal('30'))
        self.assertAlmostEqual(overtime_pay, expected, places=2)
