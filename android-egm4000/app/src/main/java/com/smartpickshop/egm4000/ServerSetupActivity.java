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

/** Android v0.3 production-service handoff. */
public final class ServerSetupActivity extends Activity {
    private static final String PREFS = "egm4000";
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;
    private EditText serverUrl;
    private TextView status;
    private Button continueButton;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String saved = prefs.getString("apiBaseUrl", "");
        if ((saved == null || saved.trim().isEmpty()) && BuildConfig.EGM_API_BASE_URL.startsWith("https://")) {
            saved = normalize(BuildConfig.EGM_API_BASE_URL);
            prefs.edit().putString("apiBaseUrl", saved).apply();
        }
        buildUi();
        if (saved != null && saved.startsWith("https://")) checkServer(false);
    }

    @Override protected void onDestroy() { io.shutdownNow(); super.onDestroy(); }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(24), dp(18), dp(36));
        root.setBackgroundColor(0xff030812);
        scroll.addView(root);
        root.addView(text("EGM4000", 30, 0xffe9fbff, true));
        root.addView(text("Android v0.3 · Production service", 16, 0xff00f2ff, true));
        root.addView(card("The canonical build can carry its HTTPS backend URL. You can still replace it with an authorized staging/recovery host without rebuilding."));
        serverUrl = new EditText(this);
        serverUrl.setHint("https://your-egm4000-host.example");
        serverUrl.setText(prefs.getString("apiBaseUrl", BuildConfig.EGM_API_BASE_URL));
        serverUrl.setSingleLine(true);serverUrl.setTextColor(0xffe9fbff);serverUrl.setHintTextColor(0xff6f8a99);serverUrl.setBackgroundColor(0xff0c1624);serverUrl.setPadding(dp(12),dp(12),dp(12),dp(12));root.addView(serverUrl);
        root.addView(button("Verify production service", v -> checkServer(true)));
        status = card("Server status: not checked.");root.addView(status);
        continueButton = button("Continue to EGM4000", v -> openMain());continueButton.setEnabled(false);root.addView(continueButton);
        root.addView(button("Continue offline", v -> startMain()));
        root.addView(text("Verification checks both /api/health and /api/health/ready. EGM4000 never asks for third-party game passwords here.",13,0xffffd28a,false));
        setContentView(scroll);
    }

    private void checkServer(boolean announce) {
        String base = normalizedUrl();if (base == null) return;
        status.setText("Server status\nChecking " + base + " …");continueButton.setEnabled(false);
        io.execute(() -> {
            try {
                ApiClient client=new ApiClient(base);JSONObject health=client.get("/api/health",null);JSONObject ready=client.get("/api/health/ready",null);
                boolean ok=health.optBoolean("ok",false);String schema=health.optString("schema","");boolean productionReady=ready.optBoolean("ready",false);
                if(!ok || !"egm.event.v1".equals(schema) || !productionReady)throw new IllegalStateException("Service health/readiness contract did not pass.");
                String checkedAt=Instant.now().toString();String service=health.optString("service","EGM4000");
                prefs.edit().putString("apiBaseUrl",base).putString("serverLastHealthyAt",checkedAt).putString("serverLastService",service).apply();
                runOnUiThread(() -> {status.setText("Server status\nREADY · "+service+"\nSchema: "+schema+"\nVerified: "+checkedAt);continueButton.setEnabled(true);if(announce)Toast.makeText(this,"EGM4000 production service is ready.",Toast.LENGTH_SHORT).show();});
            } catch(Exception ex) {
                runOnUiThread(() -> {status.setText("Server status\nNOT READY\n"+friendly(ex)+"\nOffline evidence logging remains available; sync stays pending.");continueButton.setEnabled(false);});
            }
        });
    }

    private String normalizedUrl() {
        String value=normalize(serverUrl.getText().toString());
        if(!value.startsWith("https://")){Toast.makeText(this,"Use the deployed EGM4000 HTTPS URL.",Toast.LENGTH_SHORT).show();return null;}return value;
    }
    private static String normalize(String value){String out=value==null?"":value.trim();while(out.endsWith("/"))out=out.substring(0,out.length()-1);return out;}
    private void openMain(){String base=normalizedUrl();if(base==null)return;prefs.edit().putString("apiBaseUrl",base).apply();startMain();}
    private void startMain(){startActivity(new Intent(this,MainActivity.class));finish();}
    private TextView text(String value,int sp,int color,boolean bold){TextView tv=new TextView(this);tv.setText(value);tv.setTextSize(sp);tv.setTextColor(color);if(bold)tv.setTypeface(Typeface.DEFAULT_BOLD);tv.setPadding(0,dp(8),0,dp(8));return tv;}
    private TextView card(String value){TextView tv=text(value,14,0xffd7e8f2,false);tv.setBackgroundColor(0xff0c1624);tv.setPadding(dp(12),dp(12),dp(12),dp(12));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,LinearLayout.LayoutParams.WRAP_CONTENT);lp.setMargins(0,dp(8),0,dp(8));tv.setLayoutParams(lp);return tv;}
    private Button button(String value,View.OnClickListener listener){Button b=new Button(this);b.setText(value);b.setAllCaps(false);b.setOnClickListener(listener);return b;}
    private String friendly(Exception ex){String message=ex.getMessage();return message==null||message.trim().isEmpty()?ex.getClass().getSimpleName():message;}
    private int dp(int value){return (int)(value*getResources().getDisplayMetrics().density);}
}
