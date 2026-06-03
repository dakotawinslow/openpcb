import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.text import slugify


def project_file_upload_path(instance, filename):
    return f'projects/{instance.project_id}/{filename}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} profile'


class Tag(models.Model):
    name = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Project(models.Model):
    class License(models.TextChoices):
        CC_BY = 'CC BY 4.0', 'CC BY 4.0'
        CC_BY_SA = 'CC BY-SA 4.0', 'CC BY-SA 4.0'
        MIT = 'MIT', 'MIT'
        CERN_OHL = 'CERN-OHL-S-2.0', 'CERN-OHL-S-2.0'
        ALL_RIGHTS = 'All Rights Reserved', 'All Rights Reserved'

    # SET_NULL so deleting a user doesn't cascade-delete their shared designs.
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects'
    )
    # uuid is the stable URL key — slug is decorative, auto-generated from title.
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    slug = models.SlugField(max_length=200, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    license = models.CharField(max_length=50, choices=License.choices, default=License.CC_BY_SA)
    tags = models.ManyToManyField(Tag, blank=True)
    is_public = models.BooleanField(default=True)
    # Increments once per session per project (session-deduplicated in the download view).
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class ProjectFile(models.Model):
    class FileType(models.TextChoices):
        GERBER = 'Gerber', 'Gerber'
        KICAD = 'KiCad', 'KiCad'
        EAGLE = 'Eagle', 'Eagle'
        SCHEMATIC = 'Schematic', 'Schematic'
        BOM = 'BOM', 'BOM'
        OTHER = 'Other', 'Other'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=project_file_upload_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FileType.choices, default=FileType.OTHER)
    file_size = models.PositiveIntegerField()  # bytes, set on upload
    download_count = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename

    class Meta:
        ordering = ['uploaded_at']


@receiver(post_delete, sender=ProjectFile)
def delete_projectfile_from_r2(sender, instance, **kwargs):
    instance.file.delete(save=False)
