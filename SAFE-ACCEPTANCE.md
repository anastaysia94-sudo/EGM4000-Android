# EGM4000 Acceptance Boundary

## Canonical acceptance rule

EGM4000 / F.S.A. acceptance must be verified only with software, accounts, telemetry, and game environments that SmartPickShop owns, controls, or has explicit authorization to test.

A release is **not** blocked on a live third-party gambling-style service, real-money account, or age-restricted account.

## Accepted evidence

A valid end-to-end acceptance run may use:
- the owned F.S.A. sandbox/non-cash environment;
- synthetic replay data;
- explicitly authorized test telemetry;
- an emulator or local test account with no real-money balance;
- a consenting internal tester using the owned sandbox.

The acceptance run should prove:
1. session starts;
2. telemetry is captured;
3. EGM4000 imports it;
4. analysis renders;
5. replay/catch-up works;
6. no fabricated prediction or guaranteed-outcome claim is produced;
7. session data remains isolated to the authorized test environment.

## Not required for launch

Do not require or count:
- real-money play;
- a third-party gambling account;
- bypassing age/identity/platform controls;
- access to a live service without explicit authorization.

This boundary keeps EGM4000 and F.S.A. separate products while allowing their authorized integration to be tested safely.
