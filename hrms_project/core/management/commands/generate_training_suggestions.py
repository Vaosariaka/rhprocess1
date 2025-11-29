from django.core.management.base import BaseCommand
from core.models import Employee, Competency, EmployeeCompetency, TrainingSuggestion, PerformanceReview
from django.contrib.auth import get_user_model
from django.utils import timezone

class Command(BaseCommand):
    help = 'Generate training suggestions for employees with low competency levels or missing competencies.'

    def add_arguments(self, parser):
        parser.add_argument('--min-level', type=int, default=3, help='Minimum desired competency level (default: 3)')
        parser.add_argument('--dry-run', action='store_true', help='Do not save TrainingSuggestion rows; just print what would be created')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of suggestions (0 = no limit)')

    def handle(self, *args, **options):
        min_level = options.get('min_level') or 3
        dry_run = options.get('dry_run')
        limit = int(options.get('limit') or 0)

        created = 0
        now = timezone.now()
        users = get_user_model().objects.order_by('pk')

        # Strategy:
        # - For each employee, for each competency in the system:
        #   * if employee has the competency with level < min_level -> suggest training
        #   * if employee does not have the competency but their latest performance review score < 3 -> suggest training (optional)
        # This simple heuristic is conservative and intended as a starting point.

        comps = list(Competency.objects.all())
        if not comps:
            self.stdout.write('No competencies defined; nothing to suggest.')
            return

        for e in Employee.objects.filter(is_active=True, archived=False).order_by('last_name'):
            # get mapping
            existing = {ec.competency_id: ec for ec in EmployeeCompetency.objects.filter(employee=e)}
            # latest performance review
            last_review = PerformanceReview.objects.filter(employee=e).order_by('-review_date').first()
            last_score = float(last_review.score) if last_review and last_review.score is not None else None

            for c in comps:
                ec = existing.get(c.pk)
                need = False
                reason = ''
                if ec:
                    if (ec.level or 0) < min_level:
                        need = True
                        reason = f'level {ec.level} < {min_level}'
                else:
                    # if no competency record and performance is low, suggest
                    if last_score is not None and last_score < 3.0:
                        need = True
                        reason = f'no competency record and last_score {last_score} < 3.0'

                if need:
                    title = f"Formation recommandée: {c.name}"
                    description = f"Suggestion automatique générée le {now.date()}: améliorer compétence '{c.name}' ({reason})."
                    if dry_run:
                        self.stdout.write(f"[DRY] Would create TrainingSuggestion for {e}: {title} - {description}")
                    else:
                        ts = TrainingSuggestion.objects.create(
                            employee=e,
                            competency=c,
                            title=title,
                            description=description,
                            suggested_by=None,
                        )
                        created += 1
                        self.stdout.write(f"Created TrainingSuggestion #{ts.pk} for {e} -> {c.name}")
                        if limit and created >= limit:
                            self.stdout.write('Reached limit, stopping.')
                            return

        self.stdout.write(f'Done. Created: {created} suggestions.')
