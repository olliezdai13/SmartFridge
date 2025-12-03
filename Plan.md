Implementation Plan of the Auth Feature:

- For each step, include steps for what needs to be done to make this work (env variables, migration runs, scripts to run, etc...)

* Expand user model and migration: add password_hash, optional last_login_at, and audit columns; enforce unique lowercased email; create a new Alembic revision to add the columns/indexes (and any table rename fixes from the step above). Keep the demo user row but migrate it to a hashed password.
* Choose auth format: short-lived access JWT + longer-lived refresh JWT, both signed with a new SMARTFRIDGE_AUTH_SECRET; store them as HttpOnly, Secure, SameSite=Lax cookies with clear names (e.g., sf_access, sf_refresh), predictable expirations, and path /.
* Middleware: replace the shared-secret guard with a request hook that (a) skips /healthz and /api/auth/*, (b) validates the access cookie JWT, loads the user, and attaches it to g, (c) returns 401 on missing/expired tokens. 
* Auth endpoints under /api/auth:
    * POST /signup — create user with hashed password; reject duplicates; issue fresh tokens in cookies.
    * POST /login — verify password and issue/rotate tokens; update last_login_at.
    * POST /refresh — validate refresh cookie, issue new access+refresh cookies (rotate refresh ID in the JWT payload).
    * POST /logout — clear both cookies.
    * GET /me — return current user profile; useful for frontend bootstrapping.
* Password handling: We should generate & check password hashes. Normalize emails to lowercase; add simple password policy checks server-side.
* Wire user context through existing endpoints:
    * Snapshot upload should use g.user instead of DEFAULT_USER_ID.
    * Inventory/recipes queries should use the authenticated user’s id.
    * Background worker should already persist user_id; confirm processing pipeline remains compatible.
* Frontend gating: add auth state bootstrap via /api/auth/me on app load; redirect to login screen when 401/403; block dashboard routes until authenticated; ensure ApiClient auth-error handler triggers the redirect and clears any stale UI state. Add basic login/signup forms and a logout button.
* Configuration/docs: document new env vars (SMARTFRIDGE_AUTH_SECRET, cookie settings, token lifetimes), update README.md. Adjust any setup scripts/docker env files to seed the secret with a placeholder like “FILL_ME_OUT”.
* Testing: …?