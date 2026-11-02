# Build log

A dated record of what was built. Newest entries go at the top.

## 2 Nov 2026: Phase 0, project baseline

**Built**

- Backend skeleton: 8 modules with 4 layers each, settings, logging, error handling and `/api/health`
- Frontend skeleton: design tokens from the design image, sidebar and 5 empty pages
- Local stack in Docker: PostgreSQL, Qdrant, Keycloak, Mailpit, API and web app
- Automatic checks: secrets, hardcoded values, AI co-author lines, clean architecture
- GitHub Actions pipeline, with all actions pinned to exact commits
- Documentation: README, rules, architecture, decisions, plan, guides

**Decided during the work**

- **Node 26** is now the current LTS, so we pinned that.
- **Own ports:** the other local project (SwiftDrop) already uses 3000, 8080 and 5432, so CostPilot uses 3010, 8010, 5433 and 8090.
- **Trivy runs from its Docker image** at a fixed version, not through a GitHub action.
- **Module boundaries** are checked by a small test, because it can allow `contracts.py` imports exactly.

- **Containers run on Colima**, not Docker Desktop. It is free and was already set up.
- **Removed `pip` and Python's test files from the API image.** Trivy found 5 high-severity problems, all inside these unused files, not in our own packages.

**Tested on 2 Nov 2026**

- All 6 services started with `make up`, and all 5 pages and `/api/health` answered
- API requests through the web app reached FastAPI
- Each guard was broken on purpose and caught the problem: secrets, AI co-author lines, hardcoded colours, layer rules, module borders and feature borders
- All 8 Mermaid diagrams are valid
- Keycloak used 1.05 GB of memory, which matches its official sizing

**Moved to a later phase**

- shadcn/ui, Recharts, TanStack Query and the other screen libraries are installed in the phase that first uses them, to keep the baseline small.
- SQLAlchemy and Alembic arrive in Phase 1, with the first tables.
- TypeScript types generated from the API start in Phase 2, with the first real endpoints.
- Playwright starts in Phase 1, with the first real user journey.
- `samples/` covers a Cost Explorer style bill for now. Other formats arrive in Phase 2 and 3.

**Known limits**

- The local Docker machine has only 4 GB of memory and is shared with SwiftDrop. Stop SwiftDrop if things get slow.
