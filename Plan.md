1. Scaffold `smartfridge_frontend/` with Vite + React: initialize project with TypeScript.
2. Set up routing for dashboard page. 
3. add a shared layout/shell.
4. Stub an API client that targets `/api/*` with base URL + interceptors for auth errors. 
5. Establish dev flow: run backend, and in another shell run `npm install` then `npm run dev` inside `smartfridge_frontend/` for hot reload; verify proxy/devserver wiring to reach `/api/*`. 
6. Wire backend to serve the built frontend from `smartfridge_frontend/dist` at `/`, keeping API routes under `/api/*` so a single backend process handles both dev/prod static hosting. Ensure `npm run build` outputs to `smartfridge_frontend/dist`.
7. Implement full auth in backend: user model + password hashing, signup/login endpoints, session/JWT middleware guarding `/api/*`; issue HTTP-only secure cookies, support logout/refresh, and gate app load to authenticated users or redirect to login.
8. Add security hardening: restrict CORS to allowed origin(s), rate limiting, HTTPS/secure headers, input validation, and audit/metrics logging.
