from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import F, Q
from django.db.utils import OperationalError
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .constants import MAX_FILES_PER_PROJECT, MAX_PHOTOS_PER_PROJECT, detect_file_type
from .forms import ProjectFileForm, ProjectForm, ProjectPhotoForm
from .models import Profile, Project, ProjectFile, ProjectPhoto, Tag

SORT_OPTIONS = {
    'newest': '-created_at',
    'oldest': 'created_at',
    'downloads': '-download_count',
}


def index(request):
    projects = (
        Project.objects.filter(is_public=True)
        .select_related('owner')
        .prefetch_related('tags')
        .order_by('-created_at')[:6]
    )
    return render(
        request,
        'core/index.html',
        {
            'projects': projects,
        },
    )


def explore(request):
    q = request.GET.get('q', '').strip()
    tag = request.GET.get('tag', '').strip()
    sort = request.GET.get('sort', 'newest')
    if sort not in SORT_OPTIONS:
        sort = 'newest'

    projects = (
        Project.objects.filter(is_public=True)
        .select_related('owner')
        .prefetch_related('tags')
        .order_by(SORT_OPTIONS[sort])
    )

    if q:
        projects = projects.filter(Q(title__icontains=q) | Q(description__icontains=q))

    if tag:
        projects = projects.filter(tags__name=tag)

    if q or tag:
        projects = projects.distinct()

    paginator = Paginator(projects, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Querystrings for links that preserve the current filters.
    params = request.GET.copy()
    params.pop('page', None)
    base_qs = params.urlencode()
    params.pop('tag', None)
    notag_qs = params.urlencode()

    tags = Tag.objects.filter(project__is_public=True).distinct()

    return render(
        request,
        'core/explore.html',
        {
            'page_obj': page_obj,
            'q': q,
            'tag': tag,
            'sort': sort,
            'tags': tags,
            'base_qs': base_qs,
            'notag_qs': notag_qs,
        },
    )


def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=profile_user)

    projects = (
        Project.objects.filter(owner=profile_user).prefetch_related('tags').order_by('-created_at')
    )
    if request.user != profile_user:
        projects = projects.filter(is_public=True)

    return render(
        request,
        'core/profile.html',
        {
            'profile_user': profile_user,
            'profile': profile,
            'projects': projects,
        },
    )


def project_detail(request, uuid, slug):
    project = get_object_or_404(
        Project.objects.select_related('owner').prefetch_related('tags', 'files', 'photos'),
        uuid=uuid,
    )
    # Only the owner can view a private project.
    if not project.is_public and project.owner != request.user:
        raise Http404
    # Canonicalise the slug — 301 if stale.
    if project.slug != slug:
        return HttpResponsePermanentRedirect(
            reverse('project_detail', kwargs={'uuid': project.uuid, 'slug': project.slug})
        )
    if project.owner:
        others = (
            Project.objects.filter(owner=project.owner, is_public=True)
            .exclude(pk=project.pk)
            .prefetch_related('tags')[:2]
        )
    else:
        others = []
    return render(
        request,
        'core/project_detail.html',
        {
            'project': project,
            'others': others,
        },
    )


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'project_edit',
            kwargs={
                'uuid': self.object.uuid,
                'slug': self.object.slug,
            },
        )


class OwnerOnlyMixin(UserPassesTestMixin):
    """404s (rather than 403s) for authenticated non-owners — matches
    project_detail's behavior so owner-only URLs don't leak that a
    private project exists."""

    def test_func(self):
        return self.get_object().owner == self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise Http404
        return super().handle_no_permission()


class ProjectUpdateView(LoginRequiredMixin, OwnerOnlyMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Project.objects.prefetch_related('files', 'photos'),
            uuid=self.kwargs['uuid'],
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['project'] = self.object
        return ctx

    def get_success_url(self):
        return reverse(
            'project_detail',
            kwargs={
                'uuid': self.object.uuid,
                'slug': self.object.slug,
            },
        )


class ProjectDeleteView(LoginRequiredMixin, OwnerOnlyMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('explore')

    def get_object(self, queryset=None):
        return get_object_or_404(Project, uuid=self.kwargs['uuid'])


def _get_owned_project(request, uuid):
    project = get_object_or_404(Project, uuid=uuid)
    if project.owner != request.user:
        raise Http404
    return project


def _redirect_to_edit(project, fragment=''):
    url = reverse('project_edit', kwargs={'uuid': project.uuid, 'slug': project.slug})
    if fragment:
        url += f'#{fragment}'
    return redirect(url)


@login_required
def photo_upload(request, uuid, slug):
    project = _get_owned_project(request, uuid)
    if request.method == 'POST':
        files = request.FILES.getlist('photos')
        current_count = project.photos.count()
        if current_count + len(files) > MAX_PHOTOS_PER_PROJECT:
            messages.error(request, f'A project can have at most {MAX_PHOTOS_PER_PROJECT} photos.')
        else:
            has_featured = project.photos.filter(is_featured=True).exists()
            for f in files:
                form = ProjectPhotoForm(files={'photo': f})
                if form.is_valid():
                    photo = form.save(commit=False)
                    photo.project = project
                    if not has_featured:
                        photo.is_featured = True
                        has_featured = True
                    photo.save()
                else:
                    messages.error(request, f'{f.name}: ' + ' '.join(form.errors.get('photo', [])))
    return _redirect_to_edit(project, 'photos')


@login_required
def photos_delete_selected(request, uuid, slug):
    project = _get_owned_project(request, uuid)
    if request.method == 'POST':
        photo_ids = request.POST.getlist('photo_ids')
        photos = project.photos.filter(pk__in=photo_ids)
        for photo in photos:
            photo.delete()
    return _redirect_to_edit(project, 'photos')


@login_required
def photo_set_featured(request, uuid, slug, photo_id):
    project = _get_owned_project(request, uuid)
    photo = get_object_or_404(ProjectPhoto, pk=photo_id, project=project)
    if request.method == 'POST' and not photo.is_featured:
        photo.is_featured = True
        photo.save()
    return _redirect_to_edit(project, 'photos')


@login_required
def photo_reorder(request, uuid, slug):
    project = _get_owned_project(request, uuid)
    if request.method == 'POST':
        photo_ids = request.POST.getlist('photo_id')
        valid_pks = set(project.photos.values_list('pk', flat=True))
        for index, photo_id in enumerate(photo_ids):
            # photo_id is attacker-controllable POST data — guard the int()
            # cast so a non-numeric value can't raise an unhandled 500.
            if photo_id.isdigit() and int(photo_id) in valid_pks:
                ProjectPhoto.objects.filter(pk=photo_id, project=project).update(order=index)
    return JsonResponse({'ok': True})


@login_required
def file_upload(request, uuid, slug):
    project = _get_owned_project(request, uuid)
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        replace_names = set(request.POST.getlist('replace_filenames'))
        existing_names = set(project.files.values_list('original_filename', flat=True))

        new_files = []
        for f in files:
            if f.name in existing_names:
                if f.name not in replace_names:
                    continue
                old = project.files.filter(original_filename=f.name)
                for old_file in old:
                    old_file.file.delete(save=False)
                old.delete()
            new_files.append(f)

        current_count = project.files.count()
        if current_count + len(new_files) > MAX_FILES_PER_PROJECT:
            messages.error(request, f'A project can have at most {MAX_FILES_PER_PROJECT} files.')
        else:
            for f in new_files:
                form = ProjectFileForm(files={'file': f})
                if form.is_valid():
                    project_file = form.save(commit=False)
                    project_file.project = project
                    project_file.original_filename = f.name
                    project_file.file_size = f.size
                    project_file.file_type = detect_file_type(f.name)
                    project_file.save()
                else:
                    messages.error(request, f'{f.name}: ' + ' '.join(form.errors.get('file', [])))
    return _redirect_to_edit(project, 'files')


@login_required
def files_delete_selected(request, uuid, slug):
    project = _get_owned_project(request, uuid)
    if request.method == 'POST':
        file_ids = request.POST.getlist('file_ids')
        files = list(project.files.filter(pk__in=file_ids))
        for f in files:
            f.file.delete(save=False)
            f.delete()
        if files:
            from .models import _regenerate_board_preview

            _regenerate_board_preview(project)
    return _redirect_to_edit(project, 'files')


@login_required
def files_delete_all(request, uuid, slug):
    project = _get_owned_project(request, uuid)
    if request.method == 'POST':
        files = list(project.files.all())
        for f in files:
            f.file.delete(save=False)
        project.files.all()._raw_delete(project.files.all().db)
        from .models import _regenerate_board_preview

        _regenerate_board_preview(project)
    return _redirect_to_edit(project, 'files')


def file_download(request, uuid, slug, file_id):
    project = get_object_or_404(Project, uuid=uuid)
    if not project.is_public and project.owner != request.user:
        raise Http404
    project_file = get_object_or_404(ProjectFile, pk=file_id, project=project)

    session_key = f'downloaded_file_{project_file.pk}'
    if not request.session.get(session_key):
        ProjectFile.objects.filter(pk=project_file.pk).update(
            download_count=F('download_count') + 1
        )
        Project.objects.filter(pk=project.pk).update(download_count=F('download_count') + 1)
        request.session[session_key] = True

    url = project_file.file.storage.url(project_file.file.name, expire=60)
    return redirect(url)


def board_preview_svg(request, uuid, slug, side):
    if side not in ('top', 'bottom'):
        raise Http404
    project = get_object_or_404(Project, uuid=uuid)
    if not project.is_public and project.owner != request.user:
        raise Http404
    field = getattr(project, f'board_preview_{side}')
    if not field:
        raise Http404
    return HttpResponse(field.read(), content_type='image/svg+xml')


def healthz(request):
    try:
        connection.ensure_connection()
    except OperationalError:
        return JsonResponse({'status': 'error'}, status=503)
    return JsonResponse({'status': 'ok'})
