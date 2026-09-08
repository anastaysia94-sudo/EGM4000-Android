package com.egm4000.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ProviderVisualAdaptersTest {
    @Test
    fun everySupportedProviderHasDedicatedProfile() {
        val ids = listOf("fire_kirin", "juwa", "game_master", "panda_master", "gameroom", "orion_stars")
        ids.forEach { id -> assertEquals(id, ProviderVisualAdapters.profile(id).id) }
    }

    @Test
    fun highWeaponMotionCreatesConfidenceLabelledShotEstimate() {
        val profile = ProviderVisualAdapters.profile("fire_kirin")
        val state = AdapterRuntimeState()
        val frame = VisualFrameObservations(
            overall = RegionObservation(.45, .05),
            credit = RegionObservation(.40, .01),
            weapon = RegionObservation(.50, .14),
            target = RegionObservation(.45, .03),
            bonus = RegionObservation(.44, .02),
            timestampMs = 10_000L
        )
        val output = ProviderVisualAdapters.analyze(profile, frame, state, 1_000L)
        val event = output.events.firstOrNull { it.type == "shot_activity_estimate" }
        assertTrue(event != null)
        assertTrue(event!!.confidence in 0.0..1.0)
        assertTrue(output.shotRateEstimate >= 1.0)
    }

    @Test
    fun numericValuesAreNotInventedFromHudMotion() {
        val profile = ProviderVisualAdapters.profile("panda_master")
        val state = AdapterRuntimeState()
        val frame = VisualFrameObservations(
            overall = RegionObservation(.48, .05),
            credit = RegionObservation(.55, .10),
            weapon = RegionObservation(.45, .01),
            target = RegionObservation(.40, .02),
            bonus = RegionObservation(.42, .02),
            timestampMs = 20_000L
        )
        val output = ProviderVisualAdapters.analyze(profile, frame, state, 1_000L)
        val creditEvent = output.events.firstOrNull { it.type == "credit_hud_changed" }
        assertTrue(creditEvent != null)
        assertTrue(creditEvent!!.payload["credits"] == null)
        assertTrue(creditEvent.note.contains("Numeric credit value is intentionally not inferred"))
    }
}
