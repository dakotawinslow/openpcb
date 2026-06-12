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
