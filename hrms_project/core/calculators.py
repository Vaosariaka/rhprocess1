from django.conf import settings


class PayrollCalculator:
    """
    Classe centralisée pour tous les calculs de paie
    Conforme au code du travail malgache
    """
    
    # ⚠️ PARAMÈTRES À CONFIGURER - valeurs par défaut
    SECTEUR = getattr(settings, 'HR_SECTEUR', 'non_agricole')
    HEURES_MENSUELLES_NON_AGRICOLE = getattr(settings, 'HR_HEURES_NON_AGRICOLE', 173.33)
    HEURES_MENSUELLES_AGRICOLE = getattr(settings, 'HR_HEURES_AGRICOLE', 200)
    JOURS_MENSUELS_NON_AGRICOLE = getattr(settings, 'HR_JOURS_NON_AGRICOLE', 21.67)
    JOURS_MENSUELS_AGRICOLE = getattr(settings, 'HR_JOURS_AGRICOLE', 25)
    PLAFOND_CNAPS = getattr(settings, 'HR_PLAFOND_CNAPS', 350000)
    TAUX_CNAPS_SALARIE = getattr(settings, 'HR_TAUX_CNAPS_SALARIE', 0.01)
    TAUX_SANITAIRE_SALARIE = getattr(settings, 'HR_TAUX_SANITAIRE_SALARIE', 0.01)
    
    @classmethod
    def get_heures_mensuelles(cls):
        """Retourne le nombre d'heures mensuelles selon le secteur"""
        if cls.SECTEUR == "agricole":
            return cls.HEURES_MENSUELLES_AGRICOLE
        else:
            return cls.HEURES_MENSUELLES_NON_AGRICOLE
    
    @classmethod
    def get_jours_mensuels(cls):
        """Retourne le nombre de jours mensuels selon le secteur"""
        if cls.SECTEUR == "agricole":
            return cls.JOURS_MENSUELS_AGRICOLE
        else:
            return cls.JOURS_MENSUELS_NON_AGRICOLE
    
    @classmethod
    def calculer_taux_horaire(cls, salaire_base):
        """Calcule le taux horaire selon le secteur"""
        heures_mensuelles = cls.get_heures_mensuelles()
        if salaire_base and heures_mensuelles:
            return round(salaire_base / heures_mensuelles, 2)
        return 0
    
    @classmethod
    def calculer_taux_journalier(cls, salaire_base):
        """Calcule le taux journalier selon le secteur"""
        jours_mensuels = cls.get_jours_mensuels()
        if salaire_base and jours_mensuels:
            return round(salaire_base / jours_mensuels, 2)
        return 0
    
    @classmethod
    def calculer_cnaps_salarie(cls, salaire_brut):
        """
        Calcule la cotisation CNAPS salarié
        Formule: min(salaire_brut × 1%, PLAFOND_CNAPS × 1%)
        """
        if not salaire_brut:
            return 0
        cotisation_sans_plafond = salaire_brut * cls.TAUX_CNAPS_SALARIE
        plafond_cotisation = cls.PLAFOND_CNAPS * cls.TAUX_CNAPS_SALARIE
        return min(cotisation_sans_plafond, plafond_cotisation)
    
    @classmethod
    def calculer_sanitaire_salarie(cls, salaire_brut):
        """
        Calcule la cotisation sanitaire salarié
        Formule: salaire_brut × 1% (sans plafond)
        """
        if not salaire_brut:
            return 0
        return salaire_brut * cls.TAUX_SANITAIRE_SALARIE
    
    @classmethod
    def calculer_base_imposable_irsa(cls, salaire_brut):
        """
        Calcule la base imposable pour l'IRSA
        Formule: Brut - CNAPS_salarié - Sanitaire_salarié
        """
        if not salaire_brut:
            return 0
        cnaps = cls.calculer_cnaps_salarie(salaire_brut)
        sanitaire = cls.calculer_sanitaire_salarie(salaire_brut)
        return salaire_brut - cnaps - sanitaire
    
    @classmethod
    def calculer_irsa(cls, base_imposable):
        """
        Calcule l'IRSA selon le barème progressif malgache
        Barème 2024:
        Tranche 1: 0 - 350,000 → 0%
        Tranche 2: 350,001 - 400,000 → 5%
        Tranche 3: 400,001 - 500,000 → 10%
        Tranche 4: 500,001 - 600,000 → 15%
        Tranche 5: 600,001 - 4,000,000 → 20%
        Tranche 6: > 4,000,000 → 25%
        """
        if not base_imposable or base_imposable <= 350000:
            return 0
        
        tax = 0
        # Tranche 2: 350,001 - 400,000 → 5%
        tranche2 = max(0, min(base_imposable - 350000, 50000))
        tax += tranche2 * 0.05
        
        # Tranche 3: 400,001 - 500,000 → 10%
        tranche3 = max(0, min(base_imposable - 400000, 100000))
        tax += tranche3 * 0.10
        
        # Tranche 4: 500,001 - 600,000 → 15%
        tranche4 = max(0, min(base_imposable - 500000, 100000))
        tax += tranche4 * 0.15
        
        # Tranche 5: 600,001 - 4,000,000 → 20%
        tranche5 = max(0, min(base_imposable - 600000, 3400000))
        tax += tranche5 * 0.20
        
        # Tranche 6: > 4,000,000 → 25%
        tranche6 = max(0, base_imposable - 4000000)
        tax += tranche6 * 0.25
        
        return round(tax)
    
    @classmethod
    def calculer_salaire_net(cls, salaire_brut):
        """
        Calcule le salaire net complet
        Formule: Net = Brut - (CNAPS + Sanitaire + IRSA)
        """
        if not salaire_brut:
            return 0
            
        cnaps = cls.calculer_cnaps_salarie(salaire_brut)
        sanitaire = cls.calculer_sanitaire_salarie(salaire_brut)
        base_imposable = cls.calculer_base_imposable_irsa(salaire_brut)
        irsa = cls.calculer_irsa(base_imposable)
        
        total_retenues = cnaps + sanitaire + irsa
        return salaire_brut - total_retenues
    
    @classmethod
    def generer_fiche_paie_complete(cls, salaire_brut):
        """
        Génère tous les calculs pour une fiche de paie complète
        """
        if not salaire_brut:
            return {}
            
        return {
            'salaire_brut': salaire_brut,
            'taux_horaire': cls.calculer_taux_horaire(salaire_brut),
            'taux_journalier': cls.calculer_taux_journalier(salaire_brut),
            'cnaps_salarie': cls.calculer_cnaps_salarie(salaire_brut),
            'sanitaire_salarie': cls.calculer_sanitaire_salarie(salaire_brut),
            'base_imposable_irsa': cls.calculer_base_imposable_irsa(salaire_brut),
            'irsa': cls.calculer_irsa(cls.calculer_base_imposable_irsa(salaire_brut)),
            'salaire_net': cls.calculer_salaire_net(salaire_brut),
            'total_retenues': cls.calculer_cnaps_salarie(salaire_brut) + 
                            cls.calculer_sanitaire_salarie(salaire_brut) + 
                            cls.calculer_irsa(cls.calculer_base_imposable_irsa(salaire_brut)),
            'parametres': {
                'secteur': cls.SECTEUR,
                'heures_mensuelles': cls.get_heures_mensuelles(),
                'jours_mensuels': cls.get_jours_mensuels(),
                'plafond_cnaps': cls.PLAFOND_CNAPS
            }
        }


# 🧪 FONCTIONS DE TEST
def tester_calculs_paie():
    """Tests pour vérifier la correction des calculs"""
    test_salaires = [500000, 1000000, 2000000, 5000000]
    
    for salaire in test_salaires:
        print(f"\n=== TEST SALAIRE {salaire:,} Ar ===")
        calculs = PayrollCalculator.generer_fiche_paie_complete(salaire)
        
        for key, value in calculs.items():
            if key != 'parametres':
                if isinstance(value, (int, float)):
                    print(f"{key}: {value:,.2f} Ar")
                else:
                    print(f"{key}: {value}")
        
        # Vérification cohérence
        total_retenues_calcule = calculs['cnaps_salarie'] + calculs['sanitaire_salarie'] + calculs['irsa']
        net_calcule = salaire - total_retenues_calcule
        assert abs(net_calcule - calculs['salaire_net']) < 1, f"Incohérence pour salaire {salaire}"

if __name__ == "__main__":
    tester_calculs_paie()
