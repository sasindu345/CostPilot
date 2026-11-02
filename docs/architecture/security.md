# Security

## Protection at each layer

| Area | Protection | Phase |
|---|---|---|
| Traffic | HTTPS everywhere, through Caddy and Let's Encrypt | 10 |
| Login | Keycloak handles passwords. The browser only holds a random ticket in a secure cookie | 1 |
| Data separation | Backend checks, plus PostgreSQL Row-Level Security as a second lock | 1 |
| Stored files | Private S3 bucket with AES-256 encryption | 2, 10 |
| Uploads | Type, size and content checks. Protection against compressed bombs and formula tricks | 2 |
| Secrets | `.env` locally, AWS Parameter Store in production, never in Git | 0, 10 |
| AI | Safe tools only, privacy filter, input and output checks | 6, 7 |
| Code | Gitleaks, Bandit, Trivy and Checkov in the pipeline | 0, 10 |
| Supply chain | GitHub Actions are pinned to exact commits. Dependencies use lock files | 0 |
| Containers | Run as a non-root user, on pinned image versions | 0 |
| Network | Local ports only listen on your own computer | 0 |
| Backups | Nightly encrypted database backup to S3, with a tested restore | 10 |
| Audit | Important actions and AI tool use are recorded | 1, 7 |

## Row-Level Security in simple words

Each database request first tells PostgreSQL which workspace it is for. PostgreSQL then hides all rows from other workspaces, even if our code has a bug. The app's database user has no power to turn this off, and tests in `tests/integration/test_row_level_security.py` prove it works.

The app runs as `costpilot_app`, a low-power user. Only migrations use the admin user.

## Sessions

- The browser only holds a random ticket, in an `HttpOnly` cookie that page scripts cannot read.
- The database stores a hash of the ticket, so a stolen backup cannot be used to log in.
- A session ends after `SESSION_LIFETIME_HOURS`, or at once on sign-out.
- **Known limit:** turning off a user in Keycloak does not end their current session. It ends when the session expires.

## This is not end-to-end encryption

The backend must read bills to analyse them, so CostPilot cannot claim end-to-end encryption. We use strong encryption in transit and at rest, with tight control over backend access.

## If a secret leaks

1. Replace the secret first. It is unsafe from the moment it reaches GitHub.
2. Then clean up the Git history if needed.
3. Record what happened in the build log.
