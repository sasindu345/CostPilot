# Getting started

## 1. Install the tools

On a Mac with [Homebrew](https://brew.sh):

```bash
brew install uv gitleaks pre-commit colima docker docker-compose
```

Also install:

- **A container engine.** We use **Colima**, a free, lightweight way to run Docker containers on a Mac. Start it with `colima start`. Docker Desktop works too, but needs a paid licence at larger companies
- **Node**, using nvm: run `nvm install` in the project folder. It reads the version from `.nvmrc`
- **pnpm**: run `npm install -g pnpm`

## 2. Set up the project

```bash
make setup
```

This installs all packages, sets up the Git checks, and creates a `.env` file with new random passwords. The `.env` file holds your secrets and is never committed.

## 3. Start everything

```bash
make up
```

| Service | Address |
|---|---|
| Web app | http://localhost:3010 |
| API docs | http://localhost:8010/api/docs |
| Keycloak admin | http://localhost:8090 |
| Test email inbox | http://localhost:8025 |
| Qdrant dashboard | http://localhost:6333/dashboard |

Your Keycloak admin password is `KEYCLOAK_ADMIN_PASSWORD` in `.env`.

Open http://localhost:3010 and click **Register**. After signing in, click **Try sample data** to fill the dashboard with made-up bills. The verification email appears in the test inbox at http://localhost:8025.

`make check` needs the database, so run `make up` first.

## 4. Everyday commands

| Command | What it does |
|---|---|
| `make dev-api` | Runs the API with live reload |
| `make dev-web` | Runs the web app with live reload |
| `make check` | Runs all tests and checks. Do this before committing |
| `make migrate` | Updates your database to the latest version |
| `make e2e` | Tests the full user journey in Chrome |
| `make reindex` | Rebuilds documentation search. Needs a Gemini key |
| `make eval-search` | Measures search quality. Needs a Gemini key |
| `make eval-assistant` | Scores the assistant with real Gemini, using about 30 AI calls |
| `make sample` | Creates a made-up bill |
| `make down` | Stops everything |

## Gemini keys and real bills

From Phase 5 you will need a [Gemini API key](https://aistudio.google.com/apikey).

**Do not use a free key with real bills.** Google's terms say not to send sensitive or confidential information to the free service, and that human reviewers may read it. Use made-up sample bills with a free key. Before using real bills, turn on billing for your key and set `GEMINI_TIER=paid`.

## If something goes wrong

| Problem | Fix |
|---|---|
| `set in .env` error | Run `make setup`, or fill in the empty value in `.env` |
| A port is already in use | Change the port in `.env` |
| Commit is rejected | Read the message. A check found a secret, a hardcoded value or an AI co-author line |
| Keycloak is slow to start | This is normal. It can take up to a minute |
| `Cannot connect to the Docker daemon` | Colima has stopped. Run `colima start` |
| Everything is very slow | Colima has limited memory. Stop other projects, or give it more: `colima stop`, then `colima start --memory 6` |
