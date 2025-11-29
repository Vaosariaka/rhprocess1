from django.test import TestCase
from django.core.management import call_command
from django.conf import settings
import os
from datetime import date

from core.models import Employee, Presence, Absence, PerformanceReview, Report


class PerformanceCommandTest(TestCase):
    def setUp(self):
        self.emp = Employee.objects.create(matricule='E001', first_name='Test', last_name='User', is_active=True)
        # add some presence and absence
        Presence.objects.create(employee=self.emp, date=date.today(), minutes_late=10)
        Absence.objects.create(employee=self.emp, date=date.today())

    def test_compute_performance_scores_creates_review_and_report(self):
        # run command
        call_command('compute_performance_scores')

        # assert performance review for today exists
        pr = PerformanceReview.objects.filter(employee=self.emp, review_date=date.today()).first()
        self.assertIsNotNone(pr, 'PerformanceReview should have been created')
        self.assertIsNotNone(pr.score, 'Score should be set')

        # assert a Report object was created and file exists
        rpt = Report.objects.order_by('-created_at').first()
        self.assertIsNotNone(rpt, 'Report record should exist')
        self.assertTrue(os.path.exists(rpt.xlsx_path), f'Report file should exist at {rpt.xlsx_path}')
