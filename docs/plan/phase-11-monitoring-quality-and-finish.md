# Phase 11: Monitoring, quality and finish

**You will see:** live dashboards, measured AI quality and portfolio-ready docs.
- [x] OpenTelemetry tracing through the web app, API and agents. Each agent and each Gemini call is its own span
- [x] Prometheus and Grafana locally, Grafana Cloud in production. Local runs with `make monitoring`. Production needs your free Grafana Cloud account, see `docs/guides/monitoring.md`
- [x] AI quality tests. **Changed:** our own grader instead of DeepEval or Ragas, see decision 0012. It found and helped fix a real bug
- [ ] Human-checked test cases. **Waiting on you:** 12 reference answers are written in `knowledge/quality-cases.yaml`. Check each and fill in `checked_by`
- [x] Data retention, account deletion and data export
- [x] Final security review and load test. See `docs/architecture/security-review.md`
- [x] Final README with screenshots and a demo walkthrough

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
