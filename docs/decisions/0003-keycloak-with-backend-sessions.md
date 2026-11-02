# 0003: Use Keycloak, with sessions in the backend

**Status:** Accepted, 2 Nov 2026

**Situation.** We need secure sign-up, login and password reset, at no cost, using a tool that is standard in industry.

**Decision.** Keycloak handles login. FastAPI talks to Keycloak, keeps the session in PostgreSQL, and gives the browser a random ticket in an `HttpOnly` cookie. Tokens never reach the browser.

**Why.**
- Scripts in the browser cannot steal a token they never had.
- Logging out takes effect at once, because we delete the session.
- All login logic is in one place and can be tested with Pytest.
- We avoided Auth.js because it now only receives security fixes and v5 is still in beta.

**Trade-offs.** Keycloak needs about 1 GB of memory, so the server must be at least a 2 GB `t3.small`. We store tokens, so they must be encrypted in the database.
