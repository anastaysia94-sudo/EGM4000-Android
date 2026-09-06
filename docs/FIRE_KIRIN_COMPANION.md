# EGM4000 Fire Kirin Companion

This repository implements a credential-safe Fire Kirin companion flow.

## Configured Fire Kirin login portal

Default login URL used by Android and Web/PWA:

`https://play.firekirin.xyz/web_game/firekirin777_pc/index.html`

This URL is opened externally in the user's browser/app environment. EGM4000 does not embed a fake login page and does not collect Fire Kirin credentials.

## User flow

1. Open EGM4000.
2. Confirm the Fire Kirin portal URL:
   `https://play.firekirin.xyz/web_game/firekirin777_pc/index.html`
3. Tap **Open Fire Kirin securely**.
4. Sign in directly with Fire Kirin in the browser.
5. Return to EGM4000.
6. Start authorized screen feedback only after Android or the browser asks for permission.
7. Log session events and review evidence-based feedback.

## Security boundary

EGM4000 does not ask for, proxy, capture, store, or transmit Fire Kirin credentials.

## Evidence boundary

EGM4000 feedback is based on user-recorded events and user-authorized observation signals. It does not read hidden server state, guarantee profit, predict random outcomes, manipulate balances, bypass protections, or cheat live services.

## Testing note

After this URL changes, rebuild the debug APK from GitHub Actions and install the newest `app-debug.apk` on the device. Existing installs that saved the old default can use **Reset to configured Fire Kirin login** inside the Android app.
