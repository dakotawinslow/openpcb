import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from core.models import Project, ProjectFile, ProjectPhoto


def _png(name='photo.png', color='red'):
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), color=color).save(buf, format='PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class ThumbnailSignalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.project = Project.objects.create(owner=self.owner, title='Widget')

    def test_featured_photo_generates_thumbnail(self):
        ProjectPhoto.objects.create(project=self.project, photo=_png(), is_featured=True)

        self.project.refresh_from_db()
        self.assertTrue(self.project.thumbnail)

    def test_new_featured_photo_unfeatures_siblings(self):
        first = ProjectPhoto.objects.create(
            project=self.project, photo=_png('a.png'), is_featured=True
        )
        second = ProjectPhoto.objects.create(
            project=self.project, photo=_png('b.png', 'blue'), is_featured=True
        )

        first.refresh_from_db()
        self.assertFalse(first.is_featured)
        self.assertTrue(second.is_featured)

    def test_deleting_featured_photo_promotes_next(self):
        first = ProjectPhoto.objects.create(
            project=self.project, photo=_png('a.png'), is_featured=True
        )
        second = ProjectPhoto.objects.create(project=self.project, photo=_png('b.png', 'blue'))

        first.delete()

        second.refresh_from_db()
        self.assertTrue(second.is_featured)
        self.project.refresh_from_db()
        self.assertTrue(self.project.thumbnail)

    def test_deleting_only_photo_clears_thumbnail(self):
        photo = ProjectPhoto.objects.create(project=self.project, photo=_png(), is_featured=True)

        photo.delete()

        self.project.refresh_from_db()
        self.assertFalse(self.project.thumbnail)


class ProjectFileDeleteTests(TestCase):
    def test_deleting_file_removes_it_from_storage(self):
        owner = User.objects.create_user('owner2', password='pw')
        project = Project.objects.create(owner=owner, title='Widget 2')
        project_file = ProjectFile.objects.create(
            project=project,
            file=SimpleUploadedFile('design.zip', b'zip bytes'),
            original_filename='design.zip',
            file_size=9,
        )
        storage = project_file.file.storage
        name = project_file.file.name
        self.assertTrue(storage.exists(name))

        project_file.delete()

        self.assertFalse(storage.exists(name))


MINIMAL_GERBER = (
    b'%FSLAX35Y35*%\n%MOIN*%\n%ADD10R,0.1X0.1*%\nD10*\nX0Y0D03*\nX100000Y100000D01*\nM02*\n'
)


def _gerber_file(name, content=None):
    return SimpleUploadedFile(
        name, content or MINIMAL_GERBER, content_type='application/octet-stream'
    )


class BoardPreviewSignalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('prev_owner', password='pw')
        self.project = Project.objects.create(owner=self.owner, title='Preview Test')

    def test_gerber_upload_generates_previews(self):
        ProjectFile.objects.create(
            project=self.project,
            file=_gerber_file('board.gtl'),
            original_filename='board.gtl',
            file_type=ProjectFile.FileType.GERBER,
            file_size=100,
        )

        self.project.refresh_from_db()
        self.assertTrue(self.project.board_preview_top)
        self.assertTrue(self.project.board_preview_bottom)
        self.assertIn('svg', self.project.board_preview_top.read().decode())

    def test_deleting_last_gerber_clears_previews(self):
        pf = ProjectFile.objects.create(
            project=self.project,
            file=_gerber_file('board.gtl'),
            original_filename='board.gtl',
            file_type=ProjectFile.FileType.GERBER,
            file_size=100,
        )

        self.project.refresh_from_db()
        self.assertTrue(self.project.board_preview_top)

        pf.delete()

        self.project.refresh_from_db()
        self.assertFalse(self.project.board_preview_top)
        self.assertFalse(self.project.board_preview_bottom)

    def test_non_gerber_upload_does_not_trigger_preview(self):
        ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('design.zip', b'zip bytes'),
            original_filename='design.zip',
            file_type=ProjectFile.FileType.OTHER,
            file_size=9,
        )

        self.project.refresh_from_db()
        self.assertFalse(self.project.board_preview_top)
        self.assertFalse(self.project.board_preview_bottom)

    def test_unrecognized_gerber_extension_skipped(self):
        ProjectFile.objects.create(
            project=self.project,
            file=_gerber_file('board.gbr'),
            original_filename='board.gbr',
            file_type=ProjectFile.FileType.GERBER,
            file_size=100,
        )

        self.project.refresh_from_db()
        self.assertFalse(self.project.board_preview_top)
        self.assertFalse(self.project.board_preview_bottom)

    def test_corrupt_gerber_does_not_crash(self):
        ProjectFile.objects.create(
            project=self.project,
            file=_gerber_file('board.gtl', b'not a gerber file at all'),
            original_filename='board.gtl',
            file_type=ProjectFile.FileType.GERBER,
            file_size=24,
        )

        self.project.refresh_from_db()
        # May or may not generate a preview depending on gerbonara's tolerance,
        # but must not raise an exception.
