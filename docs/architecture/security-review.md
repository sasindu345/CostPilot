# Security review

Done on 3 Nov 2026, at the end of Phase 11. It checks each area against how an attacker would try to break in, and records what was found and what still needs work.

## Automatic checks that ran

| Check | Result |
|---|---|
| Gitleaks, the whole Git history | No secrets |
| Bandit, Python code | No problems |
| `pip-audit`, every API package | No known vulnerabilities |
| `pnpm audit --prod`, every web package | No known vulnerabilities |
| Checkov, Terraform, Dockerfiles and workflows | 0 failed. 9 skips across 6 checks, each with its reason in the code |
| Trivy, the API, web and Keycloak images | Runs in the pipeline on every push |
| Browser tests | 13 of 13, including other users' data being refused |

## Area by area

| Area | How someone might attack it | What stops them | Proven by |
|---|---|---|---|
| Sign-in | Guess passwords | Keycloak locks accounts after repeated failures, and passwords need 12 characters | Realm settings |
| Sessions | Steal the cookie with a script | `HttpOnly`, `Secure` in production, `SameSite=Lax`. Only a hash is stored | `login.spec.ts` |
| Forged requests from another site | Make the browser send a request | `SameSite=Lax` keeps the cookie off cross-site posts. Deletes need a JSON body | Browser rules |
| Other users' data | Change an ID in the address | Workspace checks in code, then Row-Level Security in PostgreSQL | `test_row_level_security.py`, `api.spec.ts` |
| Uploads | Huge files, zip bombs, fake types, spreadsheet formulas | Size limits, unpacked-size limits, content checks, formula cleaning | `test_upload_limit.py`, `test_files.py` |
| AI | Instructions hidden in a bill or question | Coded injection check, untrusted data kept apart, only approved fields sent | `test_trust_layer.py` |
| Made-up numbers | The AI invents a figure | Placeholders, the Answer Checker and a template fallback | `test_trust_layer.py` |
| Injected scripts in pages | Run code in the app | Content Security Policy: only our own site may run scripts or load data | Response headers, `make e2e` |
| Admin console | Reach Keycloak admin from the internet | Caddy returns 404 for `/auth/admin` and the master realm | Production rehearsal |
| Account deletion | Delete someone else's workspace | Deletion runs inside the user's own workspace, and only for its only member | `test_account.py` |
| Server | Log in from the internet | No SSH port. Only 80 and 443 are open | Terraform |
| Secrets | Read them from Git or images | `.env` and settings files are ignored, and Gitleaks blocks commits | Pre-commit hook, pipeline |
| Supply chain | A changed GitHub Action or package | Actions pinned to commits, lock files for every package | `ci.yml` |

## Fixed during this review

- **Content Security Policy added** to the web app, with `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`. All browser tests still pass.
- **A false answer the number checks could not catch.** The AI said October cost the most, but it was September. Code now names the highest and lowest months. See decision 0012.

## Still open

| Risk | Why it matters | Suggested fix |
|---|---|---|
| **An AWS access key was pasted into a chat** | Anyone with the text could use it | Deactivate it in IAM, then create a new one. See the deployment guide |
| No request rate limit on the API | One user could send many requests. AI questions already have a daily limit | Add a rate limit in Caddy or FastAPI |
| `unsafe-inline` scripts allowed | Next.js needs it without per-request nonces | Move to nonces when the app needs a stricter policy |
| Backups use S3's encryption only | Anyone with read access to the bucket could read them | Keep bucket access narrow, or add a KMS key ($1 a month) |
| Injection checks are English patterns | Other languages or new wording can get past them | Combine with a classifier model |
| One server | A crash means a short outage | Fine for now. See decision 0011 |

## Load test

`make load-test` uses k6, a free load-testing tool. 25 signed-in users opened the Overview and Analytics pages over and over for 1 minute 45 seconds. AI questions were left out, so no Gemini quota was used.

| Setup (laptop, 2 CPUs shared with every service) | Requests per second | Errors | Slowest 5% took |
|---|---|---|---|
| Monitoring off | 57.7 | 0% | 360 ms |
| Every request traced | 54.2 | 0% | 514 ms |
| 1 in 5 traced, as in production | 56.6 | 0% | 412 ms |
| Two API processes, monitoring off | 56.6 | 0% | 569 ms |

**What this means.** One API process served about 57 requests a second with no errors. Waiting time rose because requests queued for one process. A second process did not help here, because the laptop's two CPUs were shared with the database, Keycloak and the load tool itself. The real server needs measuring again once it is running.
