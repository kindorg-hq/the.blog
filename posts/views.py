from django.conf import settings
from django.db.models import F
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404

from comments.models import Comment
from posts.forms import PostEditForm
from posts.models import Post
from posts.renderers import render_list, render_list_all, render_post
from heynik_blog.posts import POST_TYPES


DISCOVERY_LINKS = ", ".join([
    '</.well-known/api-catalog>; rel="api-catalog"',
    '</>; rel="alternate"; type="text/markdown"',
    '</rss/>; rel="alternate"; type="application/rss+xml"',
])


def index(request):
    response = render_index_markdown(request) if wants_markdown(request) else render_index_html(request)
    response["Link"] = DISCOVERY_LINKS
    return response


def render_index_html(request):
    base = Post.visible_objects().filter(is_visible_on_home_page=True)

    # HERO + RECENT share one source: latest 4 from {thoughts, blog}.
    # First → HERO, next 3 → RECENT 3-up. Their ids are excluded from THOUGHTS.
    hero_recent = list(
        base.filter(type__in=["thoughts", "blog"])
            .order_by("-published_at")[:4]
    )
    top_post = hero_recent[0] if hero_recent else None
    recent_posts = hero_recent[1:4]
    used_ids = [p.id for p in hero_recent]

    longreads = list(
        base.filter(type="blog").order_by("-published_at")[:4]
    )
    stream_posts = list(
        base.filter(type="stream").order_by("-published_at")[:5]
    )
    thoughts_posts = list(
        base.filter(type="thoughts")
            .exclude(id__in=used_ids)
            .order_by("-published_at")[:4]
    )
    books_posts = list(
        base.filter(type="books").order_by("-published_at")[:10]
    )

    blocks = []
    if top_post:
        blocks.append({"template": "index/main.html", "post": top_post})
    if recent_posts:
        blocks.append({"template": "index/posts3.html", "posts": recent_posts})
    blocks.append({"title": "About me", "template": "index/about.html", "posts": []})
    if longreads:
        blocks.append({
            "title": "Long Reads", "url": "/blog/",
            "template": "index/posts4.html", "posts": longreads,
        })
    if stream_posts:
        blocks.append({
            "title": "Stream", "url": "/stream/",
            "template": "index/stream.html", "posts": stream_posts,
        })
    if thoughts_posts:
        blocks.append({
            "title": "Thoughts", "url": "/thoughts/",
            "template": "index/posts4.html", "posts": thoughts_posts,
        })
    if books_posts:
        blocks.append({
            "title": "Books", "url": "/books/",
            "template": "index/posts3.html", "posts": books_posts,
        })

    return render(request, "index.html", {"blocks": blocks})


def list_posts(request, post_type="all"):
    posts = Post.visible_objects()

    if post_type and post_type != "all":
        if post_type not in POST_TYPES:
            raise Http404()

        posts = posts.filter(type=post_type)
        if not posts:
            raise Http404()

        return render_list(request, post_type, posts)
    else:
        return render_list_all(request, posts)


def show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    # post_type can be changed
    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    # post_type can be removed
    if post_type not in POST_TYPES:
        raise Http404()

    # drafts are visible only with a flag
    if not post.is_visible and not request.GET.get("preview"):
        raise Http404()

    Post.objects.filter(id=post.id)\
        .update(view_count=F("view_count") + 1)

    # don't show private posts into public
    if post.is_members_only:
        if not request.user.is_authenticated:
            return render(request, "users/post_access_denied.html", {
                "post": post
            })

    if post.url:
        return redirect(post.url)

    # AI agents can ask for the markdown source via "Accept: text/markdown"
    if not post.is_raw_html and wants_markdown(request):
        return render_post_markdown(post)

    comments = Comment.visible_objects()\
        .filter(post=post)\
        .order_by("created_at")

    return render_post(request, post, {
        "post": post,
        "comments": comments,
    })


def wants_markdown(request):
    return request.get_preferred_type(["text/html", "text/markdown"]) == "text/markdown"


def markdown_response(parts):
    response = HttpResponse(
        "\n\n".join(part for part in parts if part),
        content_type="text/markdown; charset=utf-8",
    )
    response["Vary"] = "Accept"
    return response


def render_post_markdown(post):
    return markdown_response([f"# {post.title}" if post.title else None, post.subtitle, post.text])


def render_index_markdown(request):
    # behind the proxy the scheme isn't forwarded, so pin https like robots.txt does
    def absolute(url):
        return url if url.startswith("http") else f"https://{request.get_host()}{url}"

    posts = Post.visible_objects().filter(is_members_only=False)
    lines = [
        f"- [{post.title or post.slug}]({absolute(post.get_absolute_url())})"
        f" ({post.published_at:%Y-%m-%d})"
        + (f" — {post.subtitle}" if post.subtitle else "")
        for post in posts
    ]
    return markdown_response([
        f"# {settings.TITLE}",
        settings.DESCRIPTION,
        "## Posts",
        "\n".join(lines),
        f"RSS: {absolute('/rss/')}\nSitemap: {absolute('/sitemap.xml')}",
    ])


def edit_post(request, post_type, post_slug):
    if not request.user.is_authenticated:
        return redirect("login")

    if not request.user.is_superuser:
        return HttpResponseForbidden()

    post = get_object_or_404(Post, type=post_type, slug=post_slug)

    if request.method == "POST":
        form = PostEditForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect("show_post", post_type=post.type, post_slug=post.slug)
    else:
        form = PostEditForm(instance=post)

    return render(request, "posts/edit.html", {
        "form": form,
    })
