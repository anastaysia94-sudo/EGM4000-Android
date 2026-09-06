# EGM4000 Cross-Chat Consolidation — 2026-09-05

This release consolidates later EGM4000 work that had diverged across chat sessions and artifacts into the database-backed/full-stack live-intelligence track while preserving the verified Web/PWA v5 and Android work already on `main`.

## Canonical product boundary

- **EGM4000:** authorized gameplay evidence, normalized events, metrics, pattern analysis, coaching, tips, replay, community, surveys, research, and owner administration.
- **F.S.A. / Fish Shooter Arcade:** separate owned virtual/non-cash fish-shooter product. It can provide exact telemetry to EGM4000 through an explicit bridge, but it remains a separate codebase/product.
- **Founder Console:** separate owner/control-plane product. Shared contracts may exist, but its distributor/agent/ledger product logic is not merged into EGM4000.

## Locked live-analysis pipeline

`Game Session → Capture Adapter → Vision/Event Engine → Normalized Gameplay Events → Live Metrics → Pattern Detection → Coaching → Session Store → Replay Lab → Experiment Engine`

## Added/preserved by this consolidation

- Verified C002 first-run tutorial, C004 community, and C005 privacy-safe surveys from current Web/PWA v5 remain authoritative.
- Framework-neutral SQLite live-intelligence core for persistent live sessions, normalized events, live metrics, rolling baselines, and evidence-grounded context packs.
- `egm.event.v1` normalized event schema with evidence/source/confidence/provenance.
- Read-only adapter registry for Fire Kirin, Panda Master, Orion Stars, Juwa, Game Master/GameVault, and Generic Fish Shooter.
- Protected F.S.A. exact-telemetry boundary while keeping F.S.A. separate.
- Full-stack continuity for the 237-user fictional seed, 100-feature owner Admin registry, exactly 25 monetization channels, 49 return-user loops, Tips Center, community, surveys, and safe Research Lab.
- Cyber-aquatic EGM4000 SVG visual mark.

## Evidence rules

EGM4000 distinguishes `exact_telemetry`, `observed_evidence`, `estimate`, `correlation`, `hypothesis`, and `unknown`.

Generic screen motion is an **estimate**, not a fish/target detector and never hidden-server-state evidence. Manual event buttons are user-verified visible evidence. Exact telemetry is reserved for authorized exact data such as the separate owned F.S.A. bridge.

## External gates still external

Public DNS/TLS, physical-device QA, signed Android release/AAB, Play Console publishing, provider credentials for monetization/email/ads, off-host backups/monitoring, legal review, and independent penetration testing remain deployment/operator tasks and are not fabricated as complete.
