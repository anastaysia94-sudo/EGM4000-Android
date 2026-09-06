# EGM4000 — Render Public Deployment Runbook

The repository root now contains `render.yaml`, which defines the public EGM4000 Python web service plus its Postgres database.

## Current account-level blocker

Render currently returns HTTP 402 `Payment information is required` when attempting to create either the free Postgres instance or the free web service in the SmartPickShop workspace. This is an account/workspace billing gate, not an application code failure.

## Once Render permits resource creation

Use the repository Blueprint (`render.yaml`) or create the same resources from the SmartPickShop workspace. The Blueprint provisions:

- `egm4000` public Python web service
- `egm4000-postgres` PostgreSQL database
- internal `DATABASE_URL` wiring
- generated `EGM_VISITOR_SECRET`
- `EGM_SECURE_COOKIES=1`
- `EGM_HOST=0.0.0.0`
- `/api/health` health check

During first Blueprint creation, Render prompts for `EGM_OWNER_PASSWORD`. Use a new strong owner password that is not committed to GitHub.

## Build/start

Build command:

```bash
cd fullstack && pip install -r requirements.txt
```

Start command:

```bash
cd fullstack && python server.py
```

## Production verification checklist

After Render reports the deployment live:

1. `GET https://<host>/api/health` returns `ok: true` and `schema: egm.event.v1`.
2. Open the PWA root and verify HTTPS loads without mixed content.
3. Register a normal user and log in.
4. Verify Tips Center, forum, blog, survey targeting, and Live Lab.
5. Verify the owner account can reach Admin routes.
6. Verify a normal user receives `403 owner_only` on owner APIs.
7. Verify Android `/api/mobile/login`, `/api/mobile/sync`, and `/api/mobile/tips` against the public hostname.
8. Set the verified public HTTPS hostname as the Android default for the next release.
9. Keep the manual server override in Android Settings for staging/recovery.
10. Add monitoring/backups and then perform physical-device QA.

## Important data rule

Do not deploy the public service with SQLite as the canonical production database. Render web-service filesystems are not the intended durable database layer. Production should use the Postgres instance wired through `DATABASE_URL`.

## Security rule

Never commit `EGM_OWNER_PASSWORD`, database credentials, mobile bearer tokens, or visitor secrets. The Blueprint references or generates secrets rather than embedding values.
