import os

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .constants import (
    ALLOWED_FILE_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_IMAGE_SIZE_BYTES,
)
from .models import Project, ProjectFile, ProjectPhoto, Tag


class ProjectForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label='Tags',
        widget=forms.TextInput(attrs={'placeholder': 'rp2040, power-supply, microcontroller'}),
        help_text='Comma-separated slugs. Lowercase, hyphens only.',
    )

    class Meta:
        model = Project
        fields = ['title', 'description', 'license', 'is_public']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(
                self.instance.tags.values_list('name', flat=True)
            )
        else:
            self.fields['license'].required = False

    def save(self, commit=True):
        project = super().save(commit=commit)
        if commit:
            raw = self.cleaned_data.get('tags_input', '')
            slugs = (slugify(t.strip()) for t in raw.split(','))
            # Dedupe (case/whitespace variants can collapse to the same slug)
            # and drop entries that slugify to '' (e.g. "!!!").
            tag_names = list(dict.fromkeys(slug for slug in slugs if slug))
            tags = [Tag.objects.get_or_create(name=name)[0] for name in tag_names]
            project.tags.set(tags)
        return project


class ProjectFileForm(forms.ModelForm):
    class Meta:
        model = ProjectFile
        fields = ['file']

    def clean_file(self):
        f = self.cleaned_data['file']
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            raise ValidationError(f'"{ext}" is not an allowed file type.')
        if f.size > MAX_FILE_SIZE_BYTES:
            raise ValidationError('File is too large (max 100MB).')
        return f


class ProjectPhotoForm(forms.ModelForm):
    class Meta:
        model = ProjectPhoto
        fields = ['photo']

    def clean_photo(self):
        f = self.cleaned_data['photo']
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(f'"{ext}" is not an allowed image type.')
        if f.size > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError('Image is too large (max 20MB).')
        return f
