package com.smartpickshop.egm4000;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

public final class SessionStore {
    public static final String[] FILTER_LABELS = {"All events", "Shots", "Credit changes", "Capture events", "Breaks", "Warnings"};
    private static final String PREFS = "egm4000";
    private final SharedPreferences prefs;

    public SessionStore(Context context) { prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE); }

    public SharedPreferences prefs() { return prefs; }

    public JSONArray events() {
        try { return new JSONArray(prefs.getString("events", "[]")); }
        catch (Exception ex) { return new JSONArray(); }
    }

    public void startFreshSession() {
        long now = System.currentTimeMillis();
        prefs.edit().putString("events", "[]")
                .putLong("sessionStartedAtEpoch", now)
                .putString("sessionStartedAt", stamp(now))
                .remove("sessionEndedAt")
                .putInt("syncedEventCount", 0)
                .apply();
    }

    public void ensureStarted() {
        if (prefs.getLong("sessionStartedAtEpoch", 0) == 0) {
            long now = System.currentTimeMillis();
            prefs.edit().putLong("sessionStartedAtEpoch", now).putString("sessionStartedAt", stamp(now)).apply();
        }
    }

    public void endSession() {
        ensureStarted();
        prefs.edit().putString("sessionEndedAt", stamp(System.currentTimeMillis())).apply();
        add("session_ended", 0, "Session ended by user.", "user_recorded", 1.0, null);
    }

    public void add(String type, int creditDelta, String note, String provenance, double confidence, String warningCode) {
        ensureStarted();
        try {
            JSONArray arr = events();
            JSONObject e = new JSONObject();
            e.put("schema", "egm4000.gameplay-event.v1");
            e.put("eventId", UUID.randomUUID().toString());
            e.put("platform", "Fire Kirin");
            e.put("type", type);
            e.put("creditDelta", creditDelta);
            e.put("note", note == null ? "" : note.trim());
            e.put("provenance", provenance);
            e.put("confidence", confidence);
            long epoch = System.currentTimeMillis();
            e.put("time", stamp(epoch));
            e.put("timeEpoch", epoch);
            if (warningCode != null) e.put("warningCode", warningCode);
            arr.put(e);
            save(arr);
            if (!"warning".equals(type)) evaluateWarnings(arr);
        } catch (Exception ignored) { }
    }

    private void save(JSONArray arr) { prefs.edit().putString("events", arr.toString()).apply(); }

    private void evaluateWarnings(JSONArray arr) {
        try {
            int net = 0, downs = 0, breaks = 0;
            List<Long> shots = new ArrayList<>();
            for (int i = 0; i < arr.length(); i++) {
                JSONObject e = arr.optJSONObject(i); if (e == null) continue;
                String t = e.optString("type"); net += e.optInt("creditDelta", 0);
                if ("credit_down".equals(t)) downs++;
                if ("break".equals(t)) breaks++;
                if ("shot".equals(t)) shots.add(e.optLong("timeEpoch", 0));
            }
            long start = prefs.getLong("sessionStartedAtEpoch", System.currentTimeMillis());
            long durationMin = Math.max(0, (System.currentTimeMillis() - start) / 60000L);
            if (downs >= 3) addWarningOnce(arr, "repeated_credit_down", "Repeated credit-down entries: review the session before increasing pace or spend.", .85);
            if (durationMin >= 60) addWarningOnce(arr, "long_session", "Session has passed 60 minutes. Consider a break and review your evidence.", .95);
            if (durationMin >= 45 && breaks == 0) addWarningOnce(arr, "no_break", "No break has been logged in 45+ minutes.", .95);
            if (net < 0 && shots.size() >= 8 && recentPaceRising(shots)) addWarningOnce(arr, "pace_up_credits_down", "Shot pace appears to be rising while recorded credits are down. Slow down and review replay evidence.", .70);
        } catch (Exception ignored) { }
    }

    private void addWarningOnce(JSONArray arr, String code, String message, double confidence) throws Exception {
        for (int i = 0; i < arr.length(); i++) if (code.equals(arr.optJSONObject(i) == null ? "" : arr.optJSONObject(i).optString("warningCode"))) return;
        JSONObject e = new JSONObject(); long epoch = System.currentTimeMillis();
        e.put("schema", "egm4000.gameplay-event.v1"); e.put("eventId", UUID.randomUUID().toString()); e.put("platform", "Fire Kirin"); e.put("type", "warning"); e.put("creditDelta", 0); e.put("note", message); e.put("provenance", "hypothesis"); e.put("confidence", confidence); e.put("time", stamp(epoch)); e.put("timeEpoch", epoch); e.put("warningCode", code); arr.put(e); save(arr);
    }

    private boolean recentPaceRising(List<Long> shots) {
        int mid = shots.size() / 2;
        double first = rate(shots.subList(0, mid));
        double second = rate(shots.subList(mid, shots.size()));
        return first > 0 && second > first * 1.25;
    }

    private double rate(List<Long> times) {
        if (times.size() < 2) return 0;
        long span = Math.max(1000L, times.get(times.size() - 1) - times.get(0));
        return (times.size() - 1) * 60000.0 / span;
    }

    public JSONObject exportPackage() throws Exception {
        JSONObject out = new JSONObject();
        out.put("schema", "egm4000.android-session.v0.2");
        out.put("exportedAt", stamp(System.currentTimeMillis()));
        out.put("platform", "Fire Kirin");
        out.put("sessionStartedAt", prefs.getString("sessionStartedAt", ""));
        out.put("sessionEndedAt", prefs.getString("sessionEndedAt", ""));
        out.put("events", events());
        return out;
    }

    public int importPackage(String raw) throws Exception {
        String text = raw == null ? "" : raw.trim();
        if (text.isEmpty()) throw new IllegalArgumentException("Paste JSON first.");
        JSONArray incoming;
        String started = "", ended = "";
        if (text.startsWith("[")) incoming = new JSONArray(text);
        else {
            JSONObject obj = new JSONObject(text);
            incoming = obj.optJSONArray("events");
            if (incoming == null) throw new IllegalArgumentException("JSON object must contain an events array.");
            started = obj.optString("sessionStartedAt", ""); ended = obj.optString("sessionEndedAt", "");
        }
        JSONArray clean = new JSONArray();
        for (int i = 0; i < incoming.length() && i < 1000; i++) {
            JSONObject e = incoming.optJSONObject(i); if (e == null) continue;
            String type = e.optString("type", "").trim(); String time = e.optString("time", "").trim(); String provenance = e.optString("provenance", "").trim();
            double confidence = e.optDouble("confidence", -1);
            if (type.isEmpty() || time.isEmpty() || provenance.isEmpty() || confidence < 0 || confidence > 1) continue;
            if (!e.has("schema")) e.put("schema", "egm4000.gameplay-event.v1");
            if (!e.has("eventId")) e.put("eventId", UUID.randomUUID().toString());
            clean.put(e);
        }
        if (clean.length() == 0) throw new IllegalArgumentException("No valid EGM4000 events found.");
        SharedPreferences.Editor edit = prefs.edit().putString("events", clean.toString()).putInt("syncedEventCount", 0);
        long now = System.currentTimeMillis();
        edit.putLong("sessionStartedAtEpoch", now).putString("sessionStartedAt", started.isEmpty() ? stamp(now) : started);
        if (ended.isEmpty()) edit.remove("sessionEndedAt"); else edit.putString("sessionEndedAt", ended);
        edit.apply();
        return clean.length();
    }

    public JSONArray unsyncedEvents() {
        JSONArray arr = events(); JSONArray out = new JSONArray(); int start = Math.max(0, prefs.getInt("syncedEventCount", 0));
        for (int i = start; i < arr.length(); i++) out.put(arr.opt(i));
        return out;
    }

    public void markSyncedAll() { prefs.edit().putInt("syncedEventCount", events().length()).putString("lastSyncedAt", stamp(System.currentTimeMillis())).apply(); }

    public Summary summary() {
        JSONArray arr = events(); int shots = 0, net = 0, downs = 0, breaks = 0, warnings = 0;
        for (int i = 0; i < arr.length(); i++) {
            JSONObject e = arr.optJSONObject(i); if (e == null) continue; String t = e.optString("type");
            if ("shot".equals(t)) shots++; if ("credit_down".equals(t)) downs++; if ("break".equals(t)) breaks++; if ("warning".equals(t)) warnings++; net += e.optInt("creditDelta", 0);
        }
        long start = prefs.getLong("sessionStartedAtEpoch", 0); long elapsedMs = start == 0 ? 0 : Math.max(0, System.currentTimeMillis() - start); double minutes = elapsedMs / 60000.0; double pace = minutes > .25 ? shots / minutes : 0;
        return new Summary(arr.length(), shots, net, downs, breaks, warnings, minutes, pace, prefs.getString("sessionStartedAt", "Not started"), prefs.getString("sessionEndedAt", "Active / not ended"));
    }

    public JSONArray filtered(String label) {
        JSONArray src = events(), out = new JSONArray();
        for (int i = 0; i < src.length(); i++) {
            JSONObject e = src.optJSONObject(i); if (e == null) continue; String type = e.optString("type"); boolean include;
            switch (label) {
                case "Shots": include = "shot".equals(type); break;
                case "Credit changes": include = type.startsWith("credit_"); break;
                case "Capture events": include = type.startsWith("screen_"); break;
                case "Breaks": include = "break".equals(type); break;
                case "Warnings": include = "warning".equals(type); break;
                default: include = true;
            }
            if (include) out.put(e);
        }
        return out;
    }

    private static String stamp(long epoch) { return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date(epoch)); }

    public static final class Summary {
        public final int events, shots, netCredits, creditDowns, breaks, warnings;
        public final double durationMinutes, shotPace;
        public final String startedAt, endedAt;
        Summary(int events, int shots, int netCredits, int creditDowns, int breaks, int warnings, double durationMinutes, double shotPace, String startedAt, String endedAt) {
            this.events=events;this.shots=shots;this.netCredits=netCredits;this.creditDowns=creditDowns;this.breaks=breaks;this.warnings=warnings;this.durationMinutes=durationMinutes;this.shotPace=shotPace;this.startedAt=startedAt;this.endedAt=endedAt;
        }
    }
}
