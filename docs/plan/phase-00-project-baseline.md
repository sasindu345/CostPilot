# Phase 0: Project baseline

**You will see:** a running empty app, full documentation, and automatic checks that protect the rules.

**Repo and safety**
- [ ] Clone the repo into the `cospilot` folder and create branch `phase-0-baseline`
- [ ] `.gitignore` covering `.env*` (keeping `.env.example`), keys, Terraform state, uploads, real bills, caches and build output
- [ ] `.env.example` listing every setting with no real values
- [ ] Gitleaks pre-commit hook, so secrets are blocked before they are committed
- [ ] `commit-msg` hook that rejects `Co-Authored-By` and AI attribution lines
- [ ] `.claude/settings.json` with attribution turned off

**Rules for humans and AI**
- [ ] `AGENTS.md`: the main rule book for any AI tool or developer
- [ ] `CLAUDE.md`: a short file that imports `AGENTS.md`, so the rules live in one place
- [ ] Rules cover: clean architecture, nothing hardcoded (colours, URLs, API keys, model names, limits), no secrets in Git, no AI co-authors, plain simple English in explanations and docs, the end-of-phase steps, and tests with every feature

**Code skeleton**
- [ ] Backend: `apps/api` with all 8 modules and their 4 layers, settings, logging, error handling and `/health`
- [ ] Frontend: `apps/web` with a design token file, sidebar layout and empty pages
- [ ] All colours sampled from your image into `tokens.css`, the only place they may exist
- [ ] `docker-compose.yml` with PostgreSQL, Qdrant, Keycloak and Mailpit (a fake email inbox)
- [ ] `Makefile` with simple commands: `make setup`, `up`, `check`, `test`
- [ ] `samples/`: a generator for made-up bills (real bills are never committed)

**Automatic checks**
- [ ] GitHub Actions: Ruff, Bandit, Pytest, ESLint, Vitest, Gitleaks, Trivy, Docker builds
- [ ] `import-linter` for clean architecture
- [ ] `scripts/check_no_hardcoded.py`, which fails on raw colours and URLs outside allowed files

**Documentation**
- [ ] `README.md`: problem, solution, features, stack, setup, status, and diagrams (system, modules, upload flow, chat flow, deployment)
- [ ] `docs/PROJECT-BRIEF.md`: your original brief, unchanged
- [ ] `docs/architecture/`: overview, backend, frontend, data model, AI, security, multi-cloud
- [ ] `docs/decisions/`: one short note per big decision, such as Qdrant, FOCUS, Keycloak and sessions
- [ ] `docs/design/`: your image and the UI spec, including the fixes in section 6
- [ ] `docs/plan/`: `ROADMAP.md` (the status of all phases), one checklist file per phase, and `EDGE-CASES.md`
- [ ] `docs/logs/BUILD-LOG.md`: dated record of what was built
- [ ] `docs/guides/`: getting started and a Keycloak beginner's guide

## Finish this phase

- [ ] All items above are ticked, or the change is explained
- [ ] `docs/plan/ROADMAP.md` is updated
- [ ] `docs/logs/BUILD-LOG.md` has a dated entry
- [ ] `make check` passes
