# Development

Hot-reloading datalab stack (API + web app + MongoDB) in Docker. Only Docker is required.

## Quick start

Create the two `.env` files below, then:

```bash
docker compose --profile dev up --build      # first run builds; later just `up`
docker compose exec api-dev /opt/.venv/bin/invoke dev.seed   # optional: spawn example data in the DB
```

- Web app: http://localhost:8081
- API: http://localhost:5001
- Database: `mongodb://localhost:27018`

Edits to `pydatalab/` and `webapp/` hot-reload. Editing `.env` does not — restart the
service: `docker compose --profile dev restart api-dev` (or `app-dev`).

### Copy into `pydatalab/.env`

Read by `invoke dev.serve` natively and inside the Docker dev container (the
`./pydatalab:/app` bind-mount maps it to `/app/.env`). `.env` files are gitignored.
Full settings reference: https://docs.datalab-org.io/en/latest/config/

```bash
PYDATALAB_IDENTIFIER_PREFIX=dev

# Option A: no auth — every API call runs as authenticated (dev only); good for
# backend/block work. NOTE: the web app UI still shows a login prompt in this mode.
PYDATALAB_TESTING=true

# Option B: real GitHub login. Set TESTING=false above and uncomment; create the
# OAuth App at https://github.com/settings/developers with
#   Homepage URL:               http://localhost:8081
#   Authorization callback URL: http://localhost:5001/login/github/authorized
#
# PYDATALAB_SECRET_KEY=      # generate: python3 -c 'import secrets; print(secrets.token_hex(64))'
# PYDATALAB_BEHIND_REVERSE_PROXY=False
# PYDATALAB_AUTO_ACTIVATE_ACCOUNTS=True
# PYDATALAB_GITHUB_ORG_ALLOW_LIST=null
# OAUTHLIB_INSECURE_TRANSPORT=1          # local HTTP only; never set in production
# GITHUB_OAUTH_CLIENT_ID=                # no PYDATALAB_ prefix on these two
# GITHUB_OAUTH_CLIENT_SECRET=
```

### Copy into `webapp/.env` (optional)

The dev compose stack already points the web app at the dev API, so this file is
only needed to customise the rest.

```bash
VUE_APP_WEBSITE_TITLE=datalab (dev)
VUE_APP_EDITABLE_INVENTORY=true
VUE_APP_AUTOMATICALLY_GENERATE_ID_DEFAULT=false
# VUE_APP_LOGO_URL=
# VUE_APP_HOMEPAGE_URL=
# VUE_APP_QR_CODE_RESOLVER_URL=
```

## Logging in

The web app needs a logged-in session: set up Option B (GitHub OAuth) in the
`pydatalab/.env` template above, restart `api-dev`, and **Login via GitHub** in
the web app. Option A (`PYDATALAB_TESTING=true`) is enough for API-only work —
every call runs as authenticated — but the web app UI has no session and keeps
showing its login prompt.

## Handy commands

```bash
# Make yourself admin (display name = the name shown in the web app)
docker compose exec api-dev /opt/.venv/bin/invoke admin.change-user-role \
  --display-name "Your Name" --role admin

docker compose logs -f api-dev          # follow API logs
docker compose --profile dev down       # stop (add -v to wipe the DB + files)

# Use a custom database name (default: datalabvue). Set in your shell before
# running `docker compose up` — it is not read from pydatalab/.env.
export DATALAB_DB_NAME=my_project
docker compose --profile dev up
```

Backend tests run natively (the Docker dev image ships without test deps); from
`pydatalab/` use `uv sync --all-extras --dev` once, then `uv run pytest`.

The webapp dev image includes the system libraries Cypress needs, so component
tests can run inside the container (use the full binary path — `node_modules`
lives at `/node_modules`, outside the bind-mounted source):

```bash
docker compose exec app-dev /node_modules/.bin/cypress run --component
```

e2e tests are not wired up for in-container use yet (`cypress.config.ts` points
at `localhost` URLs); run those natively with `yarn test:e2e` against the
containerised API.


## `dev` vs `prod` profiles

Both profiles are in `docker-compose.yml` and share the same Dockerfiles; the `dev`
services target earlier build stages and override the run command.

| | `prod` (`app`, `api`, `database`) | `dev` (`app-dev`, `api-dev`, `database-dev`) |
|---|---|---|
| Code | baked into the image at build time | bind-mounted from your checkout |
| Reload | none (rebuild to change code) | hot reload (Flask `--reload`, Vue HMR) |
| Server | gunicorn / static build | dev servers (`dev.serve`, `vue-cli-service serve`) |
| Database | host path `/data/db`, port not exposed | Docker volume, port `27018`, isolated per dev |
| Files/backups | mounted host paths under `/data` | a throwaway Docker volume |
| Restart policy | `unless-stopped` | none |

Run with `docker compose --profile prod up` or `--profile dev up`. Don't run both at
once — they share ports 5001/8081.
