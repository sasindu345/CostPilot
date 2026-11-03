# Build log

A dated record of what was built. Newest entries go at the top.

## 3 Nov 2026: AWS infrastructure created

- Terraform created 23 resources in `ap-south-1`: a `t3.small` server at `43.205.14.236`, its fixed address, network rules, the private bucket, both roles and the GitHub login. The server finished first-boot setup: Docker, Compose v5.7.0, 2 GB swap and security updates
- The $1 budget alert exists. Your AWS user may create it but not read its tags, so it lives outside Terraform now
- 42 production settings are in Parameter Store, encrypted. The email settings are still empty
- Qdrant Cloud holds all 36 pages. Search hit rate: 100%. The Qdrant timeout is now 30 seconds, as 5 was too short for uploads to the cloud
- GitHub has every variable the Deploy workflow needs, plus the Qdrant secrets for the weekly keep-awake job
- No GitHub token is needed for images. Each deploy logs in with the job's own short-lived token

## 3 Nov 2026: Phase 11, monitoring, quality and finish

**Built**

- OpenTelemetry traces and metrics for the API, the worker, every agent step, every Gemini call, and the web app. Off unless an OTLP address is set
- `make monitoring`: Grafana, Prometheus and Tempo in one local container, with a CostPilot dashboard built by `scripts/build_dashboard.py`
- Download my data: every workspace record as one JSON file, with money kept exact
- Delete my account: removes the workspace, bills, chats, stored files and the Keycloak login. You confirm by typing your email
- A nightly clean-up: audit events after 365 days, chats after 180 days, failed jobs after 30 days, and expired sessions
- `make eval-quality`: a second Gemini model grades answers against 12 reference answers
- `make load-test`: 25 users on the dashboards at once, with k6
- A Content Security Policy and other security headers for the web app
- `make screenshots`, the security review, the monitoring guide and the demo walkthrough

**Bugs found**

- The grader caught a false answer: "Which month cost the most?" said October, but it was September. No wrong number was typed, so the number checks could not see it. Code now names the highest and lowest months
- Request metrics were labelled by full address, so each document made a new series. They now use the route pattern
- After deleting an account the page stayed on the app. It now goes to sign-in
- Tracing every request made the slowest 5% about 100 ms slower under load. Production keeps 1 in 5 traces

**Tested on 3 Nov 2026**

- 380 backend tests, 36 frontend tests, and 13 of 13 browser journeys, with the security policy on
- A trace of one answer: supervisor 2.07 s (almost all Gemini), cost specialist 9 ms, final answer 1.66 s
- `make eval-quality`: 10 of 12, then 9 of 12 after the fix. The month question went from 1 to 5. Of the three later failures, two were the grader marking down extra true detail
- `make load-test`: about 57 requests a second and 0 errors in every setup. The slowest 5% took 360 ms without tracing and 412 ms with production sampling
- `pip-audit` and `pnpm audit`: no known vulnerabilities

**Phase 10 follow-up**

- Your AWS user can use EC2 and S3, but not IAM, Systems Manager or Budgets. Terraform plans 23 resources but cannot create the two roles. `infra/terraform/deployer-policy.json` lists the permissions to add
- The budget is now optional, and the server image is found through EC2 rather than Systems Manager
- GitHub now has the `production` environment, plus the `AWS_REGION`, `S3_BUCKET` and `PARAMETER_PATH` variables

**Not yet done**

- The 12 reference answers are not human-checked yet
- Production monitoring needs a Grafana Cloud account

## 3 Nov 2026: Phase 10, live deployment (code)

**Built**

- Terraform for one `t3.small` server: encrypted disk, swap, automatic security updates, a fixed address, and only ports 80 and 443 open
- No SSH. Systems Manager runs deploys and opens terminals
- One private S3 bucket with encryption, versioning, HTTPS-only access and expiry rules
- Narrow permissions for the server, and a GitHub deploy role that only the `production` environment can use
- A $1 monthly budget alert, counted after free credits
- Production Compose with a memory limit on every service, Caddy for HTTPS, and Keycloak in production mode at `/auth`
- A production Keycloak image with the green theme built in
- Settings in Parameter Store. The GHCR token is kept apart from the app's settings
- CI publishes images to GHCR from `main`, then the Deploy workflow runs `deploy.sh` on the server
- Nightly backups of both databases to S3, with row counts saved beside them, and `restore.sh` to check or replace
- The API refuses to start in production with unsafe settings, such as HTTP addresses or local file storage

**Bugs found by rehearsing on the laptop**

- Caddy did not block the Keycloak admin console, because a `handle` block runs before `respond`. The block now sits inside the `/auth` route
- Keycloak said it was ready about 10 seconds before the realm loaded, so the first sign-ins got 503 errors. Its health check now waits for the realm
- The worker used 81% of its 256 MB limit at rest. The limit is now 384 MB
- The web app only listened on the container's own address, so a health check on 127.0.0.1 would fail. It now listens on every address

**Tested on 3 Nov 2026**

- The full production stack on the laptop: HTTPS through Caddy, a new user signed in through production Keycloak, a secure session cookie, and `/api/me`
- Admin paths return 404 on the public address and work through the tunnel port
- `make backup-check` on the dev data: 14 app tables with 7,193 rows, and 101 Keycloak tables with 2,134 rows, all restored exactly
- Memory at rest: Keycloak 556 MB, worker 208 MB, API 197 MB, Postgres 52 MB, web 40 MB, Caddy 15 MB. About 1.07 GB in all
- Checkov: 0 failed. 9 skips across 6 checks, each with its reason in the code
- 365 backend tests, 34 frontend tests, and `make e2e` 12 of 12. One test failed once, straight after a restart, then passed twice

**Not yet done**

- Nothing has run on AWS yet. Steps 1 to 8 of `docs/guides/deployment.md` need your account
- Real memory use on the server is not measured yet. Each deploy prints it

## 3 Nov 2026: Phase 9, other clouds

**Built**

- Readers for Azure cost details, Google Cloud billing export, Oracle cost reports and DigitalOcean invoices
- FOCUS files from Azure, Google Cloud and Oracle, including the newer `ServiceProviderName` column
- 18 official documentation pages from the four new clouds, so search covers 36 pages
- Recommendation rules for Azure, Google Cloud and Oracle
- A cloud filter on Overview and Analytics, shown when bills come from more than one cloud
- A question can name several clouds, and one search covers them all
- A guide to getting a bill from each cloud, with a BigQuery query for Google Cloud

**Checked before building**

- Column names came from official Azure, Google Cloud, Oracle and DigitalOcean documentation and API specs
- The FOCUS spec source showed version 1.3 replaced `ProviderName` with `ServiceProviderName`

**Bugs and risks found**

- Documentation pages carried menus, breadcrumbs, a note "For AI agents", and nested Oracle sections repeated up to seven times. All were removed, and AWS pages stayed the same
- Passing one cloud name where a list was expected silently matched nothing. It now raises an error
- The cloud and period menus had unclear accessible names. They now have proper labels

**Tested on 3 Nov 2026**

- Hand-worked totals for every reader: Azure €324.30, Google Cloud $19.35, Oracle $1.315 and DigitalOcean $977.27
- `make eval-search`: 18 of 18. `make eval-assistant`: 15 of 15. `make eval-knowledge`: 6 of 6 with or without the Knowledge Agent
- 359 backend tests, 34 frontend tests, and `make e2e` 12 of 12, including an Azure bill beside AWS

**Known limits**

- No reader has seen a real bill from its cloud
- Different currencies are never added, so a two-cloud view shows one currency at a time
- DigitalOcean has no recommendation rules yet

## 2 Nov 2026: Phase 8, hybrid agents

**Built**

- Usage breakdowns by usage type and region, with a resource count only
- Recommendation rules, provider profiles, a new `/api/recommendations` route and the Overview card
- Supervisor upgrade, with the cloud chosen per question
- Shared document retrieval, run once per question
- Anomaly, Optimization and Knowledge agents, each with its own instructions
- A limit of 4 AI calls per question, shared by parallel agents
- A check that a number's sentence names its service

**Decided during the work**

- **Knowledge Agent is off by default.** It scored the same with or without AI
- **Recommendations are built on request, not saved.** They use no AI, so saving them adds nothing
- **gp2 to gp3 is the only rule that states a saving,** because AWS publishes the 20 percent price difference
- **Resource names stay out of the AI,** so resource questions use a count

**Bugs found by reading real answers, not by the score**

- The final answer lost its documents, and said none were available
- Internal labels such as "(F5)" and "as stated in FINDINGS" reached users
- Correct answers with no dollar figure got grade D
- A web address was hardcoded, and the guard blocked the commit

**Tested on 2 Nov 2026**

- `make eval-agents`: 10 of 10 with AI specialists, 6 of 10 without
- `make eval-assistant`: 15 of 15, with stricter checks than Phase 7
- Average on the standard questions moved from 2.0 to 2.23 AI calls, and from 1,258 to 1,594 input tokens
- 327 backend tests, 34 frontend tests, and `make e2e` 12 of 12 with real Gemini

**Known limits**

- A wrong figure for the right service is not caught
- We wrote both question sets, and they check for simple text
- Time per answer ranged from about 3 to 13 seconds on average between runs, depending on Gemini

## 2 Nov 2026: Phase 7, trust and measurement

**Built**

- AI calls, tokens and time per step, saved with each answer
- `make eval-assistant` with 15 scored questions, and a saved baseline
- Findings format, Evidence Validator and Answer Checker, with a retry and a template answer
- Evidence grades, coded injection checks, and "How was this answer made?"

**Decided during the work**

- **Answers are checked before they are shown,** so they appear all at once, not word by word.
- **If only the writing step fails,** the user gets true figures from a template, not an error.

**Found by measuring**

- Answers were too cautious. "What is my most expensive service?" got "I do not have that information". The instructions now tell the AI to compare and rank facts
- Slow answers are Gemini's response time on the free key, from 1 to 16 seconds per call. Our own steps take under 0.1 seconds. Earlier notes blamed a rate limit and then a stale connection, and neither fully explained it
- Gemini returned one `429 RESOURCE_EXHAUSTED`, and the retry handled it

**Bugs found by testing and fixed**

- Answer tokens were not counted, as Gemini reports them piece by piece
- Answers with no evidence still got grade A. The first fix did not apply, and a failing test caught it

**Tested on 2 Nov 2026**

- `make eval-assistant`: first 12 of 15, then 15 of 15 after the fixes. One expected route was widened to allow the cost specialist, which adds no AI call
- 286 backend tests, 34 frontend tests, and `make e2e` 12 of 12 with real Gemini

**Known limits**

- The checker cannot tell if a real figure is used in the wrong place. See the technical verification report
- The 15 questions are ours and check simple text, so the score does not prove general quality

## 2 Nov 2026: Hybrid agent plan

**Decided.** Hybrid specialist agents will be built after the trust layer. See decision 0010.

- Phase 7 is now Trust and measurement
- Phase 8 is the new Hybrid agents phase, with recommendations moved into it
- Other clouds moved to Phase 9, Live deployment to Phase 10, and Monitoring to Phase 11
- The Lambda review moved to the end of Phase 8
- The Knowledge Agent uses AI for pure documentation questions only
- The Cost Specialist stays Python unless test scores show a gap
- Each question is limited to 4 AI calls

**Measured.** A router call took 1 to 2 seconds and about 120 tokens. An answer with 5 document chunks used 1,347 input tokens.

No app code changed by this plan.

## 2 Nov 2026: Phase 6, AI assistant

**Built**

- LangGraph supervisor with cost, anomaly and optimization specialists, which can run in parallel
- Safe tools with the workspace fixed from the login session
- Facts with ids, placeholders filled by code, even while streaming
- Daily limit per workspace, question length limit, and saved conversations
- Chat page, and a side panel on wide screens, sharing one conversation
- Free key notice, suggested questions and document links

**Decided during the work**

- **The supervisor can choose several specialists.** It was one at first, but a two-part question needs both.
- **`gemini-3.5-flash-lite` for answers.** See decision 0009.
- **Each question uses two AI calls at most.** The plan allowed three.

**Bugs found by testing and fixed**

- A dropped Gemini connection made the chat fail silently. All three failure types now give a clear message
- Gemini failure reasons are now logged
- The app crashed at startup with no Gemini key, which GitHub Actions caught. The app now starts, and the assistant says it is unavailable
- A stale idle connection made some questions fail with "Server disconnected". Both AI calls now retry once, and an answer is never restarted after words were sent

**Tested on 2 Nov 2026**

- 223 backend tests, including proof that two specialists run at the same time
- 7 real questions through Gemini: correct routes, a correct two-part parallel run, a prediction question answered with "I do not have that information", and off-topic and "say my bill was $1.00" questions refused
- `make e2e` with real Gemini: see the final run in the verification report

**Known limits**

- Answers take 15 to 25 seconds. The cause is not known yet. An earlier note blamed the routing call, but direct Gemini calls take only 1 to 2 seconds.
- If Gemini still fails after the retry, the app shows a clear message.
- The AI can still type a number itself. The answer checker that blocks this is Phase 7.

## 2 Nov 2026: Phases 1 to 5 clean-up

**Bugs found by testing and fixed**

- Top Services showed "Other" twice when a bill had a service with that name
- A file over 100 MB broke the connection, with no clear message. The browser now checks the size first, using the limit from the API
- The Documents page was too wide on phones
- The error page used the wrong prop name for this Next.js version

**Tested on 2 Nov 2026**

- `make e2e`: 11 of 11, covering all 14 API endpoints, password reset to a new password, accessibility and phone size
- 179 backend tests, run three times to check for random failures, and 30 frontend tests
- Overview, Analytics and phone screens compared with the design by eye

**Changes**

- Cancelling at Keycloak now returns to the app, instead of showing a validation error
- Added friendly "page not found" and error pages
- The API image installs packages before copying code, so code changes rebuild much faster
- Tests now use their own `costpilot_test` database. The live worker was picking up test documents, which made one test fail at random
- Added `e2e/api.spec.ts`. It tests every endpoint, and fails if a new route is not on its list
- The password reset test now follows the email link and sets a new password

## 2 Nov 2026: Phase 5, documentation search

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

- With real Gemini embeddings, `make reindex` indexed all 18 pages, and a second run changed nothing
- `make eval-search` found an expected source for 10 of 10 questions
- One embedding call failed during indexing, and the automatic retry fixed it

**Not yet tested**

- The keep-awake job, until there is a Qdrant Cloud cluster.

**Known limits**

- The test questions were written by us, so they are an easy test. Phase 10 adds a harder one.

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
