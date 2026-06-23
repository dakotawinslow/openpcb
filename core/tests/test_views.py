import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from core.models import Project, ProjectFile, ProjectPhoto


def _png(name='photo.png'):
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), color='red').save(buf, format='PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class HealthzTests(TestCase):
    def test_healthz_ok(self):
        resp = self.client.get(reverse('healthz'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'ok'})


class ProjectDetailVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.other = User.objects.create_user('other', password='pw')
        self.private = Project.objects.create(
            owner=self.owner, title='Secret Board', is_public=False
        )
        self.public = Project.objects.create(owner=self.owner, title='Public Board', is_public=True)

    def _detail_url(self, project):
        return reverse('project_detail', kwargs={'uuid': project.uuid, 'slug': project.slug})

    def test_anonymous_cannot_view_private_project(self):
        resp = self.client.get(self._detail_url(self.private))
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_view_own_private_project(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self._detail_url(self.private))
        self.assertEqual(resp.status_code, 200)

    def test_other_user_cannot_view_private_project(self):
        self.client.force_login(self.other)
        resp = self.client.get(self._detail_url(self.private))
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_can_view_public_project(self):
        resp = self.client.get(self._detail_url(self.public))
        self.assertEqual(resp.status_code, 200)

    def test_stale_slug_redirects_to_canonical(self):
        url = reverse('project_detail', kwargs={'uuid': self.public.uuid, 'slug': 'wrong-slug'})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp.url, self._detail_url(self.public))


class OwnerOnlyViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.other = User.objects.create_user('other', password='pw')
        self.project = Project.objects.create(owner=self.owner, title='Widget')

    def _edit_url(self):
        return reverse(
            'project_edit', kwargs={'uuid': self.project.uuid, 'slug': self.project.slug}
        )

    def _delete_url(self):
        return reverse(
            'project_delete', kwargs={'uuid': self.project.uuid, 'slug': self.project.slug}
        )

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(self._edit_url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('account_login'), resp.url)

    def test_non_owner_gets_404_on_edit(self):
        self.client.force_login(self.other)
        resp = self.client.get(self._edit_url())
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_access_edit(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self._edit_url())
        self.assertEqual(resp.status_code, 200)

    def test_non_owner_gets_404_on_delete(self):
        self.client.force_login(self.other)
        resp = self.client.get(self._delete_url())
        self.assertEqual(resp.status_code, 404)


class FileUploadPermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.other = User.objects.create_user('other', password='pw')
        self.project = Project.objects.create(owner=self.owner, title='Widget')

    def _upload_url(self):
        return reverse('file_upload', kwargs={'uuid': self.project.uuid, 'slug': self.project.slug})

    def test_non_owner_cannot_upload(self):
        self.client.force_login(self.other)
        f = SimpleUploadedFile('design.zip', b'zip bytes')
        resp = self.client.post(self._upload_url(), {'files': [f]})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.project.files.count(), 0)

    def test_owner_can_upload_allowed_file(self):
        self.client.force_login(self.owner)
        f = SimpleUploadedFile('design.zip', b'zip bytes')
        resp = self.client.post(self._upload_url(), {'files': [f]})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.project.files.count(), 1)


class FileDuplicateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.project = Project.objects.create(owner=self.owner, title='Widget')
        self.client.force_login(self.owner)
        self.existing = ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('design.zip', b'old data'),
            original_filename='design.zip',
            file_size=8,
        )

    def _upload_url(self):
        return reverse('file_upload', kwargs={'uuid': self.project.uuid, 'slug': self.project.slug})

    def test_duplicate_without_replace_is_skipped(self):
        f = SimpleUploadedFile('design.zip', b'new data')
        self.client.post(self._upload_url(), {'files': [f]})
        self.assertEqual(self.project.files.count(), 1)
        self.assertEqual(self.project.files.first().file_size, 8)

    def test_duplicate_with_replace_replaces_file(self):
        f = SimpleUploadedFile('design.zip', b'new data!!')
        self.client.post(
            self._upload_url(),
            {'files': [f], 'replace_filenames': ['design.zip']},
        )
        self.assertEqual(self.project.files.count(), 1)
        self.assertEqual(self.project.files.first().file_size, 10)

    def test_new_file_uploaded_alongside_skipped_duplicate(self):
        f_dup = SimpleUploadedFile('design.zip', b'new data')
        f_new = SimpleUploadedFile('schematic.zip', b'other')
        self.client.post(self._upload_url(), {'files': [f_dup, f_new]})
        self.assertEqual(self.project.files.count(), 2)
        names = set(self.project.files.values_list('original_filename', flat=True))
        self.assertEqual(names, {'design.zip', 'schematic.zip'})

    def test_replace_all_replaces_all_duplicates(self):
        ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('board.gbr', b'old gbr'),
            original_filename='board.gbr',
            file_size=7,
        )
        f1 = SimpleUploadedFile('design.zip', b'new zip')
        f2 = SimpleUploadedFile('board.gbr', b'new gbr')
        self.client.post(
            self._upload_url(),
            {'files': [f1, f2], 'replace_filenames': ['design.zip', 'board.gbr']},
        )
        self.assertEqual(self.project.files.count(), 2)


class FilesDeleteAllTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.other = User.objects.create_user('other', password='pw')
        self.project = Project.objects.create(owner=self.owner, title='Widget')
        ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('a.zip', b'data'),
            original_filename='a.zip',
            file_size=4,
        )
        ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('b.zip', b'data'),
            original_filename='b.zip',
            file_size=4,
        )

    def _url(self):
        return reverse(
            'files_delete_all',
            kwargs={'uuid': self.project.uuid, 'slug': self.project.slug},
        )

    def test_owner_can_delete_all_files(self):
        self.client.force_login(self.owner)
        resp = self.client.post(self._url())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.project.files.count(), 0)

    def test_non_owner_cannot_delete_all(self):
        self.client.force_login(self.other)
        resp = self.client.post(self._url())
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.project.files.count(), 2)

    def test_anon_redirected_to_login(self):
        resp = self.client.post(self._url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
        self.assertEqual(self.project.files.count(), 2)


class ExploreViewTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('owner', password='pw')
        Project.objects.create(owner=owner, title='Public RP2040 Board', is_public=True)
        Project.objects.create(owner=owner, title='Secret Board', is_public=False)

    def test_private_projects_excluded(self):
        resp = self.client.get(reverse('explore'))
        titles = [p.title for p in resp.context['page_obj']]
        self.assertIn('Public RP2040 Board', titles)
        self.assertNotIn('Secret Board', titles)

    def test_search_filters_by_title(self):
        resp = self.client.get(reverse('explore'), {'q': 'RP2040'})
        titles = [p.title for p in resp.context['page_obj']]
        self.assertEqual(titles, ['Public RP2040 Board'])


class UnifiedEditUITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw')
        self.project = Project.objects.create(
            owner=self.owner, title='Test Board', license='MIT', is_public=True
        )

    def _edit_url(self):
        return reverse(
            'project_edit', kwargs={'uuid': self.project.uuid, 'slug': self.project.slug}
        )

    def _detail_url(self):
        return reverse(
            'project_detail', kwargs={'uuid': self.project.uuid, 'slug': self.project.slug}
        )

    def test_create_redirects_to_edit_page(self):
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse('project_create'),
            {'title': 'New Board'},
        )
        self.assertEqual(resp.status_code, 302)
        new_project = Project.objects.get(title='New Board')
        expected = reverse(
            'project_edit',
            kwargs={'uuid': new_project.uuid, 'slug': new_project.slug},
        )
        self.assertEqual(resp.url, expected)

    def test_edit_save_redirects_to_detail_page(self):
        self.client.force_login(self.owner)
        resp = self.client.post(
            self._edit_url(),
            {'title': 'Updated Board', 'license': 'MIT', 'tags_input': ''},
        )
        self.assertEqual(resp.status_code, 302)
        self.project.refresh_from_db()
        expected = reverse(
            'project_detail',
            kwargs={'uuid': self.project.uuid, 'slug': self.project.slug},
        )
        self.assertEqual(resp.url, expected)

    def test_edit_page_has_project_in_context(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self._edit_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['project'], self.project)

    def test_photo_upload_redirects_to_edit(self):
        self.client.force_login(self.owner)
        url = reverse(
            'photo_upload',
            kwargs={'uuid': self.project.uuid, 'slug': self.project.slug},
        )
        resp = self.client.post(url, {'photos': [_png('board.png')]})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self._edit_url(), resp.url)
        self.assertIn('#photos', resp.url)

    def test_photo_delete_redirects_to_edit(self):
        self.client.force_login(self.owner)
        photo = ProjectPhoto.objects.create(
            project=self.project,
            photo=_png(),
        )
        url = reverse(
            'photo_delete',
            kwargs={
                'uuid': self.project.uuid,
                'slug': self.project.slug,
                'photo_id': photo.pk,
            },
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self._edit_url(), resp.url)
        self.assertIn('#photos', resp.url)

    def test_photo_set_featured_redirects_to_edit(self):
        self.client.force_login(self.owner)
        photo = ProjectPhoto.objects.create(
            project=self.project,
            photo=_png(),
        )
        url = reverse(
            'photo_set_featured',
            kwargs={
                'uuid': self.project.uuid,
                'slug': self.project.slug,
                'photo_id': photo.pk,
            },
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self._edit_url(), resp.url)
        self.assertIn('#photos', resp.url)

    def test_file_upload_redirects_to_edit(self):
        self.client.force_login(self.owner)
        url = reverse(
            'file_upload',
            kwargs={'uuid': self.project.uuid, 'slug': self.project.slug},
        )
        f = SimpleUploadedFile('board.zip', b'zip bytes')
        resp = self.client.post(url, {'files': [f]})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self._edit_url(), resp.url)
        self.assertIn('#files', resp.url)

    def test_file_delete_redirects_to_edit(self):
        self.client.force_login(self.owner)
        pf = ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('board.zip', b'zip bytes'),
            original_filename='board.zip',
            file_size=100,
            file_type='Other',
        )
        url = reverse(
            'file_delete',
            kwargs={
                'uuid': self.project.uuid,
                'slug': self.project.slug,
                'file_id': pf.pk,
            },
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self._edit_url(), resp.url)
        self.assertIn('#files', resp.url)

    def test_detail_page_no_management_ui(self):
        self.client.force_login(self.owner)
        ProjectFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile('board.zip', b'zip bytes'),
            original_filename='board.zip',
            file_size=100,
            file_type='Other',
        )
        resp = self.client.get(self._detail_url())
        content = resp.content.decode()
        self.assertNotIn('photo_upload', content)
        self.assertNotIn('file_upload', content)
        self.assertNotIn('file_delete', content)
        self.assertNotIn('Manage photos', content)

    def test_create_page_no_file_photo_sections(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse('project_create'))
        content = resp.content.decode()
        self.assertNotIn('Project Files', content)
        self.assertNotIn('id="photos"', content)
