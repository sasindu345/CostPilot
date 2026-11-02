# Phase 10: Live deployment

**You will see:** CostPilot running on the internet with HTTPS.
- [ ] Confirm `t3.small` is free for your account
- [ ] Set up AWS budget alerts first, so there are no surprise bills
- [ ] Terraform: EC2, network rules, private S3 bucket, narrow permissions
- [ ] Checkov and Trivy scans in the pipeline
- [ ] Production Compose with memory limits and swap
- [ ] Caddy HTTPS, Keycloak in production mode, Parameter Store secrets
- [ ] Images pushed to GHCR, with automatic deployment from GitHub Actions
- [ ] Nightly encrypted backups to S3, and a tested restore
- [ ] Measure the real memory use

## Finish this phase

- [ ] All items above are ticked, or the change is explained
- [ ] `docs/plan/ROADMAP.md` is updated
- [ ] `docs/logs/BUILD-LOG.md` has a dated entry
- [ ] `make check` passes
