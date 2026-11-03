# 0011: How CostPilot is deployed

**Status:** Accepted, 3 Nov 2026

**Situation.** CostPilot must run on one `t3.small` server at about $0, with production habits: no stored cloud keys, no open admin ports, tested backups.

**Decisions.**

| Choice | Instead of | Why |
|---|---|---|
| One address, split by path: `/api`, `/auth`, the rest | A second domain for Keycloak | One HTTPS certificate, and the session cookie stays on one site |
| Systems Manager runs the deploy and opens terminals | SSH | No port 22 open to the internet, and no SSH key to lose |
| GitHub OIDC role, limited to the `production` environment | AWS keys in GitHub secrets | Nothing long-lived to leak |
| Parameter Store, encrypted with the AWS-managed key | Secrets Manager | Free. Secrets Manager charges per secret |
| A Keycloak image built in CI, with the theme inside | Mounting the theme on the server | Starts faster, uses less memory, and the server needs no source code |
| `pg_dump` every night to S3, with row counts saved beside it | Disk snapshots | Restores into any Postgres, and the counts prove a restore is complete |
| S3's own AES-256 encryption for backups | Encrypting backups ourselves | Free and simple. Same reasoning as decision 0004 |
| Terraform state on your laptop | State in S3 | One person, one machine. Moving it to S3 is a small change later |

**Trade-offs.**

- One server is a single point of failure. A crash means a short outage until it restarts, and a lost disk means restoring last night's backup.
- Backups are encrypted by S3. Anyone with read access to the bucket could read them, so bucket permissions matter.
- Local Terraform state can be lost. Keep a copy.
