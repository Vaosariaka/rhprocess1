from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta

from ..models import Employee, ReplacementRequest, SuggestedReplacement


class PlannerApproveTests(TestCase):
    def setUp(self):
        # create an HR user and a regular user
        self.hr = User.objects.create_user('hr', 'hr@example.com', 'pass')
        self.hr.is_staff = True
        self.hr.save()

        self.regular = User.objects.create_user('user', 'user@example.com', 'pass')

        # create employees and a replacement request
        self.emp = Employee.objects.create(matricule='M001', first_name='John', last_name='Doe')
        self.req = ReplacementRequest.objects.create(
            requester=self.hr,
            target_employee=self.emp,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
        )

        # candidate
        self.cand = Employee.objects.create(matricule='M002', first_name='Jane', last_name='Smith')
        self.sugg = SuggestedReplacement.objects.create(request=self.req, candidate=self.cand, score=75)

    def test_hr_can_approve_suggestion(self):
        self.client.force_login(self.hr)
        url = reverse('approve_suggestion', args=[self.sugg.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.sugg.refresh_from_db()
        self.assertTrue(self.sugg.approved)
        data = resp.json()
        self.assertEqual(data.get('result'), 'ok')

    def test_regular_cannot_approve(self):
        self.client.force_login(self.regular)
        url = reverse('approve_suggestion', args=[self.sugg.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        self.sugg.refresh_from_db()
        self.assertFalse(self.sugg.approved)
