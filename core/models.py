import io
import uuid

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from PIL import Image, ImageOps


THUMBNAIL_SIZE = (450, 600)


def project_file_upload_path(instance, filename):
    return f'projects/{instance.project_id}/{filename}'


def project_photo_upload_path(instance, filename):
    return f'projects/{instance.project_id}/photos/{filename}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} profile'


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


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
    # Server-managed: auto-generated from the featured ProjectPhoto. Never set directly.
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
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


class ProjectPhoto(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to=project_photo_upload_path)
    caption = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.project.title} — photo {self.pk}'

    class Meta:
        ordering = ['order', 'uploaded_at']


# ── Thumbnail management ──────────────────────────────────────────────────────

def _generate_thumbnail(project, photo):
    """Fill-and-crop photo to THUMBNAIL_SIZE, write JPEG to project.thumbnail on R2."""
    photo.photo.open('rb')
    img = Image.open(photo.photo).convert('RGB')
    photo.photo.close()

    img = ImageOps.fit(img, THUMBNAIL_SIZE, method=Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85, optimize=True)
    buf.seek(0)

    if project.thumbnail:
        project.thumbnail.delete(save=False)

    # Stable filename keyed to the project so re-featuring always overwrites cleanly.
    project.thumbnail.save(f'thumbnails/{project.uuid}.jpg', ContentFile(buf.read()), save=True)


def _reassign_thumbnail(project):
    """Promote next available photo after featured photo is deleted."""
    next_photo = project.photos.order_by('order', 'uploaded_at').first()
    if next_photo:
        # Use update() to avoid re-triggering post_save, then generate directly.
        ProjectPhoto.objects.filter(pk=next_photo.pk).update(is_featured=True)
        next_photo.refresh_from_db(fields=['photo'])
        _generate_thumbnail(project, next_photo)
    else:
        if project.thumbnail:
            project.thumbnail.delete(save=False)
        Project.objects.filter(pk=project.pk).update(thumbnail='')


@receiver(post_save, sender=ProjectPhoto)
def sync_thumbnail_on_photo_save(sender, instance, **kwargs):
    if not instance.is_featured:
        return
    # Unfeature all siblings via bulk update — no signal cascade.
    ProjectPhoto.objects.filter(project=instance.project).exclude(pk=instance.pk).update(is_featured=False)
    _generate_thumbnail(instance.project, instance)


@receiver(post_delete, sender=ProjectPhoto)
def on_photo_delete(sender, instance, **kwargs):
    instance.photo.delete(save=False)
    if instance.is_featured:
        _reassign_thumbnail(instance.project)


@receiver(post_delete, sender=ProjectFile)
def delete_projectfile_from_r2(sender, instance, **kwargs):
    instance.file.delete(save=False)
