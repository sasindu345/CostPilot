# CostPilot documentation

Start with the roadmap to see where the project is today.

## Plan and progress

- [Roadmap](plan/ROADMAP.md): status of every phase
- [Full development plan](plan/DEVELOPMENT-PLAN.md): the approved plan and the reasons behind it
- [Edge cases](plan/EDGE-CASES.md): unusual situations and how we handle them
- [Build log](logs/BUILD-LOG.md): dated record of what was built

## How it works

- [Overview](architecture/overview.md)
- [Backend](architecture/backend.md)
- [Frontend](architecture/frontend.md)
- [Data model](architecture/data-model.md)
- [AI system](architecture/ai.md)
- [Security](architecture/security.md)
- [Multi-cloud](architecture/multi-cloud.md)
- [Technical verification](architecture/technical-verification.md)
- [Security review and load test](architecture/security-review.md)

## Decisions

Each note explains one big decision and why we made it.

- [0001: Use FOCUS as the common bill format](decisions/0001-focus-common-format.md)
- [0002: Use Qdrant for documentation search](decisions/0002-qdrant-vector-database.md)
- [0003: Use Keycloak, with sessions in the backend](decisions/0003-keycloak-with-backend-sessions.md)
- [0004: Use S3's built-in encryption](decisions/0004-s3-built-in-encryption.md)
- [0005: The AI writes placeholders, not numbers](decisions/0005-ai-writes-placeholders.md)
- [0006: Use PostgreSQL for background jobs](decisions/0006-postgres-job-queue.md)
- [0007: Keep everything on EC2 for now, and review Lambda later](decisions/0007-lambda-is-a-later-option.md)
- [0008: Read bills with Python's csv module and Decimal](decisions/0008-read-bills-without-pandas.md)
- [0009: Use gemini-3.5-flash-lite for answers](decisions/0009-faster-gemini-model.md)
- [0010: Build hybrid agents after the trust layer](decisions/0010-hybrid-agents-after-trust-layer.md)
- [0011: How CostPilot is deployed](decisions/0011-deployment-design.md)
- [0012: Grade answers with our own small grader](decisions/0012-own-answer-grader.md)

## Design

- [UI specification](design/ui-spec.md)
- [Overview design image](design/overview-mockup.png)

## Guides

- [Getting started](guides/getting-started.md)
- [Keycloak beginner's guide](guides/keycloak-beginners-guide.md)
- [Getting a bill from each cloud](guides/cloud-bills.md)
- [Putting CostPilot online](guides/deployment.md)
- [Monitoring](guides/monitoring.md)
- [Demo walkthrough](guides/demo.md)

## Background

- [Original project brief](PROJECT-BRIEF.md)
