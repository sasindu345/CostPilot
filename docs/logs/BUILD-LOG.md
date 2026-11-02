# Build log

A dated record of what was built. Newest entries go at the top.

## 2 Nov 2026: Phase 1, login and app shell

**Built**

- Keycloak realm and green login page, both saved as files
- Sign-up, email verification, sign-in, sign-out and password reset
- Sessions in PostgreSQL, using a random ticket in a secure cookie
- Users, workspaces, memberships and audit events, with one workspace made for each new user
- Row-Level Security, plus a low-power database user for the app
- Database migrations with Alembic, run automatically by `make up`
- Top bar, user menu, login check and Settings page

**Decided during the work**

- **Small JWT library:** we use PyJWT and a short login file, not Authlib. It is easier to read.
- **Password after email check:** Keycloak 26.8 asks for the password after the email is verified. We kept this, as it is safer.
- **Only the ID token is stored,** because sign-out needs it. Nothing else needs Keycloak tokens.
- **Login page colours** come from the web app's `tokens.css`, so there is still one source of colours.
- **`make e2e` uses your installed Chrome.** Playwright's own browser download stalled here.

**Tested on 2 Nov 2026**

- `make e2e`: sign up, verify email, choose a password, reach the app, see Settings, sign out, sign in, and request a password reset email
- 24 backend tests, including 6 against real PostgreSQL that try to cross between workspaces
- 7 frontend tests
- Trivy found no high or critical problems in the API or web images, after removing `pip` and `npm` from them. The scan ran from the Mac, because the vulnerability database would not download inside Colima

**Known limits**

- The bell in the top bar does nothing yet. Notifications arrive with later features.
- The reset test confirms the email is sent. It does not follow the link.
- Turning off a user in Keycloak does not end their current session until it expires.
- `make e2e` is not in GitHub Actions yet, to save free minutes.

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
- TypeScript types generated from the API start in Phase 2, with the first real endpoints.
- `samples/` covers a Cost Explorer style bill for now. Other formats arrive in Phase 2 and 3.

**Known limits**

- The local Docker machine has only 4 GB of memory and is shared with SwiftDrop. Stop SwiftDrop if things get slow.
