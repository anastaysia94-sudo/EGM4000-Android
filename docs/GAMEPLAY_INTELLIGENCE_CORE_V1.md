# EGM4000 Gameplay Intelligence Core v1

Status: reconciled implementation contract for EGM4000's primary gameplay-intelligence experience.

## Product priority
Gameplay intelligence is the primary EGM4000 function. Community, surveys, Tips, research, first-run tutorial, Android/PWA support, and Admin100 remain supporting modules rather than being discarded.

## Core modes
- LIVE: user-authorized screen/session observation, normalized event extraction, confidence-scored metrics, and coaching.
- REPLAY: reconstruct recorded/captured sessions for inspection, correction, and detector evaluation.
- SIMULATOR: original/local simulations for automated strategy and UI experiments without controlling third-party accounts.

## Adapter registry
Initial targets: Panda Master, Fire Kirin, Juwa, Game Room, Game Master, GameVault, Orion Stars, Milky Way, Ultra Panda, Vegas Sweeps, plus Generic Fish Shooter fallback.

Adapters describe observable HUD regions, normalized event mappings, detector capabilities, and confidence thresholds. They never contain third-party credentials or protection-bypass logic.

## Evidence contract
Every derived item is explicitly classified:
- observed: directly visible or exact telemetry-backed
- estimate: computed from incomplete observable evidence; confidence 0..1 required
- hypothesis: proposed explanation/change requiring testing
- experiment: controlled F.S.A. test
- validated: experiment met declared success criteria
- promoted: approved for normal F.S.A. behavior
- rejected/rolled_back: failed or withdrawn experiment

No hidden server state, random outcome prediction, profit guarantee, or autonomous third-party wagering is represented as known.

## EGM -> F.S.A. insight contract
Each versioned insight contains: id, kind (ui|gameplay|balance|tutorial|accessibility), status, title, rationale, evidenceRefs[], confidence, applicability, proposal, experimentSpec, version, createdAt.

F.S.A. may consume experiment/validated/promoted insights. Runtime changes remain feature-flagged and rollbackable. Promotion requires evidence and an explicit version.

## F.S.A. -> EGM telemetry contract
Preserve the existing F.S.A. exact telemetry boundary. F.S.A. already reports session/game lifecycle, room changes, weapon changes, powers, performance samples, shots, hits, kills, score, combo, fever, wave, target count, and boss ratio. Extend it with experiment exposure/outcome/applied/rollback events.

F.S.A. exact owned-game telemetry is ground truth for validating EGM recognition and coaching.

## Feedback loop
Observe -> normalize -> measure -> explain -> propose -> experiment in F.S.A. -> measure -> validate/reject -> promote/rollback -> feed exact telemetry back into EGM.

## UI requirements
- Home: game selector + LIVE / REPLAY / SIMULATOR as the dominant entry point.
- Live Lab: capture status, targets/events, confidence, metrics, timeline, coaching.
- Replay Lab: timeline scrub, detections, corrections, evidence.
- Insight Library: evidence/status/version history.
- EGM Lab in F.S.A./Founder Console: preview, enable/disable experiments, compare before/after, promote, rollback.

## Compatibility
This rebuild extends rather than deletes the repository's existing normalized evidence, live metrics, replay, learned baselines, Tips Center, community/blog, surveys, tutorial, Admin100 registry, Android client, PWA, backend, and F.S.A. telemetry boundary.

## Safety boundary
Observation/coaching and owned simulation may be automated. EGM4000 does not autonomously wager, manipulate third-party credits/balances, store third-party passwords, bypass protections, or control third-party gambling/reward accounts.
