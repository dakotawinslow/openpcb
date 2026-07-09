from django.core.management.base import BaseCommand
from django.db.models import Q

from core.constants import GERBER_MAYBE_EXCELLON_EXTENSIONS
from core.models import Project, ProjectFile, _regenerate_board_preview


class Command(BaseCommand):
    help = 'Re-render board preview SVGs for all projects that have Gerber/drill files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project',
            metavar='UUID',
            help='Re-process a single project by UUID instead of all projects.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List affected projects without rendering anything.',
        )

    def handle(self, *args, **options):
        q = Q(file_type__in=[ProjectFile.FileType.GERBER, ProjectFile.FileType.DRILL])
        for ext in GERBER_MAYBE_EXCELLON_EXTENSIONS:
            q |= Q(original_filename__iendswith=ext)

        project_ids = ProjectFile.objects.filter(q).values_list('project_id', flat=True).distinct()
        qs = Project.objects.filter(pk__in=project_ids).order_by('title')

        if options['project']:
            qs = qs.filter(uuid=options['project'])
            if not qs.exists():
                self.stderr.write(
                    self.style.ERROR(f'No project found with UUID {options["project"]}')
                )
                return

        total = qs.count()
        if total == 0:
            self.stdout.write('No projects with board files found.')
            return

        noun = 'project' if total == 1 else 'projects'
        if options['dry_run']:
            self.stdout.write(f'Would reprocess {total} {noun}:')
            for p in qs:
                self.stdout.write(f'  {p.uuid}  {p.title}')
            return

        self.stdout.write(f'Reprocessing {total} {noun}...')
        ok = failed = 0
        for p in qs:
            try:
                _regenerate_board_preview(p)
                self.stdout.write(self.style.SUCCESS(f'  OK  {p.title}'))
                ok += 1
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'  FAIL  {p.title}: {exc}'))
                failed += 1

        self.stdout.write(f'\nDone: {ok} succeeded, {failed} failed.')
