# Upload / Continue on GitHub Instructions

Use this file when continuing EGM4000 with any AI assistant.

## Repo

`anastaysia94-sudo/EGM4000-Android`

## Standard GitHub workflow

1. Pull or inspect latest `main`.
2. Read `docs/ai-continuation/README.md` and `PROJECT_STATUS_SV09.md`.
3. Make changes in a feature branch when possible.
4. Preserve Android, web, shared schema, and docs.
5. Commit with a plain message describing the milestone.
6. Let GitHub Actions run.
7. If the Android workflow fails, inspect logs and fix the actual compiler/test issue.
8. If the web smoke workflow fails, inspect static file paths and JavaScript syntax.
9. Update docs after behavior changes.
10. Report what passed, what failed, and what needs real-device testing.

## Important repo paths

- Android app: `android-egm4000/`
- Android manifest: `android-egm4000/app/src/main/AndroidManifest.xml`
- Main Android Kotlin source: `android-egm4000/app/src/main/java/...`
- Web/PWA app: `web/`
- Shared schema: `shared/`
- AI continuation docs: `docs/ai-continuation/`
- Android APK workflow: `.github/workflows/build-egm4000-apk.yml`
- Web smoke workflow: `.github/workflows/web-pwa-smoke.yml`

## Build APK from GitHub Actions

1. Open the repository.
2. Go to `Actions`.
3. Choose `Build EGM4000 Fire Kirin APK`.
4. Run workflow on `main` or push a commit that affects Android files.
5. Wait for green success.
6. Open the completed run.
7. Download artifact: `EGM4000-Fire-Kirin-Companion-debug-apk`.
8. Extract the ZIP to get `app-debug.apk`.

## Local Android build

From the repository root:

```bash
cd android-egm4000
gradle :app:assembleDebug --stacktrace
```

Expected debug APK path:

```text
android-egm4000/app/build/outputs/apk/debug/app-debug.apk
```

## Web/PWA local smoke check

From the repository root:

```bash
python3 -m http.server 4173 -d web
```

Then open:

```text
http://localhost:4173
```

## Do not do this

- Do not upload random binary ZIPs when source files can be committed directly.
- Do not recreate the broken `buildsrc` base64 workflow.
- Do not delete the web/PWA folder.
- Do not delete shared schemas.
- Do not call debug APK production-ready.
- Do not bypass safety boundaries for Fire Kirin or any third-party game.
