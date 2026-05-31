from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('explore/', views.explore, name='explore'),
    path('projects/<int:id>/', views.project_detail, name='project_detail'),
]
