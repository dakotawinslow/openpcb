import io
import logging
import os
import uuid

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from PIL import Image, ImageOps

from .constants import (
    GERBER_DRILL_EXTENSIONS,
    GERBER_DRILL_GBR_NPTH_SUFFIXES,
    GERBER_DRILL_GBR_PTH_SUFFIXES,
    GERBER_EXTENSION_TO_LAYER,
    GERBER_OUTLINE_EXTENSIONS,
    GERBER_OUTLINE_SUFFIXES,
    GERBER_SUFFIX_TO_LAYER,
)

logger = logging.getLogger(__name__)

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

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Project(models.Model):
    class License(models.TextChoices):
        CC_BY = 'CC BY 4.0', 'CC BY 4.0'
        CC_BY_SA = 'CC BY-SA 4.0', 'CC BY-SA 4.0'
        CC_BY_NC = 'CC BY-NC 4.0', 'CC BY-NC 4.0'
        CC_BY_ND = 'CC BY-ND 4.0', 'CC BY-ND 4.0'
        CC_BY_NC_SA = 'CC BY-NC-SA 4.0', 'CC BY-NC-SA 4.0'
        CC_BY_NC_ND = 'CC BY-NC-ND 4.0', 'CC BY-NC-ND 4.0'
        CC0 = 'CC0 1.0', 'CC0 1.0'
        UNLICENSE = 'Unlicense', 'Unlicense (Public Domain)'
        MIT = 'MIT', 'MIT'
        CERN_OHL = 'CERN-OHL-S-2.0', 'CERN-OHL-S-2.0'

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
    board_preview_top = models.FileField(
        upload_to='previews/',
        blank=True,
    )
    board_preview_bottom = models.FileField(
        upload_to='previews/',
        blank=True,
    )
    # Increments once per session per project (session-deduplicated in the download view).
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ProjectFile(models.Model):
    class FileType(models.TextChoices):
        GERBER = 'Gerber', 'Gerber'
        DRILL = 'Drill', 'Drill'
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

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return self.original_filename


class ProjectPhoto(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to=project_photo_upload_path)
    caption = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f'{self.project.title} — photo {self.pk}'


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
    ProjectPhoto.objects.filter(project=instance.project).exclude(pk=instance.pk).update(
        is_featured=False
    )
    _generate_thumbnail(instance.project, instance)


@receiver(post_delete, sender=ProjectPhoto)
def on_photo_delete(sender, instance, **kwargs):
    instance.photo.delete(save=False)
    if instance.is_featured:
        _reassign_thumbnail(instance.project)


@receiver(post_delete, sender=ProjectFile)
def delete_projectfile_from_r2(sender, instance, **kwargs):
    instance.file.delete(save=False)
    if instance.file_type in (ProjectFile.FileType.GERBER, ProjectFile.FileType.DRILL):
        _regenerate_board_preview(instance.project)


# ── Board preview management ─────────────────────────────────────────────────


def _try_parse_excellon(content, GerberFile, ExcellonFile):
    """Parse drill content as ExcellonFile, falling back to converting from Gerber X2 format."""
    try:
        return ExcellonFile.from_string(content)
    except Exception:
        pass
    try:
        return GerberFile.from_string(content).to_excellon(errors='ignore')
    except Exception:
        return None


def _regenerate_board_preview(project):
    """Re-render board preview SVGs from all Gerber files in the project."""
    from gerbonara import ExcellonFile, GerberFile, LayerStack

    gerber_files = project.files.filter(
        file_type__in=[ProjectFile.FileType.GERBER, ProjectFile.FileType.DRILL]
    )
    if not gerber_files.exists():
        if project.board_preview_top:
            project.board_preview_top.delete(save=False)
        if project.board_preview_bottom:
            project.board_preview_bottom.delete(save=False)
        Project.objects.filter(pk=project.pk).update(board_preview_top='', board_preview_bottom='')
        return

    graphic_layers = {}
    drill_pth = None
    drill_npth = None
    for pf in gerber_files:
        name_stem, ext = os.path.splitext(pf.original_filename)
        ext = ext.lower()
        try:
            content = pf.file.read().decode('utf-8', errors='replace')
            pf.file.close()
        except Exception:
            logger.warning('Could not read Gerber file %s', pf.original_filename)
            continue

        try:
            if ext in GERBER_DRILL_EXTENSIONS:
                ef = ExcellonFile.from_string(content)
                if name_stem.endswith('-NPTH'):
                    drill_npth = ef
                else:
                    drill_pth = ef
            elif ext in GERBER_OUTLINE_EXTENSIONS:
                graphic_layers[('mechanical', 'outline')] = GerberFile.from_string(content)
            elif layer_key := GERBER_EXTENSION_TO_LAYER.get(ext):
                graphic_layers[layer_key] = GerberFile.from_string(content)
            elif ext == '.gbr':
                upper_stem = name_stem.upper()
                if any(name_stem.endswith(s) for s in GERBER_OUTLINE_SUFFIXES):
                    graphic_layers[('mechanical', 'outline')] = GerberFile.from_string(content)
                elif any(upper_stem.endswith(s) for s in GERBER_DRILL_GBR_NPTH_SUFFIXES):
                    ef = _try_parse_excellon(content, GerberFile, ExcellonFile)
                    if ef is not None:
                        drill_npth = ef
                elif any(upper_stem.endswith(s) for s in GERBER_DRILL_GBR_PTH_SUFFIXES):
                    ef = _try_parse_excellon(content, GerberFile, ExcellonFile)
                    if ef is not None:
                        drill_pth = ef
                else:
                    for suffix, layer_key in GERBER_SUFFIX_TO_LAYER.items():
                        if name_stem.endswith(suffix):
                            graphic_layers[layer_key] = GerberFile.from_string(content)
                            break
        except Exception:
            logger.warning('Could not parse Gerber file %s', pf.original_filename, exc_info=True)
            continue

    if not graphic_layers:
        return

    stack = LayerStack(
        graphic_layers=graphic_layers,
        drill_pth=drill_pth,
        drill_npth=drill_npth,
    )

    for side in ('top', 'bottom'):
        try:
            svg_str = str(
                stack.to_pretty_svg(
                    side=side,
                    colors={
                        'copper': '#C9A84C',
                        'mask': '#004200bf',
                        'paste': '#999999',
                        'silk': '#e0e0e0',
                        'drill': '#303030',
                        'outline': '#F0C000',
                    },
                )
            ).replace('style="background-color:white"', '')
        except Exception:
            logger.warning('Could not render %s board preview', side, exc_info=True)
            continue

        field = getattr(project, f'board_preview_{side}')
        if field:
            field.delete(save=False)
        field.save(
            f'{project.uuid}_board_{side}.svg',
            ContentFile(svg_str.encode('utf-8')),
            save=False,
        )
    project.save(update_fields=['board_preview_top', 'board_preview_bottom'])


@receiver(post_save, sender=ProjectFile)
def regenerate_board_preview_on_file_save(sender, instance, **kwargs):
    if instance.file_type in (ProjectFile.FileType.GERBER, ProjectFile.FileType.DRILL):
        _regenerate_board_preview(instance.project)
