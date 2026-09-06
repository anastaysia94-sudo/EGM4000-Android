# EGM4000 / EduGameMaster 4000

Cyber-aquatic gameplay intelligence for user-authorized session evidence.

**Core loop:** Watch → Measure → Explain → Improve.

This repository now contains a clean emergency launch rebuild that preserves the established EGM4000 direction while making the project buildable from normal GitHub Actions infrastructure.

## What is included

- `android-egm4000/` — native Android project for EGM4000 Fire Kirin Companion.
- `web/` — local-first EGM4000 web/PWA public beta.
- `shared/` — normalized gameplay event schema.
- `docs/` — safety, Fire Kirin companion, and project status documentation.
- `.github/workflows/build-egm4000-apk.yml` — builds the installable debug APK.

## Fire Kirin workflow

EGM4000 does **not** create a fake Fire Kirin login and does **not** store Fire Kirin credentials.

The safe workflow is:

1. Open EGM4000.
2. Tap **Open Fire Kirin securely**.
3. Sign in directly with Fire Kirin in the browser.
4. Return to EGM4000.
5. Start authorized screen feedback.
6. Log session evidence.
7. Review EGM4000 feedback, replay, metrics, and tips.

## Safety boundary

EGM4000 does not guarantee profit, predict random outcomes, infer hidden server state, manipulate balances, bypass protections, or provide live-service cheating. It only explains authorized evidence and clearly labels estimates/hypotheses.

## Build APK

Open GitHub → Actions → **Build EGM4000 Fire Kirin APK**. The output artifact is named:

`EGM4000-Fire-Kirin-Companion-debug-apk`

Inside that artifact is:

`app-debug.apk`

## Web/PWA

Open `web/index.html` locally or host the `web/` folder on HTTPS. Browser screen feedback requires HTTPS and user permission.
