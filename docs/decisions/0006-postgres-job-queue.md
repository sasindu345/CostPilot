# 0006: Use PostgreSQL for background jobs

**Status:** Accepted, 2 Nov 2026

**Situation.** Reading a large bill is too slow to do during a web request. The usual answer is Celery with Redis, but that adds another service to a server with little memory.

**Decision.** Keep a `jobs` table in PostgreSQL, and run a small worker that takes jobs using `FOR UPDATE SKIP LOCKED`.

**Why.** It uses no extra memory or services, and jobs survive restarts. A job and its data can be saved together in one transaction.

**Trade-offs.** It does not suit very high job volumes. If that ever happens, the job code sits behind an interface and can move to a real queue.
