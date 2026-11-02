# Phase 0: Project baseline

**You will see:** a running empty app, full documentation, and automatic checks that protect the rules.

**Repo and safety**
- [x] Clone the repo into the `cospilot` folder and create branch `phase-0-baseline`
- [x] `.gitignore` covering `.env*` (keeping `.env.example`), keys, Terraform state, uploads, real bills, caches and build output
- [x] `.env.example` listing every setting with no real values
- [x] Gitleaks pre-commit hook, so secrets are blocked before they are committed
- [x] `commit-msg` hook that rejects `Co-Authored-By` and AI attribution lines
- [x] `.claude/settings.json` with attribution turned off

**Rules for humans and AI**
- [x] `AGENTS.md`: the main rule book for any AI tool or developer
- [x] `CLAUDE.md`: a short file that imports `AGENTS.md`, so the rules live in one place
- [x] Rules cover: clean architecture, nothing hardcoded (colours, URLs, API keys, model names, limits), no secrets in Git, no AI co-authors, plain simple English in explanations and docs, the end-of-phase steps, and tests with every feature

**Code skeleton**
- [x] Backend: `apps/api` with all 8 modules and their 4 layers, settings, logging, error handling and `/health`
- [x] Frontend: `apps/web` with a design token file, sidebar layout and empty pages
- [x] All colours sampled from your image into `tokens.css`, the only place they may exist
- [x] `docker-compose.yml` with PostgreSQL, Qdrant, Keycloak and Mailpit (a fake email inbox)
- [x] `Makefile` with simple commands: `make setup`, `up`, `check`, `test`
- [x] `samples/`: a generator for made-up bills (real bills are never committed)

**Automatic checks**
- [x] GitHub Actions: Ruff, Bandit, Pytest, ESLint, Vitest, Gitleaks, Trivy, Docker builds
- [x] `import-linter` for clean architecture
- [x] `scripts/check_no_hardcoded.py`, which fails on raw colours and URLs outside allowed files

**Documentation**
- [x] `README.md`: problem, solution, features, stack, setup, status, and diagrams (system, modules, upload flow, chat flow, deployment)
- [x] `docs/PROJECT-BRIEF.md`: your original brief, unchanged
- [x] `docs/architecture/`: overview, backend, frontend, data model, AI, security, multi-cloud
- [x] `docs/decisions/`: one short note per big decision, such as Qdrant, FOCUS, Keycloak and sessions
- [x] `docs/design/`: your image and the UI spec, including the fixes in section 6
- [x] `docs/plan/`: `ROADMAP.md` (the status of all phases), one checklist file per phase, and `EDGE-CASES.md`
- [x] `docs/logs/BUILD-LOG.md`: dated record of what was built
- [x] `docs/guides/`: getting started and a Keycloak beginner's guide

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
