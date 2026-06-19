# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Official Docker orchestration for Frappe applications (ERPNext, CRM, Helpdesk, etc.). It contains Docker images, Compose files, and operational docs — not the Frappe/ERPNext application source code itself.

## Local instance (already installed)

This working directory has ERPNext v16.23.0 running via `docker-compose.local.yml` (created locally — not part of the upstream repo).

```powershell
# Start all services
docker compose -f docker-compose.local.yml up -d

# Stop (data preserved in volumes)
docker compose -f docker-compose.local.yml down

# Wipe everything including data
docker compose -f docker-compose.local.yml down -v

# Tail logs for a specific service
docker compose -f docker-compose.local.yml logs -f backend
```

Access at `http://localhost:8080` — login: `Administrator` / `admin`

## Site operations (bench commands)

All `bench` commands run inside the `backend` container:

```powershell
# Interactive shell
docker compose -f docker-compose.local.yml exec backend bash

# Create a new site
docker compose -f docker-compose.local.yml exec backend bench new-site <sitename> --mariadb-user-host-login-scope='%' --db-root-password admin --admin-password admin --install-app erpnext

# Migrate after code changes
docker compose -f docker-compose.local.yml exec backend bench --site <sitename> migrate

# Install additional app
docker compose -f docker-compose.local.yml exec backend bench --site <sitename> install-app <appname>

# Backup
docker compose -f docker-compose.local.yml exec backend bench --site <sitename> backup
```

## Architecture: compose files

| File | Purpose |
|---|---|
| `compose.yaml` | Base for production setups — no DB or Redis, requires overrides |
| `pwd.yml` | Disposable all-in-one demo (Docker Swarm format) |
| `docker-compose.local.yml` | Local all-in-one (Docker Compose format, created here) |
| `overrides/compose.*.yaml` | Mix-in overrides for DB, proxy, Redis, SSL, etc. |

The production pattern is to layer `compose.yaml` with overrides:
```bash
docker compose --env-file custom.env \
    -f compose.yaml \
    -f overrides/compose.mariadb.yaml \
    -f overrides/compose.redis.yaml \
    -f overrides/compose.noproxy.yaml \
    config > compose.custom.yaml
```

## Architecture: services

Every Frappe deployment runs these containers from the same image (`frappe/erpnext`):

- **configurator** — one-shot: writes `common_site_config.json` with DB/Redis URLs; all other services wait for it to exit before starting
- **backend** — Gunicorn/Werkzeug (Python app server)
- **frontend** — Nginx: serves static assets, proxies to backend and websocket
- **websocket** — Node.js + Socket.IO for realtime
- **queue-short / queue-long** — RQ background workers
- **scheduler** — cron-style scheduled tasks

## Architecture: images

Four Dockerfiles in `images/`:

| Image | Use case |
|---|---|
| `production` | Frappe + ERPNext only, not customizable |
| `layered` | Fastest to build; extends prebuilt Docker Hub images; uses `apps.json` |
| `custom` | From plain Python base; most control; uses `apps.json` |
| `bench` | CLI tooling only, for development |

Build a custom image (requires Docker Engine v23+ for BuildKit secrets):
```bash
docker build \
  --build-arg=FRAPPE_BRANCH=version-16 \
  --secret=id=apps_json,src=apps.json \
  --tag=custom:16 \
  --file=images/layered/Containerfile .
```

Never use `--build-arg` for `apps.json` — it leaks tokens into image history.

## Custom apps

To add custom apps, create `apps.json` in the repo root before building:
```json
[
  { "url": "https://github.com/frappe/erpnext", "branch": "version-16" },
  { "url": "https://github.com/myorg/myapp", "branch": "main" }
]
```

## Environment variables

Copy `example.env` as the starting point. Key variables:

- `ERPNEXT_VERSION` — image tag
- `DB_PASSWORD` — MariaDB root password
- `FRAPPE_SITE_NAME_HEADER` — override site resolution (default: `$host`)
- `CUSTOM_IMAGE` / `CUSTOM_TAG` / `PULL_POLICY=missing` — for locally built images

## Development environment (VSCode devcontainer)

For active Frappe/ERPNext development (editing Python/JS source):
```bash
cp -R devcontainer-example .devcontainer
cp -R development/vscode-example development/.vscode
# Then: VSCode → "Dev Containers: Reopen in Container"
```

Inside the container, use `development/installer.py` to bootstrap a bench:
```bash
python installer.py  # creates bench + site with ERPNext from apps-example.json
```

## Windows-specific note

Set `COMPOSE_CONVERT_WINDOWS_PATHS=1` if volume mount issues occur. Site names must end with `.localhost` for local browser access.

## Troubleshooting

**MariaDB access denied after container rebuild:** Connect via `docker exec -it nexterp-backend-1 bash` then `mysql -uroot -padmin -hdb` to verify network, then fix user grants per `docs/07-troubleshooting/01-troubleshoot.md`.

**Reset everything:** `docker compose -f docker-compose.local.yml down -v` removes all volumes including DB data.
