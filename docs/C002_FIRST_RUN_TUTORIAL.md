# C002 — First-time operation tutorial

Status: **IMPLEMENTED in Web/PWA build**

Completed: 2026-09-05 America/Los_Angeles

## What changed

The EGM4000 repository now contains a responsive guided first-run tutorial at `web/c002-tutorial.html` and the PWA manifest starts new installed PWA launches through that tutorial surface.

The tutorial covers all required C002 topics:

1. EGM4000 setup and safe third-party sign-in boundaries.
2. Logging session events.
3. Monitoring user-authorized events and evidence confidence.
4. Reading descriptive analytics without treating them as prediction.
5. Using AI/evidence-labeled tips and the future dedicated Tips Center.
6. Bankroll Guard limits, breaks, and anti-chasing guidance.
7. Community use plus privacy and local-prototype storage boundaries.
8. Safe Research Lab scope: local/original sandbox modding, reverse-engineering education, AI experiments, and defensive anti-cheat study only.

The tutorial has Back/Next/Skip controls, keyboard left/right navigation, responsive mobile layout, visible progress, local completion persistence through `localStorage`, and a direct transition into the EGM4000 app.

## Persistence

Prototype key:

`egm4000.web.c002.tutorial.v1`

Prototype state:

```json
{
  "seen": true,
  "completed": false,
  "step": 0
}
```

This is local prototype persistence only. It is not a production user-profile database.

## PWA integration

`web/manifest.webmanifest` now uses `./c002-tutorial.html` as its start URL, and `web/sw.js` includes the tutorial in the offline asset cache. This keeps C002 inside the installable Web/PWA build instead of treating it as external documentation.

## Security / production contract

No production credentials are stored by C002. Production account/tutorial state should be associated with an authenticated server-side user record, with secure sessions/cookies, authorization, CSRF defenses, rate limiting, audit logs, and account recovery. Third-party game credentials must remain with their providers.

Suggested production state contract:

- `GET /api/me/onboarding`
- `PATCH /api/me/onboarding`
- fields: `tutorialVersion`, `startedAt`, `completedAt`, `lastStep`, `skippedAt`

The server must derive user identity from the authenticated session rather than accepting an arbitrary user ID from the client.

## Safety

The tutorial explicitly states that EGM4000 does not guarantee profit, predict random outcomes, expose hidden server state, manipulate balances, steal/store third-party credentials, bypass protections, or provide unauthorized live-service cheating.

## Project ledger

- C001 — Major visual redesign: completed in prior build work.
- C002 — First-time operation tutorial: **implemented**.
- C004 — Community forum + blog: preserved and already implemented in the current Web/PWA build.
- Next planned checklist milestone: C005 — Visitor and returning-user surveys.
