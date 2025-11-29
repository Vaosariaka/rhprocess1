from django.test import TestCase
from django.conf import settings
from core.calculators import PayrollCalculator


class PayrollCalculatorTests(TestCase):
    def test_basic_consistency(self):
        """Net should equal brut - (cnaps + sanitaire + irsa) for several salaries"""
        salaries = [0, 100000, 350000, 350001, 400000, 500000, 600000, 1000000, 5000000]
        for s in salaries:
            with self.subTest(s=s):
                data = PayrollCalculator.generer_fiche_paie_complete(s)
                if not data:
                    # for s == 0 expect empty dict
                    self.assertEqual(s, 0)
                    continue
                brut = data['salaire_brut']
                cnaps = data['cnaps_salarie']
                sanitaire = data['sanitaire_salarie']
                irsa = data['irsa']
                total_ret = cnaps + sanitaire + irsa
                expected_net = brut - total_ret
                # Use approx equality for floats
                self.assertAlmostEqual(data['salaire_net'], expected_net, delta=1)

    def test_irsa_zero_below_threshold(self):
        """IRSA should be zero for base_imposable <= 350000"""
        self.assertEqual(PayrollCalculator.calculer_irsa(0), 0)
        self.assertEqual(PayrollCalculator.calculer_irsa(350000), 0)
        self.assertEqual(PayrollCalculator.calculer_irsa(349999), 0)

    def test_rates_and_hours(self):
        """Taux horaire/journalier should be positive for positive salary"""
        s = 1000000
        th = PayrollCalculator.calculer_taux_horaire(s)
        tj = PayrollCalculator.calculer_taux_journalier(s)
        self.assertGreater(th, 0)
        self.assertGreater(tj, 0)

