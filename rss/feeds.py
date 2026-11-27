from django.contrib.syndication.views import Feed
from django.template.defaultfilters import truncatechars
from django.utils.html import strip_tags

from posts.models import Post
from django.conf import settings


class FullFeed(Feed):
    title = "heynik.blog"
    link = "/rss/"
    description = settings.DESCRIPTION

    def items(self):
        items = Post.visible_objects()\
            .filter(is_visible_on_home_page=True)\
            .order_by("-published_at")[:30]
        return items

    def item_title(self, item):
        return item.title

    def author_name(self):
        return "Nik ILyushkin"

    def item_copyright(self):
        return "heynik.blog"

    def item_pubdate(self, item):
        return item.created_at

    def item_description(self, item):
        url = item.get_absolute_url()

        result = ""

        if item.image:
            result += f"<a href='https://{settings.APP_HOST}{url}'><img src='{item.image}'></a><br><br>"

        if item.og_description:
            result += item.og_description
        elif item.html_cache:
            result += truncatechars(strip_tags(item.html_cache), 500)
        else:
            result += truncatechars(item.text or "", 500)

        return result


class PrivateFeed(FullFeed):
    title = "HeyNik.blog: Secret Feed"
    link = "/rss/private/"


class PublicFeed(FullFeed):
    title = "HeyNik.blog: Public Posts Feed"
    link = "/rss/public/"

    def items(self):
        items = Post.visible_objects()\
            .filter(is_visible_on_home_page=True, is_members_only=False)\
            .order_by("-created_at")[:20]
        return items
