# AI Handoff — EGM4000 / EduGameMaster4000

Updated: 2026-09-26 America/Los_Angeles

## Identity

- Canonical repository: `anastaysia94-sudo/EGM4000-Android`
- Master project IDs: P045, P048
- Portfolio index: `anastaysia94-sudo/anastaysia94-sudo` → `CROSS_LLM_BOOTSTRAP.md`
- Machine-readable register: `portfolio/PROJECTS.json`

## Purpose

Fish-shooter gameplay intelligence, analysis, coaching, simulation, research, Web/PWA, and Android work.

## Continuity rules

- Separate measured facts, calculations, inferences, hypotheses, and unknowns.
- Do not claim hidden third-party mechanics or predictive certainty without evidence.
- Acceptance is limited to software, accounts, telemetry, and environments SmartPickShop owns, controls, or is explicitly authorized to test.
- A live third-party gambling-style service, real-money account, or bypass of age/identity/platform controls is not required for acceptance.
- Historical chat summaries are context, not proof of the current build.
- Record exact workflow/test evidence before declaring the integration complete.

## Current source checkpoint

Current observed main head: `2af2022b53c92e0711ac8067a5489f47d9581952`.

Changes since the prior continuity snapshot:
- `c637d85b4d2e2080faa3a384c137e9c93318dd6a` adds `tests/fsa-runtime-bridge.test.js`.
- `2af2022b53c92e0711ac8067a5489f47d9581952` adds the `F.S.A. runtime bridge` GitHub Actions workflow.

The bridge checks out the separate F.S.A. repository, runs its telemetry-v1 contract, loads the F.S.A. runtime telemetry code in an isolated test harness, records synthetic shot/hit/destroy events, converts them to exact-telemetry evidence, and feeds them into EGM skill analysis. The test explicitly preserves the limitation that the analysis does not predict hidden outcomes.

## Verification boundary

The bridge implementation is present in source. Its current GitHub Actions result was not verified in this continuity refresh.

## Smallest next execution block

1. Inspect/run the `F.S.A. runtime bridge` workflow on current main.
2. If green, record the exact run/commit evidence.
3. Then complete Web/PWA + Android acceptance in an owned/authorized non-cash environment using synthetic replay or explicitly authorized telemetry.
4. Prove session → telemetry → EGM import/analysis → replay/catch-up → isolation.
5. Do not introduce real-money or third-party account requirements.
