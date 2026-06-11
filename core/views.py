from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .constants import MAX_FILES_PER_PROJECT, MAX_PHOTOS_PER_PROJECT, detect_file_type
from .forms import ProjectForm, ProjectFileForm, ProjectPhotoForm
from .models import Profile, Project, ProjectFile, ProjectPhoto, Tag


WHY_ITEMS = [
    {
        "title": "All your files in one place",
        "body": "Gerbers, KiCad project, schematic, BOM — one URL, all versioned together.",
    },
    {
        "title": "Open licenses, clearly stated",
        "body": "Every design shows its license upfront so you know exactly what you can do with it.",
    },
    {
        "title": "Designed for the hardware community",
        "body": "Not a generic file host. Built around how EE and maker projects actually work.",
    },
]

STATS = [
    {"value": "1,200+", "label": "Designs shared"},
    {"value": "48",     "label": "Contributors"},
    {"value": "9,400+", "label": "Downloads"},
    {"value": "100%",   "label": "Open source"},
]

SORT_OPTIONS = {
    'newest':    '-created_at',
    'oldest':    'created_at',
    'downloads': '-download_count',
}


def index(request):
    projects = (
        Project.objects
        .filter(is_public=True)
        .select_related('owner')
        .prefetch_related('tags')
        .order_by('-created_at')[:6]
    )
    return render(request, 'core/index.html', {
        'projects':  projects,
        'why_items': WHY_ITEMS,
        'stats':     STATS,
    })


def explore(request):
    q = request.GET.get('q', '').strip()
    tag = request.GET.get('tag', '').strip()
    sort = request.GET.get('sort', 'newest')
    if sort not in SORT_OPTIONS:
        sort = 'newest'

    projects = (
        Project.objects
        .filter(is_public=True)
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

    return render(request, 'core/explore.html', {
        'page_obj':  page_obj,
        'q':         q,
        'tag':       tag,
        'sort':      sort,
        'tags':      tags,
        'base_qs':   base_qs,
        'notag_qs':  notag_qs,
    })


def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=profile_user)

    projects = (
        Project.objects
        .filter(owner=profile_user)
        .prefetch_related('tags')
        .order_by('-created_at')
    )
    if request.user != profile_user:
        projects = projects.filter(is_public=True)

    return render(request, 'core/profile.html', {
        'profile_user': profile_user,
        'profile':      profile,
        'projects':     projects,
    })


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
            Project.objects
            .filter(owner=project.owner, is_public=True)
            .exclude(pk=project.pk)
            .prefetch_related('tags')[:2]
        )
    else:
        others = []
    return render(request, 'core/project_detail.html', {
        'project': project,
        'others':  others,
    })


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project_detail', kwargs={
            'uuid': self.object.uuid,
            'slug': self.object.slug,
        })


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
        return get_object_or_404(Project, uuid=self.kwargs['uuid'])

    def get_success_url(self):
        return reverse('project_detail', kwargs={
            'uuid': self.object.uuid,
            'slug': self.object.slug,
        })


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
    return redirect('project_detail', uuid=project.uuid, slug=project.slug)


@login_required
def photo_delete(request, uuid, slug, photo_id):
    project = _get_owned_project(request, uuid)
    photo = get_object_or_404(ProjectPhoto, pk=photo_id, project=project)
    if request.method == 'POST':
        photo.delete()
    return redirect('project_detail', uuid=project.uuid, slug=project.slug)


@login_required
def photo_set_featured(request, uuid, slug, photo_id):
    project = _get_owned_project(request, uuid)
    photo = get_object_or_404(ProjectPhoto, pk=photo_id, project=project)
    if request.method == 'POST' and not photo.is_featured:
        photo.is_featured = True
        photo.save()
    return redirect('project_detail', uuid=project.uuid, slug=project.slug)


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
        current_count = project.files.count()
        if current_count + len(files) > MAX_FILES_PER_PROJECT:
            messages.error(request, f'A project can have at most {MAX_FILES_PER_PROJECT} files.')
        else:
            for f in files:
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
    return redirect('project_detail', uuid=project.uuid, slug=project.slug)


@login_required
def file_delete(request, uuid, slug, file_id):
    project = _get_owned_project(request, uuid)
    project_file = get_object_or_404(ProjectFile, pk=file_id, project=project)
    if request.method == 'POST':
        project_file.delete()
    return redirect('project_detail', uuid=project.uuid, slug=project.slug)


def file_download(request, uuid, slug, file_id):
    project = get_object_or_404(Project, uuid=uuid)
    if not project.is_public and project.owner != request.user:
        raise Http404
    project_file = get_object_or_404(ProjectFile, pk=file_id, project=project)

    session_key = f'downloaded_file_{project_file.pk}'
    if not request.session.get(session_key):
        ProjectFile.objects.filter(pk=project_file.pk).update(download_count=F('download_count') + 1)
        Project.objects.filter(pk=project.pk).update(download_count=F('download_count') + 1)
        request.session[session_key] = True

    url = project_file.file.storage.url(project_file.file.name, expire=60)
    return redirect(url)
