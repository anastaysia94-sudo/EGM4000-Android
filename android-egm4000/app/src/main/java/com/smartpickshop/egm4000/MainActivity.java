package com.smartpickshop.egm4000;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int REQ_CAPTURE = 4000;
    private SharedPreferences prefs;
    private EditText portalUrl;
    private EditText sessionNote;
    private TextView status;
    private LinearLayout eventList;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("egm4000", MODE_PRIVATE);
        buildUi();
        renderEvents();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(32));
        root.setBackgroundColor(0xff050914);
        scroll.addView(root);

        TextView brand = label("EGM4000 / EduGameMaster 4000", 25, true);
        root.addView(brand);
        root.addView(label("Watch. Measure. Explain. Improve.", 16, false));
        root.addView(warning("PUBLIC BETA: user-authorized evidence only. EGM4000 does not predict random outcomes, guarantee profit, bypass protections, manipulate balances, or store Fire Kirin credentials."));

        root.addView(section("Fire Kirin Companion"));
        portalUrl = input("Fire Kirin portal URL", prefs.getString("fireKirinUrl", "https://firekirin.com"));
        root.addView(portalUrl);
        root.addView(button("Open Fire Kirin securely", v -> openFireKirin()));
        root.addView(label("Sign in directly with Fire Kirin in your browser. EGM4000 never asks for or stores your Fire Kirin password.", 14, false));

        root.addView(section("Authorized Screen Feedback"));
        root.addView(button("Start authorized screen feedback", v -> requestScreenFeedback()));
        root.addView(button("Stop screen feedback", v -> stopService(new Intent(this, ScreenFeedbackService.class))));
        status = warning("Status: local-first. Screen feedback requires Android permission. This v0.1 app logs session evidence and aggregate feedback prompts; it does not save raw screen frames.");
        root.addView(status);

        root.addView(section("Session Logger"));
        sessionNote = input("Event note", "Shot burst, boss target, pause, credit change, mistake, win/loss observation");
        root.addView(sessionNote);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.addView(button("Shot +1", v -> addEvent("shot", 1, sessionNote.getText().toString())));
        row.addView(button("Credit +", v -> addEvent("credit_up", 10, sessionNote.getText().toString())));
        row.addView(button("Credit -", v -> addEvent("credit_down", -10, sessionNote.getText().toString())));
        root.addView(row);
        root.addView(button("Pause / Break reminder", v -> addEvent("break", 0, "Break reminder recorded. Pressure makes clarity.")));
        root.addView(button("Clear local test data", v -> clearEvents()));

        root.addView(section("EGM4000 Feedback"));
        root.addView(label("Feedback is based on what you record and explicitly authorize: shot pace, session length, credit movement, drawdown warnings, replay notes, and visible screen-activity estimates. Correlation is not prediction.", 14, false));
        eventList = new LinearLayout(this);
        eventList.setOrientation(LinearLayout.VERTICAL);
        root.addView(eventList);

        setContentView(scroll);
    }

    private void openFireKirin() {
        String url = portalUrl.getText().toString().trim();
        if (!url.startsWith("https://")) {
            Toast.makeText(this, "Use an HTTPS Fire Kirin portal URL.", Toast.LENGTH_LONG).show();
            return;
        }
        prefs.edit().putString("fireKirinUrl", url).apply();
        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
    }

    private void requestScreenFeedback() {
        MediaProjectionManager mgr = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        if (mgr == null) {
            Toast.makeText(this, "Screen feedback is not available on this device.", Toast.LENGTH_LONG).show();
            return;
        }
        startActivityForResult(mgr.createScreenCaptureIntent(), REQ_CAPTURE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_CAPTURE && resultCode == RESULT_OK) {
            Intent svc = new Intent(this, ScreenFeedbackService.class);
            svc.putExtra("startedAt", now());
            if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(svc); else startService(svc);
            status.setText("Status: authorized screen feedback is active. Raw frames are not stored. Record session events below so EGM4000 can explain your play with evidence labels.");
            addEvent("screen_feedback_started", 0, "Android screen permission granted by user.");
        } else if (requestCode == REQ_CAPTURE) {
            Toast.makeText(this, "Screen feedback was not authorized.", Toast.LENGTH_LONG).show();
        }
    }

    private void addEvent(String type, int creditDelta, String note) {
        try {
            JSONArray arr = new JSONArray(prefs.getString("events", "[]"));
            JSONObject e = new JSONObject();
            e.put("schema", "egm4000.gameplay-event.v1");
            e.put("platform", "Fire Kirin");
            e.put("type", type);
            e.put("creditDelta", creditDelta);
            e.put("note", note == null ? "" : note.trim());
            e.put("provenance", type.startsWith("screen") ? "user_authorized_device_signal" : "user_recorded");
            e.put("confidence", type.startsWith("screen") ? 0.55 : 1.0);
            e.put("time", now());
            arr.put(e);
            prefs.edit().putString("events", arr.toString()).apply();
            renderEvents();
        } catch (Exception ex) {
            Toast.makeText(this, "Could not save event: " + ex.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void clearEvents() {
        prefs.edit().remove("events").apply();
        renderEvents();
    }

    private void renderEvents() {
        if (eventList == null) return;
        eventList.removeAllViews();
        try {
            JSONArray arr = new JSONArray(prefs.getString("events", "[]"));
            int shots = 0;
            int net = 0;
            for (int i = 0; i < arr.length(); i++) {
                JSONObject e = arr.getJSONObject(i);
                if ("shot".equals(e.optString("type"))) shots++;
                net += e.optInt("creditDelta", 0);
            }
            eventList.addView(card("Session summary", "Recorded events: " + arr.length() + "\nShots: " + shots + "\nNet credit movement: " + net + " credits\nTip: if pace rises while net credits fall, slow down and review the replay before continuing."));
            for (int i = arr.length() - 1; i >= 0; i--) {
                JSONObject e = arr.getJSONObject(i);
                eventList.addView(card(e.optString("type") + " · " + e.optString("time"), "Credit delta: " + e.optInt("creditDelta") + "\nEvidence: " + e.optString("provenance") + " · confidence " + e.optDouble("confidence") + "\n" + e.optString("note")));
            }
        } catch (Exception ex) {
            eventList.addView(card("No local evidence yet", "Open Fire Kirin, sign in there, return to EGM4000, authorize feedback, then log a few session events."));
        }
    }

    private String now() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date());
    }

    private TextView label(String text, int sp, boolean title) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(sp);
        tv.setTextColor(title ? 0xff00f2ff : 0xffd8f7ff);
        tv.setPadding(0, dp(6), 0, dp(6));
        return tv;
    }

    private TextView section(String text) {
        TextView tv = label("\n" + text.toUpperCase(Locale.US), 18, true);
        tv.setGravity(Gravity.START);
        return tv;
    }

    private TextView warning(String text) {
        TextView tv = label(text, 13, false);
        tv.setBackgroundColor(0xff102033);
        tv.setPadding(dp(12), dp(10), dp(12), dp(10));
        return tv;
    }

    private EditText input(String hint, String value) {
        EditText input = new EditText(this);
        input.setHint(hint);
        input.setText(value);
        input.setSingleLine(false);
        input.setTextColor(0xffffffff);
        input.setHintTextColor(0xff8fa8b5);
        return input;
    }

    private Button button(String text, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setOnClickListener(listener);
        b.setPadding(dp(8), dp(8), dp(8), dp(8));
        return b;
    }

    private TextView card(String title, String body) {
        TextView tv = label(title + "\n" + body, 14, false);
        tv.setBackgroundColor(0xff081827);
        tv.setPadding(dp(12), dp(12), dp(12), dp(12));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(0, dp(8), 0, dp(8));
        tv.setLayoutParams(lp);
        return tv;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }
}
