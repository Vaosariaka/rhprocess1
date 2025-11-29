from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
import csv
from datetime import timedelta
from statistics import mean, median

from core.models import Employee, Payroll, Presence, Report


class Command(BaseCommand):
    help = 'Detect simple anomalies in payrolls and presence records and write a CSV report.'

    def add_arguments(self, parser):
        parser.add_argument('--payroll-lookback-months', type=int, default=6, help='Months to consider for payroll baseline')
        parser.add_argument('--presence-lookback-days', type=int, default=90, help='Days to consider for presence baseline')

    def handle(self, *args, **options):
        now = timezone.now().date()
        pl_months = int(options.get('payroll_lookback_months') or 6)
        pres_days = int(options.get('presence_lookback_days') or 90)

        anomalies = []

        # Payroll anomalies: compare each payroll to avg of prior N months for the same employee
        for p in Payroll.objects.select_related('employee').all().order_by('-year', '-month'):
            e = p.employee
            try:
                # build a list of prior payroll gross values for same employee in the lookback window
                prior_payrolls = Payroll.objects.filter(employee=e).exclude(pk=p.pk).order_by('-year','-month')[:pl_months]
                prior_vals = [float(x.gross_salary or 0) for x in prior_payrolls if x.gross_salary]
                if prior_vals:
                    baseline = mean(prior_vals)
                    gross = float(p.gross_salary or 0)
                    if baseline > 0:
                        dev = abs(gross - baseline) / baseline
                        # flag if deviation > 40% or if gross is zero
                        if dev > 0.4 or gross == 0:
                            anomalies.append({
                                'type': 'payroll',
                                'employee_id': e.pk,
                                'matricule': e.matricule or '',
                                'name': f"{e.last_name} {e.first_name}".strip(),
                                'period': f"{p.year}-{p.month}",
                                'value': gross,
                                'baseline': baseline,
                                'deviation_pct': round(dev * 100, 1),
                                'reason': 'gross deviation >40% or zero gross',
                            })
            except Exception:
                continue

        # Presence anomalies: for recent presences compare to median worked_minutes baseline
        pres_cutoff = now - timedelta(days=pres_days)
        pres_qs = Presence.objects.select_related('employee').filter(date__gte=pres_cutoff).order_by('-date')
        for pres in pres_qs:
            e = pres.employee
            try:
                hist = Presence.objects.filter(employee=e, date__lt=pres.date).order_by('-date')[:pres_days]
                hist_vals = [int(x.worked_minutes or 0) for x in hist if x.worked_minutes is not None]
                if hist_vals:
                    base_m = median(hist_vals)
                    cur = int(pres.worked_minutes or 0)
                    # flag if current > 3x median or < 10% median
                    if base_m > 0:
                        if cur > base_m * 3 or cur < max(1, base_m * 0.1):
                            anomalies.append({
                                'type': 'presence',
                                'employee_id': e.pk,
                                'matricule': e.matricule or '',
                                'name': f"{e.last_name} {e.first_name}".strip(),
                                'period': pres.date.isoformat(),
                                'value': cur,
                                'baseline': base_m,
                                'deviation_pct': round((cur - base_m) / base_m * 100, 1) if base_m else 0,
                                'reason': 'worked_minutes outlier compared to median',
                            })
            except Exception:
                continue

        # write CSV
        base = Path(__file__).resolve().parents[4]
        reports_dir = base / 'exports' / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        now_s = now.isoformat()
        fname = reports_dir / f"anomalies_{now_s}.csv"

        if anomalies:
            with open(fname, 'w', newline='', encoding='utf-8') as fh:
                fieldnames = ['type', 'employee_id', 'matricule', 'name', 'period', 'value', 'baseline', 'deviation_pct', 'reason']
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in anomalies:
                    writer.writerow(row)
            self.stdout.write(self.style.SUCCESS(f'Wrote anomalies report: {fname}'))
            try:
                Report.objects.create(report_type='anomalies', file_path=str(fname), generated_by='management_command')
            except Exception:
                pass
        else:
            self.stdout.write('No anomalies detected.')
