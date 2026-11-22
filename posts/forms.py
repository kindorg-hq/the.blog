from django import forms
from django.forms import ModelForm

from posts.models import Post


class PostEditForm(ModelForm):
    title = forms.CharField(
        label="Title",
        required=True,
    )

    subtitle = forms.CharField(
        label="Subtitle",
        required=False,
    )

    image = forms.URLField(
        label="Image",
        required=False,
        assume_scheme="https",
    )

    text = forms.CharField(
        label="Text",
        min_length=0,
        max_length=100000,
        required=True,
        widget=forms.Textarea(
            attrs={
                "id": "post-editor",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "subtitle",
            "image",
            "text",
        ]

