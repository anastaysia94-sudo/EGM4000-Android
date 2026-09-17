package com.egm4000.app.data

import org.json.JSONObject
import java.time.Instant
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException

/**
 * Converts owned Fish Shooter Arcade telemetry into EGM4000 sessions.
 *
 * Security/integrity goals:
 * - only owned F.S.A. envelopes are accepted as exact telemetry;
 * - duplicate event IDs are ignored;
 * - one stable F.S.A. session ID maps to one EGM4000 session;
 * - malformed or out-of-order timestamps are rejected instead of silently trusted;
 * - virtual/non-cash credit semantics are preserved.
 */
object FsaTelemetryIngestor {
    const val SOURCE_PRODUCT = "fsa"
    const val PLATFORM = "Fish Shooter Arcade"

    data class IngestResult(
        val sessions: List<GameplaySession>,
        val accepted: Boolean,
        val duplicate: Boolean = false,
        val reason: String,
        val sessionId: String? = null,
        val eventId: String? = null
    )

    fun ingest(existing: List<GameplaySession>, jsonText: String): IngestResult = runCatching {
        ingest(existing, JSONObject(jsonText))
    }.getOrElse {
        IngestResult(existing, accepted = false, reason = it.message ?: "Invalid F.S.A. telemetry JSON")
    }

    fun ingest(existing: List<GameplaySession>, envelope: JSONObject): IngestResult {
        val schema = envelope.optString("schema")
        if (schema != EVENT_SCHEMA) {
            return IngestResult(existing, false, reason = "Unsupported telemetry schema: $schema")
        }

        val source = envelope.optString("sourceProduct", SOURCE_PRODUCT).lowercase()
        if (source != SOURCE_PRODUCT) {
            return IngestResult(existing, false, reason = "Telemetry source is not owned F.S.A.")
        }

        val sessionId = envelope.optString("sessionId").trim()
        val eventId = envelope.optString("eventId", envelope.optString("id")).trim()
        if (sessionId.isBlank()) return IngestResult(existing, false, reason = "Missing sessionId")
        if (eventId.isBlank()) return IngestResult(existing, false, reason = "Missing eventId", sessionId = sessionId)

        if (existing.asSequence().flatMap { it.events.asSequence() }.any { it.id == eventId }) {
            return IngestResult(existing, accepted = true, duplicate = true, reason = "Duplicate event ignored", sessionId = sessionId, eventId = eventId)
        }

        val eventType = envelope.optString("eventType", envelope.optString("type")).trim()
        if (eventType.isBlank()) return IngestResult(existing, false, reason = "Missing event type", sessionId = sessionId, eventId = eventId)

        val provenance = envelope.optString("evidenceLabel", envelope.optString("provenance")).trim()
        if (provenance != EvidenceKind.EXACT_TELEMETRY.wire) {
            return IngestResult(existing, false, reason = "F.S.A. telemetry must declare exact_telemetry provenance", sessionId = sessionId, eventId = eventId)
        }

        val confidence = envelope.optDouble("confidence", -1.0)
        if (confidence !in 0.0..1.0) {
            return IngestResult(existing, false, reason = "Confidence must be between 0 and 1", sessionId = sessionId, eventId = eventId)
        }

        val timestampMs = parseTimestamp(envelope)
            ?: return IngestResult(existing, false, reason = "Missing or invalid telemetry timestamp", sessionId = sessionId, eventId = eventId)

        val payloadObject = envelope.optJSONObject("payload") ?: JSONObject()
        if (eventType == "credit_changed") {
            val currency = payloadObject.optString("currencyType")
            if (currency.isNotBlank() && currency != "virtual_non_cash_credit") {
                return IngestResult(existing, false, reason = "Only virtual/non-cash F.S.A. credits are accepted", sessionId = sessionId, eventId = eventId)
            }
        }

        val payload = payloadObject.keys().asSequence().associateWith { key -> payloadObject.opt(key)?.toString().orEmpty() }
        val creditDelta = when {
            envelope.has("creditDelta") -> envelope.optInt("creditDelta", 0)
            eventType == "credit_changed" -> payloadObject.optInt("delta", 0)
            else -> 0
        }

        val event = GameplayEvent(
            id = eventId,
            type = eventType,
            timestampMs = timestampMs,
            creditDelta = creditDelta,
            note = envelope.optString("note"),
            evidence = EvidenceKind.EXACT_TELEMETRY,
            confidence = confidence,
            payload = payload + mapOf("sourceProduct" to SOURCE_PRODUCT, "sessionId" to sessionId)
        )

        val index = existing.indexOfFirst { it.id == sessionId }
        val current = if (index >= 0) existing[index] else GameplaySession(
            id = sessionId,
            platform = "F.S.A.",
            startedAtMs = timestampMs,
            title = "F.S.A. exact telemetry session",
            notes = "Owned Fish Shooter Arcade exact telemetry. Virtual/non-cash by default."
        )

        if (current.platform != "F.S.A." && current.platform != PLATFORM) {
            return IngestResult(existing, false, reason = "Session ID belongs to another platform", sessionId = sessionId, eventId = eventId)
        }

        val latestTimestamp = current.events.maxOfOrNull { it.timestampMs }
        if (latestTimestamp != null && timestampMs < latestTimestamp) {
            return IngestResult(existing, false, reason = "Out-of-order F.S.A. timestamp rejected", sessionId = sessionId, eventId = eventId)
        }

        var updated = current.copy(events = current.events + event)
        if (eventType == "session_started") {
            updated = updated.copy(startedAtMs = timestampMs, endedAtMs = null)
        } else if (eventType == "session_ended") {
            updated = updated.copy(endedAtMs = timestampMs)
        }

        val result = if (index >= 0) existing.toMutableList().also { it[index] = updated }.toList() else existing + updated
        return IngestResult(result, true, reason = "Exact F.S.A. telemetry accepted", sessionId = sessionId, eventId = eventId)
    }

    private fun parseTimestamp(envelope: JSONObject): Long? {
        if (envelope.has("occurredAtMs")) {
            val value = envelope.optLong("occurredAtMs", -1L)
            if (value >= 0L) return value
        }
        val raw = envelope.optString("occurredAt", envelope.optString("time")).trim()
        if (raw.isBlank()) return null
        return try {
            OffsetDateTime.parse(raw).toInstant().toEpochMilli()
        } catch (_: DateTimeParseException) {
            try { Instant.parse(raw).toEpochMilli() } catch (_: DateTimeParseException) { null }
        }
    }
}
