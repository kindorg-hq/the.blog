"""A URL typed without a scheme gets https, in every form that takes one
(Django 6's default; 5.2 defaults to http and warns)."""
import pytest
from django.contrib import admin
from django.test import RequestFactory

from posts.admin import PostAdminForm
from posts.forms import PostEditForm
from posts.models import Post
from users.models import User


def admin_form(model):
    request = RequestFactory().get("/")
    request.user = User(is_superuser=True, is_staff=True)
    return admin.site._registry[model].get_form(request)


@pytest.mark.parametrize("form_class, field", [
    (PostEditForm, "image"),
    (PostAdminForm, "url"),
    (PostAdminForm, "og_image"),
    (PostAdminForm, "book_amazon_url"),
    (lambda: admin_form(Post), "image"),
    (lambda: admin_form(User), "avatar"),
], ids=["edit-image", "admin-form-url", "admin-form-og_image", "admin-form-book_amazon_url",
        "post-admin-image", "user-admin-avatar"])
def test_scheme_less_url_cleans_to_https(db, form_class, field):
    if not isinstance(form_class, type):
        form_class = form_class()
    assert form_class().fields[field].clean("example.com/x") == "https://example.com/x"
