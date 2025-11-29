from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Employee, LeaveBalance


class Command(BaseCommand):
    help = 'Process annual carryover: carry unused leave from previous two years into current year (cap 90 days) and purge balances older than 3 years.'

    def handle(self, *args, **options):
        now = timezone.now()
        year = now.year
        processed = 0
        for emp in Employee.objects.filter(is_active=True):
            curr_lb, _ = LeaveBalance.objects.get_or_create(employee=emp, year=year)
            prev_years = [year - 1, year - 2]
            carryable = 0.0
            prev_unusables = []
            for y in prev_years:
                lb = LeaveBalance.objects.filter(employee=emp, year=y).first()
                unused = 0.0
                if lb:
                    unused = float(lb.entitlement_days - lb.used_days)
                    if unused < 0:
                        unused = 0.0
                prev_unusables.append((y, unused))
                carryable += unused

            # cap carry to 90 days total
            carry = min(carryable, 90.0)

            if carry > 0:
                # apply carry preferentially from oldest year
                remaining = carry
                for y, unused in sorted(prev_unusables):
                    if remaining <= 0:
                        break
                    take = min(unused, remaining)
                    if take > 0:
                        lb = LeaveBalance.objects.get(employee=emp, year=y)
                        lb.entitlement_days = float(lb.entitlement_days) - take
                        if lb.entitlement_days < 0:
                            lb.entitlement_days = 0
                        lb.save()
                        remaining -= take
                # add carry to current year entitlement
                curr_lb.entitlement_days = float(curr_lb.entitlement_days) + carry
                curr_lb.save()

            # purge balances older than 3 years (year-3 and earlier)
            cutoff = year - 3
            olds = LeaveBalance.objects.filter(employee=emp, year__lte=cutoff)
            if olds.exists():
                olds.delete()

            processed += 1
            self.stdout.write(self.style.NOTICE(f'Processed carryover for {emp}: added {carry} days to year {year}'))

        self.stdout.write(self.style.SUCCESS(f'Carryover processed for {processed} employees'))
