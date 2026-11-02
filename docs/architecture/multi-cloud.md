# Multi-cloud support

Every cloud has its own bill format. Instead of teaching the whole app about each one, we convert every bill into one standard: **FOCUS**, the FinOps Open Cost and Usage Specification.

```
 Any bill file ─► detect type ─► one small reader per format ─► FOCUS records ─► PostgreSQL
```

Everything after the reader never knows which cloud a bill came from. That covers analytics, the dashboard and the AI.

## Support plan

| Cloud | Files | Phase |
|---|---|---|
| AWS | Cost Explorer CSV, CUR old and new columns, FOCUS | 3 |
| Azure, Google Cloud, Oracle | FOCUS export, using the shared reader | 9 |
| Azure, Google Cloud, Oracle | Native report formats | 9 |
| DigitalOcean | Invoice CSV. It has no FOCUS export, so it needs its own reader | 9 |

## Adding a new format

1. Add a reader in `modules/billing/domain/readers/` and list it in `READERS`.
2. It must answer two questions: "Is this file mine?" and "What are its FOCUS records?"
3. Add a made-up sample file to `tests/fixtures/`, with hand-checked totals.

Nothing else should need to change. If it does, the design has a leak.

## Agents and clouds

From Phase 8, tools take a provider setting, and each cloud has a small profile with its documents and rules. A new cloud adds a profile, not new agents.

## File types compared

| File | Setup needed | Detail | What the AI can explain |
|---|---|---|---|
| Cost Explorer CSV | None, instant download | Service totals per month | Which service changed |
| CUR or FOCUS | Must be set up first; covers dates from then on | Every line item | Which resource and usage type changed |

## Things that differ between clouds

- **Names:** AWS `EC2` and Azure `Virtual Machines` both map to the FOCUS category `Compute`.
- **Versions:** providers may lag behind the newest FOCUS version, so the reader accepts the columns they really send.
- **Currency:** a user may have bills in different currencies. These are shown separately and never added.
- **Advice:** documentation in Qdrant is tagged by provider, so AWS advice is never given for an Azure cost.
- **Column details:** check each format against a real sample before finishing its reader.
