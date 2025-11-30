from __future__ import annotations

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from core.models import Employee


class Command(BaseCommand):
    help = (
        "Synchronise les fiches Employé avec les utilisateurs Django (Employé/RH/Manager)"
        " en attribuant les groupes adéquats et, si besoin, un mot de passe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-password',
            dest='default_password',
            help='Mot de passe appliqué aux nouveaux comptes (généré aléatoirement si omis).',
        )
        parser.add_argument(
            '--force-password',
            action='store_true',
            help='Réinitialise le mot de passe même pour les comptes existants.',
        )
        parser.add_argument(
            '--hr-departments',
            default='rh,ressources humaines,human resources',
            help='Mots-clés (séparés par des virgules) détectant un service RH.',
        )
        parser.add_argument(
            '--manager-keywords',
            default='chef,manager,responsable,lead',
            help='Mots-clés (séparés par des virgules) détectant une fonction managériale.',
        )
        parser.add_argument(
            '--only-matricules',
            help='Limiter la synchronisation à une liste de matricules (séparés par des virgules).',
        )
        parser.add_argument(
            '--export-path',
            help="Chemin d'un fichier CSV où stocker les identifiants générés (username,password,groups).",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule la synchronisation sans rien écrire en base.',
        )

    def handle(self, *args, **options):
        default_password = options.get('default_password')
        force_password = options.get('force_password')
        dry_run = options.get('dry_run')
        hr_keywords = self._parse_keywords(options.get('hr_departments'))
        manager_keywords = self._parse_keywords(options.get('manager_keywords'))
        export_path = options.get('export_path')
        only_matricules = (
            self._parse_list(options.get('only_matricules'))
            if options.get('only_matricules')
            else None
        )

        User = get_user_model()
        employee_group = self._ensure_group('Employe')
        hr_group = self._ensure_group('RH')
        manager_group = self._ensure_group('Manager')

        employees = Employee.objects.all().order_by('matricule')
        if only_matricules:
            employees = employees.filter(matricule__in=only_matricules)

        created_users = 0
        updated_users = 0
        password_events = 0
        credentials_dump = []

        with transaction.atomic():
            for employee in employees:
                username = self._username_for(employee)
                if not username:
                    self.stdout.write(self.style.WARNING(f"Employé #{employee.pk} sans matricule — ignoré."))
                    continue

                user_defaults = {
                    'first_name': employee.first_name or '',
                    'last_name': employee.last_name or '',
                    'email': employee.email or '',
                    'is_active': bool(employee.is_active and not employee.archived),
                }
                user, created = User.objects.get_or_create(username=username, defaults=user_defaults)
                groups_to_assign = [employee_group]

                is_hr = self._is_hr_profile(employee, hr_keywords)
                is_manager = self._is_manager_profile(employee, manager_keywords)
                if is_hr:
                    groups_to_assign.append(hr_group)
                if is_manager:
                    groups_to_assign.append(manager_group)

                if not created:
                    updated_field = False
                    for field, value in user_defaults.items():
                        if getattr(user, field) != value:
                            setattr(user, field, value)
                            updated_field = True
                    if updated_field:
                        updated_users += 1
                        if not dry_run:
                            user.save(update_fields=['first_name', 'last_name', 'email', 'is_active'])
                else:
                    if not dry_run:
                        user.save()
                    created_users += 1

                should_be_staff = bool(is_hr or is_manager)
                if not user.is_superuser and user.is_staff != should_be_staff:
                    user.is_staff = should_be_staff
                    if not dry_run:
                        user.save(update_fields=['is_staff'])

                password_to_record = None
                if created or force_password:
                    password_to_record = default_password or self._generate_password()
                    password_events += 1
                    if not dry_run:
                        user.set_password(password_to_record)
                        user.save(update_fields=['password'])

                if not dry_run:
                    for group in groups_to_assign:
                        user.groups.add(group)

                if password_to_record:
                    credentials_dump.append({
                        'username': user.username,
                        'password': password_to_record,
                        'groups': ','.join(g.name for g in groups_to_assign),
                    })

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Créés: {created_users}, mis à jour: {updated_users}, mots de passe définis/forcés: {password_events}"
        ))

        if export_path and credentials_dump:
            csv_path = Path(export_path)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open('w', newline='', encoding='utf-8') as fh:
                writer = csv.DictWriter(fh, fieldnames=['username', 'password', 'groups'])
                writer.writeheader()
                writer.writerows(credentials_dump)
            self.stdout.write(self.style.SUCCESS(f"Identifiants enregistrés dans {csv_path}"))
        elif credentials_dump:
            self.stdout.write(self.style.WARNING('Identifiants générés (notez-les maintenant):'))
            for cred in credentials_dump:
                self.stdout.write(f"  - {cred['username']} / {cred['password']} ({cred['groups']})")

    @staticmethod
    def _parse_keywords(raw):
        if not raw:
            return []
        return [token.strip().lower() for token in raw.split(',') if token.strip()]

    @staticmethod
    def _parse_list(raw):
        if not raw:
            return []
        return [token.strip() for token in raw.split(',') if token.strip()]

    @staticmethod
    def _username_for(employee: Employee) -> str:
        matricule = (employee.matricule or '').strip()
        if matricule:
            return matricule
        slug = slugify(f"{employee.last_name}-{employee.first_name}")
        if slug:
            return slug
        return f"emp-{employee.pk}"

    @staticmethod
    def _ensure_group(name: str) -> Group:
        group, _ = Group.objects.get_or_create(name=name)
        return group

    @staticmethod
    def _is_hr_profile(employee: Employee, keywords: list[str]) -> bool:
        haystack = ' '.join(filter(None, [employee.department, employee.service, employee.function])).lower()
        return any(key in haystack for key in keywords)

    @staticmethod
    def _is_manager_profile(employee: Employee, keywords: list[str]) -> bool:
        haystack = ' '.join(filter(None, [employee.function, employee.service, employee.category.name if employee.category else ''])).lower()
        return any(key in haystack for key in keywords)

    @staticmethod
    def _generate_password(length: int = 12) -> str:
        alphabet = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789@#$%'
        return get_random_string(length=length, allowed_chars=alphabet)
