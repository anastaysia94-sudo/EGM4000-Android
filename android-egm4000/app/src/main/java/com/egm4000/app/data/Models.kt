package com.egm4000.app.data

import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

const val EVENT_SCHEMA = "egm4000.gameplay-event.v1"
const val BUNDLE_SCHEMA = "egm4000.session-bundle.v3"

enum class EvidenceKind(val wire: String) {
    EXACT_TELEMETRY("exact_telemetry"), OBSERVED_EVIDENCE("observed_evidence"), ESTIMATE("estimate"),
    CORRELATION("correlation"), HYPOTHESIS("hypothesis"), UNKNOWN("unknown"),
    USER_RECORDED("user_recorded"), DEVICE_SIGNAL("user_authorized_device_signal");
    companion object { fun fromWire(value: String) = entries.firstOrNull { it.wire == value } ?: UNKNOWN }
}

data class GameplayEvent(
    val id: String = UUID.randomUUID().toString(),
    val type: String,
    val timestampMs: Long = System.currentTimeMillis(),
    val creditDelta: Int = 0,
    val note: String = "",
    val evidence: EvidenceKind = EvidenceKind.USER_RECORDED,
    val confidence: Double = 1.0,
    val payload: Map<String, String> = emptyMap()
)

data class GameplaySession(
    val id: String = UUID.randomUUID().toString(), val platform: String = "Fire Kirin",
    val startedAtMs: Long = System.currentTimeMillis(), val endedAtMs: Long? = null,
    val title: String = "Fire Kirin session", val events: List<GameplayEvent> = emptyList(), val notes: String = ""
)

data class SessionMetrics(
    val events: Int, val shots: Int, val creditIn: Int, val creditOut: Int, val netCredits: Int,
    val durationMinutes: Double, val shotsPerMinute: Double, val estimatedSignals: Int, val exactSignals: Int
)

fun GameplaySession.metrics(nowMs: Long = System.currentTimeMillis()): SessionMetrics {
    val minutes = (((endedAtMs ?: nowMs) - startedAtMs).coerceAtLeast(1L) / 60000.0).coerceAtLeast(1.0 / 60.0)
    val shots = events.count { it.type == "shot" || it.type == "shot_fired" }
    val creditIn = events.sumOf { if (it.creditDelta > 0) it.creditDelta else 0 }
    val creditOut = -events.sumOf { if (it.creditDelta < 0) it.creditDelta else 0 }
    return SessionMetrics(events.size, shots, creditIn, creditOut, creditIn - creditOut, minutes, shots / minutes,
        events.count { it.evidence == EvidenceKind.ESTIMATE || it.evidence == EvidenceKind.DEVICE_SIGNAL },
        events.count { it.evidence == EvidenceKind.EXACT_TELEMETRY })
}

fun GameplaySession.riskFlags(maxMinutes: Int = 45, maxDrawdown: Int = 250, maxShots: Int = 500): List<String> {
    val m = metrics(); return buildList {
        if (m.durationMinutes >= maxMinutes) add("Session length reached ${m.durationMinutes.toInt()} minutes. Consider a break.")
        if (m.netCredits <= -maxDrawdown) add("Recorded credit drawdown reached ${-m.netCredits} credits. Stop and review before continuing.")
        if (m.shots >= maxShots) add("Recorded shot count reached ${m.shots}. Slow down and review pace.")
        if (m.shotsPerMinute > 60 && m.netCredits < 0) add("Shot pace is high while recorded net credits are negative. This is a review signal, not a prediction.")
    }
}

fun GameplaySession.coachingTips(): List<String> {
    val m = metrics(); return buildList {
        if (events.isEmpty()) add("Record a few events or authorize capture signals to unlock evidence-based feedback.")
        if (m.netCredits < 0) add("Recorded credits are down ${-m.netCredits}. Compare the last high-spend segment with your earlier pace before continuing.")
        if (m.shotsPerMinute > 45) add("Your recorded shot pace is ${"%.1f".format(m.shotsPerMinute)}/min. Try a slower interval and compare outcomes rather than chasing losses.")
        if (events.any { it.type == "break" }) add("A break was recorded. Compare metrics before and after the break instead of assuming a causal effect.")
        if (m.estimatedSignals > 0) add("${m.estimatedSignals} signal(s) are estimates/device observations. Treat them as lower-confidence than exact F.S.A. telemetry.")
        if (m.exactSignals > 0) add("${m.exactSignals} event(s) came from exact owned-environment telemetry and can be used as ground truth in validation.")
        add("Correlation is not prediction. EGM4000 explains recorded evidence; it does not know future random outcomes or hidden server state.")
    }
}

fun GameplayEvent.toJson(): JSONObject = JSONObject().apply {
    put("schema", EVENT_SCHEMA); put("eventId", id); put("eventType", type); put("occurredAtMs", timestampMs)
    put("creditDelta", creditDelta); put("note", note); put("evidenceLabel", evidence.wire)
    put("confidence", confidence.coerceIn(0.0, 1.0)); put("payload", JSONObject(payload))
}

fun eventFromJson(o: JSONObject): GameplayEvent = GameplayEvent(
    id = o.optString("eventId", o.optString("id", UUID.randomUUID().toString())),
    type = o.optString("eventType", o.optString("type", "unknown")),
    timestampMs = o.optLong("occurredAtMs", o.optLong("timestampMs", System.currentTimeMillis())),
    creditDelta = o.optInt("creditDelta", 0), note = o.optString("note", ""),
    evidence = EvidenceKind.fromWire(o.optString("evidenceLabel", o.optString("provenance", "unknown"))),
    confidence = o.optDouble("confidence", 0.0).coerceIn(0.0, 1.0),
    payload = o.optJSONObject("payload")?.let { p -> p.keys().asSequence().associateWith { p.optString(it, "") } } ?: emptyMap()
)

fun GameplaySession.toJson(): JSONObject = JSONObject().apply {
    put("sessionId", id); put("platform", platform); put("startedAtMs", startedAtMs); endedAtMs?.let { put("endedAtMs", it) }
    put("title", title); put("notes", notes); put("events", JSONArray().apply { events.forEach { put(it.toJson()) } })
}

fun sessionFromJson(o: JSONObject): GameplaySession {
    val a = o.optJSONArray("events") ?: JSONArray(); val events = buildList { for (i in 0 until a.length()) add(eventFromJson(a.getJSONObject(i))) }
    return GameplaySession(
        id = o.optString("sessionId", o.optString("id", UUID.randomUUID().toString())), platform = o.optString("platform", "Fire Kirin"),
        startedAtMs = o.optLong("startedAtMs", System.currentTimeMillis()), endedAtMs = if (o.has("endedAtMs") && !o.isNull("endedAtMs")) o.optLong("endedAtMs") else null,
        title = o.optString("title", "Gameplay session"), events = events, notes = o.optString("notes", "")
    )
}
