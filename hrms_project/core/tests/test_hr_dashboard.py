import unittest
from django.test import SimpleTestCase


@unittest.skip("Static dashboard tests removed; replaced with dynamic DB-driven tests")
class HRDashboardViewTests(SimpleTestCase):
    def test_placeholder(self):
        # Placeholder to indicate static tests were removed.
        self.assertTrue(True)
