from django.test import TestCase
from django.core.management import call_command, CommandError
from django.conf import settings
from pathlib import Path


class ImportCommandTest(TestCase):
    def test_missing_file_raises(self):
        with self.assertRaises(CommandError):
            call_command('import_payroll', payroll_file='file_that_does_not_exist.xlsx')

    def test_dry_run_on_sample_file(self):
        # Try to run dry-run on the sample file if present in workspace parent
        base = Path(settings.BASE_DIR)
        candidate = base.parent / 'ETAT DE PAIE MAJ.xlsx'
        if candidate.exists():
            call_command('import_payroll', payroll_file=str(candidate), dry_run=True)
        else:
            # skip if sample not present
            self.skipTest('Sample Excel file not present')
