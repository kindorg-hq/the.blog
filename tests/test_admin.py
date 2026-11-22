"""Every admin page a model registers opens: an admin page broke on a Django
major bump with the rest of the suite green. With Django's next-version
deprecations as errors (pyproject's filterwarnings), what the next release
removes fails here first."""
from datetime import datetime

import pytest
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

from posts.models import Post
from users.models import User

MODEL_ADMINS = sorted(admin.site._registry.items(), key=lambda item: item[0]._meta.label)
IDS = [model._meta.label for model, _ in MODEL_ADMINS]


@pytest.fixture
def superuser_client(client, db):
    superuser = User.objects.create_superuser(
        username="admin", email="admin@example.com", password="admin-pass",
    )
    client.force_login(superuser)
    return client


def admin_url(model, view):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}")


def test_the_registry_is_not_empty():
    assert Post in admin.site._registry and User in admin.site._registry


@pytest.mark.parametrize("model, model_admin", MODEL_ADMINS, ids=IDS)
def test_admin_changelist_opens(superuser_client, post, model, model_admin):
    response = superuser_client.get(admin_url(model, "changelist"))
    assert response.status_code == 200


@pytest.mark.parametrize("model, model_admin", MODEL_ADMINS, ids=IDS)
def test_admin_add_view_opens(superuser_client, model, model_admin):
    response = superuser_client.get(admin_url(model, "add"))
    assert response.status_code == 200


def test_admin_post_change_view_opens(superuser_client, post):
    response = superuser_client.get(reverse("admin:posts_post_change", args=[post.id]))
    assert response.status_code == 200


def test_admin_post_changelist_with_newsletter_sent_and_not(superuser_client, post):
    assert post.newsletter_sent_at is None
    Post.objects.create(
        type="blog", slug="sent", author="nik", title="Sent",
        created_at=timezone.now(), is_visible=True,
        newsletter_sent_at=datetime(2026, 1, 2, 3, 4),
    )
    response = superuser_client.get(admin_url(Post, "changelist"))
    assert response.status_code == 200
    content = response.content.decode()
    assert '<span style="color:#888;">—</span>' in content
    assert "Sent 2026-01-02 03:04" in content
