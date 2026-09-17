package com.egm4000.app

import com.egm4000.app.data.EvidenceKind
import com.egm4000.app.data.FsaTelemetryIngestor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FsaTelemetryIngestorTest {
    private fun envelope(
        eventId: String,
        type: String,
        at: String,
        payload: String = "{}"
    ) = """
        {
          "schema":"egm4000.gameplay-event.v1",
          "sourceProduct":"fsa",
          "sessionId":"fsa-session-1",
          "eventId":"$eventId",
          "platform":"Fish Shooter Arcade",
          "eventType":"$type",
          "occurredAt":"$at",
          "evidenceLabel":"exact_telemetry",
          "confidence":1.0,
          "payload":$payload
        }
    """.trimIndent()

    @Test
    fun `creates session and preserves exact provenance`() {
        val result = FsaTelemetryIngestor.ingest(
            emptyList(),
            envelope("evt-1", "session_started", "2026-09-16T20:00:00-07:00")
        )
        assertTrue(result.accepted)
        assertFalse(result.duplicate)
        assertEquals(1, result.sessions.size)
        assertEquals("fsa-session-1", result.sessions.single().id)
        assertEquals("F.S.A.", result.sessions.single().platform)
        assertEquals(EvidenceKind.EXACT_TELEMETRY, result.sessions.single().events.single().evidence)
    }

    @Test
    fun `deduplicates by event id`() {
        val first = FsaTelemetryIngestor.ingest(
            emptyList(),
            envelope("evt-1", "session_started", "2026-09-16T20:00:00-07:00")
        )
        val second = FsaTelemetryIngestor.ingest(
            first.sessions,
            envelope("evt-1", "session_started", "2026-09-16T20:00:00-07:00")
        )
        assertTrue(second.accepted)
        assertTrue(second.duplicate)
        assertEquals(1, second.sessions.single().events.size)
    }

    @Test
    fun `maps exact credit delta and closes session`() {
        var sessions = FsaTelemetryIngestor.ingest(
            emptyList(), envelope("evt-1", "session_started", "2026-09-16T20:00:00-07:00")
        ).sessions
        sessions = FsaTelemetryIngestor.ingest(
            sessions,
            envelope(
                "evt-2", "credit_changed", "2026-09-16T20:01:00-07:00",
                "{\"currencyType\":\"virtual_non_cash_credit\",\"delta\":-5,\"balanceAfter\":940}"
            )
        ).sessions
        val ended = FsaTelemetryIngestor.ingest(
            sessions, envelope("evt-3", "session_ended", "2026-09-16T20:02:00-07:00")
        )
        assertTrue(ended.accepted)
        assertEquals(-5, ended.sessions.single().events[1].creditDelta)
        assertTrue(ended.sessions.single().endedAtMs != null)
    }

    @Test
    fun `rejects wrong provenance and noncash violations`() {
        val wrongEvidence = envelope("evt-1", "shot_fired", "2026-09-16T20:00:00-07:00")
            .replace("exact_telemetry", "estimate")
        assertFalse(FsaTelemetryIngestor.ingest(emptyList(), wrongEvidence).accepted)

        val cashLike = envelope(
            "evt-2", "credit_changed", "2026-09-16T20:00:00-07:00",
            "{\"currencyType\":\"redeemable_cash\",\"delta\":10}"
        )
        assertFalse(FsaTelemetryIngestor.ingest(emptyList(), cashLike).accepted)
    }

    @Test
    fun `rejects out of order event timestamps`() {
        val first = FsaTelemetryIngestor.ingest(
            emptyList(), envelope("evt-1", "session_started", "2026-09-16T20:05:00-07:00")
        )
        val older = FsaTelemetryIngestor.ingest(
            first.sessions, envelope("evt-2", "shot_fired", "2026-09-16T20:04:00-07:00")
        )
        assertFalse(older.accepted)
        assertEquals(1, older.sessions.single().events.size)
    }
}
