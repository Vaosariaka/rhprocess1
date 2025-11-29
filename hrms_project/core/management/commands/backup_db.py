from django.core.management.base import BaseCommand
import subprocess
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Create a JSON dump of the DB (dumpdata) and package it with media into exports/backup_<ts>.tar.gz'

    def add_arguments(self, parser):
        parser.add_argument('--outdir', type=str, default=None)

    def handle(self, *args, **options):
        outdir = options.get('outdir') or os.path.join(os.getcwd(), 'exports')
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_fname = os.path.join(outdir, f'db_dump_{ts}.json')
        try:
            # run dumpdata
            with open(json_fname, 'wb') as f:
                proc = subprocess.run(['python3', 'manage.py', 'dumpdata', '--natural-primary', '--natural-foreign', '--indent', '2'], stdout=f, check=True)
            # create tar.gz with media and dump
            tar_name = os.path.join(outdir, f'backup_{ts}.tar.gz')
            media_dir = os.path.join(os.getcwd(), 'media')
            cmd = ['tar', 'czf', tar_name, os.path.basename(json_fname)]
            if os.path.exists(media_dir):
                cmd = ['tar', 'czf', tar_name, os.path.basename(json_fname), 'media']
            # run tar from outdir
            cwd = os.getcwd()
            try:
                # copy json into outdir root for tar convenience
                # (json is already in outdir)
                subprocess.run(cmd, cwd=outdir, check=True)
            finally:
                pass
            self.stdout.write(self.style.SUCCESS(f'Backup created: {tar_name}'))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f'dumpdata or tar failed: {e}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Backup error: {e}'))
