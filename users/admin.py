from django.contrib import admin
from django.db import models

from users.models import User


class UsersAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "username",
        "city",
        "country",
        "created_at",
        "vas3k_club_slug",
        "patreon_id",
        "telegram_id",
        "is_banned",
    )
    ordering = ("-created_at",)
    # avatar: a URL typed without a scheme gets https (Django 6's default)
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}


admin.site.register(User, UsersAdmin)
