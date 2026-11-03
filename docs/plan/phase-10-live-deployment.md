# Phase 10: Live deployment

**You will see:** CostPilot running on the internet with HTTPS.
- [ ] Confirm `t3.small` is free for your account. **Waiting on you:** one command in `docs/guides/deployment.md`, step 1
- [ ] Set up AWS budget alerts first, so there are no surprise bills. **Written** in `infra/terraform/budget.tf`. **Waiting on you** to apply it, step 2
- [x] Terraform: EC2, network rules, private S3 bucket, narrow permissions. No SSH port: Systems Manager instead
- [x] Checkov and Trivy scans in the pipeline. Checkov also scans Dockerfiles and workflows. Shellcheck checks the server scripts
- [x] Production Compose with memory limits and swap
- [x] Caddy HTTPS, Keycloak in production mode, Parameter Store secrets. Rehearsed on the laptop with HTTPS and a real sign-in
- [x] Images pushed to GHCR, with automatic deployment from GitHub Actions. Runs for the first time after the merge to `main` and the GitHub setup in step 7
- [x] Nightly encrypted backups to S3, and a tested restore. `make backup-check` restores every table and compares row counts
- [ ] Measure the real memory use. **Rehearsal on the laptop:** about 1.07 GB at rest. **Waiting on** the real server: each deploy prints it

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
