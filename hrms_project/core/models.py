from datetime import datetime, timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class Category(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Employee(models.Model):
    matricule = models.CharField(max_length=32, unique=True)
    email = models.EmailField(blank=True, null=True)
    cnaps_number = models.CharField(max_length=64, blank=True, null=True)
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    function = models.CharField(max_length=128, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, null=True, blank=True)
    civil_status = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    department = models.CharField(max_length=128, blank=True)
    service = models.CharField(max_length=128, blank=True)
    osti_number = models.CharField(max_length=64, blank=True, null=True)
    salary_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    phone = models.CharField(max_length=32, blank=True)
    photo = models.ImageField(upload_to='employees/photos/%Y/%m/%d/', null=True, blank=True)
    emergency_contact = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.matricule} - {self.last_name} {self.first_name}"

    def get_full_name(self):
        return f"{(self.last_name or '').upper()} {(self.first_name or '').title()}".strip()

    def get_initials(self):
        first_initial = (self.first_name[:1] if self.first_name else '').upper()
        last_initial = (self.last_name[:1] if self.last_name else '').upper()
        initials = (first_initial + last_initial).strip()
        return initials or (self.matricule[:2].upper() if self.matricule else '--')

    def get_active_contract(self):
        return self.contracts.filter(active=True).order_by('-date_start', '-created_at').first()

    def get_seniority_components(self, as_of=None):
        if not self.hire_date:
            return None
        if as_of is None:
            try:
                as_of = timezone.localdate()
            except Exception:
                as_of = timezone.now().date()
        if as_of < self.hire_date:
            as_of = self.hire_date
        delta = relativedelta(as_of, self.hire_date)
        return delta.years, delta.months, delta.days

    def get_seniority_display(self, as_of=None):
        components = self.get_seniority_components(as_of=as_of)
        if not components:
            return None
        years, months, days = components
        parts = []
        if years:
            parts.append(f"{years} an{'s' if years > 1 else ''}")
        if months:
            parts.append(f"{months} mois")
        if days or not parts:
            parts.append(f"{days} jour{'s' if days > 1 else ''}")
        return ' '.join(parts)

    def get_salary_summary(self):
        latest_entry = self.position_histories.exclude(new_salary__isnull=True).order_by('-effective_date', '-created_at').first()
        if latest_entry:
            effective_date = latest_entry.effective_date or (latest_entry.created_at.date() if latest_entry.created_at else None)
            return {
                'current': latest_entry.new_salary,
                'previous': latest_entry.old_salary,
                'effective_date': effective_date,
            }
        return {
            'current': self.salary_base,
            'previous': None,
            'effective_date': self.hire_date,
        }

    def get_contract_badge(self):
        contract = self.get_active_contract()
        if not contract:
            return None
        color_map = {
            'ESSAI': '#f97316',  # orange
            'CDD': '#dc2626',    # red
            'CDI': '#065f46',    # dark green
        }
        return {
            'label': contract.get_type_display(),
            'color': color_map.get(contract.type, '#334155'),
            'contract': contract,
        }

    def get_contract_status_banner(self, as_of=None):
        contract = self.get_active_contract()
        if not contract:
            return None
        if as_of is None:
            try:
                as_of = timezone.localdate()
            except Exception:
                as_of = timezone.now().date()
        days_left = None
        if contract.date_end:
            days_left = (contract.date_end - as_of).days
        if contract.type == 'ESSAI' and contract.date_end:
            if days_left is not None and days_left >= 0:
                message = f"Fin d'essai dans {days_left} jour{'s' if days_left > 1 else ''}"
            else:
                message = "Période d'essai dépassée"
        elif contract.type == 'CDD' and contract.date_end:
            if days_left is not None and days_left >= 0:
                message = f"CDD se termine le {contract.date_end.strftime('%d/%m/%Y')}"
            else:
                message = "CDD expiré — action requise"
        else:
            message = "Contrat CDI actif"
        return {
            'message': message,
            'days_left': days_left,
            'contract': contract,
        }

    def get_upcoming_deadlines(self, limit=3, as_of=None):
        if as_of is None:
            try:
                as_of = timezone.localdate()
            except Exception:
                as_of = timezone.now().date()
        events = []
        contract = self.get_active_contract()
        if contract and contract.date_end:
            label = "Fin d'essai" if contract.type == 'ESSAI' else ('Fin CDD' if contract.type == 'CDD' else 'Fin contrat')
            severity = 'danger' if (contract.date_end - as_of).days <= 30 else 'warning'
            events.append({
                'label': label,
                'date': contract.date_end,
                'severity': severity,
            })
        documents = self.documents.filter(valid_to__isnull=False, valid_to__gte=as_of).order_by('valid_to')
        for doc in documents[:limit]:
            days_left = (doc.valid_to - as_of).days
            if days_left > 90:
                severity = 'safe'
            elif days_left >= 0:
                severity = 'warning'
            else:
                severity = 'danger'
            events.append({
                'label': f"{doc.get_type_display()}",
                'date': doc.valid_to,
                'severity': severity,
            })
        alerts = getattr(self, 'alerts', None)
        if alerts is not None:
            for alert in alerts.filter(statut='OPEN').order_by('date_creation')[:limit]:
                events.append({
                    'label': alert.message,
                    'date': alert.date_creation.date() if alert.date_creation else as_of,
                    'severity': 'info',
                })
        events.sort(key=lambda item: item['date'] or as_of)
        deduped = []
        for event in events:
            if event not in deduped:
                deduped.append(event)
        return deduped[:limit]


class Contract(models.Model):
    CONTRACT_TYPES = [
        ('ESSAI', 'Essai'),
        ('CDD', 'CDD'),
        ('CDI', 'CDI'),
        ('AUTRE', 'Autre'),
    ]
    SECTOR_CHOICES = [
        ('NON_AGRI', 'Non agricole'),
        ('AGRI', 'Agricole'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contracts')
    type = models.CharField(max_length=20, choices=CONTRACT_TYPES)
    sector = models.CharField(max_length=20, choices=SECTOR_CHOICES, default='NON_AGRI')
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    trial_renewals = models.PositiveSmallIntegerField(default=0)
    max_trial_renewals = models.PositiveSmallIntegerField(default=1)
    auto_convert_to_cdi = models.BooleanField(default=False)
    full_time = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.type} ({self.date_start} -> {self.date_end})"

    # Business logic helpers
    def is_trial(self):
        return self.type == 'ESSAI'

    def can_renew_trial(self):
        return self.is_trial() and self.trial_renewals < self.max_trial_renewals

    def renew_trial(self, extend_days=180, by_user=None):
        """Renew the trial period by extend_days (default ~6 months).

        Returns True if renewed, False if cannot renew.
        Records a ContractHistory entry.
        """
        if not self.can_renew_trial():
            return False
        # extend end date
        if self.date_end:
            self.date_end = self.date_end + timedelta(days=extend_days)
        else:
            self.date_end = self.date_start + timedelta(days=extend_days)
        self.trial_renewals = self.trial_renewals + 1
        self.save()
        ContractHistory.objects.create(employee=self.employee, contract=self, action='TRIAL_RENEWED', details=f'Renewed trial to {self.date_end}')
        return True

    def convert_to_cdd(self, months=12, by_user=None):
        """Convert contract to a CDD for given months (default 12).
        Ensures date_end is set and marks type.
        """
        self.type = 'CDD'
        if not self.date_end or (self.date_end and (self.date_end - self.date_start).days <= 0):
            self.date_end = self.date_start + timedelta(days=int(months * 30))
        # ensure CDD max 24 months
        max_end = self.date_start + timedelta(days=365 * 2)
        if self.date_end and self.date_end > max_end:
            self.date_end = max_end
        self.save()
        ContractHistory.objects.create(employee=self.employee, contract=self, action='CONVERTED_TO_CDD', details=f'Converted to CDD until {self.date_end}')
        return True

    def convert_to_cdi(self, by_user=None):
        """Convert contract to CDI (remove end date).
        """
        self.type = 'CDI'
        self.date_end = None
        self.save()
        ContractHistory.objects.create(employee=self.employee, contract=self, action='CONVERTED_TO_CDI', details='Converted to CDI')
        return True

    def terminate(self, date_termination=None, reason='', by_user=None):
        """Terminate the contract: set active=False and date_end if provided.
        Record history and create an alert.
        """
        self.active = False
        if date_termination:
            self.date_end = date_termination
        self.save()
        ContractHistory.objects.create(employee=self.employee, contract=self, action='TERMINATED', details=reason)
        # create alert for HR
        Alerte.objects.create(employee=self.employee, type='CONTRACT_TERMINATED', message=f'Contract terminated: {reason}', statut='OPEN')
        return True


class ContractHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contract_histories')
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    date_action = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.action} @ {self.date_action}"


class Document(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    TYPE_CHOICES = [
        ('ID', 'Carte d\'identité'),
        ('CV', 'CV'),
        ('DIPLOMA', 'Diplôme'),
        ('CONTRACT', 'Contrat'),
        ('CERT', 'Certificat'),
        ('PHOTO', 'Photo'),
        ('OTHER', 'Autre'),
    ]
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default='OTHER')
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255, blank=True)
    # Validity window for documents (optional) so we can notify expirations
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    date_upload = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = self.file.name
        super().save(*args, **kwargs)

    def is_expired(self, as_of=None):
        """Return True if document is expired as of given date (defaults to today)."""
        from datetime import date

        if as_of is None:
            as_of = date.today()
        if self.valid_to:
            return self.valid_to < as_of
        return False

    def days_until_expiry(self, as_of=None):
        from datetime import date
        if as_of is None:
            as_of = date.today()
        if not self.valid_to:
            return None
        return (self.valid_to - as_of).days

    def __str__(self):
        return f"{self.employee} - {self.type}"


class PositionHistory(models.Model):
    """Tracks changes of position/service/salary for an employee."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='position_histories')
    old_position = models.CharField(max_length=128, blank=True)
    new_position = models.CharField(max_length=128, blank=True)
    old_service = models.CharField(max_length=128, blank=True)
    new_service = models.CharField(max_length=128, blank=True)
    old_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} position change @ {self.effective_date or self.created_at}"



class Leave(models.Model):
    LEAVE_TYPES = [
        ('PAID', 'Congé payé'),
        ('UNPAID', 'Congé sans solde'),
        ('SICK', 'Congé maladie'),
        ('MAT', 'Congé maternité/paternité'),
        ('OTHER', 'Autre'),
    ]
    STATUS = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvée'),
        ('REJECTED', 'Refusée'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPES, default='PAID')
    status = models.CharField(max_length=10, choices=STATUS, default='PENDING')
    note = models.TextField(blank=True)

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.employee} {self.leave_type} {self.start_date} -> {self.end_date}"


class LeaveRequest(models.Model):
    STATUS = [
        ('DRAFT', 'Draft'),
        ('REQUESTED', 'Requested'),
        ('DEPT_APPROVED', 'Dept Approved'),
        ('HR_APPROVED', 'HR Approved'),
        ('REFUSED', 'Refused'),
        ('CANCELLED', 'Cancelled'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=10, choices=Leave.LEAVE_TYPES, default='PAID')
    status = models.CharField(max_length=20, choices=STATUS, default='DRAFT')
    reason = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    dept_approver = models.ForeignKey('auth.User', null=True, blank=True, related_name='dept_approvals', on_delete=models.SET_NULL)
    hr_approver = models.ForeignKey('auth.User', null=True, blank=True, related_name='hr_approvals', on_delete=models.SET_NULL)
    decision_note = models.TextField(blank=True)
    attachment = models.FileField(upload_to='leaves/%Y/%m/%d/', null=True, blank=True)

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"LeaveRequest {self.employee} {self.start_date} -> {self.end_date} ({self.status})"

    def approve_by_hr(self, hr_user=None):
        """Attempt HR approval: check entitlement and create a Leave if allowed.

        Returns (success: bool, message: str)
        """
        from datetime import date

        min_tenure_days = getattr(settings, 'HR_PAYROLL', {}).get('PAID_LEAVE_MIN_TENURE_DAYS', 365)
        hire_date = getattr(self.employee, 'hire_date', None)
        start_ref = self.start_date or date.today()
        tenure_days = (start_ref - hire_date).days if hire_date else 0
        if tenure_days < min_tenure_days:
            return False, (
                "Employé non éligible: la période d'essai est inférieure à 1 an. "
                "Veuillez attendre l'ancienneté requise avant d'approuver ce congé."
            )

        # only paid leaves require entitlement check
        if self.leave_type == 'PAID':
            avail = employee_available_leave(self.employee, as_of_date=self.start_date)
            if self.days > avail:
                return False, f'Insufficient leave balance: requested {self.days}, available {avail:.2f}'

        # create approved Leave record
        Leave.objects.create(employee=self.employee, start_date=self.start_date, end_date=self.end_date, leave_type=self.leave_type, status='APPROVED', note=self.reason)
        self.status = 'HR_APPROVED'
        if hr_user:
            self.hr_approver = hr_user
        self.save()
        # update LeaveBalance used_days for year
        year = self.start_date.year
        lb = _ensure_leave_balance(self.employee, year)
        lb.used_days = float(lb.used_days) + self.days
        lb.save()
        return True, 'Leave approved and record created.'

    def clean(self):
        """Validate minimum advance notice and other business rules on leave request."""
        from django.core.exceptions import ValidationError
        from datetime import date

        min_days = 15
        if self.start_date and (self.start_date - (date.today())).days < min_days and self.status in ['REQUESTED', 'DEPT_APPROVED', 'HR_APPROVED']:
            raise ValidationError(f'Les demandes de congé doivent être faites au moins {min_days} jours à l\'avance.')

        # If requested and paid leave, check availability and create an alert (but allow saving for HR to review)
        if self.leave_type == 'PAID' and self.status == 'REQUESTED':
            avail = employee_available_leave(self.employee, as_of_date=self.start_date or date.today())
            if self.days > avail:
                # create an alert for RH to review insufficient balance
                Alerte.objects.create(employee=self.employee, type='INSUFFICIENT_LEAVE', message=f'Requested {self.days} days but only {avail:.2f} available', statut='OPEN')

        min_tenure_days = getattr(settings, 'HR_PAYROLL', {}).get('PAID_LEAVE_MIN_TENURE_DAYS', 365)
        hire_date = getattr(self.employee, 'hire_date', None)
        start_ref = self.start_date or date.today()
        tenure_days = (start_ref - hire_date).days if hire_date else 0
        if self.status in ['REQUESTED', 'DEPT_APPROVED', 'HR_APPROVED'] and tenure_days < min_tenure_days:
            message = (
                f"Congé demandé alors que l'ancienneté est de {tenure_days} jour(s). "
                f"Minimum requis: {min_tenure_days} jour(s)."
            )
            Alerte.objects.get_or_create(
                employee=self.employee,
                type='LEAVE_INELIGIBLE',
                message=message,
                defaults={'statut': 'OPEN'}
            )

    def save(self, *args, **kwargs):
        # ensure validation runs
        try:
            self.clean()
        except Exception:
            # allow save so admin can override, but ensure alert created in clean
            pass
        super().save(*args, **kwargs)


class LeaveBalance(models.Model):
    """Tracks leave entitlement and usage per employee per year.

    For simplicity we store entitlement_days and used_days; accrual job will
    increment entitlement_days by 2.5 each month for active employees.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField()
    entitlement_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('employee', 'year')

    def available_days(self):
        return float(self.entitlement_days - self.used_days)


class LeaveAccrual(models.Model):
    """Record of monthly leave accruals to avoid double-applying accruals.

    Each record indicates that `days` were credited to the employee for the
    specified (year, month). The management command will create one record per
    employee/month when accrual runs.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_accruals')
    year = models.IntegerField()
    month = models.IntegerField()
    days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')

    def __str__(self):
        return f"Accrual {self.employee} {self.year}-{self.month}: {self.days}d"


def _days_between(start_date, end_date):
    return (end_date - start_date).days + 1


def employee_available_leave(employee, as_of_date=None):
    """Compute available paid leave for the employee for the year of as_of_date.

    This is a pragmatic computation: we look at the LeaveBalance for the year,
    subtract approved Leave days and pending requested days (REQUESTED/DEPT_APPROVED).
    """
    from datetime import date

    if as_of_date is None:
        as_of_date = date.today()
    year = as_of_date.year

    # Consider balances of the current year and up to two previous years (3-year window)
    years = [year, year - 1, year - 2]
    total_entitlement = 0.0
    total_used = 0.0
    for y in years:
        lb = LeaveBalance.objects.filter(employee=employee, year=y).first()
        if lb:
            total_entitlement += float(lb.entitlement_days)
            total_used += float(lb.used_days)

    # Count approved leaves overlapping any of the years in the window
    approved_overlap = 0
    for l in Leave.objects.filter(employee=employee, status='APPROVED'):
        # compute overlap days between leave and the 3-year window
        overlap = 0
        for y in years:
            from datetime import date

            year_start = date(y, 1, 1)
            year_end = date(y, 12, 31)
            # overlap between [l.start_date, l.end_date] and [year_start, year_end]
            s = max(l.start_date, year_start)
            e = min(l.end_date, year_end)
            if s <= e:
                overlap += (e - s).days + 1
        approved_overlap += overlap

    # Count pending requested days overlapping the window
    pending_overlap = 0
    for r in LeaveRequest.objects.filter(employee=employee, status__in=['REQUESTED', 'DEPT_APPROVED', 'HR_APPROVED']):
        overlap = 0
        for y in years:
            from datetime import date

            year_start = date(y, 1, 1)
            year_end = date(y, 12, 31)
            s = max(r.start_date, year_start)
            e = min(r.end_date, year_end)
            if s <= e:
                overlap += (e - s).days + 1
        pending_overlap += overlap

    available = total_entitlement - total_used - approved_overlap - pending_overlap
    return float(available)


def _ensure_leave_balance(employee, year):
    lb, created = LeaveBalance.objects.get_or_create(employee=employee, year=year)
    return lb


def _approx_months_to_days(months):
    # approximate month as 30 days for accrual math
    return int(months * 30)


def compute_anciennete(employee, as_of_date=None):
    """Compute ancienneté based on hire_date (in days, years, months) including trial.

    Returns a dict: {'days': int, 'years': int, 'months': int}
    """
    from datetime import date

    if as_of_date is None:
        as_of_date = date.today()
    if getattr(employee, 'hire_date', None):
        delta = as_of_date - employee.hire_date
        days = delta.days
        years = days // 365
        months = (days % 365) // 30
        return {'days': days, 'years': years, 'months': months}
    # fallback: sum contract durations
    total_days = 0
    for c in employee.contracts.all():
        if not c.date_start:
            continue
        end = c.date_end or as_of_date
        total_days += (end - c.date_start).days
    years = total_days // 365
    months = (total_days % 365) // 30
    return {'days': total_days, 'years': years, 'months': months}


class LeaveHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_histories')
    leave = models.ForeignKey(Leave, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.action} @ {self.date_action}"


class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    month = models.IntegerField()  # 1-12
    year = models.IntegerField()
    salary_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    etat_paie = models.CharField(max_length=50, default='MAJ')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year}"

    def save(self, *args, **kwargs):
        """Auto-calculate gross_salary, net_salary, and deductions before saving."""
        try:
            from .payroll import compute_payroll_for_employee
            # Calculate payroll breakdown
            data = compute_payroll_for_employee(
                self.employee, 
                int(self.year), 
                int(self.month), 
                dry_run=True
            )
            if isinstance(data, dict):
                # Update calculated fields
                self.gross_salary = data.get('gross', 0)
                self.deductions = data.get('deductions', 0)
                self.net_salary = data.get('net', 0)
        except Exception as e:
            # If calculation fails, keep existing values or zeros
            pass
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Computed properties (read-only): gross/net should be computed using
    # payroll logic rather than treated as authoritative stored fields.
    # We keep the DB columns for backward compatibility/auditing, but prefer
    # to compute values on the fly for display and report generation.
    # ------------------------------------------------------------------
    @property
    def computed_breakdown(self):
        """Return the payroll breakdown computed for this employee/month.

        Uses the shared compute_payroll_for_employee() function in
        `core.payroll` to ensure the same logic is used across commands
        and views.
        """
        try:
            from .payroll import compute_payroll_for_employee
            data = compute_payroll_for_employee(self.employee, int(self.year), int(self.month), dry_run=True)
            return data
        except Exception:
            return {}

    @property
    def gross_computed(self):
        """Gross salary computed on the fly (float) or None on error."""
        data = self.computed_breakdown
        return data.get('gross') if isinstance(data, dict) else None

    @property
    def net_computed(self):
        """Net salary computed on the fly (float) or None on error."""
        data = self.computed_breakdown
        return data.get('net') if isinstance(data, dict) else None

    @property
    def deductions_computed(self):
        data = self.computed_breakdown
        return data.get('deductions') if isinstance(data, dict) else None


class Absence(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='absences')
    date = models.DateField()
    reason = models.TextField(blank=True)
    justified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Absence {self.employee} @ {self.date}"


class Presence(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='presences')
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    minutes_late = models.IntegerField(default=0)
    worked_minutes = models.IntegerField(default=0)
    pause_minutes = models.IntegerField(default=30)
    pause_excess_minutes = models.IntegerField(default=0)
    # minute-level breakdowns to support pay majorations and overtime calculation
    overtime_minutes = models.IntegerField(default=0)
    night_minutes = models.IntegerField(default=0)
    sunday_minutes = models.IntegerField(default=0)
    holiday_minutes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"Presence {self.employee} @ {self.date}"

    def _pause_config(self):
        cfg = getattr(settings, 'HR_PAYROLL', {})
        standard = int(cfg.get('PAUSE_STANDARD_MINUTES', 30) or 30)
        tolerance = int(cfg.get('PAUSE_TOLERANCE_MINUTES', 5) or 0)
        return max(standard, 0), max(tolerance, 0)

    def _total_minutes_worked(self):
        if not self.date or not self.time_in or not self.time_out:
            return None
        start_dt = datetime.combine(self.date, self.time_in)
        end_dt = datetime.combine(self.date, self.time_out)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        delta = end_dt - start_dt
        return int(delta.total_seconds() // 60)

    def save(self, *args, **kwargs):
        standard_pause, pause_tolerance = self._pause_config()
        pause_value = self.pause_minutes if self.pause_minutes is not None else standard_pause
        if pause_value <= 0:
            pause_value = standard_pause
        self.pause_minutes = pause_value
        allowed_pause = standard_pause + pause_tolerance
        self.pause_excess_minutes = max(0, self.pause_minutes - allowed_pause)

        total_minutes = self._total_minutes_worked()
        if total_minutes is not None:
            effective_pause = self.pause_minutes
            computed_worked = max(0, total_minutes - effective_pause)
            self.worked_minutes = computed_worked

        if self.worked_minutes and total_minutes is not None:
            max_possible = max(0, total_minutes - max(self.pause_minutes, 0))
            if self.worked_minutes > max_possible:
                self.worked_minutes = max_possible

        super().save(*args, **kwargs)


class Alerte(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='alerts')
    type = models.CharField(max_length=100)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, default='OPEN')

    def __str__(self):
        return f"Alerte {self.type} - {self.statut}"


class Historique(models.Model):
    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='histories')
    action = models.CharField(max_length=100)
    date_action = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.action} @ {self.date_action}"


class AuditLog(models.Model):
    """Simple audit log to record create/update/delete events for key models.

    Note: current user is attached via middleware (threadlocal) if enabled.
    """
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=20)  # CREATE, UPDATE, DELETE
    model_name = models.CharField(max_length=128)
    object_pk = models.CharField(max_length=128, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return f"[{self.timestamp.isoformat()}] {self.action} {self.model_name}({self.object_pk}) by {self.user}"


class Report(models.Model):
    """Persist generated reports so admins can browse history, download and preview.

    Stores file paths (on disk) for the generated XLSX and optional PDF.
    """
    name = models.CharField(max_length=255)
    xlsx_path = models.CharField(max_length=1024)
    pdf_path = models.CharField(max_length=1024, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.name} @ {self.created_at.isoformat()}"


# ------------------------------------------------------------------
# Planner / replacement scaffolding
# ------------------------------------------------------------------
class ReplacementRequest(models.Model):
    """A request created by HR/manager when an employee is scheduled to be
    on leave and a replacement must be found.

    Minimal fields: requester (User), target_employee, start_date, end_date,
    role/department hint and a status. SuggestedReplacement objects can be
    attached with scores/comments.
    """
    STATUS = [
        ('DRAFT', 'Draft'),
        ('OPEN', 'Open'),
        ('FILLED', 'Filled'),
        ('CANCELLED', 'Cancelled'),
    ]

    requester = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    target_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='replacement_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    department_hint = models.CharField(max_length=128, blank=True)
    function_hint = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='DRAFT')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ReplacementRequest {self.target_employee} {self.start_date} -> {self.end_date} ({self.status})"


class SuggestedReplacement(models.Model):
    """A suggested candidate for a ReplacementRequest.

    We store a simple numeric score and an optional note.
    """
    request = models.ForeignKey(ReplacementRequest, on_delete=models.CASCADE, related_name='suggestions')
    candidate = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='replacement_suggestions')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    # approval by HR
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_replacements')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('request', 'candidate')

    def approve(self, user):
        """Mark this suggestion as approved by an HR user."""
        from django.utils import timezone

        self.approved = True
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def __str__(self):
        status = 'approved' if self.approved else 'pending'
        return f"Suggestion {self.candidate} for {self.request} (score={self.score}, {status})"


class ShiftPlan(models.Model):
    """High level model to store generated shift/coverage plans for a period.

    For now it's a simple stub that can store metadata and a JSON mapping of
    assigned replacements (request_id -> candidate_id).
    """
    name = models.CharField(max_length=255)
    year = models.IntegerField()
    month = models.IntegerField()
    data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"ShiftPlan {self.name} {self.month}/{self.year}"


# ------------------------------------------------------------------
# Performance, competencies and messaging (basic backend scaffolding)
# ------------------------------------------------------------------
class Competency(models.Model):
    """A simple competency tag attached to employees or used in job descriptions."""
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name



class EmployeeCompetency(models.Model):
    """Mapping between an Employee and a Competency with a skill level.

    level: integer scale (1..5) where higher means stronger skill.
    """
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='competencies')
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE, related_name='employee_links')
    level = models.PositiveSmallIntegerField(default=1)
    last_used = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'competency')

    def __str__(self):
        return f"{self.employee} - {self.competency} (lvl {self.level})"


class PerformanceReview(models.Model):
    """Store periodic performance reviews for employees (backend storage).

    This is intentionally minimal: reviewer (User), employee, date, score and
    a free-text comment. More advanced scoring workflows can be built on top.
    """
    reviewer = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviews_given')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_reviews')
    review_date = models.DateField()
    score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.employee} @ {self.review_date} ({self.score})"


class TrainingSuggestion(models.Model):
    """Suggestions of training for an employee or a competency mapping."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_suggestions', null=True, blank=True)
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    suggested_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.employee or (self.competency.name if self.competency else 'General')
        return f"TrainingSuggestion {self.title} -> {target}"


class Message(models.Model):
    """Simple HR messaging model to send messages to employees."""
    sender = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='messages_sent')
    recipient = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='messages_received')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message to {self.recipient} - {self.subject[:40]}"


