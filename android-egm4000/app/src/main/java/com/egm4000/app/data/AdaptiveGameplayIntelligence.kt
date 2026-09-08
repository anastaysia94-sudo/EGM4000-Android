package com.egm4000.app.data

import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * AdaptiveGameplayIntelligence is EGM4000's evidence-aware learning layer.
 *
 * It learns from the growing local session corpus every time an analysis is requested.
 * F.S.A. exact telemetry is weighted more heavily than user-authorized visual observations
 * from third-party platforms. It never claims access to hidden provider state and never
 * represents probabilistic forecasts as guaranteed outcomes.
 */
object AdaptiveGameplayIntelligence {

    val supportedPlatforms = listOf(
        "F.S.A.",
        "Fire Kirin",
        "Juwa",
        "Game Master",
        "Panda Master",
        "GameRoom",
        "Orion Stars"
    )

    enum class Phase { BEFORE, DURING, AFTER }

    data class LearnedProfile(
        val platform: String,
        val completedSessions: Int,
        val totalEvents: Int,
        val weightedEvidence: Double,
        val averageDurationMinutes: Double,
        val averageShotsPerMinute: Double,
        val averageNetCredits: Double,
        val netCreditsStdDev: Double,
        val transitionProbabilities: Map<String, Double>,
        val evidenceConfidence: Double,
        val exactTelemetryShare: Double,
        val observedEvidenceShare: Double
    )

    data class Forecast(
        val title: String,
        val description: String,
        val confidence: Double,
        val evidenceLabel: EvidenceKind,
        val horizon: String,
        val caveat: String
    )

    data class Advice(
        val phase: Phase,
        val title: String,
        val text: String,
        val confidence: Double,
        val evidenceLabel: EvidenceKind,
        val why: String
    )

    data class Analysis(
        val platform: String,
        val profile: LearnedProfile,
        val forecasts: List<Forecast>,
        val advice: List<Advice>,
        val modelSummary: String
    )

    fun analyze(
        allSessions: List<GameplaySession>,
        platform: String,
        activeSession: GameplaySession? = allSessions.lastOrNull { normalizePlatform(it.platform) == normalizePlatform(platform) },
        phase: Phase = if (activeSession?.endedAtMs == null) Phase.DURING else Phase.AFTER
    ): Analysis {
        val profile = learn(allSessions, platform)
        val forecasts = forecast(profile, activeSession)
        val advice = advice(profile, activeSession, phase)
        val platformSessions = allSessions.count { normalizePlatform(it.platform) == normalizePlatform(platform) }
        val summary = if (platformSessions == 0) {
            "No prior $platform sessions are available yet. EGM4000 is using conservative defaults until real evidence accumulates."
        } else {
            "Learned from $platformSessions $platform session(s), ${profile.totalEvents} event(s), with ${(profile.evidenceConfidence * 100).toInt()}% evidence confidence. The model automatically recalculates as more sessions are saved."
        }
        return Analysis(platform, profile, forecasts, advice, summary)
    }

    fun learn(allSessions: List<GameplaySession>, platform: String): LearnedProfile {
        val sessions = allSessions.filter { normalizePlatform(it.platform) == normalizePlatform(platform) }
        val completed = sessions.filter { it.endedAtMs != null }
        val usable = if (completed.isNotEmpty()) completed else sessions
        val metrics = usable.map { it.metrics() }
        val events = sessions.flatMap { it.events }

        val avgDuration = metrics.map { it.durationMinutes }.averageOrZero()
        val avgPace = metrics.map { it.shotsPerMinute }.averageOrZero()
        val avgNet = metrics.map { it.netCredits.toDouble() }.averageOrZero()
        val variance = if (metrics.size >= 2) metrics.map { (it.netCredits - avgNet) * (it.netCredits - avgNet) }.average() else 0.0
        val stdDev = sqrt(max(0.0, variance))

        val weightedEvidence = events.sumOf { evidenceWeight(it.evidence) * it.confidence.coerceIn(0.0, 1.0) }
        val maxWeight = events.sumOf { evidenceWeight(it.evidence) }.coerceAtLeast(1.0)
        val quality = (weightedEvidence / maxWeight).coerceIn(0.0, 1.0)
        val sampleFactor = (1.0 - kotlin.math.exp(-events.size / 120.0)).coerceIn(0.0, 1.0)
        val confidence = (quality * 0.65 + sampleFactor * 0.35).coerceIn(0.0, 0.95)

        val exact = events.count { it.evidence == EvidenceKind.EXACT_TELEMETRY }.toDouble()
        val observed = events.count {
            it.evidence == EvidenceKind.OBSERVED_EVIDENCE ||
                it.evidence == EvidenceKind.DEVICE_SIGNAL ||
                it.evidence == EvidenceKind.ESTIMATE
        }.toDouble()
        val denom = events.size.toDouble().coerceAtLeast(1.0)

        val transitions = mutableMapOf<String, MutableMap<String, Double>>()
        sessions.forEach { session ->
            session.events.sortedBy { it.timestampMs }.zipWithNext().forEach { (a, b) ->
                val from = a.type.ifBlank { "unknown" }
                val to = b.type.ifBlank { "unknown" }
                val weight = min(evidenceWeight(a.evidence), evidenceWeight(b.evidence)) *
                    min(a.confidence, b.confidence).coerceIn(0.05, 1.0)
                transitions.getOrPut(from) { mutableMapOf() }[to] =
                    (transitions[from]?.get(to) ?: 0.0) + weight
            }
        }

        val flattened = mutableMapOf<String, Double>()
        transitions.forEach { (from, nexts) ->
            val total = nexts.values.sum().coerceAtLeast(0.0001)
            nexts.forEach { (to, score) -> flattened["$from->$to"] = score / total }
        }

        return LearnedProfile(
            platform = platform,
            completedSessions = completed.size,
            totalEvents = events.size,
            weightedEvidence = weightedEvidence,
            averageDurationMinutes = avgDuration,
            averageShotsPerMinute = avgPace,
            averageNetCredits = avgNet,
            netCreditsStdDev = stdDev,
            transitionProbabilities = flattened,
            evidenceConfidence = confidence,
            exactTelemetryShare = exact / denom,
            observedEvidenceShare = observed / denom
        )
    }

    private fun forecast(profile: LearnedProfile, active: GameplaySession?): List<Forecast> = buildList {
        val session = active
        if (profile.totalEvents < 8) {
            add(Forecast(
                "Learning baseline",
                "There is not enough platform-specific history for a useful forecast yet. EGM4000 will learn automatically as more sessions and verified events are recorded.",
                min(profile.evidenceConfidence, 0.35),
                EvidenceKind.HYPOTHESIS,
                "next session",
                standardForecastCaveat()
            ))
            return@buildList
        }

        if (session != null) {
            val lastType = session.events.maxByOrNull { it.timestampMs }?.type
            if (lastType != null) {
                val candidates = profile.transitionProbabilities
                    .filterKeys { it.startsWith("$lastType->") }
                    .map { (k, p) -> k.substringAfter("->") to p }
                    .sortedByDescending { it.second }
                    .take(3)
                candidates.forEach { (next, probability) ->
                    add(Forecast(
                        "Likely next visible event: ${next.replace('_', ' ')}",
                        "In prior $${profile.platform} evidence, this event followed '$lastType' about ${(probability * 100).toInt()}% of weighted observed transitions.",
                        min(profile.evidenceConfidence, probability).coerceIn(0.05, 0.90),
                        if (profile.exactTelemetryShare > 0.5) EvidenceKind.CORRELATION else EvidenceKind.ESTIMATE,
                        "next observed event",
                        standardForecastCaveat()
                    ))
                }
            }
        }

        if (profile.completedSessions >= 3) {
            val low = profile.averageNetCredits - profile.netCreditsStdDev
            val high = profile.averageNetCredits + profile.netCreditsStdDev
            add(Forecast(
                "Historical session outcome band",
                "Completed $${profile.platform} sessions have centered around ${"%.1f".format(profile.averageNetCredits)} recorded net credits; one historical-standard-deviation band is ${"%.1f".format(low)} to ${"%.1f".format(high)}.",
                profile.evidenceConfidence.coerceAtMost(0.80),
                EvidenceKind.FORECAST_COMPAT(),
                "session-level descriptive forecast",
                "This is a descriptive statistical range from recorded history, not a promised payout range or prediction of random outcomes."
            ))
        }

        if (profile.averageDurationMinutes > 0.0) add(Forecast(
            "Typical session duration",
            "Based on recorded $${profile.platform} history, sessions have averaged ${"%.1f".format(profile.averageDurationMinutes)} minutes.",
            profile.evidenceConfidence,
            EvidenceKind.CORRELATION,
            "session duration",
            "Behavioral/session-length forecasts describe recorded user patterns, not hidden game state."
        ))
    }

    private fun advice(profile: LearnedProfile, session: GameplaySession?, phase: Phase): List<Advice> = buildList {
        val m = session?.metrics()
        when (phase) {
            Phase.BEFORE -> {
                add(Advice(phase, "Set a session plan",
                    if (profile.averageDurationMinutes > 0) "Your recorded $${profile.platform} sessions average ${"%.1f".format(profile.averageDurationMinutes)} minutes. Choose a time limit before starting and keep it visible." else "Choose a session time limit before starting so decisions are not made only in reaction to short-term outcomes.",
                    max(0.55, profile.evidenceConfidence), EvidenceKind.CORRELATION,
                    "Pre-session limits make later comparisons cleaner and reduce reactive decision-making."))
                if (profile.averageShotsPerMinute > 0) add(Advice(phase, "Start from a known pace",
                    "Historical recorded pace is ${"%.1f".format(profile.averageShotsPerMinute)} shots/min. Start deliberately rather than immediately exceeding your normal pace.",
                    profile.evidenceConfidence, EvidenceKind.CORRELATION,
                    "A stable baseline makes it easier to compare later segments."))
            }
            Phase.DURING -> {
                if (m != null && m.shotsPerMinute > max(45.0, profile.averageShotsPerMinute * 1.35)) add(Advice(phase, "Pace spike detected",
                    "Current recorded pace is ${"%.1f".format(m.shotsPerMinute)} shots/min, materially above the learned $${profile.platform} baseline. Slow down and compare the next segment rather than escalating after losses.",
                    min(0.90, max(profile.evidenceConfidence, 0.65)), EvidenceKind.CORRELATION,
                    "The current pace is being compared with your own accumulated session history."))
                if (m != null && m.netCredits < 0) add(Advice(phase, "Review the current segment",
                    "Recorded net credits are ${m.netCredits}. Treat this as a review signal, not evidence that a win is now 'due'.",
                    0.95, EvidenceKind.VERIFIED_COMPAT(),
                    "Recorded drawdown is directly observable, while future random outcomes are not."))
                if (m != null && m.durationMinutes >= 30) add(Advice(phase, "Time checkpoint",
                    "This session has reached ${m.durationMinutes.toInt()} minutes. Compare pace, credits and decision quality with the first segment before continuing.",
                    0.95, EvidenceKind.VERIFIED_COMPAT(),
                    "Session duration is known from the local record."))
            }
            Phase.AFTER -> {
                if (m != null) add(Advice(phase, "Close the learning loop",
                    "This session ended with ${m.events} recorded events, ${m.shots} exact/manual shots, ${"%.1f".format(m.shotsPerMinute)} shots/min and ${m.netCredits} recorded net credits. Compare it with the learned $${profile.platform} baseline before changing strategy.",
                    max(profile.evidenceConfidence, 0.70), EvidenceKind.CORRELATION,
                    "Post-session comparison is where new evidence updates the adaptive profile."))
                add(Advice(phase, "Label what was actually learned",
                    "Keep exact F.S.A. telemetry separate from visually inferred third-party signals. Promote an observed pattern only after repeated, independently consistent sessions.",
                    0.95, EvidenceKind.CORRELATION,
                    "Higher-quality labels improve future forecasting and reduce false patterns."))
            }
        }
        add(Advice(phase, "Prediction boundary",
            "EGM4000 may forecast visible event transitions, session behavior and evidence-based ranges. It must not represent hidden server state, RNG results, jackpots, payouts or wins as knowable in advance.",
            1.0, EvidenceKind.UNKNOWN,
            "A useful model must preserve uncertainty instead of manufacturing certainty."))
    }

    private fun evidenceWeight(kind: EvidenceKind): Double = when (kind) {
        EvidenceKind.EXACT_TELEMETRY -> 1.0
        EvidenceKind.USER_RECORDED -> 0.90
        EvidenceKind.OBSERVED_EVIDENCE -> 0.72
        EvidenceKind.DEVICE_SIGNAL -> 0.62
        EvidenceKind.ESTIMATE -> 0.50
        EvidenceKind.CORRELATION -> 0.48
        EvidenceKind.HYPOTHESIS -> 0.22
        EvidenceKind.UNKNOWN -> 0.10
    }

    private fun normalizePlatform(value: String): String = value.lowercase()
        .replace("firekirin", "fire kirin")
        .replace("panda-master", "panda master")
        .replace("orion-stars", "orion stars")
        .replace("gamemaster", "game master")
        .replace("fsa", "f.s.a.")
        .trim()

    private fun Iterable<Double>.averageOrZero(): Double = if (none()) 0.0 else average()

    private fun standardForecastCaveat() =
        "Forecasts describe patterns in recorded evidence. They do not reveal hidden provider state or make future random outcomes certain."

    // Compatibility helpers keep the evidence vocabulary honest without expanding the persisted enum.
    private fun EvidenceKind.CompanionLikeVerified(): EvidenceKind = EvidenceKind.EXACT_TELEMETRY
    private fun EvidenceKind.CompanionLikeForecast(): EvidenceKind = EvidenceKind.CORRELATION
    private fun EvidenceKind.VERIFIED_COMPAT(): EvidenceKind = EvidenceKind.EXACT_TELEMETRY
    private fun EvidenceKind.FORECAST_COMPAT(): EvidenceKind = EvidenceKind.CORRELATION
}
