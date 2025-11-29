from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from core.models import Presence, Employee
import csv, os

class Command(BaseCommand):
    help = 'Export aggregated presence/time data for payroll for a given month (defaults to current month).'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Year (e.g. 2025)')
        parser.add_argument('--month', type=int, help='Month (1-12)')

    def handle(self, *args, **options):
        today = timezone.now().date()
        year = options.get('year') or today.year
        month = options.get('month') or today.month
        export_dir = os.path.join(os.getcwd(), 'exports')
        os.makedirs(export_dir, exist_ok=True)
        out_path = os.path.join(export_dir, f'time_export_{year}_{month:02d}.csv')
        rows = []
        headers = ['matricule', 'employee', 'worked_minutes', 'overtime_minutes', 'night_minutes', 'sunday_minutes', 'holiday_minutes', 'minutes_late', 'pause_minutes', 'pause_excess_minutes']
        for emp in Employee.objects.filter(is_active=True, archived=False):
            pres = Presence.objects.filter(employee=emp, date__year=year, date__month=month)
            totals = {
                'worked_minutes': 0,
                'overtime_minutes': 0,
                'night_minutes': 0,
                'sunday_minutes': 0,
                'holiday_minutes': 0,
                'minutes_late': 0,
                'pause_minutes': 0,
                'pause_excess_minutes': 0,
            }
            for p in pres:
                totals['worked_minutes'] += int(p.worked_minutes or 0)
                totals['overtime_minutes'] += int(p.overtime_minutes or 0)
                totals['night_minutes'] += int(p.night_minutes or 0)
                totals['sunday_minutes'] += int(p.sunday_minutes or 0)
                totals['holiday_minutes'] += int(p.holiday_minutes or 0)
                totals['minutes_late'] += int(p.minutes_late or 0)
                totals['pause_minutes'] += int(p.pause_minutes or 0)
                totals['pause_excess_minutes'] += int(p.pause_excess_minutes or 0)
            rows.append([
                emp.matricule,
                f"{emp.last_name} {emp.first_name}",
                totals['worked_minutes'],
                totals['overtime_minutes'],
                totals['night_minutes'],
                totals['sunday_minutes'],
                totals['holiday_minutes'],
                totals['minutes_late'],
                totals['pause_minutes'],
                totals['pause_excess_minutes'],
            ])
        # write CSV
        with open(out_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(rows)
        self.stdout.write(self.style.SUCCESS(f'Wrote time export to {out_path}'))
