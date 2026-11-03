# CostPilot – Development Plan

> **Updated 2 Nov 2026:** Phases 7 onward were reordered to add hybrid agents. See [decision 0010](../decisions/0010-hybrid-agents-after-trust-layer.md). The roadmap is the current source of truth.

## 1. Context

**Why this plan exists.** CostPilot turns confusing cloud bills into clear answers. A user uploads a bill, sees their spending on a dashboard, and asks an AI assistant questions in plain English. The numbers come from normal code, not from the AI, so they can be trusted.

**Starting point.** The GitHub repo `sasindu345/CostPilot` is private and empty, and so is the local `cospilot` folder. There is no existing code to reuse, so this plan creates everything.

**The aim.** Show real-world, production-level skill while spending as close to $0 as possible. Every design choice is made as if real customers would use it, even though there are none yet.

**Your decisions so far**

| Topic | Decision |
|---|---|
| Hosting | AWS EC2 free tier, $0 target, production-level practices |
| Vector database | Qdrant (something new; you have already used pgvector) |
| Login | Keycloak, with a step-by-step guide because it is new to you |
| Clouds | Start with AWS, but built to support Azure, GCP, Oracle and DigitalOcean |
| Git commits | Keep `wijewardanasj.23@uom.lk`; no AI co-author lines anywhere |

---

## 2. What I changed from your brief, and why

| Your brief | This plan | Why it is better |
|---|---|---|
| AWS billing format only | **All bills are converted into FOCUS**, an open standard format for cloud bills | AWS, Azure, Google Cloud and Oracle can all export FOCUS. One FOCUS reader covers four clouds, so we write far less code. Adding a cloud later means adding one small reader, nothing else changes. |
| ChromaDB | **Qdrant** | Your choice. It has a free cloud plan, which saves memory on our small server, and it filters by cloud provider well. |
| Own login | **Keycloak checks the password; FastAPI keeps the session** | The browser only holds a meaningless ticket (a cookie), never a real token. Safer, and all the login logic stays in one place. I avoided Auth.js: it now only receives security fixes and v5 is still in beta. |
| Custom AES-256-GCM encryption with KMS | **S3's built-in AES-256 encryption** (a config setting turns on KMS later) | Free, and hand-written encryption code is risky. A customer KMS key costs $1 a month. |
| Pandas does all calculations | **Pandas reads files; exact totals are done in PostgreSQL with exact decimals** | Normal computer decimals cause small rounding errors, which is not acceptable for money. |
| Many AI agents | **Same supervisor and specialist agents, but most steps are plain code** | The free Gemini plan allows very few requests per minute. Aim: at most 3 AI calls per question. |
| AI recommendations | **Plain-code rules find the problem; AI only explains it.** Made once after upload and saved | Loading the dashboard costs no AI calls, and the findings are always repeatable. |
| Prometheus and Grafana on the server | **Grafana Cloud free plan** in production; the full stack runs only on your laptop | Saves memory on the small server. |
| AWS Secrets Manager | **AWS Parameter Store** (standard tier) | Free. Secrets Manager charges per secret. |

**Added because they were missing:**
- `uv`, a fast Python package tool
- Playwright for browser tests
- Automatic checks that catch hardcoded values
- Automatic checks that keep the clean architecture rules
- TypeScript types generated from the API, so the frontend and backend cannot drift apart

---

## 3. Hosting at $0: the limits you should know

**Keycloak is the problem.** Its official guide says it needs about 1 GB of memory even when idle, so a 1 GB `t3.micro` server cannot run it. We need a **2 GB server (`t3.small`)**.

**Memory plan for `t3.small`** (only the Keycloak figure is official; the rest are my estimates, measured in Phase 10):

| Service | Memory |
|---|---|
| Keycloak | ~1,000 MB |
| FastAPI and background worker | ~450 MB |
| PostgreSQL | ~200 MB |
| Next.js | ~150 MB |
| Caddy (web server and free HTTPS) | ~30 MB |
| **Total** | **~1.8 GB, plus 2 GB of swap as a safety buffer** |

Qdrant does not run on this server. It uses the free Qdrant Cloud plan. If memory is still too tight, Next.js moves to Vercel's free plan with no code change.

**What is free, and what catches you out**

| Item | Choice | Catch |
|---|---|---|
| EC2 `t3.small` | Free plan credits | AWS's free plan lasts 6 months or until credits run out. Costs about $20 of credits a month with storage and IP address (my estimate), so $100 lasts about 5 months. |
| Public IP address | Comes with the server | About $3.65 a month, taken from your credits. |
| Qdrant Cloud | Free 1 GB plan | Paused after 1 week of no use, deleted after 4 weeks. A weekly automatic search keeps it awake, and one command rebuilds it. |
| Gemini | Free key | **See the warning below.** |
| HTTPS and domain | Caddy, Let's Encrypt, DuckDNS | Free. The address looks like `costpilot.duckdns.org`. |
| GitHub Actions | 2,000 free minutes a month on private repos | Our images could pass the 500 MB private storage limit, so we keep only the latest two. Making the repo public removes both limits. |

**⚠️ Gemini free key warning.** Google's terms say not to send sensitive or confidential information to the free service, and that human reviewers may read it. So:
- Build and demo with **made-up sample bills only**.
- Gemini only ever receives summary numbers, never account IDs, resource names or tags.
- The app shows a notice while it is on a free key.
- Before uploading real bills, switch to a paid key. It costs roughly under 1 cent per question, and the only change is one setting.

**When the free AWS period ends**, the account may close, so the setup stays portable: everything is Docker, and nightly backups go to S3. You can then pay for AWS or move to Oracle Cloud's Always Free server (about 12 GB of memory, no time limit).

**One check first.** Phase 10 starts by confirming your account really allows `t3.small`, because a micro-only account cannot run Keycloak. This takes one command.

---

## 4. Final tech stack

| Part | Tools |
|---|---|
| Frontend | Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui, Recharts, TanStack Query, React Hook Form, Zod |
| Backend | Python 3.13, FastAPI, Pydantic, SQLAlchemy, Alembic, uv |
| Data | PostgreSQL, Pandas, NumPy, Amazon S3 (a local folder during development) |
| AI | Gemini, LangChain, LangGraph, Qdrant |
| Login | Keycloak |
| Testing | Pytest, Vitest, Playwright, DeepEval or Ragas |
| Security checks | Ruff, Bandit, Gitleaks, Trivy, Checkov |
| Delivery | Docker Compose, GitHub Actions, GHCR, Terraform, Caddy |
| Monitoring | OpenTelemetry, Prometheus, Grafana |

Gemini model names live only in settings, never in code. Starting choices: `gemini-3.8-flash` for answers, `gemini-3.5-flash-lite` for simple routing, `gemini-embedding-2` for documents.

**Your machine needs:** `uv` (not installed) and a current Node LTS. Your Node 20 is past its support date, so I will pin Node 24 or newer. pnpm comes through corepack.

---

## 5. How the system fits together

```
 Browser
    │  HTTPS, one web address
    ▼
 Caddy ──► Next.js (screens)
    │
    ├────► FastAPI (one app, split into clear modules)
    │        ├─ identity         who you are, your workspace
    │        ├─ documents        upload, store, status
    │        ├─ billing          read any cloud's bill, convert to FOCUS
    │        ├─ analytics        all money calculations
    │        ├─ recommendations  rule-based cost findings
    │        ├─ assistant        LangGraph agents and safety checks
    │        ├─ knowledge        cloud documentation search
    │        └─ audit            record of what happened
    │
    └────► Keycloak (login pages)

 FastAPI talks to: PostgreSQL · S3 · Qdrant · Gemini
```

### Clean architecture rules

Each backend module has the same four layers, and code only points inward:

```
api  →  application  →  domain  ←  infrastructure
```

- **domain:** pure business rules. No FastAPI, database or LangChain imports.
- **application:** the steps of each use case, plus interfaces such as "storage" or "parser".
- **infrastructure:** the real tools, such as S3, Postgres and Gemini.
- **api:** routes only, with no business logic.

Modules only use each other's public interface. `import-linter` fails the build if a rule is broken, so the rules enforce themselves.

### Multi-cloud design

```
 Any bill file ─► detect type ─► one small reader per format ─► FOCUS records ─► PostgreSQL
```

Everything after the reader, including analytics, the dashboard and the AI, never knows which cloud a bill came from.

| Cloud | Files we read | Phase |
|---|---|---|
| AWS | Cost Explorer CSV, CUR (old and new columns), FOCUS | 3 |
| Azure, Google Cloud, Oracle | FOCUS export first (works from the shared reader) | 9 |
| Azure, Google Cloud, Oracle | Native report formats | 9 |
| DigitalOcean | Invoice CSV (no FOCUS export, so it needs its own reader) | 9 |

### How login works (explained simply)

1. You click Sign in, and FastAPI sends you to the Keycloak login page.
2. Keycloak checks your password and sends you back with a proof of identity.
3. FastAPI verifies the proof, saves your session in PostgreSQL, and gives the browser a random ticket in a secure cookie.
4. Every request carries that ticket. FastAPI looks it up and knows who you are.

Keycloak knows **who you are**. Our database knows **which workspace is yours**.

### How the AI is kept honest

1. **Tools run first.** Plain code fetches the real numbers and gives each fact an ID, such as `F1 = EC2 cost in September`.
2. **The AI writes placeholders, not numbers.** It writes "EC2 rose to `{{F1}}`", and our code fills in the real value. The AI cannot invent a figure it never had.
3. **A checker reads the answer.** Any money or percentage not linked to a fact is rejected. After one retry, the app uses a plain template answer.
4. **Evidence gets a grade.** Code, not the AI, gives a grade from A to D based on the data and documents found.
5. **Savings need proof.** A savings amount only appears if code can calculate it. Otherwise it says "Needs usage data". Bills do not show how busy a server is, so "Right-size EC2, save ~$32" cannot be proven from a bill alone.
6. **The AI cannot reach other users' data.** The workspace ID comes from the login session, and the AI cannot pass or change it. PostgreSQL Row-Level Security blocks other workspaces as a second lock.
7. **Bills are treated as untrusted.** A tag on a bill could say "ignore your instructions". Only approved fields ever reach the AI.

---

## 6. Problems I found in the design image

| Problem | Fix |
|---|---|
| "This Month" shows **+8.2%** in red while "Change" shows **−8.2%**. The real value is **−8.1%** ($248.60 vs $270.40). | One calculated value, shown in one direction. A drop is not shown as a red warning. |
| The filter says "Last 6 Months" but the chart shows 5 months. | The chart always matches the filter. |
| September is about $262 on the chart but "Last Month" is $270.40. | Both use the same data. |
| Top Services add up to $203.60 of $248.60, so $45 is missing. | Add an "Other" row. |
| The chart's axis starts at $100, which makes changes look bigger. | Start at $0. |
| Savings like "~$32/month" break your own rule about unproven numbers. | See point 5 above. |
| The AI Assistant appears as both a side panel and a full page. | Same conversation in both. The side panel shows on wide screens only. |
| A half-finished month looks like a big drop against a full month. | Compare the same number of days and label it "so far". |

---

## 7. Edge cases covered

| Situation | What happens | Phase |
|---|---|---|
| Same file uploaded twice | Detected by its fingerprint; the user is told and nothing is counted twice | 2 |
| Two files cover the same month | The newest or more detailed file wins; the other is marked "Replaced" | 3 |
| AWS updates a bill after month end | The new version replaces the old one | 3 |
| Wrong or broken file | Rejected with a clear reason, and the row number where possible | 2, 3 |
| Very large file or compressed bomb | Size limits and read-in-chunks | 2 |
| Upload fails halfway | The job can be retried safely, with no half-saved data | 2 |
| Credits, refunds, tax, Savings Plans, reserved instances | Handled as separate charge types, using FOCUS rules | 3 |
| Different currencies | Never added together; shown separately | 3, 4 |
| Formula tricks in a CSV | Cleaned when read and when exported | 2 |
| Summary-only file (Cost Explorer) | The AI knows it has no detail and says so honestly | 6 |
| Gemini rate limit or downtime | Retry, then a clear message; dashboards keep working | 6 |
| Qdrant asleep | The AI still answers bill questions and says documents were unavailable | 6 |
| Document deleted | Its data, summaries and file are removed, and totals are recalculated | 2, 4 |
| User asks about other users or tries to break the AI | Blocked and logged | 7 |
| New user with no data | Friendly empty screens and a sample-data option | 4 |

---

## 8. Phase-by-phase plan

Every phase ends with the same steps:
- Tick the checklist in the phase file
- Update `docs/plan/ROADMAP.md`
- Add an entry to `docs/logs/BUILD-LOG.md`
- All checks pass

### Phase 0 – Project baseline
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

### Phase 1 – Login and app shell
**You will see:** sign up, sign in, and the real sidebar layout from your design.
- [x] Keycloak setup saved as a file, so it rebuilds automatically
- [x] Beginner's guide: what a realm, client, role and token are
- [x] Sign in, sign out, session storage and secure cookies
- [x] Email verification and password reset
- [x] Green Keycloak login page to match the app
- [x] Users, workspaces and memberships, with one workspace made for each new user
- [x] Row-Level Security turned on, with a test proving users cannot see each other's data
- [x] Audit table started
- [x] Sidebar, top bar, user menu and Settings page

### Phase 2 – Document upload
**You will see:** upload a file and watch its status change.
- [x] Storage interface, with a local folder and S3 versions
- [x] Background job table in PostgreSQL (no Redis needed) and a small worker
- [x] File checks: type, size, fingerprint, safe names
- [x] Documents page: upload, list, status, details, delete, reprocess
- [x] Sample bill generator working for AWS

### Phase 3 – Reading bills (AWS first)
**You will see:** an uploaded bill turned into clean records.
- [x] FOCUS-based tables, including provider and data detail level
- [x] Reader interface and file type detection
- [x] AWS readers: Cost Explorer, CUR old and new columns, FOCUS
- [x] `.csv` and `.csv.gz` support
- [x] Overlap rules for files covering the same period
- [x] Hand-checked "golden" test bills, so the totals are proven correct
- [x] Monthly and service summary tables

### Phase 4 – Dashboard and analytics
**You will see:** your design working with real calculated data.
- [x] Analytics calculations: totals, changes, top services, trends, period comparison
- [x] Unusual spending detection
- [x] Overview page, matching your design with the fixes in section 6
- [x] Analytics page with filters
- [x] Empty, loading and error states
- [x] Mobile and accessibility review

### Phase 5 – Documentation search (RAG)
**You will see:** a test search returns the right AWS advice.
- [x] `knowledge/sources.yaml`: the list of trusted documents
- [x] Load, split, create embeddings, save to Qdrant, tagged by provider
- [x] `make reindex`, safe to run repeatedly
- [x] Search with a relevance check
- [x] Starter set of test questions, to measure search quality
- [x] Weekly job to keep the free Qdrant cluster awake

### Phase 6 – AI assistant
**You will see:** ask a question and get a live, streaming answer about your bill.
- [x] Gemini connection with limits on usage per workspace, plus retries
- [x] Privacy filter: only approved summary fields reach the AI
- [x] Safe tools that cannot accept a workspace ID
- [x] LangGraph supervisor with cost, anomaly and optimization specialists
- [x] Streaming answers
- [x] Chat page and side panel, sharing one conversation
- [x] Saved conversations and suggested questions

### Phase 7 – Trust and measurement
**You will see:** every answer shows its evidence and grade, and quality can be measured.
- [x] Time every step of an answer, and find the cause of the 15 to 25 second answers
- [x] Record AI calls, tokens and time for each question in the audit log
- [x] Scored test questions, `make eval-assistant`, and a saved baseline
- [x] Findings format in Pydantic
- [x] Evidence Validator
- [x] Answer Checker with a retry and a template fallback, which also covers chat history
- [x] Evidence grades A to D
- [x] Coded protection against prompt injection
- [x] "How was this answer made?" view from the audit records

### Phase 8 – Hybrid agents
**You will see:** deeper answers from specialist agents, proven against the baseline. See decision 0010.
- [x] Breakdown tools: usage type, region and resource
- [x] Recommendation rules and the Overview card
- [x] Provider profiles and shared document retrieval
- [x] Supervisor upgrade
- [x] Anomaly Agent: Python detector first, AI only if needed
- [x] Optimization Agent
- [x] Knowledge Agent: built, but off by default, as it did not beat the baseline
- [x] Final Response Agent, using validated findings only
- [x] Limit of 4 AI calls per question, with a Python fallback
- [x] Compare each AI agent with the baseline, and remove any that does not help
- [x] Review the Lambda options in decision 0007

### Phase 9 – Other clouds
**You will see:** a bill from each cloud shows up in the same dashboard.
- [x] FOCUS reader tested with Azure, Google Cloud and Oracle samples
- [x] Native readers for Azure, Google Cloud and Oracle
- [x] DigitalOcean invoice reader
- [x] Provider filter in the dashboard
- [x] Documentation for each cloud added to Qdrant
- [x] Provider-specific recommendation rules

### Phase 10 – Live deployment
**You will see:** CostPilot running on the internet with HTTPS.
- [ ] Confirm `t3.small` is free for your account
- [ ] Set up AWS budget alerts first, so there are no surprise bills
- [x] Terraform: EC2, network rules, private S3 bucket, narrow permissions
- [x] Checkov and Trivy scans in the pipeline
- [x] Production Compose with memory limits and swap
- [x] Caddy HTTPS, Keycloak in production mode, Parameter Store secrets
- [x] Images pushed to GHCR, with automatic deployment from GitHub Actions
- [x] Nightly encrypted backups to S3, and a tested restore
- [ ] Measure the real memory use

### Phase 11 – Monitoring, quality and finish
**You will see:** live dashboards, measured AI quality and portfolio-ready docs.
- [x] OpenTelemetry tracing through the web app, API and agents
- [x] Prometheus and Grafana locally, Grafana Cloud in production
- [x] AI quality tests with our own grader instead of DeepEval or Ragas (decision 0012). Human checks of the reference answers are still to do
- [x] Data retention, account deletion and data export
- [x] Final security review and load test
- [x] Final README with screenshots and a demo walkthrough

**Later ideas (not in this plan):** connect directly to a cloud account with read-only access. This would give real usage data, so right-sizing savings could finally be proven.

---

## 9. Git workflow

- One branch per phase, for example `phase-1-login`, merged into `main` through a pull request.
- Commits use your name and `wijewardanasj.23@uom.lk`. Add this email to your GitHub account so the commits count on your profile.
- No `Co-Authored-By` or AI attribution in commits or pull requests. A hook enforces this.
- I commit locally, and only push when you tell me to.

---

## 10. How we will know Phase 0 works

1. `make setup` and `make up` start all services from a fresh clone.
2. `/health` on the API returns OK, and all five pages open in the browser.
3. `make check` passes every test, lint and security check.
4. **The safety rules are proven by trying to break them:**
   - A fake API key in a commit is blocked by Gitleaks
   - A commit with `Co-Authored-By` is rejected
   - A hex colour in a component fails the check
   - The domain layer importing FastAPI fails `import-linter`
   - `git check-ignore .env` confirms `.env` is ignored
5. All diagrams display correctly in the README.
6. GitHub Actions runs green on the first push, once you approve pushing.

---

## 11. Facts checked (2 Nov 2026)

- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) and [Gemini API terms](https://ai.google.dev/gemini-api/terms)
- [EC2 free tier by account date](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
- [AWS public IPv4 charge](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights)
- [Keycloak memory sizing](https://www.keycloak.org/high-availability/concepts-memory-and-cpu-sizing)
- [Qdrant pricing](https://qdrant.tech/pricing/) and [Qdrant free cluster rules](https://qdrant.tech/documentation/cloud/create-cluster/)
- [FOCUS specification](https://focus.finops.org/focus-specification/)
- [AWS CUR 2.0 columns](https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-cur2-line-item.html)
- [DigitalOcean invoices](https://docs.digitalocean.com/platform/billing/invoices/)
- [Oracle Always Free changes](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- [Auth.js status](https://authjs.dev/getting-started/integrations)
- [Next.js version table](https://www.it-server-room.com/en/next-js-version-support-policy-lts-eol-eol/)
- [LangChain release policy](https://docs.langchain.com/oss/python/release-policy.md)

**Still to confirm when building:** `langchain-google-genai` works on Python 3.13, each cloud's exact file columns (from real sample files), and Oracle's current free limits.
