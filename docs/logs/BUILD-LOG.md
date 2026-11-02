# Build log

A dated record of what was built. Newest entries go at the top.

## 2 Nov 2026: Phase 5, documentation search (waiting for a Gemini key)

**Built**

- 18 trusted AWS pages in `knowledge/sources.yaml`, and 10 test questions
- Load, clean, split, embed and save to Qdrant, tagged by cloud
- `make reindex`, which skips unchanged pages and removes old ones
- Search with a cloud filter and a minimum score
- `make eval-search`, and a job that keeps the free Qdrant cluster awake

**Decided during the work**

- **Qdrant's own client, not LangChain's wrapper.** It gives direct control of filters and page hashes.
- **Page hashes decide what to embed,** so a rerun uses no free quota.

**Tested on 2 Nov 2026**

- 20 tests using a real in-memory Qdrant and a fake embedder
- All 18 live AWS pages loaded, and the real Qdrant container stored and found data
- `langchain-google-genai` works on Python 3.13, which closes an open item from the plan

**Not yet tested**

- Real Gemini embeddings, `make reindex` and `make eval-search`, because there is no key yet.
- The keep-awake job, until there is a Qdrant Cloud cluster.

## 2 Nov 2026: Phase 4, dashboard and analytics (waiting for browser check)

**Built**

- Exact calculations: totals, change, trends, top services with an Other row, and month comparison
- Unusual spending detection with NumPy, using each service's own usual level
- Overview page with the corrections from `docs/design/ui-spec.md`
- Analytics page with period, cost type, provider and currency filters
- Sample data button, phone navigation, and a table view for the chart

**Decided during the work**

- **Cards are labelled by month,** such as "Oct 2026". "This Month" would be wrong when the newest bill is from last month.
- **Half-finished months** compare with the same days of the month before. Summary files cannot do that, so the percentage shows "Not available" and no guess is made.
- **A month with no bill stays empty.** It is not shown as $0.
- **Recommendations card** only says they are coming. It shows no made-up savings.

**Tested on 2 Nov 2026**

- 156 backend tests, including the design's −8.1% and half-finished months on real PostgreSQL
- 29 frontend tests

**Not yet tested**

- The pages have not been seen in a real browser. `e2e/dashboard.spec.ts` has not been run.

## 2 Nov 2026: Phase 3, reading bills

**Built**

- Common FOCUS records, with provider and detail level
- Readers for AWS Cost Explorer, CUR old and new columns, and FOCUS exports
- `.csv` and `.csv.gz` support, with all records saved together or not at all
- Overlap rules, a new `replaced` status, and monthly summaries built only from counted files
- Provider, billing period and record count on the Documents page

**Decided during the work**

- **No Pandas for reading bills.** See decision 0008.
- **Billed and effective cost are both kept.** Billed matches the invoice. Effective spreads prepaid Savings Plans and reserved instances over the usage they paid for.

**Tested on 2 Nov 2026**

- Hand-worked bills: Savings Plans, reserved instances, credits, exact decimals, and old and new CUR columns giving identical records
- 123 backend tests, including real PostgreSQL tests for overlaps, currencies, double counting, partial failures and workspace privacy
- Sample bill totals exactly $248.60

**Known limits**

- All reader formats were built from AWS docs and memory, with made-up files. They have not been checked against a real AWS file yet. The Cost Explorer layout is the least certain.
- Two Cost Explorer files from different accounts look the same, so the newest wins.
- Unknown AWS services are grouped as `Other`.

## 2 Nov 2026: Phase 2, document upload

**Built**

- Upload with type, size and fingerprint checks, plus safe file names
- Local folder and S3 storage behind one interface
- Background job table in PostgreSQL and a separate worker
- Documents page: upload, list, status, details, delete and reprocess
- API types generated into the frontend with `make types`
- Sample AWS bills: Cost Explorer, CUR 2.0 and compressed CUR

**Decided during the work**

- **The `jobs` table has no Row-Level Security,** as the worker must see every workspace. It only holds IDs and error class names.
- **`composition.py` connects the modules,** because the API and the worker both need it.
- **`JobRunner.process` knows nothing about the queue,** which keeps the Lambda option in decision 0007 open.
- **`make e2e` runs one test at a time,** as Chrome timed out starting several at once on this machine.

**Tested on 2 Nov 2026**

- `make e2e`: upload, processing, duplicate refused, wrong type refused, empty bill fails with a reason, details, reprocess, delete, and one user cannot see or delete another user's document
- S3 storage with a fake S3 service (moto), not real AWS yet

**Moved to a later phase**

- Cleaning formula tricks from bill cells moved to Phase 3, where the cells are first read. File names are cleaned now.

**Known limits**

- If deleting a stored file fails after its record is deleted, the file stays and only a log line records it.
- The local disk and Docker network were both tight during this work. See the Roadmap.

## 2 Nov 2026: First GitHub Actions results

- `phase-1-login`: all 4 jobs passed (project rules, backend, frontend, Docker images). This branch holds all of Phase 0 as well, so Phase 0 is now closed.
- `phase-0-baseline`: the image scan failed, because the `npm` security fix is only on `phase-1-login`. No fix is needed on that branch.
- `main` was pushed earlier at an older commit. Its run failed at the Docker images step, and it has not been updated.

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
