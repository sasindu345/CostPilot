# Roadmap

This is the one place to see what is done and what remains. Update it at the end of every phase.

**Status key:** ✅ Done · 🔄 In progress · ⬜ Not started

| Phase | Name | What you get | Status |
|---|---|---|---|
| 0 | [Project baseline](phase-00-project-baseline.md) | Running empty app, docs and automatic checks | ✅ |
| 1 | [Login and app shell](phase-01-login-and-app-shell.md) | Sign up, sign in, real layout | ✅ |
| 2 | [Document upload](phase-02-document-upload.md) | Upload a file and watch its status | ✅ |
| 3 | [Reading bills (AWS first)](phase-03-reading-bills-aws-first.md) | Bills turned into clean records | ⬜ |
| 4 | [Dashboard and analytics](phase-04-dashboard-and-analytics.md) | The design working with real data | ⬜ |
| 5 | [Documentation search](phase-05-documentation-search-rag.md) | Search finds the right cloud advice | ⬜ |
| 6 | [AI assistant](phase-06-ai-assistant.md) | Live answers about your bill | ⬜ |
| 7 | [Trust layer and recommendations](phase-07-trust-layer-and-recommendations.md) | Every answer shows its evidence | ⬜ |
| 8 | [Other clouds](phase-08-other-clouds.md) | Azure, Google Cloud, Oracle, DigitalOcean | ⬜ |
| 9 | [Live deployment](phase-09-live-deployment.md) | Running on the internet with HTTPS | ⬜ |
| 10 | [Monitoring, quality and finish](phase-10-monitoring-quality-and-finish.md) | Dashboards, measured AI quality, final docs | ⬜ |

## Limits to keep in mind

| Limit | Value | Why it matters |
|---|---|---|
| Server memory | 2 GB plus 2 GB swap (`t3.small`) | Keycloak alone needs about 1 GB. Check before adding any service |
| AWS free plan | 6 months or until credits run out | Keep backups and stay portable |
| Gemini free key | Few requests per minute; do not send sensitive data | Use made-up bills. Aim for at most 3 AI calls per question |
| Qdrant Cloud free | Paused after 1 week idle, deleted after 4 | Weekly job keeps it awake; `make reindex` rebuilds it |
| GitHub, private repo | 2,000 Actions minutes, 500 MB image storage | Keep only the latest two images |

## Open items

- After Phase 7, review the Lambda options in [decision 0007](../decisions/0007-lambda-is-a-later-option.md).
- The `phase-0-baseline` branch shows a red pipeline run, because the `npm` security fix is on `phase-1-login`. Merging `phase-1-login` into `main` carries everything.
- Phase 9 starts by confirming `t3.small` is free on your AWS account. A micro-only account cannot run Keycloak.
- Add `wijewardanasj.23@uom.lk` to your GitHub account so commits count on your profile.
