# CostPilot project rules

These rules are for every developer and every AI coding tool working on this project.

## What this project is

CostPilot helps people understand their cloud bills. Users upload a bill, see their spending on a dashboard, and ask an AI assistant questions in plain English. It is built to production standards using free services.

Before you start, read:

1. `docs/plan/ROADMAP.md`: what is done and what is next
2. The checklist file for the current phase in `docs/plan/`
3. `docs/architecture/overview.md`: how the system fits together

## Rule 1: Explain things simply

- Write explanations, docs and commit messages in plain, simple English.
- Use short sentences and everyday words.
- When you must use a technical term, explain it in one line.
- New tools get a beginner-friendly guide in `docs/guides/`.

## Rule 2: Never hardcode values

Values that may change live in one place only.

| Value | Where it lives |
|---|---|
| Colours, fonts, spacing, shadows | `apps/web/src/styles/tokens.css` |
| URLs, ports, hostnames | Environment variables |
| API keys, passwords | Environment variables, never in code |
| AI model names | Environment variables |
| Limits and thresholds (file size, rate limits) | `apps/api/src/costpilot/shared/config.py` settings |

Every new setting must also be added to `.env.example` with no real value. `scripts/check_no_hardcoded.py` fails the build if a rule is broken.

## Rule 3: Never commit secrets or real data

- Never commit `.env`, keys, tokens or passwords.
- Never commit real billing files. Use `samples/` or `apps/api/tests/fixtures/`, with made-up data only.
- Gitleaks blocks secrets before each commit. Do not skip it with `--no-verify`.
- If a secret is committed by mistake, tell the owner straight away and replace the secret. Deleting the commit is not enough.

## Rule 4: No AI co-authors

- Commits use the developer's own Git name and email.
- No `Co-Authored-By` lines and no "Generated with" lines, in commits or pull requests.
- A Git hook rejects these commits.

## Rule 5: Keep clean architecture

The backend is one app split into modules: `identity`, `documents`, `billing`, `analytics`, `recommendations`, `assistant`, `knowledge`, `audit`.

Every module has four layers. Code only points inward:

```
api  →  application  →  domain  ←  infrastructure
```

| Layer | What goes here | What must not go here |
|---|---|---|
| `domain` | Pure business rules | FastAPI, SQLAlchemy, LangChain, Pandas |
| `application` | Steps of a use case, plus interfaces such as "storage" | Direct database or API calls |
| `infrastructure` | Real tools: Postgres, S3, Gemini, Qdrant | Business rules |
| `api` | Routes and request or response shapes | Business logic |

- One module may only import another module through its `contracts.py` file.
- `composition.py` is the only place that connects modules to real tools.
- `lint-imports` and `tests/architecture/` fail the build if these rules are broken.

On the frontend, each screen lives in `apps/web/src/features/<name>/`. Features do not import each other. Shared parts go in `src/components/` and `src/lib/`.

## Rule 6: Money must be exact

- All money calculations are done by normal code, never by the AI.
- Use `Decimal` in Python and `NUMERIC` in PostgreSQL. Never use `float` for money.
- Never add amounts in different currencies together.
- The AI may only show numbers that came from a tool. See `docs/architecture/ai.md`.

## Rule 7: Keep user data separate

- Every table with user data has a `workspace_id` and a Row-Level Security rule.
- AI tools never accept a `workspace_id` as an input. It comes from the login session.
- Bills and documents are untrusted data, never instructions to the AI.
- Only approved summary fields are sent to Gemini: no account IDs, resource names or tags.

## Rule 8: Keep it free

Choose the production-quality option that costs $0. If something cannot be free, say so before adding it. Check `docs/plan/ROADMAP.md` for the memory limits on our small server.

## Rule 9: Test everything you build

- Every feature comes with tests.
- Every bug fix comes with a test that would have caught it.
- Money calculations are checked against hand-worked "golden" test bills.
- Run `make up`, then `make check`, before every commit.

## Finishing a phase

Do all of these before saying a phase is done:

1. Tick every item in the phase's checklist file. If an item was moved or dropped, say why.
2. Update the status table in `docs/plan/ROADMAP.md`.
3. Add a dated entry to `docs/logs/BUILD-LOG.md`.
4. Add a note to `docs/decisions/` for any big decision.
5. Update `README.md` if setup or features changed.
6. Make sure `make check` passes.

## Git workflow

- One branch per phase, such as `phase-1-login`. Merge into `main` with a pull request.
- Commit messages are short and say what changed: `Add upload size check`.
- AI tools commit locally and only push when told to.

## Useful commands

| Command | What it does |
|---|---|
| `make setup` | Installs everything and creates your `.env` |
| `make up` | Starts all services in Docker |
| `make down` | Stops all services |
| `make check` | Runs all tests, style checks and rule checks |
| `make test` | Runs tests only |
| `make e2e` | Tests the full user journey in Chrome |
| `make types` | Updates the frontend's API types. Run it after changing an API |
| `make reindex` | Rebuilds documentation search |
| `make eval-search` | Measures search quality |
| `make eval-assistant` | Scores the assistant with real Gemini |
| `make eval-agents` | Compares hard questions with and without AI specialists |
| `make eval-knowledge` | Compares documentation questions with and without the Knowledge Agent |
| `make sample` | Creates made-up bills in `samples/output/` |
| `make backup-check` | Proves a database backup restores in full |
| `make infra-check` | Checks the Terraform files and server scripts |
