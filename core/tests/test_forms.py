import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from core.forms import ProjectFileForm, ProjectForm, ProjectPhotoForm
from core.models import Tag


def _png_bytes(color='red'):
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), color=color).save(buf, format='PNG')
    return buf.getvalue()


def _bmp_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), color='red').save(buf, format='BMP')
    return buf.getvalue()


class ProjectFormTagsTests(TestCase):
    def _form(self, tags_input):
        return ProjectForm(
            data={
                'title': 'Test Project',
                'description': '',
                'license': 'CC BY-SA 4.0',
                'is_public': True,
                'tags_input': tags_input,
            }
        )

    def test_blank_and_unslugifiable_tags_are_dropped(self):
        form = self._form('rp2040, !!!, , Power Supply')
        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()
        self.assertEqual(
            set(project.tags.values_list('name', flat=True)),
            {'rp2040', 'power-supply'},
        )
        self.assertFalse(Tag.objects.filter(name='').exists())

    def test_duplicate_tags_collapse_to_one(self):
        form = self._form('RP2040, rp2040, rp-2040')
        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()
        self.assertEqual(
            set(project.tags.values_list('name', flat=True)),
            {'rp2040', 'rp-2040'},
        )


class ProjectFileFormTests(TestCase):
    def test_allowed_extension_is_valid(self):
        f = SimpleUploadedFile('design.zip', b'zip bytes', content_type='application/zip')
        form = ProjectFileForm(files={'file': f})
        self.assertTrue(form.is_valid(), form.errors)

    def test_disallowed_extension_is_rejected(self):
        f = SimpleUploadedFile('virus.exe', b'bytes', content_type='application/octet-stream')
        form = ProjectFileForm(files={'file': f})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

    def test_oversized_file_is_rejected(self):
        f = SimpleUploadedFile('design.zip', b'x' * 1024, content_type='application/zip')
        with patch('core.forms.MAX_FILE_SIZE_BYTES', 100):
            form = ProjectFileForm(files={'file': f})
            self.assertFalse(form.is_valid())


class ProjectPhotoFormTests(TestCase):
    def test_allowed_image_is_valid(self):
        f = SimpleUploadedFile('photo.png', _png_bytes(), content_type='image/png')
        form = ProjectPhotoForm(files={'photo': f})
        self.assertTrue(form.is_valid(), form.errors)

    def test_disallowed_extension_is_rejected(self):
        f = SimpleUploadedFile('photo.bmp', _bmp_bytes(), content_type='image/bmp')
        form = ProjectPhotoForm(files={'photo': f})
        self.assertFalse(form.is_valid())
        self.assertIn('photo', form.errors)

    def test_oversized_image_is_rejected(self):
        f = SimpleUploadedFile('photo.png', _png_bytes(), content_type='image/png')
        with patch('core.forms.MAX_IMAGE_SIZE_BYTES', 10):
            form = ProjectPhotoForm(files={'photo': f})
            self.assertFalse(form.is_valid())
