1. Scaffold `smartfridge_frontend/` with Vite + React: initialize project with TypeScript.
2. Set up routing for dashboard page.
4. Stub an API client that targets `/api/*` with base URL + interceptors for auth errors. 
5. Set up a simple workflow to build and run the frontend + backend together via Dockerfile. We should be able to `docker compose --build up` and easily have the fresh frontend and backend deployed.
6. Implement full auth in backend: user model + password hashing, signup/login endpoints, session/JWT middleware guarding `/api/*`; issue HTTP-only secure cookies, support logout/refresh, and gate app load to authenticated users or redirect to login.
7. Add security hardening: restrict CORS to allowed origin(s), rate limiting, HTTPS/secure headers, input validation, and audit/metrics logging.