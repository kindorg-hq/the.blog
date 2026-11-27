from django import forms
from django.contrib import admin, messages
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from inside.models import Subscriber
from inside.senders.email import send_post_newsletter
from posts.models import Post
from posts.openlibrary import fetch_book_metadata
from posts.templatetags.books import amazon_asin


BOOK_DATA_FIELDS = (
    "author", "year", "pages", "rating",
    "amazon_url", "bookshop_url", "goodreads_url", "domain",
)


def https_url_formfield(db_field, **kwargs):
    # a URL typed without a scheme gets https (Django 6's default, 5.2 warns)
    if isinstance(db_field, models.URLField):
        kwargs.setdefault("assume_scheme", "https")
    return db_field.formfield(**kwargs)


class PostAdminForm(forms.ModelForm):
    book_author = forms.CharField(label="Author", required=False)
    book_year = forms.IntegerField(label="Year", required=False)
    book_pages = forms.IntegerField(label="Pages", required=False)
    book_rating = forms.IntegerField(label="Rating (1-10)", required=False, min_value=1, max_value=10)
    book_amazon_url = forms.URLField(label="Amazon URL", required=False, assume_scheme="https")
    book_bookshop_url = forms.URLField(label="Bookshop URL", required=False, assume_scheme="https")
    book_goodreads_url = forms.URLField(label="Goodreads URL", required=False, assume_scheme="https")
    book_domain = forms.CharField(label="Domain / topic", required=False)

    class Meta:
        model = Post
        fields = "__all__"
        # the admin builds its own form from this one with its own callback,
        # which reads PostAdmin.formfield_overrides: both say https
        formfield_callback = https_url_formfield

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = (self.instance.data or {}) if self.instance else {}
        for field in BOOK_DATA_FIELDS:
            value = data.get(field)
            if value is not None:
                self.fields[f"book_{field}"].initial = value

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.type == "books":
            data = dict(instance.data or {})
            for field in BOOK_DATA_FIELDS:
                value = self.cleaned_data.get(f"book_{field}")
                if value in (None, ""):
                    data.pop(field, None)
                else:
                    data[field] = value
            instance.data = data
        if commit:
            instance.save()
        return instance


class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = (
        "title", "slug", "type", "created_at",
        "published_at", "comment_count", "view_count",
        "is_visible", "newsletter_status",
    )
    ordering = ("-created_at",)
    change_form_template = "admin/posts/post/change_form.html"
    # url, image, og_image: https, as PostAdminForm
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}

    fieldsets = (
        (None, {
            "fields": (
                "slug", "type", "author", "url",
                "title", "subtitle", "image",
                "og_title", "og_image", "og_description", "announce_text",
                "text", "html_cache", "data", "css",
                "created_at", "published_at",
                "comment_count", "view_count", "word_count",
                "is_raw_html", "is_visible", "is_members_only",
                "is_commentable", "is_visible_on_home_page",
                "newsletter_sent_at",
            ),
        }),
        ("Book metadata (only used when type = books)", {
            "classes": ("collapse",),
            "fields": (
                "book_author", "book_year", "book_pages", "book_rating",
                "book_amazon_url", "book_bookshop_url", "book_goodreads_url",
                "book_domain",
            ),
        }),
    )

    def newsletter_status(self, obj):
        if obj.newsletter_sent_at:
            return format_html(
                '<span style="color:#1b8a3a;">Sent {}</span>',
                obj.newsletter_sent_at.strftime("%Y-%m-%d %H:%M"),
            )
        return format_html('<span style="color:#888;">{}</span>', "—")
    newsletter_status.short_description = "Newsletter"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<uuid:object_id>/send-newsletter/",
                self.admin_site.admin_view(self.send_newsletter_view),
                name="posts_post_send_newsletter",
            ),
            path(
                "<uuid:object_id>/send-test-newsletter/",
                self.admin_site.admin_view(self.send_test_newsletter_view),
                name="posts_post_send_test_newsletter",
            ),
            path(
                "<uuid:object_id>/fetch-book-metadata/",
                self.admin_site.admin_view(self.fetch_book_metadata_view),
                name="posts_post_fetch_book_metadata",
            ),
        ]
        return custom + urls

    def send_newsletter_view(self, request, object_id):
        if not request.user.is_superuser:
            messages.error(request, "Superuser only.")
            return self._back(object_id)

        post = self.get_object(request, object_id)
        if not post:
            messages.error(request, "Post not found.")
            return self._back(object_id)

        if post.newsletter_sent_at:
            messages.error(
                request,
                f"Newsletter for this post was already sent on "
                f"{post.newsletter_sent_at.strftime('%Y-%m-%d %H:%M')} UTC. "
                f"Clear the timestamp in the form below if you really need to resend.",
            )
            return self._back(object_id)

        subscribers = Subscriber.objects.filter(is_confirmed=True)
        total = subscribers.count()
        if total == 0:
            messages.warning(request, "No confirmed subscribers — nothing sent.")
            return self._back(object_id)

        sent, failures = send_post_newsletter(post, subscribers)

        post.newsletter_sent_at = timezone.now()
        post.save(flush_cache=False)

        if failures:
            messages.warning(
                request,
                f"Sent to {sent}/{total}. Failures: " +
                ", ".join(f"{email} ({err})" for email, err in failures[:5]) +
                (f" (+{len(failures) - 5} more)" if len(failures) > 5 else ""),
            )
        else:
            messages.success(request, f"Newsletter sent to {sent} subscribers.")

        return self._back(object_id)

    def send_test_newsletter_view(self, request, object_id):
        if not request.user.is_superuser:
            messages.error(request, "Superuser only.")
            return self._back(object_id)

        post = self.get_object(request, object_id)
        if not post:
            messages.error(request, "Post not found.")
            return self._back(object_id)

        test_email = request.user.email
        test_subscriber = Subscriber(
            email=test_email,
            secret_hash="test",
            is_confirmed=True,
        )
        sent, failures = send_post_newsletter(
            post, [test_subscriber], subject_prefix="[TEST] "
        )

        if failures:
            messages.error(request, f"Test send to {test_email} failed: {failures[0][1]}")
        else:
            messages.success(request, f"Test newsletter sent to {test_email}.")

        return self._back(object_id)

    def fetch_book_metadata_view(self, request, object_id):
        if not request.user.is_superuser:
            messages.error(request, "Superuser only.")
            return self._back(object_id)

        post = self.get_object(request, object_id)
        if not post:
            messages.error(request, "Post not found.")
            return self._back(object_id)

        if post.type != "books":
            messages.error(request, "Only books posts have Amazon metadata.")
            return self._back(object_id)

        amazon_url = (post.data or {}).get("amazon_url")
        isbn = amazon_asin(amazon_url)
        if not isbn:
            messages.error(
                request,
                "No Amazon URL found in book metadata. Add it first and save.",
            )
            return self._back(object_id)

        fetched = fetch_book_metadata(isbn)
        if not fetched:
            messages.warning(
                request,
                f"Open Library returned nothing for ISBN={isbn}. "
                f"Either it's not in their catalogue or the lookup failed.",
            )
            return self._back(object_id)

        data = dict(post.data or {})
        added = []
        skipped = []
        for key, value in fetched.items():
            if data.get(key):
                skipped.append(key)
            else:
                data[key] = value
                added.append(f"{key}={value}")

        post.data = data
        post.save(flush_cache=False)

        if added:
            msg = f"Filled: {', '.join(added)}."
            if skipped:
                msg += f" Skipped (already set): {', '.join(skipped)}."
            messages.success(request, msg)
        else:
            messages.info(
                request,
                f"All fields already set; nothing to fill. Open Library had: "
                f"{', '.join(fetched.keys())}.",
            )
        return self._back(object_id)

    def _back(self, object_id):
        return HttpResponseRedirect(
            reverse("admin:posts_post_change", args=[object_id])
        )


admin.site.register(Post, PostAdmin)
