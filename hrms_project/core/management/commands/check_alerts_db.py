from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Run DB alert checks using fn_check_hr_alerts stored function'

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute("SELECT fn_check_hr_alerts()")
        self.stdout.write(self.style.SUCCESS('DB alert checks executed'))
