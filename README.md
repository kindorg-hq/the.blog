# the.blog

It's a fork from vas3k blog codebase. Which was never written with intention of scalability or wider adoption.

⚠️ Use it at your own risk! I'm not responsible for any damages or your wasted time trying to get your blog up and running on this. Also, I don't provide any support for this code, sorry.


## ⚙️ Tech details

**Backend:**
- Python 3.10+
- Django 4+
- PostgreSQL
- [Poetry](https://python-poetry.org/) as a package manager

**Frontend:**
- [htmx](https://htmx.org/)
- Mostly pure JS, no webpack, no builders
- No CSS framework

**Blogging part:**
- Markdown with a bunch of [custom plugins](common/markdown/plugins)

**CI/CD:**
- Github Actions builds an arm64 image and pushes it to `ghcr.io/kindorg-hq/blog`
- Deployment is GitOps: CI writes the new image tag into the
  [homelab-k8s](https://github.com/kindorg-hq/homelab-k8s) repository and
  ArgoCD rolls it out to a Kubernetes cluster running at home
- `docker-compose.yml` is for local development only — there is no production
  compose file any more

## 🏗️ How to build

If you like to build it from scratch:

```
$ pip3 install poetry
$ poetry install
$ poetry run python3 manage.py migrate
$ poetry run python3 manage.py runserver 0.0.0.0:8000
```

Don't forget to create an empty Postgres database called `vas3k_blog` or your migrations will fail.

Another option for those who prefer Docker:

```
$ docker compose up
```

Then open http://localhost:8000 and see an empty page.

## 🧪 Tests

Smoke suite via pytest-django:

```
$ poetry run pytest
```

Or inside Docker:

```
$ docker compose exec -T blog_app poetry run pytest
```

## 🤔 Contributions, etc

Well, like, who in their right mind contributes to other people's blogs? But feel free to use Github Issues if you want to repord bug or anything else :)

## 🧸 Repository mascot

![](https://i.vas3k.ru/dxq.jpg)
