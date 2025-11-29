from decimal import Decimal
from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone

from ..models import Employee, Contract, Presence, LeaveBalance, Alerte
from ..payroll import compute_payroll_for_employee, DEFAULTS


class PayrollLatenessTests(TestCase):
    def setUp(self):
        self.salary_base = Decimal('1000000')
        self.emp = Employee.objects.create(
            matricule='LATE1',
            first_name='Late',
            last_name='Worker',
            salary_base=self.salary_base,
        )
        Contract.objects.create(
            employee=self.emp,
            type='CDI',
            date_start=date(2024, 1, 1),
            salary=self.salary_base,
            active=True,
        )

    def _make_presence(self, minutes_late, day=15):
        Presence.objects.create(
            employee=self.emp,
            date=date(2025, 1, day),
            worked_minutes=8 * 60,
            minutes_late=minutes_late,
        )

    def test_late_minutes_consume_leave_before_salary_penalty(self):
        LeaveBalance.objects.create(
            employee=self.emp,
            year=2025,
            entitlement_days=Decimal('10.00'),
            used_days=Decimal('0.00'),
        )
        self._make_presence(480)
        result = compute_payroll_for_employee(self.emp, 2025, 1, dry_run=False)
        lb = LeaveBalance.objects.get(employee=self.emp, year=2025)
        self.assertEqual(lb.used_days, Decimal('1.00'))
        self.assertAlmostEqual(result['details'].get('late_leave_days', 0.0), 1.0, places=2)
        self.assertAlmostEqual(result['details'].get('late_salary_penalty', 0.0), 0.0, places=2)

    def test_salary_penalty_applied_when_no_leave_available(self):
        self._make_presence(90)
        result = compute_payroll_for_employee(self.emp, 2025, 1, dry_run=True)
        hourly = self.salary_base / DEFAULTS['HOURS_PER_MONTH']['NON_AGRI']
        hourly_penalty_rate = (hourly * DEFAULTS['LATE_PENALTY_MULTIPLIER']).quantize(Decimal('0.01'))
        expected_penalty = (Decimal('1.5') * hourly_penalty_rate).quantize(Decimal('0.01'))
        self.assertAlmostEqual(result['details'].get('late_salary_penalty', 0.0), float(expected_penalty), places=2)

    def test_late_alerts_marked_resolved_after_payroll(self):
        self._make_presence(60)
        alert = Alerte.objects.create(employee=self.emp, type='LATE', message='Late test', statut='OPEN')
        alert.date_creation = timezone.make_aware(datetime(2025, 1, 20, 9, 0, 0))
        alert.save(update_fields=['date_creation'])
        compute_payroll_for_employee(self.emp, 2025, 1, dry_run=False)
        alert.refresh_from_db()
        self.assertEqual(alert.statut, 'RESOLVED')
