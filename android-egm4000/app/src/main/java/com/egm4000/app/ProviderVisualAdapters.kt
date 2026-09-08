package com.egm4000.app

import kotlin.math.max

/**
 * Confidence-aware visual adapter layer for third-party game observation.
 *
 * Adapters operate only on user-authorized pixels. They deliberately emit
 * visual observations/estimates, not hidden server state. Numeric credits or
 * weapon levels must never be invented: until a numeric extractor is
 * calibrated and confident, adapters report HUD change/activity only.
 */
data class NormalizedRoi(
    val left: Double,
    val top: Double,
    val right: Double,
    val bottom: Double
) {
    init {
        require(left in 0.0..1.0 && right in 0.0..1.0 && top in 0.0..1.0 && bottom in 0.0..1.0)
        require(right > left && bottom > top)
    }
}

data class AdapterProfile(
    val id: String,
    val displayName: String,
    val creditHud: NormalizedRoi,
    val weaponHud: NormalizedRoi,
    val targetField: NormalizedRoi,
    val bonusRegion: NormalizedRoi,
    val shotMotionThreshold: Double,
    val targetMotionThreshold: Double,
    val transitionMotionThreshold: Double
)

data class RegionObservation(val brightness: Double, val motion: Double)

data class VisualFrameObservations(
    val overall: RegionObservation,
    val credit: RegionObservation,
    val weapon: RegionObservation,
    val target: RegionObservation,
    val bonus: RegionObservation,
    val timestampMs: Long
)

data class AdapterEvent(
    val type: String,
    val confidence: Double,
    val note: String,
    val payload: Map<String, String> = emptyMap()
)

data class AdapterOutput(
    val events: List<AdapterEvent>,
    val tip: String,
    val shotRateEstimate: Double,
    val targetActivity: Double,
    val qualityConfidence: Double
)

class AdapterRuntimeState {
    val shotBursts = ArrayDeque<Long>()
    val lastEventAt = mutableMapOf<String, Long>()
    var lastMinuteMarker = -1L
}

object ProviderVisualAdapters {
    private val profiles = listOf(
        AdapterProfile("fire_kirin", "Fire Kirin", NormalizedRoi(.00,.00,.42,.18), NormalizedRoi(.56,.72,1.0,1.0), NormalizedRoi(.12,.16,.90,.78), NormalizedRoi(.18,.02,.82,.30), .070,.038,.105),
        AdapterProfile("juwa", "Juwa", NormalizedRoi(.00,.00,.45,.20), NormalizedRoi(.55,.70,1.0,1.0), NormalizedRoi(.10,.17,.92,.79), NormalizedRoi(.16,.02,.84,.32), .068,.040,.102),
        AdapterProfile("game_master", "Game Master", NormalizedRoi(.00,.00,.46,.20), NormalizedRoi(.54,.69,1.0,1.0), NormalizedRoi(.10,.16,.92,.80), NormalizedRoi(.14,.02,.86,.31), .072,.040,.108),
        AdapterProfile("panda_master", "Panda Master", NormalizedRoi(.00,.00,.44,.19), NormalizedRoi(.56,.70,1.0,1.0), NormalizedRoi(.10,.16,.91,.79), NormalizedRoi(.16,.02,.84,.31), .070,.039,.104),
        AdapterProfile("gameroom", "GameRoom", NormalizedRoi(.00,.00,.45,.19), NormalizedRoi(.55,.70,1.0,1.0), NormalizedRoi(.10,.16,.92,.80), NormalizedRoi(.15,.02,.85,.32), .071,.041,.106),
        AdapterProfile("orion_stars", "Orion Stars", NormalizedRoi(.00,.00,.43,.19), NormalizedRoi(.57,.70,1.0,1.0), NormalizedRoi(.09,.16,.92,.80), NormalizedRoi(.15,.02,.85,.31), .069,.039,.103)
    ).associateBy { it.id }

    fun profile(providerId: String): AdapterProfile = profiles[providerId] ?: profiles.getValue("fire_kirin")

    fun analyze(
        profile: AdapterProfile,
        frame: VisualFrameObservations,
        state: AdapterRuntimeState,
        captureStartedAtMs: Long
    ): AdapterOutput {
        val now = frame.timestampMs
        val events = mutableListOf<AdapterEvent>()

        val brightnessQuality = when {
            frame.overall.brightness < .08 -> .30
            frame.overall.brightness < .16 -> .58
            frame.overall.brightness > .94 -> .52
            else -> .90
        }
        val motionQuality = if (frame.overall.motion > .45) .62 else .94
        val quality = (brightnessQuality * motionQuality).coerceIn(.20, .96)

        fun allowed(key: String, cooldownMs: Long): Boolean {
            val last = state.lastEventAt[key] ?: 0L
            if (now - last < cooldownMs) return false
            state.lastEventAt[key] = now
            return true
        }

        if (frame.weapon.motion >= profile.shotMotionThreshold && allowed("shot", 180)) {
            state.shotBursts.addLast(now)
            events += AdapterEvent(
                "shot_activity_estimate",
                (quality * .74).coerceIn(.25, .88),
                "Weapon-area motion burst observed; this is an estimated shot/input signal.",
                mapOf("provider" to profile.id, "weaponRegionMotion" to "%.4f".format(frame.weapon.motion))
            )
        }
        while (state.shotBursts.isNotEmpty() && now - state.shotBursts.first() > 60_000L) state.shotBursts.removeFirst()
        val shotRate = state.shotBursts.size.toDouble()

        if (frame.target.motion >= profile.targetMotionThreshold && allowed("target", 900)) {
            events += AdapterEvent(
                "target_activity_estimate",
                (quality * .78).coerceIn(.28, .90),
                "Elevated movement detected in the provider-specific target field.",
                mapOf("provider" to profile.id, "activity" to "%.4f".format(frame.target.motion))
            )
        }

        if (frame.credit.motion >= profile.transitionMotionThreshold * .55 && allowed("credit", 1400)) {
            events += AdapterEvent(
                "credit_hud_changed",
                (quality * .64).coerceIn(.22, .78),
                "Visible credit-HUD region changed. Numeric credit value is intentionally not inferred without a validated numeric extractor.",
                mapOf("provider" to profile.id, "hudMotion" to "%.4f".format(frame.credit.motion))
            )
        }

        if (frame.weapon.motion >= profile.transitionMotionThreshold * 1.35 && frame.overall.motion < .20 && allowed("weapon_change", 2200)) {
            events += AdapterEvent(
                "weapon_hud_changed",
                (quality * .58).coerceIn(.20, .72),
                "Weapon-control HUD changed independently of broad scene motion. Exact weapon level is not asserted without validated text/icon recognition.",
                mapOf("provider" to profile.id)
            )
        }

        val transitionScore = max(frame.bonus.motion, frame.overall.motion)
        if (frame.bonus.motion >= profile.transitionMotionThreshold && transitionScore >= .10 && allowed("bonus", 2600)) {
            events += AdapterEvent(
                "bonus_or_round_transition_estimate",
                (quality * .70).coerceIn(.24, .84),
                "Large change detected in the provider-specific bonus/round region.",
                mapOf("provider" to profile.id, "transitionScore" to "%.4f".format(transitionScore))
            )
        }

        val elapsedMinutes = ((now - captureStartedAtMs).coerceAtLeast(0L) / 60_000L)
        if (elapsedMinutes > 0 && elapsedMinutes != state.lastMinuteMarker) {
            state.lastMinuteMarker = elapsedMinutes
            events += AdapterEvent(
                "session_duration_observed",
                .99,
                "Authorized capture session duration reached $elapsedMinutes minute(s).",
                mapOf("minutes" to elapsedMinutes.toString(), "provider" to profile.id)
            )
        }

        val tip = when {
            quality < .50 -> "Capture confidence is low. Keep the full gameplay HUD visible and avoid overlays before acting on visual estimates."
            shotRate >= 45 && frame.target.motion < profile.targetMotionThreshold -> "Estimated input pace is high while visible target activity is comparatively low. Slow the pace and compare a controlled segment instead of chasing short-term outcomes."
            shotRate >= 30 -> "Input activity is elevated. Use a fixed short observation window, keep spend pace controlled, and compare the result with your saved baseline."
            frame.target.motion >= profile.targetMotionThreshold * 1.8 -> "Target-field activity is high. Keep inputs deliberate and record the segment; high activity is not evidence of a future payout."
            events.any { it.type == "bonus_or_round_transition_estimate" } -> "Possible round/bonus transition detected. Record the transition and compare before/after metrics rather than assuming it predicts the next outcome."
            else -> "Scene is stable enough for observation. Keep a consistent pace and build a longer evidence window before changing strategy."
        }

        return AdapterOutput(events, tip, shotRate, frame.target.motion, quality)
    }
}
