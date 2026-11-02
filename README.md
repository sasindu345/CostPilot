# CostPilot

**An AI assistant that explains your cloud bill in plain English, with numbers you can trust.**

![CostPilot overview design](docs/design/overview-mockup.png)

> **Status:** Phase 1 (login and app shell) is built. The design above is the target, not the current app. See the [roadmap](docs/plan/ROADMAP.md) for what is built and what remains.

## The problem

Cloud bills are hard to read. A single monthly report can have thousands of rows, and each cloud provider uses its own format. So people usually only notice a cost problem after they have paid for it. They then have to ask questions like:

- Why did my bill go up this month?
- Which service costs me the most?
- Where can I safely save money?

General AI chatbots are risky for this job. They can invent numbers, and they can suggest savings that have no evidence behind them. For money, a wrong answer that sounds right is worse than no answer.

## The solution

CostPilot gives you one place to upload bills, see your spending and ask questions.

- **Upload any bill.** Bills from any cloud are converted into one standard format, called [FOCUS](https://focus.finops.org/).
- **See your spending.** The dashboard shows totals, trends, top services and unusual changes, for all your history.
- **Ask in plain English.** The AI assistant reads your data through safe tools and uses trusted cloud documentation.
- **Trust the numbers.** All calculations are done by normal code. The AI cannot write a figure of its own. Every answer shows its evidence and a grade.
- **Keep data private.** Each user's data is locked to their own workspace, and only summary numbers ever reach the AI.

## Features

| Area | What it does |
|---|---|
| **Overview** | Total spending, monthly change, trends, top services and recommendations |
| **Documents** | Upload, track, reprocess and delete bills |
| **Analytics** | Compare periods, explore services and find unusual spending |
| **AI Assistant** | Ask questions about your bills and cloud cost best practice |

**Clouds:** AWS first, then Azure, Google Cloud, Oracle Cloud and DigitalOcean.

## System overview

```mermaid
flowchart LR
    user([User]) -->|HTTPS| caddy[Caddy web server]
    caddy --> web[Next.js screens]
    caddy --> api[FastAPI backend]
    caddy --> keycloak[Keycloak login]
    api --> postgres[(PostgreSQL)]
    api --> s3[(Amazon S3<br/>original bills)]
    api --> qdrant[(Qdrant<br/>cloud documentation)]
    api --> gemini[Gemini AI]
    keycloak --> postgres
```

## Inside the backend

The backend is one app, split into clear modules. This keeps it simple to run, but a module can become its own service later if needed.

```mermaid
flowchart TB
    subgraph backend [FastAPI backend]
        identity[identity<br/>who you are]
        documents[documents<br/>upload and store]
        billing[billing<br/>read any bill]
        analytics[analytics<br/>all money calculations]
        recommendations[recommendations<br/>rule-based findings]
        assistant[assistant<br/>AI agents and checks]
        knowledge[knowledge<br/>documentation search]
        audit[audit<br/>record of what happened]
    end
    documents --> billing --> analytics
    analytics --> recommendations
    assistant --> analytics
    assistant --> knowledge
    assistant --> audit
    recommendations --> knowledge
```

Each module follows clean architecture: `api → application → domain ← infrastructure`. Automatic checks fail the build if these rules are broken.

## How a bill is processed

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI
    participant S3 as Private storage
    participant DB as PostgreSQL
    participant Worker as Background worker

    User->>API: Upload bill
    API->>API: Check type, size and fingerprint
    API->>S3: Store original file
    API->>DB: Save document and job
    API-->>User: Status: processing
    Worker->>DB: Pick up job
    Worker->>S3: Read file
    Worker->>Worker: Detect format and convert to FOCUS
    Worker->>DB: Save records and update summaries
    Worker-->>User: Status: processed
```

## How a question is answered

```mermaid
sequenceDiagram
    actor User
    participant Agent as Supervisor agent
    participant Tools as Safe tools
    participant Docs as Qdrant
    participant AI as Gemini
    participant Check as Answer checker

    User->>Agent: Why did my EC2 cost go up?
    Agent->>Tools: Fetch real numbers for this workspace
    Tools-->>Agent: Facts with IDs: F1, F2, F3
    Agent->>Docs: Find relevant documentation
    Docs-->>Agent: Trusted passages
    Agent->>AI: Facts and passages
    AI-->>Agent: Answer with placeholders, such as {{F1}}
    Agent->>Check: Fill in real values and check
    Check-->>User: Answer, evidence and grade
```

The AI writes `{{F1}}` instead of a number, and our code fills in the real value. So it cannot make up a figure. See [how the AI is kept honest](docs/architecture/ai.md).

## Deployment

Everything runs on one small server, with free services around it.

```mermaid
flowchart TB
    internet([Internet]) -->|HTTPS| caddy
    subgraph ec2 [AWS EC2 t3.small, 2 GB memory]
        caddy[Caddy] --> web[Next.js]
        caddy --> api[FastAPI and worker]
        caddy --> keycloak[Keycloak]
        api --> postgres[(PostgreSQL)]
        keycloak --> postgres
    end
    api --> s3[(Amazon S3)]
    api --> qdrant[(Qdrant Cloud free plan)]
    api --> gemini[Gemini]
    postgres -->|nightly backup| s3
    github[GitHub Actions] -->|tested images| ec2
```

## Tech stack

| Part | Tools |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Recharts, TanStack Query |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Data | PostgreSQL, Pandas, NumPy, Amazon S3 |
| AI | Gemini, LangChain, LangGraph, Qdrant |
| Login | Keycloak |
| Testing | Pytest, Vitest, Playwright, DeepEval or Ragas |
| Security | Gitleaks, Bandit, Trivy, Checkov, Row-Level Security |
| Delivery | Docker, GitHub Actions, GHCR, Terraform, Caddy |
| Monitoring | OpenTelemetry, Prometheus, Grafana |

## Getting started

You need Docker (we use [Colima](https://github.com/abiosoft/colima)), [uv](https://docs.astral.sh/uv/), Node (version in `.nvmrc`), pnpm, Gitleaks and pre-commit. See the [getting started guide](docs/guides/getting-started.md) for how to install them.

```bash
make setup   # Install everything and create your .env
make up      # Start all services
make check   # Run all tests and checks
```

| Service | Address |
|---|---|
| Web app | http://localhost:3010 |
| API docs | http://localhost:8010/api/docs |
| Keycloak | http://localhost:8090 |
| Test email inbox | http://localhost:8025 |

## Project structure

```
apps/
  api/        FastAPI backend, split into modules
  web/        Next.js frontend, split into features
docs/         Plans, architecture, decisions, guides and build log
infra/        Server and database setup
samples/      Generator for made-up bills
scripts/      Project checks and setup
```

## Documentation

- [Documentation index](docs/README.md)
- [Roadmap and progress](docs/plan/ROADMAP.md)
- [Build log](docs/logs/BUILD-LOG.md)
- [Project rules](AGENTS.md)
