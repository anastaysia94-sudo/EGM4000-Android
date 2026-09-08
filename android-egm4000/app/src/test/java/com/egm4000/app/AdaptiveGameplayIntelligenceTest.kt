package com.egm4000.app

import com.egm4000.app.data.AdaptiveGameplayIntelligence
import com.egm4000.app.data.EvidenceKind
import com.egm4000.app.data.GameplayEvent
import com.egm4000.app.data.GameplaySession
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AdaptiveGameplayIntelligenceTest {

    @Test
    fun supportsFsaAndSixExternalPlatforms() {
        assertEquals(
            listOf("F.S.A.", "Fire Kirin", "Juwa", "Game Master", "Panda Master", "GameRoom", "Orion Stars"),
            AdaptiveGameplayIntelligence.supportedPlatforms
        )
    }

    @Test
    fun learnsPlatformSpecificTransitionsWithoutCrossContamination() {
        val fireEvents = (0 until 12).flatMap { index ->
            listOf(
                GameplayEvent(type = "target_activity_estimate", timestampMs = 1_000L + index * 20L, evidence = EvidenceKind.DEVICE_SIGNAL, confidence = .8),
                GameplayEvent(type = "shot_activity_estimate", timestampMs = 1_010L + index * 20L, evidence = EvidenceKind.DEVICE_SIGNAL, confidence = .8)
            )
        }
        val fsaEvents = listOf(
            GameplayEvent(type = "exact_target", timestampMs = 10L, evidence = EvidenceKind.EXACT_TELEMETRY),
            GameplayEvent(type = "exact_hit", timestampMs = 20L, evidence = EvidenceKind.EXACT_TELEMETRY)
        )
        val sessions = listOf(
            GameplaySession(platform = "Fire Kirin", startedAtMs = 1L, endedAtMs = 5_000L, events = fireEvents),
            GameplaySession(platform = "F.S.A.", startedAtMs = 1L, endedAtMs = 5_000L, events = fsaEvents)
        )

        val fire = AdaptiveGameplayIntelligence.learn(sessions, "Fire Kirin")
        val fsa = AdaptiveGameplayIntelligence.learn(sessions, "F.S.A.")

        assertTrue((fire.transitionProbabilities["target_activity_estimate->shot_activity_estimate"] ?: 0.0) > .9)
        assertTrue(fsa.exactTelemetryShare > .99)
        assertEquals(2, fsa.totalEvents)
        assertEquals(24, fire.totalEvents)
    }

    @Test
    fun confidenceGrowsWithMoreHighQualityEvidence() {
        val small = GameplaySession(
            platform = "F.S.A.",
            events = listOf(GameplayEvent(type = "shot", evidence = EvidenceKind.EXACT_TELEMETRY, confidence = 1.0))
        )
        val many = GameplaySession(
            platform = "F.S.A.",
            events = (0 until 150).map { GameplayEvent(type = if (it % 2 == 0) "shot" else "hit", timestampMs = it.toLong(), evidence = EvidenceKind.EXACT_TELEMETRY, confidence = 1.0) }
        )

        val c1 = AdaptiveGameplayIntelligence.learn(listOf(small), "F.S.A.").evidenceConfidence
        val c2 = AdaptiveGameplayIntelligence.learn(listOf(many), "F.S.A.").evidenceConfidence
        assertTrue(c2 > c1)
        assertTrue(c2 <= .95)
    }

    @Test
    fun forecastsRemainExplicitlyProbabilistic() {
        val events = (0 until 10).flatMap { index ->
            listOf(
                GameplayEvent(type = "round_transition", timestampMs = (index * 2).toLong(), evidence = EvidenceKind.EXACT_TELEMETRY),
                GameplayEvent(type = "target_activity", timestampMs = (index * 2 + 1).toLong(), evidence = EvidenceKind.EXACT_TELEMETRY)
            )
        }
        val session = GameplaySession(platform = "F.S.A.", events = events)
        val analysis = AdaptiveGameplayIntelligence.analyze(listOf(session), "F.S.A.", session, AdaptiveGameplayIntelligence.Phase.DURING)

        assertTrue(analysis.forecasts.isNotEmpty())
        assertTrue(analysis.forecasts.all { it.confidence in 0.0..0.95 })
        assertTrue(analysis.advice.any { it.title == "Prediction boundary" })
        assertTrue(analysis.advice.last().text.contains("cannot know hidden provider state", ignoreCase = true))
    }
}
