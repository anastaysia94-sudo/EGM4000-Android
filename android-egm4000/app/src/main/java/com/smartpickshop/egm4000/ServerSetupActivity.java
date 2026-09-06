package com.smartpickshop.egm4000;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.time.Instant;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Android v0.2.1 deployment handoff.
 *
 * Validates the canonical EGM4000 HTTPS service before the user enters the
 * account/sync screen. The URL remains user-editable so staging/recovery hosts
 * can be used without rebuilding the APK.
 */
public final class ServerSetupActivity extends Activity {
    private static final String PREFS = "egm4000";
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private SharedPreferences prefs;
    private EditText serverUrl;
    private TextView status;
    private Button continueButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        buildUi();
        String saved = prefs.getString("apiBaseUrl", "");
        if (saved != null && saved.startsWith("https://")) checkServer(false);
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(24), dp(18), dp(36));
        root.setBackgroundColor(0xff030812);
        scroll.addView(root);

        root.addView(text("EGM4000", 30, 0xffe9fbff, true));
        root.addView(text("Android v0.2.1 · Server connection", 16, 0xff00f2ff, true));
        root.addView(card("Connect to the canonical HTTPS service before account sync. Local evidence logging still works if the server is unavailable."));

        serverUrl = new EditText(this);
        serverUrl.setHint("https://your-egm4000-host.onrender.com");
        serverUrl.setText(prefs.getString("apiBaseUrl", ""));
        serverUrl.setSingleLine(true);
        serverUrl.setTextColor(0xffe9fbff);
        serverUrl.setHintTextColor(0xff6f8a99);
        serverUrl.setBackgroundColor(0xff0c1624);
        serverUrl.setPadding(dp(12), dp(12), dp(12), dp(12));
        root.addView(serverUrl);

        Button check = button("Check server health", v -> checkServer(true));
        root.addView(check);

        status = card("Server status: not checked.");
        root.addView(status);

        continueButton = button("Continue to EGM4000", v -> openMain());
        root.addView(continueButton);
        root.addView(button("Continue offline", v -> startMain()));

        root.addView(text("Expected endpoint: /api/health → ok=true, schema=egm.event.v1. EGM4000 never asks for third-party game passwords here.", 13, 0xffffd28a, false));
        setContentView(scroll);
    }

    private void checkServer(boolean announce) {
        String base = normalizedUrl();
        if (base == null) return;
        status.setText("Server status\nChecking " + base + " …");
        continueButton.setEnabled(false);
        io.execute(() -> {
            try {
                JSONObject health = new ApiClient(base).get("/api/health", null);
                boolean ok = health.optBoolean("ok", false);
                String schema = health.optString("schema", "");
                String service = health.optString("service", "EGM4000");
                if (!ok || !"egm.event.v1".equals(schema)) {
                    throw new IllegalStateException("Unexpected health response.");
                }
                String checkedAt = Instant.now().toString();
                prefs.edit()
                        .putString("apiBaseUrl", base)
                        .putString("serverLastHealthyAt", checkedAt)
                        .putString("serverLastService", service)
                        .apply();
                runOnUiThread(() -> {
                    status.setText("Server status\nONLINE · " + service + "\nSchema: " + schema + "\nVerified: " + checkedAt);
                    continueButton.setEnabled(true);
                    if (announce) Toast.makeText(this, "EGM4000 server is online.", Toast.LENGTH_SHORT).show();
                });
            } catch (Exception ex) {
                runOnUiThread(() -> {
                    status.setText("Server status\nOFFLINE / NOT VERIFIED\n" + friendly(ex) + "\nYou can continue offline; sync will remain pending.");
                    continueButton.setEnabled(true);
                });
            }
        });
    }

    private String normalizedUrl() {
        String value = serverUrl.getText().toString().trim();
        if (!value.startsWith("https://")) {
            Toast.makeText(this, "Use the deployed EGM4000 HTTPS URL.", Toast.LENGTH_SHORT).show();
            return null;
        }
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        return value;
    }

    private void openMain() {
        String base = normalizedUrl();
        if (base == null) return;
        prefs.edit().putString("apiBaseUrl", base).apply();
        startMain();
    }

    private void startMain() {
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }

    private TextView text(String value, int sp, int color, boolean bold) {
        TextView tv = new TextView(this);
        tv.setText(value);
        tv.setTextSize(sp);
        tv.setTextColor(color);
        if (bold) tv.setTypeface(Typeface.DEFAULT_BOLD);
        tv.setPadding(0, dp(8), 0, dp(8));
        return tv;
    }

    private TextView card(String value) {
        TextView tv = text(value, 14, 0xffd7e8f2, false);
        tv.setBackgroundColor(0xff0c1624);
        tv.setPadding(dp(12), dp(12), dp(12), dp(12));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, dp(8), 0, dp(8));
        tv.setLayoutParams(lp);
        return tv;
    }

    private Button button(String value, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(value);
        b.setAllCaps(false);
        b.setOnClickListener(listener);
        return b;
    }

    private String friendly(Exception ex) {
        String message = ex.getMessage();
        return message == null || message.trim().isEmpty() ? ex.getClass().getSimpleName() : message;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }
}
