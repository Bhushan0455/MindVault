# Integrated backend

The tested Role A + Role B backend is in [backend/](backend/).

Start with [backend/README.md](backend/README.md) for local setup and PostgreSQL migration instructions.
Frontend developers should use [the API integration guide](backend/FRONTEND_INTEGRATION.md).
Current verification and limitations are recorded in [the integration report](backend/INTEGRATION_REPORT.md).

Verified: 370 PostgreSQL tests; 367 SQLite tests with three PostgreSQL-only checks skipped; actual HTTP approval workflow; all three live Gemini services through fictional local API fixtures.

The backend/frontend directory contains a tested TypeScript API helper, not the website. Actual frontend and hosted deployment acceptance remain outstanding.

Credentials, local databases, virtual environments and downloaded runtimes are excluded. Create your private .env locally using the setup instructions.
