from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Employee, Leave, Payroll


class Command(BaseCommand):
    help = 'Initialize standard HR roles and assign basic permissions'

    def handle(self, *args, **options):
        roles = {
            'RH': {'models': [Employee, Leave, Payroll], 'perms': ['add', 'change', 'delete', 'view']},
            'Chef de service': {'models': [Employee, Leave], 'perms': ['view', 'change']},
            'Employe': {'models': [Employee], 'perms': ['view']},
            'Direction': {'models': [Employee, Payroll], 'perms': ['view']},
        }
        created = 0
        for role_name, cfg in roles.items():
            group, g_created = Group.objects.get_or_create(name=role_name)
            if g_created:
                created += 1
            perms = []
            for model in cfg['models']:
                ct = ContentType.objects.get_for_model(model)
                for p in cfg['perms']:
                    codename = f"{p}_{model._meta.model_name}"
                    try:
                        perm = Permission.objects.get(codename=codename, content_type=ct)
                        perms.append(perm)
                    except Permission.DoesNotExist:
                        # missing permission (unlikely) — skip
                        continue
            group.permissions.set(perms)
            group.save()
            self.stdout.write(self.style.SUCCESS(f'Role {role_name} ready (created={g_created})'))
        self.stdout.write(self.style.SUCCESS(f'Initialized roles (new groups created: {created})'))
