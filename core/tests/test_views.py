from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Project


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
