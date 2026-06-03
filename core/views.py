from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import ProjectForm
from .models import Project


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

FILTER_LABELS = ['All', 'Microcontrollers', 'Power', 'RF', 'Sensors']


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
    projects = (
        Project.objects
        .filter(is_public=True)
        .select_related('owner')
        .prefetch_related('tags')
        .order_by('-created_at')
    )
    return render(request, 'core/explore.html', {
        'projects':      projects,
        'filter_labels': FILTER_LABELS,
    })


def project_detail(request, uuid, slug):
    project = get_object_or_404(
        Project.objects.select_related('owner').prefetch_related('tags', 'files'),
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


class ProjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'

    def get_object(self, queryset=None):
        return get_object_or_404(Project, uuid=self.kwargs['uuid'])

    def test_func(self):
        return self.get_object().owner == self.request.user

    def get_success_url(self):
        return reverse('project_detail', kwargs={
            'uuid': self.object.uuid,
            'slug': self.object.slug,
        })


class ProjectDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('explore')

    def get_object(self, queryset=None):
        return get_object_or_404(Project, uuid=self.kwargs['uuid'])

    def test_func(self):
        return self.get_object().owner == self.request.user
