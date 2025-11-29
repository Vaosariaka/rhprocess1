from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, date
import os
import csv
from pathlib import Path

try:
    from openpyxl import Workbook
except Exception:
    Workbook = None

from core.models import Presence, Employee, Report


def _parse_date(s):
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    raise ValueError(f'Invalid date format: {s}')


class Command(BaseCommand):
    help = 'Generate presence (attendance) report for a given period.'

    def add_arguments(self, parser):
        parser.add_argument('--start', help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end', help='End date (YYYY-MM-DD)')
        parser.add_argument('--department', help='Filter by department name', default=None)
        parser.add_argument('--format', choices=['xlsx', 'csv'], default='xlsx')
        parser.add_argument('--output-dir', default=os.path.join(os.getcwd(), 'exports'))
        parser.add_argument('--create-report', action='store_true', help='Create a Report DB row pointing to the generated file')

    def handle(self, *args, **options):
        start = _parse_date(options.get('start')) if options.get('start') else None
        end = _parse_date(options.get('end')) if options.get('end') else None
        dept = options.get('department')
        fmt = options.get('format')
        outdir = options.get('output_dir') if options.get('output_dir') else options.get('output-dir')
        create_report = options.get('create_report') if options.get('create_report') is not None else options.get('create-report')

        if start is None:
            # default to first day of current month
            today = date.today()
            start = today.replace(day=1)
        if end is None:
            end = date.today()

        if start > end:
            raise CommandError('Start date must be before end date')

        qs = Presence.objects.filter(date__gte=start, date__lte=end)
        if dept:
            qs = qs.filter(employee__department=dept)

        # build aggregates per employee
        employees = {}
        details = []
        for p in qs.select_related('employee').order_by('employee__matricule', 'date'):
            emp = p.employee
            key = emp.pk
            if key not in employees:
                employees[key] = {
                    'matricule': emp.matricule,
                    'name': f'{emp.last_name} {emp.first_name}',
                    'present_days': 0,
                    'minutes_late': 0,
                    'worked_minutes': 0,
                    'pause_minutes': 0,
                    'pause_excess_minutes': 0,
                }
            employees[key]['present_days'] += 1
            employees[key]['minutes_late'] += (p.minutes_late or 0)
            employees[key]['worked_minutes'] += (p.worked_minutes or 0)
            employees[key]['pause_minutes'] += (p.pause_minutes or 0)
            employees[key]['pause_excess_minutes'] += (p.pause_excess_minutes or 0)
            details.append({
                'matricule': emp.matricule,
                'name': f'{emp.last_name} {emp.first_name}',
                'date': p.date.isoformat(),
                'time_in': p.time_in.isoformat() if p.time_in else '',
                'time_out': p.time_out.isoformat() if p.time_out else '',
                'minutes_late': p.minutes_late,
                'worked_minutes': p.worked_minutes,
                'pause_minutes': p.pause_minutes,
                'pause_excess_minutes': p.pause_excess_minutes,
            })

        # ensure output dir
        os.makedirs(outdir, exist_ok=True)
        base = f'presence_report_{start.isoformat()}_{end.isoformat()}'
        primary_path = None
        if fmt == 'xlsx' and Workbook:
            fname = os.path.join(outdir, base + '.xlsx')
            wb = Workbook()
            # summary sheet
            ws = wb.active
            ws.title = 'Summary'
            ws.append(['Matricule', 'Name', 'Days Present', 'Minutes Late', 'Worked Minutes', 'Pause Minutes', 'Pause Excess Minutes'])
            for v in employees.values():
                ws.append([
                    v['matricule'],
                    v['name'],
                    v['present_days'],
                    v['minutes_late'],
                    v['worked_minutes'],
                    v['pause_minutes'],
                    v['pause_excess_minutes'],
                ])
            # details sheet
            ws2 = wb.create_sheet('Details')
            ws2.append(['Matricule', 'Name', 'Date', 'Time In', 'Time Out', 'Minutes Late', 'Worked Minutes', 'Pause Minutes', 'Pause Excess Minutes'])
            for d in details:
                ws2.append([
                    d['matricule'],
                    d['name'],
                    d['date'],
                    d['time_in'],
                    d['time_out'],
                    d['minutes_late'],
                    d['worked_minutes'],
                    d['pause_minutes'],
                    d['pause_excess_minutes'],
                ])
            wb.save(fname)
            self.stdout.write(self.style.SUCCESS(f'Wrote XLSX presence report to {fname}'))
            primary_path = Path(fname).resolve()
        else:
            # fallback to CSV with two files
            fname = os.path.join(outdir, base + '.summary.csv')
            with open(fname, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Matricule', 'Name', 'Days Present', 'Minutes Late', 'Worked Minutes', 'Pause Minutes', 'Pause Excess Minutes'])
                for v in employees.values():
                    writer.writerow([
                        v['matricule'],
                        v['name'],
                        v['present_days'],
                        v['minutes_late'],
                        v['worked_minutes'],
                        v['pause_minutes'],
                        v['pause_excess_minutes'],
                    ])
            fname2 = os.path.join(outdir, base + '.details.csv')
            with open(fname2, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Matricule', 'Name', 'Date', 'Time In', 'Time Out', 'Minutes Late', 'Worked Minutes', 'Pause Minutes', 'Pause Excess Minutes'])
                for d in details:
                    writer.writerow([
                        d['matricule'],
                        d['name'],
                        d['date'],
                        d['time_in'],
                        d['time_out'],
                        d['minutes_late'],
                        d['worked_minutes'],
                        d['pause_minutes'],
                        d['pause_excess_minutes'],
                    ])
            self.stdout.write(self.style.SUCCESS(f'Wrote CSV presence reports to {fname} and {fname2}'))
            primary_path = Path(fname).resolve()

        # Optionally create a Report row pointing to the primary file
        try:
            if create_report:
                rpath = str(primary_path) if primary_path else ''
                report_kwargs = {
                    'name': f'Presence {start.isoformat()} to {end.isoformat()}',
                    'pdf_path': '',
                    'xlsx_path': '',
                    'created_by': None,
                }
                if rpath.lower().endswith(('.xlsx', '.xls', '.csv')):
                    report_kwargs['xlsx_path'] = rpath
                else:
                    report_kwargs['pdf_path'] = rpath
                Report.objects.create(**report_kwargs)
                self.stdout.write(self.style.SUCCESS('Created Report DB row'))
        except Exception:
            self.stdout.write(self.style.WARNING('Could not create Report DB row'))
