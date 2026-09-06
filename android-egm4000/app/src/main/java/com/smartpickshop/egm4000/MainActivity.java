package com.smartpickshop.egm4000;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int REQ_CAPTURE = 4000;
    private static final String DEFAULT_FIRE_KIRIN_URL = "https://play.firekirin.xyz/web_game/firekirin777_pc/index.html";
    private static final String PREFS = "egm4000";

    private SharedPreferences prefs;
    private SessionStore sessions;
    private SecureTokenStore tokenStore;
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private EditText apiUrl;
    private EditText username;
    private EditText password;
    private TextView accountStatus;
    private TextView syncStatus;
    private TextView tipsList;
    private EditText portalUrl;
    private EditText sessionNote;
    private TextView captureStatus;
    private TextView summaryView;
    private LinearLayout eventList;
    private Spinner filterSpinner;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        sessions = new SessionStore(this);
        tokenStore = new SecureTokenStore(this);
        migrateDefaultPortalUrl();
        buildUi();
        renderAccount();
        renderEvents();
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }

    private void migrateDefaultPortalUrl() {
        String saved = prefs.getString("fireKirinUrl", "");
        if (saved == null || saved.trim().isEmpty() || "https://firekirin.com".equals(saved.trim())) {
            prefs.edit().putString("fireKirinUrl", DEFAULT_FIRE_KIRIN_URL).apply();
        }
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(36));
        root.setBackgroundColor(0xff030812);
        scroll.addView(root);

        root.addView(label("EGM4000", 30, true));
        root.addView(label("Native Android v0.2 · Watch. Measure. Explain. Improve.", 15, false));
        root.addView(warning("Evidence companion — not a prediction engine. EGM4000 does not guarantee profit, infer hidden server state, manipulate third-party balances, store game-provider passwords, or bypass protections."));

        root.addView(section("EGM Account + Cross-device Sync"));
        apiUrl = input("EGM4000 HTTPS server URL", prefs.getString("apiBaseUrl", ""));
        apiUrl.setSingleLine(true);
        root.addView(apiUrl);
        username = input("EGM4000 username", prefs.getString("egmUsername", ""));
        username.setSingleLine(true);
        root.addView(username);
        password = input("EGM4000 password", "");
        password.setSingleLine(true);
        password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root.addView(password);
        LinearLayout accountButtons = row();
        accountButtons.addView(button("Sign in", v -> mobileLogin()), weighted());
        accountButtons.addView(button("Sign out", v -> signOut()), weighted());
        root.addView(accountButtons);
        LinearLayout syncButtons = row();
        syncButtons.addView(button("Sync new evidence", v -> syncEvidence()), weighted());
        syncButtons.addView(button("Refresh Tips", v -> refreshTips()), weighted());
        root.addView(syncButtons);
        root.addView(button("Open EGM4000 Web/PWA", v -> openWebApp()));
        accountStatus = card("Account", "Not signed in.");
        root.addView(accountStatus);
        syncStatus = card("Sync", "Local evidence has not been synced in this session.");
        root.addView(syncStatus);

        root.addView(section("Personalized Tips"));
        root.addView(label("Tips pulled from your EGM4000 account remain evidence-labeled. They describe your recorded history; they are not guaranteed winning instructions.", 13, false));
        tipsList = card("Tips Center", "Sign in and tap Refresh Tips.");
        root.addView(tipsList);

        root.addView(section("Fire Kirin Companion"));
        portalUrl = input("Fire Kirin portal URL", prefs.getString("fireKirinUrl", DEFAULT_FIRE_KIRIN_URL));
        portalUrl.setSingleLine(true);
        root.addView(portalUrl);
        root.addView(button("Open Fire Kirin securely", v -> openFireKirin()));
        root.addView(label("Sign in directly with Fire Kirin in its browser/site. EGM4000 never asks for or stores that password.", 13, false));

        root.addView(section("Authorized Screen Feedback"));
        LinearLayout captureButtons = row();
        captureButtons.addView(button("Start feedback", v -> requestScreenFeedback()), weighted());
        captureButtons.addView(button("Stop feedback", v -> stopFeedback()), weighted());
        root.addView(captureButtons);
        captureStatus = warning("Status: screen feedback is off. Android permission is always required. Raw frames are not stored by this v0.2 client.");
        root.addView(captureStatus);

        root.addView(section("Session Logger"));
        sessionNote = input("Event note", "Shot burst, boss target, pause, credit change, mistake, win/loss observation");
        root.addView(sessionNote);
        LinearLayout sessionControls = row();
        sessionControls.addView(button("Start fresh session", v -> startFresh()), weighted());
        sessionControls.addView(button("End session", v -> endSession()), weighted());
        root.addView(sessionControls);
        LinearLayout row1 = row();
        row1.addView(button("Shot +1", v -> addUserEvent("shot", 0)), weighted());
        row1.addView(button("Credit +10", v -> addUserEvent("credit_up", 10)), weighted());
        row1.addView(button("Credit -10", v -> addUserEvent("credit_down", -10)), weighted());
        root.addView(row1);
        root.addView(button("Pause / Break", v -> {
            sessions.add("break", 0, "Break recorded by user.", "user_recorded", 1.0, null);
            renderEvents();
        }));

        root.addView(section("Evidence Review"));
        summaryView = card("Session summary", "No local evidence yet.");
        root.addView(summaryView);
        filterSpinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, SessionStore.FILTER_LABELS);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        filterSpinner.setAdapter(adapter);
        filterSpinner.setOnItemSelectedListener(new SimpleItemSelectedListener(this::renderEvents));
        root.addView(filterSpinner);
        LinearLayout exchange = row();
        exchange.addView(button("Share JSON", v -> shareJson()), weighted());
        exchange.addView(button("Import / Paste JSON", v -> showImportDialog()), weighted());
        root.addView(exchange);
        root.addView(button("Clear local evidence", v -> confirmClear()));
        eventList = new LinearLayout(this);
        eventList.setOrientation(LinearLayout.VERTICAL);
        root.addView(eventList);

        root.addView(section("Evidence Legend"));
        root.addView(card("user_recorded · 100%", "A button or note you explicitly recorded. This is visible/user-entered evidence, not hidden game state."));
        root.addView(card("user_authorized_device_signal · ~55%", "A device/capture signal created only after Android permission. It is an observation/estimate and may be wrong."));
        root.addView(card("hypothesis / warning · conservative", "A derived risk flag such as longer sessions, repeated credit-down entries, or rising pace while credits are down. It is decision support, not prediction."));
    }

    private void mobileLogin() {
        String base = saveAndValidateApiUrl();
        if (base == null) return;
        String user = username.getText().toString().trim();
        String pass = password.getText().toString();
        if (user.length() < 3 || pass.length() < 1) { toast("Enter your EGM4000 username and password."); return; }
        accountStatus.setText("Account\nSigning in…");
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("username", user).put("password", pass);
                JSONObject out = new ApiClient(base).post("/api/mobile/login", body, null);
                tokenStore.save(out.getString("token"));
                JSONObject u = out.optJSONObject("user");
                prefs.edit().putString("egmUsername", user)
                        .putString("egmDisplayName", u == null ? user : u.optString("display_name", user))
                        .putString("egmRole", u == null ? "user" : u.optString("role", "user"))
                        .putString("mobileTokenExpiresAt", out.optString("expires_at", ""))
                        .apply();
                runOnUiThread(() -> { password.setText(""); renderAccount(); refreshTips(); });
            } catch (Exception ex) { runOnUiThread(() -> accountStatus.setText("Account\nSign in failed: " + friendly(ex))); }
        });
    }

    private void signOut() {
        tokenStore.clear();
        prefs.edit().remove("mobileTokenExpiresAt").remove("egmDisplayName").remove("egmRole").apply();
        renderAccount();
        tipsList.setText("Tips Center\nSign in and tap Refresh Tips.");
    }

    private void renderAccount() {
        String token = tokenStore.get();
        if (token.isEmpty()) {
            accountStatus.setText("Account\nNot signed in. Your local session logger still works offline.");
        } else {
            String name = prefs.getString("egmDisplayName", prefs.getString("egmUsername", "EGM4000 user"));
            String exp = prefs.getString("mobileTokenExpiresAt", "");
            accountStatus.setText("Account\nSigned in as " + name + ". Mobile token is encrypted with Android Keystore." + (exp.isEmpty() ? "" : "\nToken expiry: " + exp));
        }
    }

    private void syncEvidence() {
        String token = tokenStore.get(); if (token.isEmpty()) { toast("Sign in to EGM4000 first."); return; }
        String base = saveAndValidateApiUrl(); if (base == null) return;
        JSONArray pending = sessions.unsyncedEvents();
        if (pending.length() == 0) { syncStatus.setText("Sync\nNo new local evidence to upload."); return; }
        syncStatus.setText("Sync\nUploading " + pending.length() + " new event(s)…");
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("platform", "Fire Kirin").put("events", pending);
                JSONObject out = new ApiClient(base).post("/api/mobile/sync", body, token);
                sessions.markSyncedAll();
                JSONObject m = out.optJSONObject("metrics");
                String detail = "Accepted: " + out.optInt("accepted", 0) + " · backend session " + out.optInt("session_id", 0);
                if (m != null) detail += "\nEvents " + m.optInt("events") + " · shots " + m.optInt("shots") + " · hits " + m.optInt("hits") + " · kills " + m.optInt("kills");
                String finalDetail = detail;
                runOnUiThread(() -> { syncStatus.setText("Sync\n" + finalDetail); refreshTips(); });
            } catch (Exception ex) {
                runOnUiThread(() -> syncStatus.setText("Sync\nFailed: " + friendly(ex) + "\nLocal evidence was kept and can be retried."));
            }
        });
    }

    private void refreshTips() {
        String token = tokenStore.get(); if (token.isEmpty()) { tipsList.setText("Tips Center\nSign in first."); return; }
        String base = saveAndValidateApiUrl(); if (base == null) return;
        tipsList.setText("Tips Center\nLoading…");
        io.execute(() -> {
            try {
                String text = RawJsonClient.getArray(base + "/api/mobile/tips", token);
                JSONArray tips = new JSONArray(text);
                StringBuilder b = new StringBuilder();
                int shown = Math.min(8, tips.length());
                if (shown == 0) b.append("No tips yet. Sync a session, then refresh.");
                for (int i = 0; i < shown; i++) {
                    JSONObject t = tips.optJSONObject(i); if (t == null) continue;
                    if (i > 0) b.append("\n\n");
                    b.append(t.optString("title", "Tip"));
                    if (!t.optString("platform", "").isEmpty()) b.append(" · ").append(t.optString("platform"));
                    b.append("\n").append(t.optString("body", ""));
                    b.append("\nEvidence: ").append(t.optString("evidence", "Not provided"));
                    b.append("\nConfidence: ").append(t.optString("confidence", "unknown"));
                }
                String finalText = b.toString();
                runOnUiThread(() -> tipsList.setText("Tips Center\n" + finalText));
            } catch (Exception ex) { runOnUiThread(() -> tipsList.setText("Tips Center\nCould not refresh: " + friendly(ex))); }
        });
    }

    private void openWebApp() {
        String base = saveAndValidateApiUrl(); if (base == null) return;
        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(base)));
    }

    private String saveAndValidateApiUrl() {
        String base = apiUrl.getText().toString().trim();
        if (!base.startsWith("https://")) { toast("Set the deployed EGM4000 HTTPS server URL first."); return null; }
        while (base.endsWith("/")) base = base.substring(0, base.length() - 1);
        prefs.edit().putString("apiBaseUrl", base).apply();
        return base;
    }

    private void openFireKirin() {
        String url = portalUrl.getText().toString().trim();
        if (!url.startsWith("https://")) { toast("Use an HTTPS Fire Kirin portal URL."); return; }
        prefs.edit().putString("fireKirinUrl", url).apply();
        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
    }

    private void requestScreenFeedback() {
        MediaProjectionManager mgr = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        if (mgr == null) { toast("Screen feedback is not available on this device."); return; }
        startActivityForResult(mgr.createScreenCaptureIntent(), REQ_CAPTURE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_CAPTURE) return;
        if (resultCode == RESULT_OK) {
            Intent svc = new Intent(this, ScreenFeedbackService.class);
            svc.putExtra("startedAt", System.currentTimeMillis());
            if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(svc); else startService(svc);
            captureStatus.setText("Status: authorized screen feedback is active. Raw frames are not stored by this client. Device signals remain estimates unless separately verified.");
            sessions.add("screen_feedback_started", 0, "Android screen permission granted by user.", "user_authorized_device_signal", .55, null);
            renderEvents();
        } else toast("Screen feedback was not authorized.");
    }

    private void stopFeedback() {
        stopService(new Intent(this, ScreenFeedbackService.class));
        captureStatus.setText("Status: screen feedback is off.");
        sessions.add("screen_feedback_stopped", 0, "Screen feedback stopped by user.", "user_recorded", 1.0, null);
        renderEvents();
    }

    private void startFresh() {
        new AlertDialog.Builder(this).setTitle("Start fresh session?")
                .setMessage("This clears the current local event list after you have shared or synced it if needed.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Start", (d,w) -> { sessions.startFreshSession(); renderEvents(); syncStatus.setText("Sync\nFresh local session started."); })
                .show();
    }

    private void endSession() { sessions.endSession(); renderEvents(); }

    private void addUserEvent(String type, int creditDelta) {
        sessions.add(type, creditDelta, sessionNote.getText().toString(), "user_recorded", 1.0, null);
        renderEvents();
    }

    private void renderEvents() {
        if (summaryView == null || eventList == null) return;
        SessionStore.Summary s = sessions.summary();
        String risk = s.warnings == 0 ? "No conservative risk flags recorded yet." : s.warnings + " conservative risk flag(s) recorded — review Warnings filter.";
        summaryView.setText("Session summary\nStart: " + s.startedAt + "\nEnd: " + s.endedAt +
                String.format(Locale.US, "\nDuration: %.1f min · Estimated shot pace: %.1f/min", s.durationMinutes, s.shotPace) +
                "\nEvents: " + s.events + " · Shots: " + s.shots + " · Net credit movement: " + s.netCredits +
                "\nCredit-down entries: " + s.creditDowns + " · Breaks: " + s.breaks + "\n" + risk +
                "\nReminder: these are descriptive records, not predictions of future outcomes.");
        eventList.removeAllViews();
        String filter = filterSpinner == null || filterSpinner.getSelectedItem() == null ? "All events" : String.valueOf(filterSpinner.getSelectedItem());
        JSONArray arr = sessions.filtered(filter);
        if (arr.length() == 0) { eventList.addView(card("No matching evidence", "Record events or choose another filter.")); return; }
        for (int i = arr.length() - 1; i >= 0; i--) {
            JSONObject e = arr.optJSONObject(i); if (e == null) continue;
            String conf = String.format(Locale.US, "%.0f%%", e.optDouble("confidence", 0) * 100.0);
            eventList.addView(card(e.optString("type") + " · " + e.optString("time"),
                    "Credit delta: " + e.optInt("creditDelta", 0) + "\nEvidence: " + e.optString("provenance", "unknown") + " · confidence " + conf + "\n" + e.optString("note", "")));
        }
    }

    private void shareJson() {
        try {
            String json = sessions.exportPackage().toString(2);
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_SUBJECT, "EGM4000 Android session evidence");
            send.putExtra(Intent.EXTRA_TEXT, json);
            startActivity(Intent.createChooser(send, "Share EGM4000 JSON"));
        } catch (Exception ex) { toast("Could not export JSON: " + ex.getMessage()); }
    }

    private void showImportDialog() {
        EditText paste = input("Paste EGM4000 JSON", "");
        paste.setMinLines(10); paste.setGravity(Gravity.TOP); paste.setSingleLine(false);
        new AlertDialog.Builder(this).setTitle("Import / Paste session JSON")
                .setMessage("Validates required event fields before replacing the current local session. Maximum 1000 events.")
                .setView(paste)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Import", (d,w) -> {
                    try { int count = sessions.importPackage(paste.getText().toString()); renderEvents(); toast("Imported " + count + " valid event(s)."); }
                    catch (Exception ex) { toast("Import failed: " + ex.getMessage()); }
                }).show();
    }

    private void confirmClear() {
        new AlertDialog.Builder(this).setTitle("Clear local evidence?")
                .setMessage("This does not delete evidence already synced to your EGM4000 account.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Clear", (d,w) -> { sessions.startFreshSession(); renderEvents(); })
                .show();
    }

    private String friendly(Exception ex) {
        if (ex instanceof ApiClient.ApiException) {
            ApiClient.ApiException a = (ApiClient.ApiException) ex;
            if (a.statusCode == 401) return "authentication failed or token expired";
            if (a.statusCode == 429) return "too many attempts — try again later";
            return a.getMessage();
        }
        return ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage();
    }

    private void toast(String value) { Toast.makeText(this, value, Toast.LENGTH_LONG).show(); }

    private TextView label(String text, int sp, boolean title) {
        TextView tv = new TextView(this); tv.setText(text); tv.setTextSize(sp); tv.setTextColor(title ? 0xff5cecff : 0xffd8f7ff); tv.setPadding(0, dp(6), 0, dp(6));
        if (title) tv.setTypeface(Typeface.DEFAULT, Typeface.BOLD); return tv;
    }
    private TextView section(String text) { TextView tv = label("\n" + text.toUpperCase(Locale.US), 18, true); tv.setGravity(Gravity.START); return tv; }
    private TextView warning(String text) { TextView tv = label(text, 13, false); tv.setTextColor(0xffffd58a); tv.setBackgroundColor(0xff102033); tv.setPadding(dp(12),dp(10),dp(12),dp(10)); return tv; }
    private EditText input(String hint, String value) { EditText in = new EditText(this); in.setHint(hint); in.setText(value); in.setTextColor(0xffffffff); in.setHintTextColor(0xff7897a8); in.setBackgroundColor(0xff071725); in.setPadding(dp(12),dp(10),dp(12),dp(10)); LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(0,dp(6),0,dp(6));in.setLayoutParams(lp);return in; }
    private Button button(String text, View.OnClickListener listener) { Button b=new Button(this);b.setText(text);b.setAllCaps(false);b.setOnClickListener(listener);b.setPadding(dp(8),dp(8),dp(8),dp(8));return b; }
    private TextView card(String title, String body) { TextView tv=label(title+"\n"+body,14,false);tv.setBackgroundColor(0xff081827);tv.setPadding(dp(12),dp(12),dp(12),dp(12));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(0,dp(8),0,dp(8));tv.setLayoutParams(lp);return tv; }
    private LinearLayout row() { LinearLayout r=new LinearLayout(this);r.setOrientation(LinearLayout.HORIZONTAL);r.setGravity(Gravity.CENTER_VERTICAL);return r; }
    private LinearLayout.LayoutParams weighted() { LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1f);lp.setMargins(dp(2),dp(4),dp(2),dp(4));return lp; }
    private int dp(int value) { return (int)(value*getResources().getDisplayMetrics().density); }

    private static final class SimpleItemSelectedListener implements android.widget.AdapterView.OnItemSelectedListener {
        private final Runnable action;
        SimpleItemSelectedListener(Runnable action) { this.action=action; }
        @Override public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) { action.run(); }
        @Override public void onNothingSelected(android.widget.AdapterView<?> parent) { }
    }

    private static final class RawJsonClient {
        static String getArray(String url, String bearer) throws Exception {
            java.net.HttpURLConnection conn=(java.net.HttpURLConnection)new java.net.URL(url).openConnection();
            conn.setRequestMethod("GET");conn.setConnectTimeout(12000);conn.setReadTimeout(20000);conn.setRequestProperty("Accept","application/json");conn.setRequestProperty("Authorization","Bearer "+bearer);conn.setRequestProperty("User-Agent","EGM4000-Android/0.2");
            int code=conn.getResponseCode();java.io.InputStream stream=code>=200&&code<300?conn.getInputStream():conn.getErrorStream();java.io.BufferedReader r=new java.io.BufferedReader(new java.io.InputStreamReader(stream,java.nio.charset.StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();String line;while((line=r.readLine())!=null)b.append(line);r.close();conn.disconnect();if(code<200||code>=300)throw new ApiClient.ApiException(code,"HTTP "+code,new JSONObject());return b.toString();
        }
    }
}
