# C004 — Community forum + blog

Status: **IMPLEMENTED in Web/PWA prototype**

Completed: 2026-09-05 19:18 America/Los_Angeles

## What changed

The EGM4000 Web/PWA now includes a responsive local-first community module with:

- Forum topics
- Blog posts
- Registered prototype member identities
- Comments
- Useful and Insightful reactions
- Reports
- Duplicate-report protection
- Search and content filtering
- Owner moderation queue
- Owner-only hide, restore, and report-dismiss actions
- Moderation audit records in local state
- Community data included in JSON export/import
- A visible C004 checklist/ledger completion entry

Community statements are explicitly user-generated content. They are not promoted into EGM4000 gameplay evidence automatically and must not be represented as verified game mechanics.

## Prototype security boundary

This repository's browser build is a local/mock prototype. `localStorage` is persistence, not a production database or authentication system.

Production implementation must provide server-side authentication and authorization, password hashing, secure sessions/cookies, CSRF defenses, input validation and sanitization, rate limiting, abuse controls, audit logs, account recovery, moderation permissions, and database-backed ownership checks. The production API must never trust a client-supplied role value.

## Production API/data contract

Suggested endpoints:

- `GET /api/community/posts`
- `POST /api/community/posts`
- `GET /api/community/posts/:id`
- `POST /api/community/posts/:id/comments`
- `POST /api/community/posts/:id/reactions`
- `POST /api/community/posts/:id/reports`
- `GET /api/admin/community/reports`
- `POST /api/admin/community/posts/:id/moderate`

Core records should include `User`, `CommunityPost`, `CommunityComment`, `Reaction`, `Report`, and `ModerationAudit` entities with server-generated IDs and timestamps.

## Safety

The community must not be used to facilitate live-service cheating, credential theft, protection bypasses, balance manipulation, or guaranteed-profit claims. Research/modding discussion remains limited to local/original sandbox software, owned/test environments, and defensive education.

## Next checklist item

C005 — Visitor and returning-user surveys.
