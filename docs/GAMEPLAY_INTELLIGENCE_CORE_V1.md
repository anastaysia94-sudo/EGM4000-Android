# EGM4000 Gameplay Intelligence Core v1

Status: implementation contract for the primary EGM4000 experience.

## Product priority
Gameplay intelligence is the primary EGM4000 function. Community, surveys, Tips, research and Admin100 remain supporting modules.

## Core modes
- LIVE: user-authorized screen/session observation, normalized event extraction, confidence-scored metrics and coaching.
- REPLAY: reconstruct recorded/captured sessions for inspection and correction.
- SIMULATOR: original/local simulations for automated strategy experiments without controlling third-party accounts.

## Adapter registry
Panda Master, Fire Kirin, Juwa, Game Room, Game Master, GameVault, Orion Stars, Milky Way, Ultra Panda, Vegas Sweeps, plus Generic Fish Shooter fallback.

Adapters describe observable HUD regions, event mappings and confidence thresholds. They never contain third-party credentials or bypass logic.

## Evidence contract
Every derived item is one of:
- observed: directly visible/telemetry-backed
- estimate: computed from incomplete observable evidence and includes confidence 0..1
- hypothesis: proposed explanation/change requiring testing
- experiment: controlled F.S.A. test
- validated: experiment met declared success criteria
- promoted: approved for normal F.S.A. behavior

No hidden server state, random outcome prediction, profit guarantee or autonomous third-party wagering is represented as known.

## EGM -> F.S.A. insight contract
Each insight contains:
id, kind (ui|gameplay|balance|tutorial|accessibility), status, title, rationale, evidenceRefs[], confidence, applicability, proposal, experimentSpec, version, createdAt.

Only experiment/validated/promoted insights may be consumed by F.S.A. Runtime behavior must remain rollbackable. Promoted changes require evidence and an explicit version.

## F.S.A. -> EGM telemetry contract
F.S.A. emits exact owned-game telemetry: session/game lifecycle, room changes, weapon changes, powers, performance samples, shots/hits/kills/score/combo/fever/wave/target count/boss ratio, plus experiment exposure/outcome events.

This exact telemetry is ground truth for validating EGM recognition and coaching.

## Feedback loop
Observe -> normalize -> measure -> explain -> propose -> experiment in F.S.A. -> measure -> validate/reject -> promote/rollback -> feed telemetry back into EGM.

## UI requirements
Home: game selector + LIVE/REPLAY/SIMULATOR.
Live Lab: capture status, targets/events, confidence, metrics, timeline and coaching.
Replay Lab: timeline scrub, detections, corrections and evidence.
Insight Library: evidence/status/version history.
EGM Lab in Founder Console/F.S.A.: preview, enable/disable, compare before/after, promote and rollback.

## Safety
Observation/coaching and owned simulation may be automated. EGM4000 must not autonomously wager, manipulate credits/balances, store third-party passwords, bypass protections, or control third-party gambling/reward accounts.
