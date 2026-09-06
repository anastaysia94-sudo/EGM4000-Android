# Founder Console → EGM4000 Contract

Status: draft contract for a separate owner/admin product.

## Purpose

Founder Console is the admin/control-plane side of the ecosystem. It should help the owner manage EGM4000 and F.S.A. safely without becoming a cheat panel, unauthorized third-party controller, or real-balance manipulation tool.

Founder Console tagline options:

- `Control the chaos.`
- `Pressure makes clarity.`

## Product boundary

Founder Console is separate from EGM4000 and F.S.A.

Allowed relationship:

`Founder Console configures owned app settings -> EGM4000/F.S.A. consume safe settings -> users see transparent app behavior`

Not allowed relationship:

`Founder Console controls third-party games, reads hidden state, manipulates credits, bypasses protection, or edits real balances`

## Safe admin controls

Founder Console may manage:

- owner account settings;
- app feature flags;
- user roles for owned products;
- local content/tip templates;
- evidence-label definitions;
- safety copy and warnings;
- F.S.A. virtual/non-cash credit settings;
- F.S.A. difficulty in owned/simulated environments;
- experiment definitions for owned environments;
- telemetry dashboards for authorized data;
- app health, build status, and release notes;
- web/PWA deployment checklists;
- Android APK release checklist;
- consent copy and privacy settings.

## Prohibited admin controls

Founder Console must not include:

- Fire Kirin password collection;
- third-party credential storage;
- third-party hidden-state access;
- third-party balance manipulation;
- third-party gameplay automation intended to cheat;
- bypass tools;
- payout guarantees;
- random-outcome prediction claims;
- admin override for real money or redeemable balances without a full legal/compliance system.

## Suggested configuration object

```json
{
  "schema": "smartpickshop.founder-console.egm4000-config.v1",
  "updatedAt": "2026-09-05T17:05:00-07:00",
  "product": "egm4000",
  "safety": {
    "credentialCollectionDisabled": true,
    "profitGuaranteesDisabled": true,
    "thirdPartyManipulationDisabled": true,
    "showResponsiblePlayWarnings": true
  },
  "features": {
    "sessionLogger": true,
    "authorizedScreenFeedback": true,
    "replay": true,
    "tipsCenter": true,
    "dataExport": true,
    "fsaTelemetryIngest": false
  },
  "copy": {
    "primaryTagline": "Watch. Measure. Explain. Improve.",
    "safetyBanner": "User-authorized evidence only. No profit guarantees. No hidden-state access."
  }
}
```

## Next implementation target

Create a separate `founder-console/` folder only after the EGM4000 Android/Web foundations are stable. It may start as a static local admin dashboard that edits a safe JSON config file, but it must not pretend to control third-party games.
