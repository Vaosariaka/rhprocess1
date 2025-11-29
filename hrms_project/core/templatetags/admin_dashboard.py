from datetime import date

from django import template
from django.db.models import Q

from core.models import Employee, Alerte, LeaveRequest, Payroll, Presence


register = template.Library()


@register.simple_tag
def admin_kpis():
    """Return a dictionary of quick metrics for the admin landing page."""
    today = date.today()

    try:
        total_employees = Employee.objects.count()
    except Exception:
        total_employees = 0

    try:
        active_employees = Employee.objects.filter(is_active=True, archived=False).count()
    except Exception:
        active_employees = 0

    try:
        open_alerts = Alerte.objects.exclude(statut='CLOSED').count()
    except Exception:
        open_alerts = 0

    try:
        pending_leaves = LeaveRequest.objects.filter(status__in=['REQUESTED', 'DEPT_APPROVED']).count()
    except Exception:
        pending_leaves = 0

    try:
        payrolls_month = Payroll.objects.filter(year=today.year, month=today.month).count()
    except Exception:
        payrolls_month = 0

    try:
        presence_today = Presence.objects.filter(date=today).count()
        late_today = Presence.objects.filter(date=today, minutes_late__gt=0).count()
    except Exception:
        presence_today = 0
        late_today = 0

    return {
        'total_employees': total_employees,
        'active_employees': active_employees,
        'open_alerts': open_alerts,
        'pending_leaves': pending_leaves,
        'payrolls_month': payrolls_month,
        'presence_today': presence_today,
        'late_today': late_today,
        'today': today,
    }
