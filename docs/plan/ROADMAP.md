# Roadmap

This is the one place to see what is done and what remains. Update it at the end of every phase.

**Status key:** ✅ Done · 🔄 In progress · ⬜ Not started

| Phase | Name | What you get | Status |
|---|---|---|---|
| 0 | [Project baseline](phase-00-project-baseline.md) | Running empty app, docs and automatic checks | ✅ |
| 1 | [Login and app shell](phase-01-login-and-app-shell.md) | Sign up, sign in, real layout | ✅ |
| 2 | [Document upload](phase-02-document-upload.md) | Upload a file and watch its status | ✅ |
| 3 | [Reading bills (AWS first)](phase-03-reading-bills-aws-first.md) | Bills turned into clean records | ✅ |
| 4 | [Dashboard and analytics](phase-04-dashboard-and-analytics.md) | The design working with real data | ✅ |
| 5 | [Documentation search](phase-05-documentation-search-rag.md) | Search finds the right cloud advice | ✅ |
| 6 | [AI assistant](phase-06-ai-assistant.md) | Live answers about your bill | ✅ |
| 7 | [Trust and measurement](phase-07-trust-and-measurement.md) | Every answer shows its evidence, and quality can be measured | ✅ |
| 8 | [Hybrid agents](phase-08-hybrid-agents.md) | Deeper answers from specialist agents, proven against a baseline | ✅ |
| 9 | [Other clouds](phase-09-other-clouds.md) | Azure, Google Cloud, Oracle, DigitalOcean | ✅ |
| 10 | [Live deployment](phase-10-live-deployment.md) | Running on the internet with HTTPS | 🔄 Code done and rehearsed. Waiting on AWS permissions, see the deployment guide step 2 |
| 11 | [Monitoring, quality and finish](phase-11-monitoring-quality-and-finish.md) | Dashboards, measured AI quality, final docs | ✅ Human check of reference answers still to do |

## Limits to keep in mind

| Limit | Value | Why it matters |
|---|---|---|
| Server memory | 2 GB plus 2 GB swap (`t3.small`) | Keycloak alone needs about 1 GB. Check before adding any service |
| AWS free plan | 6 months or until credits run out | Keep backups and stay portable |
| Gemini free key | Few requests per minute; do not send sensitive data | Use made-up bills. At most 4 AI calls per question from Phase 8 |
| Qdrant Cloud free | Paused after 1 week idle, deleted after 4 | Weekly job keeps it awake; `make reindex` rebuilds it |
| Your Mac's disk | About 2 GB free of 228 GB | Docker builds and browser tests can fail. Free up space before Phase 5 |
| GitHub, private repo | 2,000 Actions minutes, 500 MB image storage | Keep only the latest two images |

## How to check everything

| Command | What it proves |
|---|---|
| `make check` | 380 backend tests, 36 frontend tests, style, architecture and security rules. Needs `make up` |
| `make e2e` | 13 browser and API tests, including data export and account deletion, including every API endpoint, a real Gemini answer, accessibility and phone size |
| `make eval-search` | Search quality across five clouds. It was 18 of 18 |
| `make eval-assistant` | Whole assistant, with real Gemini. It was 15 of 15, and uses about 30 AI calls |
| `make eval-knowledge` | Documentation questions with and without the Knowledge Agent. It was 6 of 6 both ways |
| `make backup-check` | Backs up the local databases, restores them into copies and compares every table |
| `make infra-check` | Terraform files and server scripts are valid |
| `make eval-quality` | Answers graded against reference answers by a second model. It was 9 of 12 |
| `make load-test` | 25 users at once on the dashboards. It was 57 requests a second with 0 errors |
| `make monitoring` | Starts everything with Grafana at http://localhost:3011 |
| `make eval-agents` | Hard questions with and without AI specialists. It was 10 of 10 against 6 of 10, and uses about 50 AI calls |

## Manual setup you will need

Code cannot do these for you.

| When | What to do |
|---|---|
| Before real bills | Turn on billing for your Gemini key and set `GEMINI_TIER=paid`. See `docs/guides/getting-started.md` |
| To check the bill readers | Upload a real bill from any cloud you use. See `docs/guides/cloud-bills.md`. Remove account IDs if you share them |
| Now | **Replace the AWS access key that was pasted into a chat.** See the deployment guide, "If an access key is ever exposed" |
| Phase 10 | Add the `CostPilotDeployer` permissions to your AWS user (deployment guide step 2). `t3.small` is confirmed free on your account |
| Phase 10 | Create a free Qdrant Cloud cluster and run `make reindex` against it. Add `QDRANT_URL` and `QDRANT_API_KEY` to GitHub secrets |
| Phase 10 | Choose a free DuckDNS name and point it at the server |
| Phase 10 | Choose a real email service for Keycloak, as Mailpit is only for testing |
| Phase 10 | Fill in production settings and copy them to Parameter Store. `AWS_REGION`, `S3_BUCKET` and `PARAMETER_PATH` are already set in GitHub |
| Phase 11 | Check the 12 reference answers in `knowledge/quality-cases.yaml` and fill in `checked_by` |
| Phase 11 | Optional: a free Grafana Cloud account for production monitoring |
| Phase 8 | Check your free limits at https://aistudio.google.com/rate-limit. One 429 rate-limit error was seen in testing |
| Any time | Add `wijewardanasj.23@uom.lk` to your GitHub account |

## Open items

- Review the Lambda options again in Phase 10, with real server numbers. See [decision 0007](../decisions/0007-lambda-is-a-later-option.md).
- The `phase-0-baseline` branch shows a red pipeline run, because the `npm` security fix is on `phase-1-login`. Merging `phase-1-login` into `main` carries everything.
- Phase 10 is finished once the server is live and its real memory use is measured.
- Add `wijewardanasj.23@uom.lk` to your GitHub account so commits count on your profile.
