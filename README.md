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

**CI/CD:** the kindorg-hq golden path,
[ci v4](https://github.com/kindorg-hq/ci/blob/v4/README.md)
- A pull request runs `ci / Build` (the arm64 image, then the tests in
  `compose.test.yml` against it) and `ci / Accept` (image scan, PR title
  `type(#N): summary`, secrets, dependencies). Both are required.
- A squash-merge to `main` ships (`ship.yml`): the image is pushed to
  `ghcr.io/kindorg-hq/blog:<sha>`, tested and scanned again; a `feat`, `fix`
  or `perf` change becomes a Release `vX.Y.Z`, and a GitOps PR pins that
  image by digest in [homelab-k8s](https://github.com/kindorg-hq/homelab-k8s);
  ArgoCD rolls it out to the Kubernetes cluster at home
  (https://heynik.blog). The merged PRs get a `released` label and a comment
  that turns "running" once it does.
- Re-deliver the latest Release (a delivery that died on the way; nothing is
  rebuilt): `gh workflow run redeliver.yml --repo kindorg-hq/the.blog`.
- `docker-compose.yml` is for local development only — there is no production
  compose file any more. How to change this repo: [AGENTS.md](AGENTS.md).

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

Smoke suite via pytest-django, against a real Postgres:

```
$ poetry run pytest
```

Or as CI runs it (`compose.test.yml`: the built image next to Postgres 16,
`migrate` then `pytest`):

```
$ docker build -t blog:test .
$ IMAGE_BLOG=blog:test docker compose -f compose.test.yml run --rm -T test
$ docker compose -f compose.test.yml down -v
```

## 🤔 Contributions, etc

Well, like, who in their right mind contributes to other people's blogs? But feel free to use Github Issues if you want to repord bug or anything else :)

## 🧸 Repository mascot

![](https://i.vas3k.ru/dxq.jpg)
