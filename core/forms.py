from django import forms
from django.utils.text import slugify

from .models import Project, Tag


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

    def save(self, commit=True):
        project = super().save(commit=commit)
        if commit:
            raw = self.cleaned_data.get('tags_input', '')
            tag_names = [slugify(t.strip()) for t in raw.split(',') if t.strip()]
            tags = [Tag.objects.get_or_create(name=name)[0] for name in tag_names]
            project.tags.set(tags)
        return project
