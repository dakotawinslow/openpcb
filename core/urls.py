from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('explore/', views.explore, name='explore'),
    path('projects/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<uuid:uuid>/<slug:slug>/', views.project_detail, name='project_detail'),
    path('projects/<uuid:uuid>/<slug:slug>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<uuid:uuid>/<slug:slug>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<uuid:uuid>/<slug:slug>/photos/upload/', views.photo_upload, name='photo_upload'),
    path('projects/<uuid:uuid>/<slug:slug>/photos/<int:photo_id>/delete/', views.photo_delete, name='photo_delete'),
    path('projects/<uuid:uuid>/<slug:slug>/photos/<int:photo_id>/feature/', views.photo_set_featured, name='photo_set_featured'),
    path('projects/<uuid:uuid>/<slug:slug>/photos/reorder/', views.photo_reorder, name='photo_reorder'),
    path('projects/<uuid:uuid>/<slug:slug>/files/upload/', views.file_upload, name='file_upload'),
    path('projects/<uuid:uuid>/<slug:slug>/files/<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('projects/<uuid:uuid>/<slug:slug>/files/<int:file_id>/download/', views.file_download, name='file_download'),
]
