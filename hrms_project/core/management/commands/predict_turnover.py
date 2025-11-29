from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
import csv
from datetime import timedelta

from core.models import Employee, Absence, PerformanceReview, Report, Presence


class Command(BaseCommand):
    help = 'Predict turnover risk per active employee (heuristic). Writes CSV to exports/reports and creates a Report record.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=365, help='Lookback window for absences (days)')
        parser.add_argument('--min-score', type=int, default=0, help='Minimum score to include in output')

    def handle(self, *args, **options):
        days = int(options.get('days') or 365)
        min_score = int(options.get('min_score') or 0)
        now = timezone.now().date()
        lookback = now - timedelta(days=days)

        rows = []
        for e in Employee.objects.filter(is_active=True, archived=False).order_by('last_name', 'first_name'):
            # tenure months
            tenure_months = 0
            try:
                if e.hire_date:
                    tenure_months = max(0, (now.year - e.hire_date.year) * 12 + (now.month - e.hire_date.month))
            except Exception:
                tenure_months = 0

            # recent unjustified absences
            try:
                abs_count = Absence.objects.filter(employee=e, date__gte=lookback, justified=False).count()
            except Exception:
                abs_count = 0

            # recent lates (minutes) in last 90 days
            try:
                recent_presence = Presence.objects.filter(employee=e, date__gte=(now - timedelta(days=90)))
                late_minutes = recent_presence.aggregate(total=('minutes_late'))['total'] if recent_presence.exists() else 0
                # fallback aggregate may be None
                if late_minutes is None:
                    late_minutes = 0
            except Exception:
                late_minutes = 0

            # latest performance score (0-100) if available
            perf_score = None
            try:
                pr = PerformanceReview.objects.filter(employee=e).order_by('-review_date').first()
                if pr and getattr(pr, 'score', None) is not None:
                    perf_score = float(pr.score)
            except Exception:
                perf_score = None

            # Heuristic risk scoring (0-100): higher means more likely to churn
            # - base: 10
            # - short tenure (<6 months): +25
            # - absences: +min(30, abs_count * 6)
            # - late minutes: +min(20, late_minutes / 30)
            # - low performance: if perf_score available, add (50 - perf_score)*0.6 if perf_score < 50
            score = 10
            if tenure_months < 6:
                score += 25
            score += min(30, abs_count * 6)
            try:
                score += min(20, int(late_minutes) // 30)
            except Exception:
                pass
            if perf_score is not None and perf_score < 50:
                score += int((50 - perf_score) * 0.6)

            # clamp
            score = max(0, min(100, int(score)))

            if score >= min_score:
                rows.append({
                    'employee_id': e.pk,
                    'matricule': e.matricule or '',
                    'name': f"{e.last_name} {e.first_name}".strip(),
                    'tenure_months': tenure_months,
                    'absences_last_{}d'.format(days): abs_count,
                    'late_minutes_90d': int(late_minutes or 0),
                    'latest_perf_score': perf_score if perf_score is not None else '',
                    'risk_score': score,
                })

        # ensure exports/reports exists
        base = Path(__file__).resolve().parents[4]
        reports_dir = base / 'exports' / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        fname = reports_dir / f"turnover_prediction_{now.isoformat()}.csv"

        if rows:
            with open(fname, 'w', newline='', encoding='utf-8') as fh:
                fieldnames = list(rows[0].keys())
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow(r)
            self.stdout.write(self.style.SUCCESS(f'Wrote turnover prediction: {fname}'))
            # create Report record if model available
            try:
                Report.objects.create(report_type='turnover_prediction', file_path=str(fname), generated_by='management_command')
            except Exception:
                pass
        else:
            self.stdout.write('No rows matched the filter; no report generated.')
