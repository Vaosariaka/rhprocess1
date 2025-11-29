from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Avg
from decimal import Decimal
import os
import csv
from datetime import date, timedelta

from core.models import Employee, Presence, Absence, PerformanceReview, Report


def _clamp_score(v):
    if v is None:
        return Decimal('0.00')
    if v < 0:
        v = 0
    if v > 100:
        v = 100
    return Decimal(str(round(v, 2)))


class Command(BaseCommand):
    help = 'Compute automated performance scores for employees and generate a CSV report.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', help='Directory to write reports (default: <BASE_DIR>/exports/reports)')

    def handle(self, *args, **options):
        today = date.today()
        one_year_ago = today - timedelta(days=365)

        base_dir = getattr(settings, 'BASE_DIR', None) or os.getcwd()
        out_dir = options.get('output_dir') or os.path.join(base_dir, 'exports', 'reports')
        os.makedirs(out_dir, exist_ok=True)

        filename = f'performance_report_{today.isoformat()}.csv'
        path = os.path.join(out_dir, filename)

        rows = []

        employees = Employee.objects.filter(is_active=True, archived=False)
        for emp in employees:
            # recent presence and absence metrics
            pres_qs = Presence.objects.filter(employee=emp, date__gte=one_year_ago, date__lte=today)
            abs_qs = Absence.objects.filter(employee=emp, date__gte=one_year_ago, date__lte=today)

            pres_count = pres_qs.count()
            abs_count = abs_qs.count()

            # average minutes late
            avg_minutes = pres_qs.aggregate(avg=Avg('minutes_late'))['avg'] or 0

            # Heuristic scoring (0-100): start at 100, penalize absences and lateness
            score = 100.0
            # Penalize 2 points per unjustified absence
            score -= float(abs_count) * 2.0
            # Penalize lateness: each 60 minutes of average late = -1 point
            score -= (float(avg_minutes) / 60.0) * 1.0

            # If employee has no presence/absence records, keep a neutral score of 75
            if pres_count + abs_count == 0:
                score = 75.0

            score = max(0.0, min(100.0, score))
            score_dec = _clamp_score(score)

            # Create or update a PerformanceReview for today
            pr, created = PerformanceReview.objects.get_or_create(employee=emp, review_date=today, defaults={'score': score_dec})
            if not created:
                pr.score = score_dec
                pr.save()

            rows.append({
                'matricule': emp.matricule,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'score': str(score_dec),
                'presences': pres_count,
                'absences': abs_count,
                'avg_minutes_late': round(float(avg_minutes), 2),
            })

        # Write CSV
        fieldnames = ['matricule', 'first_name', 'last_name', 'score', 'presences', 'absences', 'avg_minutes_late']
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

        # Create a Report record for admin tracking
        report = Report.objects.create(
            name=f'Performance report {today.isoformat()}',
            xlsx_path=path,
            pdf_path='',
            created_by=None,
        )

        self.stdout.write(self.style.SUCCESS(f'Wrote performance report: {path}'))
        self.stdout.write(self.style.SUCCESS(f'Created Report record id={report.id}'))
