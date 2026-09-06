package com.smartpickshop.egm4000;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

public class TutorialActivity extends Activity {
    private static final String PREFS = "egm4000";
    private static final String KEY_DONE = "c002TutorialCompleted";
    private static final String KEY_STEP = "c002TutorialStep";

    private final String[] titles = {
            "Welcome to EGM4000",
            "1. Setup",
            "2. Log sessions",
            "3. Monitor authorized events",
            "4. Read analytics",
            "5. Use AI / evidence tips",
            "6. Bankroll Guard",
            "7. Community + privacy",
            "8. Safe Research Lab"
    };

    private final String[] bodies = {
            "EGM4000 is a fish-shooter gameplay intelligence companion. Watch → Measure → Explain → Improve. It works from evidence you record or explicitly authorize; it does not predict random outcomes or guarantee profit.",
            "Open a supported game portal, sign in with the provider itself, then return to EGM4000. EGM4000 should never collect or store your Fire Kirin, GameVault, Panda Master, Juwa, or other third-party password.",
            "Use the session logger to record shots, credit movement, breaks, target notes, and other observations. These events become your personal replay evidence.",
            "Authorized screen feedback begins only after Android permission. EGM4000 must distinguish exact user-recorded events from device signals, detections, estimates, correlations, and hypotheses by evidence labels and confidence.",
            "Analytics summarize evidence already collected, such as event count, shot pace, credit movement, session length, drawdown patterns, and replay markers. Descriptive metrics do not reveal hidden server state or prove future outcomes.",
            "Use tips as evidence-labeled coaching. A tip should explain what evidence supports it and how confident the system is. Treat low-confidence signals as review cues, never guaranteed winning instructions.",
            "Bankroll Guard is a decision-support safety layer. Use limits, break reminders, drawdown review, and stop conditions instead of chasing losses or assuming a win is due.",
            "Community is for registered-user posts, blogs, comments, reactions, reports, and moderated discussion. Community claims are user-generated content, not verified game evidence by default. Tutorial progress is stored locally on this device.",
            "The Research Lab is limited to local/original sandbox modding, reverse-engineering education, AI experiments, and defensive anti-cheat study in systems you own or are authorized to test. Do not bypass protections or compromise live third-party services without authorization."
    };

    private SharedPreferences prefs;
    private int step;
    private TextView title;
    private TextView body;
    private TextView counter;
    private ProgressBar progress;
    private Button back;
    private Button next;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        if (prefs.getBoolean(KEY_DONE, false)) {
            openApp();
            return;
        }
        step = Math.max(0, Math.min(titles.length - 1, prefs.getInt(KEY_STEP, 0)));
        buildUi();
        render();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(24), dp(18), dp(28));
        root.setBackgroundColor(0xff050914);
        scroll.addView(root);

        TextView brand = text("EGM4000 · C002", 13, 0xff00f2ff);
        root.addView(brand);
        root.addView(text("First-time operation tutorial", 28, 0xffe9fbff));

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(titles.length);
        root.addView(progress);

        counter = text("", 13, 0xff9db7c4);
        title = text("", 24, 0xff00d4c8);
        body = text("", 17, 0xffe9fbff);
        body.setLineSpacing(0f, 1.25f);
        root.addView(counter);
        root.addView(title);
        root.addView(body);

        TextView safety = text("Safety boundary: EGM4000 does not guarantee profit, predict random outcomes, infer hidden server state, manipulate balances, store third-party passwords, bypass protections, or provide unauthorized live-service cheating.", 14, 0xffffd28a);
        safety.setBackgroundColor(0xff102033);
        safety.setPadding(dp(12), dp(12), dp(12), dp(12));
        root.addView(safety);

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setGravity(Gravity.CENTER_VERTICAL);
        back = button("Back", v -> previous());
        next = button("Next", v -> advance());
        Button skip = button("Skip for now", v -> openApp());
        controls.addView(back, weighted());
        controls.addView(next, weighted());
        root.addView(controls);
        root.addView(skip);

        setContentView(scroll);
    }

    private void render() {
        counter.setText("Step " + (step + 1) + " of " + titles.length);
        title.setText(titles[step]);
        body.setText(bodies[step]);
        progress.setProgress(step + 1);
        back.setEnabled(step > 0);
        next.setText(step == titles.length - 1 ? "Finish tutorial" : "Next");
        prefs.edit().putInt(KEY_STEP, step).apply();
    }

    private void previous() {
        if (step > 0) {
            step--;
            render();
        }
    }

    private void advance() {
        if (step == titles.length - 1) {
            prefs.edit().putBoolean(KEY_DONE, true).putInt(KEY_STEP, 0).apply();
            openApp();
            return;
        }
        step++;
        render();
    }

    private void openApp() {
        startActivity(new Intent(this, ServerSetupActivity.class));
        finish();
    }

    private TextView text(String value, int sp, int color) {
        TextView tv = new TextView(this);
        tv.setText(value);
        tv.setTextSize(sp);
        tv.setTextColor(color);
        tv.setPadding(0, dp(8), 0, dp(8));
        return tv;
    }

    private Button button(String value, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(value);
        b.setAllCaps(false);
        b.setOnClickListener(listener);
        return b;
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        lp.setMargins(dp(3), dp(8), dp(3), dp(8));
        return lp;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }
}
