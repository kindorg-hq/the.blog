"""Boot smoke: the shipped image, booted as Production boots it, serves pages.

Run by compose.test.yml's service `test` after pytest, against the service
`blog` (IMAGE_BLOG with its own CMD: migrate, gunicorn + uvicorn workers,
ASGI, DEBUG off). pytest's test client never starts gunicorn or uvicorn and
runs with DEBUG on; this is real HTTP to the real server. It seeds one post
in `blog`'s database, then wants 200, no redirect, for each page below.
Not a pytest module (pytest's test database is not the one `blog` reads).

    BLOG_URL=http://blog:8022 python -m tests.boot_smoke
"""
import os
import sys
import urllib.error
import urllib.request

BLOG_URL = os.environ.get("BLOG_URL", "http://blog:8022").rstrip("/")
SLUG = "boot-smoke"

HEADERS = {
    # DEBUG off: the Host must be in ALLOWED_HOSTS
    "Host": "localhost",
    # TODO(#66): drop once utils/request.py stops reading request.environ,
    # which an ASGI request has no: without a proxy's header a post page is a
    # 500 (https://github.com/kindorg-hq/the.blog/issues/66)
    "X-Forwarded-For": "203.0.113.7",
}

PAGES = [
    ("/", "text/html", b"<html"),
    (f"/blog/{SLUG}/", "text/html", b"Boot smoke"),
    ("/godmode/login/", "text/html", b"csrfmiddlewaretoken"),
    ("/static/css/base.css", "text/css", b"{"),
]


def seed_post():
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "heynik_blog.settings")
    django.setup()
    from django.utils import timezone
    from posts.models import Post

    Post.objects.update_or_create(slug=SLUG, defaults={
        "type": "blog",
        "author": "ci",
        "title": "Boot smoke",
        "text": "# Boot smoke\n\nThe **shipped** image serves a post.",
        "created_at": timezone.now(),
        "is_visible": True,
    })


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a 3xx is an HTTPError: the page itself must be 200


def check(opener, path, content_type, needle):
    request = urllib.request.Request(BLOG_URL + path, headers=HEADERS)
    try:
        with opener.open(request, timeout=30) as response:
            status, ctype, body = response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as e:
        status, ctype, body = e.code, e.headers.get("Content-Type", ""), e.read()
    except OSError as e:
        return f"{path}: no answer ({e})"

    if status != 200:
        return f"{path}: {status}, want 200: {body[:300]!r}"
    if not ctype.startswith(content_type):
        return f"{path}: Content-Type {ctype!r}, want {content_type}"
    if needle not in body:
        return f"{path}: 200 but {needle!r} is not in the body"
    return None


def main():
    seed_post()
    opener = urllib.request.build_opener(NoRedirect)
    failures = 0
    for path, content_type, needle in PAGES:
        problem = check(opener, path, content_type, needle)
        if problem:
            failures += 1
            print(f"boot smoke FAILED {problem}")
        else:
            print(f"boot smoke ok     {path}")
    if failures:
        print(f"boot smoke: {failures} of {len(PAGES)} pages failed on {BLOG_URL} "
              "(its traceback is in the service blog's log)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
