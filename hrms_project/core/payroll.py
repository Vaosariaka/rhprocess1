from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange
from datetime import date

from django.conf import settings

from .models import Contract, Presence, Absence, LeaveBalance, Alerte

# Default payroll settings (can be overridden in Django settings)
DEFAULTS = {
    'HOURS_PER_MONTH': {'NON_AGRI': Decimal('173.33'), 'AGRI': Decimal('200')},
    'CNAPS': {
        'NON_AGRI_TOTAL': Decimal('0.13'),
        'AGRI_TOTAL': Decimal('0.08'),
        'EMPLOYEE_SHARE': Decimal('0.04'),
        'EMPLOYER_SHARE': Decimal('0.09'),
        # default plafonnement expressed as a multiplier of the salary (eg MULTIPLIER:8)
        'CAP': 'MULTIPLIER:8',
    },
    'OSTIE_RATE': Decimal('0.01'),
    'OVERTIME_RATES': {'NIGHT': Decimal('0.30'), 'SUNDAY': Decimal('1.00'), 'HOLIDAY': Decimal('2.00')},
    'WORK_DAY_HOURS': Decimal('8'),
    'LATE_PENALTY_MULTIPLIER': Decimal('2.5'),
}


def _get(cfg_path, default=None):
    cfg = getattr(settings, 'HR_PAYROLL', {})
    cur = cfg
    for p in cfg_path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def _get_work_day_hours():
    raw = _get(['WORK_DAY_HOURS'], DEFAULTS['WORK_DAY_HOURS'])
    try:
        value = Decimal(str(raw))
        return value if value > 0 else DEFAULTS['WORK_DAY_HOURS']
    except Exception:
        return DEFAULTS['WORK_DAY_HOURS']


def _get_late_penalty_multiplier():
    raw = _get(['LATE_PENALTY_MULTIPLIER'], DEFAULTS['LATE_PENALTY_MULTIPLIER'])
    try:
        value = Decimal(str(raw))
        return value if value > 0 else DEFAULTS['LATE_PENALTY_MULTIPLIER']
    except Exception:
        return DEFAULTS['LATE_PENALTY_MULTIPLIER']


def _consume_leave_for_lateness(employee, payroll_year, leave_days_needed, *, apply_changes=False):
    """Consume leave days across the rolling 3-year window to cover lateness."""
    if leave_days_needed <= 0:
        return Decimal('0')
    years = [payroll_year, payroll_year - 1, payroll_year - 2]
    remaining = Decimal(leave_days_needed)
    consumed = Decimal('0')
    for yr in years:
        lb = LeaveBalance.objects.filter(employee=employee, year=yr).first()
        if not lb:
            continue
        entitlement = Decimal(str(lb.entitlement_days or 0))
        used = Decimal(str(lb.used_days or 0))
        available = entitlement - used
        if available <= 0:
            continue
        take = available if available < remaining else remaining
        if take <= 0:
            continue
        consumed += take
        if apply_changes:
            lb.used_days = (used + take).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            lb.save(update_fields=['used_days'])
        remaining -= take
        if remaining <= 0:
            break
    return consumed


def _close_late_alerts(employee, year, month):
    try:
        start = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end = date(year, month, last_day)
        Alerte.objects.filter(
            employee=employee,
            type='LATE',
            statut='OPEN',
            date_creation__date__range=(start, end)
        ).update(statut='RESOLVED')
    except Exception:
        pass


def compute_payroll_for_employee(employee, year, month, *, dry_run=True):
    """Compute payroll for one employee for the given year/month.
    Returns a dict with breakdown: gross, deductions, net, details.
    Uses presence records and absences to determine worked hours and deductions.
    """
    # get active contract
    contract = Contract.objects.filter(employee=employee, active=True).order_by('-date_start').first()
    sector = contract.sector if contract else 'NON_AGRI'

    hours_per_month = Decimal(str(_get(['HOURS_PER_MONTH', sector], DEFAULTS['HOURS_PER_MONTH'][sector])))
    cnaps_cfg = _get(['CNAPS'], DEFAULTS['CNAPS'])
    ostie_rate = Decimal(str(_get(['OSTIE_RATE'], DEFAULTS['OSTIE_RATE'])))
    overtime_rates = _get(['OVERTIME_RATES'], DEFAULTS['OVERTIME_RATES'])

    salary_base = Decimal(contract.salary) if contract else Decimal('0')

    # presence within month
    presences = list(Presence.objects.filter(employee=employee, date__year=year, date__month=month))
    total_worked_minutes = sum([p.worked_minutes or 0 for p in presences])
    hours_worked = (Decimal(total_worked_minutes) / Decimal(60)).quantize(Decimal('0.01'))

    # basic gross: salary_base (assume monthly salary covers normal hours)
    gross = Decimal(salary_base)

    # detect overtime (hours beyond expected)
    expected_hours = hours_per_month
    overtime_hours = Decimal('0')
    if hours_worked > expected_hours:
        overtime_hours = (hours_worked - expected_hours).quantize(Decimal('0.01'))

    # naive handling: treat overtime as normal hourly * (1 + average overtime rate)
    if expected_hours > 0:
        hourly = salary_base / hours_per_month
    else:
        hourly = Decimal('0')

    # compute overtime and special majorations from Presence breakdowns if available
    overtime_pay = Decimal('0')
    night_premium = Decimal('0')
    sunday_premium = Decimal('0')
    holiday_premium = Decimal('0')

    # Build holiday set for the given year from settings (supports MM-DD recurring or YYYY-MM-DD)
    holiday_dates = set()
    for h in getattr(settings, 'HR_HOLIDAYS', []):
        try:
            if len(h) == 5 and h[2] == '-':
                # MM-DD recurring
                mm, dd = int(h.split('-')[0]), int(h.split('-')[1])
                holiday_dates.add(date(year, mm, dd))
            else:
                # try full date YYYY-MM-DD
                y, m, d = [int(x) for x in h.split('-')]
                holiday_dates.add(date(y, m, d))
        except Exception:
            # ignore parse errors
            continue

    total_overtime_minutes = sum([(p.overtime_minutes or 0) for p in presences])
    total_night_minutes = sum([(p.night_minutes or 0) for p in presences])
    # If presence rows already tag sunday_minutes/holiday_minutes use them, otherwise infer from date
    total_sunday_minutes = sum([(p.sunday_minutes or 0) for p in presences])
    total_holiday_minutes = sum([(p.holiday_minutes or 0) for p in presences])
    total_pause_excess_minutes = sum([(p.pause_excess_minutes or 0) for p in presences])
    total_recorded_late_minutes = sum([(p.minutes_late or 0) for p in presences])
    total_late_minutes = total_recorded_late_minutes + total_pause_excess_minutes

    # Infer holiday minutes for presences on configured holiday dates if not already counted
    if holiday_dates:
        for p in presences:
            try:
                if (p.date in holiday_dates) and ((p.holiday_minutes or 0) == 0):
                    # count the worked minutes on that day as holiday minutes
                    total_holiday_minutes += (p.worked_minutes or 0)
            except Exception:
                continue

    # convert minutes to hours
    overtime_hours_from_pres = (Decimal(total_overtime_minutes) / Decimal(60)).quantize(Decimal('0.01'))
    night_hours = (Decimal(total_night_minutes) / Decimal(60)).quantize(Decimal('0.01'))
    sunday_hours = (Decimal(total_sunday_minutes) / Decimal(60)).quantize(Decimal('0.01'))
    holiday_hours = (Decimal(total_holiday_minutes) / Decimal(60)).quantize(Decimal('0.01'))
    late_hours = (Decimal(total_late_minutes) / Decimal(60)).quantize(Decimal('0.01'))

    # base overtime pay with progressive majoration (first 8h +30%, next 12h +50%)
    if overtime_hours_from_pres > 0 and hourly > 0:
        overtime_capped = min(overtime_hours_from_pres, Decimal('20'))
        first_8_hours = min(overtime_capped, Decimal('8'))
        pay_first_8 = (first_8_hours * hourly * Decimal('1.3')).quantize(Decimal('0.01'))

        remaining_hours = max(Decimal('0'), overtime_capped - Decimal('8'))
        next_12_hours = min(remaining_hours, Decimal('12'))
        pay_next_12 = (next_12_hours * hourly * Decimal('1.5')).quantize(Decimal('0.01'))

        overtime_pay = (pay_first_8 + pay_next_12).quantize(Decimal('0.01'))
    else:
        overtime_pay = Decimal('0')

    # premiums: apply configured multipliers (e.g., NIGHT: 0.30 means +30% of base hourly)
    night_rate = Decimal(str(overtime_rates.get('NIGHT', DEFAULTS['OVERTIME_RATES']['NIGHT'])))
    sunday_rate = Decimal(str(overtime_rates.get('SUNDAY', DEFAULTS['OVERTIME_RATES']['SUNDAY'])))
    holiday_rate = Decimal(str(overtime_rates.get('HOLIDAY', DEFAULTS['OVERTIME_RATES']['HOLIDAY'])))

    night_premium = (night_hours * hourly * night_rate).quantize(Decimal('0.01'))
    sunday_premium = (sunday_hours * hourly * sunday_rate).quantize(Decimal('0.01'))
    holiday_premium = (holiday_hours * hourly * holiday_rate).quantize(Decimal('0.01'))

    late_leave_days = Decimal('0')
    late_salary_penalty = Decimal('0')
    late_hours_penalized = Decimal('0')
    hourly_penalty_rate = Decimal('0')
    if total_late_minutes > 0 and salary_base > 0:
        work_day_hours = _get_work_day_hours()
        work_day_minutes = work_day_hours * Decimal('60') if work_day_hours > 0 else Decimal('480')
        penalty_multiplier = _get_late_penalty_multiplier()
        late_minutes_decimal = Decimal(total_late_minutes)
        if work_day_minutes > 0:
            leave_days_needed = late_minutes_decimal / work_day_minutes
            leave_days_consumed = _consume_leave_for_lateness(
                employee,
                year,
                leave_days_needed,
                apply_changes=not dry_run,
            )
            leave_minutes_used = leave_days_consumed * work_day_minutes
        else:
            leave_days_consumed = Decimal('0')
            leave_minutes_used = Decimal('0')
        penalty_minutes = max(Decimal('0'), Decimal(total_late_minutes) - leave_minutes_used)
        late_hours_penalized = (penalty_minutes / Decimal('60')).quantize(Decimal('0.01'))
        hourly_penalty_rate = (hourly * penalty_multiplier).quantize(Decimal('0.01')) if hourly > 0 else Decimal('0')
        late_salary_penalty = (late_hours_penalized * hourly_penalty_rate).quantize(Decimal('0.01'))
        late_leave_days = leave_days_consumed.quantize(Decimal('0.01')) if leave_days_consumed > 0 else Decimal('0')
        if not dry_run and total_late_minutes > 0:
            _close_late_alerts(employee, year, month)

    gross += overtime_pay + night_premium + sunday_premium + holiday_premium

    # additions for special premiums (simple approach: sum minutes flagged in presence as late/nights not stored here)
    # In a later step we will track specific night/sunday/holiday hours in presence to compute exact premiums.

    # compute CNAPS (employee + employer shares) and OSTIE
    employee_cnaps_rate = Decimal(str(cnaps_cfg.get('EMPLOYEE_SHARE', DEFAULTS['CNAPS']['EMPLOYEE_SHARE'])))
    employer_cnaps_rate = Decimal(str(cnaps_cfg.get('EMPLOYER_SHARE', DEFAULTS['CNAPS']['EMPLOYER_SHARE'])))
    cnaps_cap = cnaps_cfg.get('CAP')
    cnaps_base = gross
    # if CAP is numeric, use it; if CAP is an expression like 'MULTIPLIER:8' we allow multiplier from salary
    if cnaps_cap:
        try:
            cnaps_cap_dec = Decimal(str(cnaps_cap))
            cnaps_base = min(cnaps_cap_dec, gross)
        except Exception:
            # fallback: if cap indicates multiplier, e.g. 'MULTIPLIER:8'
            if isinstance(cnaps_cap, str) and cnaps_cap.upper().startswith('MULTIPLIER:'):
                try:
                    mul = Decimal(cnaps_cap.split(':', 1)[1])
                    cnaps_base = min((salary_base * mul), gross)
                except Exception:
                    cnaps_base = gross

    cnaps_employee = (cnaps_base * employee_cnaps_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    cnaps_employer = (cnaps_base * employer_cnaps_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    ostie = (gross * Decimal(ostie_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # absences: sum unjustified absence days in the month and deduct proportionally
    absences = Absence.objects.filter(employee=employee, date__year=year, date__month=month, justified=False)
    absent_days = absences.count()
    # approximate deduction: (salary_base / expected_working_days) * absent_days
    # assume 26 working days per month if not provided
    working_days = Decimal('26')
    if expected_hours > 0:
        # approximate daily salary from monthly salary
        daily = (salary_base / working_days).quantize(Decimal('0.01'))
    else:
        daily = Decimal('0')
    absence_deduction = (daily * absent_days).quantize(Decimal('0.01'))

    # total deductions (employee-side): CNAPS employee + OSTIE + absence deduction + other employee deductions
    deductions = (cnaps_employee + ostie + absence_deduction + late_salary_penalty).quantize(Decimal('0.01'))

    
    # include employer contributions in details (not deducted from net)
    employer_contributions = {
        'cnaps_employer': float(cnaps_employer),
    }

    late_notes = []
    if late_leave_days > 0:
        late_notes.append(f"Retards convertis en congé: {late_leave_days} jour(s)")
    if late_salary_penalty > 0:
        late_notes.append(
            f"Déduction retard: {late_hours_penalized} h × {hourly_penalty_rate} = {late_salary_penalty}"
        )
    if total_pause_excess_minutes > 0:
        late_notes.append(f"Pauses excédentaires: {total_pause_excess_minutes} minute(s)")
    late_notes_text = ' | '.join(late_notes)

    net = (gross - deductions).quantize(Decimal('0.01'))

    result = {
        'employee_id': employee.id,
        'year': year,
        'month': month,
        'salary_base': float(salary_base),
        'hours_worked': float(hours_worked),
        'overtime_hours': float(overtime_hours),
        'hourly_rate': float(hourly),
        'gross': float(gross),
    'cnaps_employee': float(cnaps_employee),
    'cnaps_employer': float(cnaps_employer),
        'ostie': float(ostie),
        'absence_deduction': float(absence_deduction),
        'deductions': float(deductions),
        'net': float(net),
        'details': {
            'overtime_pay': float(overtime_pay),
            'night_premium': float(night_premium),
            'sunday_premium': float(sunday_premium),
            'holiday_premium': float(holiday_premium),
            'late_minutes_from_presence': int(total_recorded_late_minutes),
            'late_minutes_from_pause': int(total_pause_excess_minutes),
            'late_minutes_total': int(total_late_minutes),
            'late_hours_total': float(late_hours),
            'late_hours_penalized': float(late_hours_penalized),
            'late_leave_days': float(late_leave_days),
            'late_salary_penalty': float(late_salary_penalty),
            'late_penalty_rate': float(hourly_penalty_rate),
            'late_notes': late_notes_text,
            'employer_contributions': employer_contributions,
        }
    }

    return result
