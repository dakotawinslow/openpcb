from django.contrib import admin

from .models import Profile, ProjectFile, Project, Tag


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'website', 'created_at']
    search_fields = ['user__username', 'user__email']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class ProjectFileInline(admin.TabularInline):
    model = ProjectFile
    extra = 0
    fields = ['original_filename', 'file_type', 'file_size', 'download_count', 'uploaded_at']
    readonly_fields = ['download_count', 'uploaded_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'license', 'is_public', 'download_count', 'created_at']
    list_filter = ['license', 'is_public', 'tags']
    search_fields = ['title', 'description', 'owner__username']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['uuid', 'download_count', 'created_at', 'updated_at']
    inlines = [ProjectFileInline]


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'project', 'file_type', 'file_size', 'download_count', 'uploaded_at']
    list_filter = ['file_type']
    search_fields = ['original_filename', 'project__title']
    readonly_fields = ['download_count', 'uploaded_at']
