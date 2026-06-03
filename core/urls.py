from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('explore/', views.explore, name='explore'),
    path('projects/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<uuid:uuid>/<slug:slug>/', views.project_detail, name='project_detail'),
    path('projects/<uuid:uuid>/<slug:slug>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<uuid:uuid>/<slug:slug>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
]
