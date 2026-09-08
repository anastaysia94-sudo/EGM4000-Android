package com.egm4000.app.data

import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Evidence-aware adaptive learning for EGM4000.
 *
 * The engine recalculates from the growing saved-session corpus, separately by platform.
 * Exact F.S.A. telemetry carries more weight than user-authorized visual estimates from
 * third-party providers. Forecasts are probabilistic summaries of observed history only.
 */
object AdaptiveGameplayIntelligence {
    val supportedPlatforms = listOf(
        "F.S.A.", "Fire Kirin", "Juwa", "Game Master", "Panda Master", "GameRoom", "Orion Stars"
    )

    enum class Phase { BEFORE, DURING, AFTER }

    data class LearnedProfile(
        val platform: String,
        val sessions: Int,
        val completedSessions: Int,
        val totalEvents: Int,
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
        activeSession: GameplaySession? = allSessions.lastOrNull {
            normalizePlatform(it.platform) == normalizePlatform(platform)
        },
        phase: Phase = when {
            activeSession == null -> Phase.BEFORE
            activeSession.endedAtMs == null -> Phase.DURING
            else -> Phase.AFTER
        }
    ): Analysis {
        val profile = learn(allSessions, platform)
        val summary = if (profile.sessions == 0) {
            "No prior $platform sessions are available yet. EGM4000 will establish a baseline as real evidence accumulates."
        } else {
            "Adaptive profile learned from ${profile.sessions} $platform session(s) and ${profile.totalEvents} event(s). Current evidence confidence: ${(profile.evidenceConfidence * 100).toInt()}%. The profile recalculates automatically whenever saved data changes."
        }
        return Analysis(
            platform = platform,
            profile = profile,
            forecasts = forecast(profile, activeSession),
            advice = advice(profile, activeSession, phase),
            modelSummary = summary
        )
    }

    fun learn(allSessions: List<GameplaySession>, platform: String): LearnedProfile {
        val sessions = allSessions.filter { normalizePlatform(it.platform) == normalizePlatform(platform) }
        val completed = sessions.filter { it.endedAtMs != null }
        val baselineSessions = if (completed.isNotEmpty()) completed else sessions
        val metrics = baselineSessions.map { it.metrics() }
        val events = sessions.flatMap { it.events }

        val avgDuration = metrics.map { it.durationMinutes }.averageOrZero()
        val avgPace = metrics.map { it.shotsPerMinute }.averageOrZero()
        val avgNet = metrics.map { it.netCredits.toDouble() }.averageOrZero()
        val variance = if (metrics.size >= 2) {
            metrics.map { (it.netCredits - avgNet) * (it.netCredits - avgNet) }.average()
        } else 0.0

        val weightedQuality = if (events.isEmpty()) 0.0 else events.sumOf {
            evidenceWeight(it.evidence) * it.confidence.coerceIn(0.0, 1.0)
        } / events.size.toDouble()
        val sampleFactor = (1.0 - exp(-events.size / 120.0)).coerceIn(0.0, 1.0)
        val confidence = (weightedQuality * 0.68 + sampleFactor * 0.32).coerceIn(0.0, 0.95)

        val exact = events.count { it.evidence == EvidenceKind.EXACT_TELEMETRY }.toDouble()
        val observed = events.count {
            it.evidence == EvidenceKind.OBSERVED_EVIDENCE ||
                it.evidence == EvidenceKind.DEVICE_SIGNAL ||
                it.evidence == EvidenceKind.ESTIMATE
        }.toDouble()
        val denominator = events.size.toDouble().coerceAtLeast(1.0)

        val transitionWeights = mutableMapOf<String, MutableMap<String, Double>>()
        sessions.forEach { session ->
            session.events.sortedBy { it.timestampMs }.zipWithNext().forEach { (a, b) ->
                val from = a.type.ifBlank { "unknown" }
                val to = b.type.ifBlank { "unknown" }
                val weight = min(evidenceWeight(a.evidence), evidenceWeight(b.evidence)) *
                    min(a.confidence, b.confidence).coerceIn(0.05, 1.0)
                transitionWeights.getOrPut(from) { mutableMapOf() }[to] =
                    (transitionWeights[from]?.get(to) ?: 0.0) + weight
            }
        }
        val transitionProbabilities = mutableMapOf<String, Double>()
        transitionWeights.forEach { (from, nexts) ->
            val total = nexts.values.sum().coerceAtLeast(0.0001)
            nexts.forEach { (to, score) -> transitionProbabilities["$from->$to"] = score / total }
        }

        return LearnedProfile(
            platform = platform,
            sessions = sessions.size,
            completedSessions = completed.size,
            totalEvents = events.size,
            averageDurationMinutes = avgDuration,
            averageShotsPerMinute = avgPace,
            averageNetCredits = avgNet,
            netCreditsStdDev = sqrt(max(0.0, variance)),
            transitionProbabilities = transitionProbabilities,
            evidenceConfidence = confidence,
            exactTelemetryShare = exact / denominator,
            observedEvidenceShare = observed / denominator
        )
    }

    private fun forecast(profile: LearnedProfile, active: GameplaySession?): List<Forecast> = buildList {
        if (profile.totalEvents < 8) {
            add(
                Forecast(
                    title = "Baseline still learning",
                    description = "There is not enough platform-specific history for a useful short-horizon forecast yet.",
                    confidence = profile.evidenceConfidence.coerceAtMost(0.35),
                    evidenceLabel = EvidenceKind.HYPOTHESIS,
                    horizon = "next session",
                    caveat = standardForecastCaveat()
                )
            )
            return@buildList
        }

        val lastType = active?.events?.maxByOrNull { it.timestampMs }?.type
        if (lastType != null) {
            profile.transitionProbabilities
                .filterKeys { it.startsWith("$lastType->") }
                .map { (key, probability) -> key.substringAfter("->") to probability }
                .sortedByDescending { it.second }
                .take(3)
                .forEach { (next, probability) ->
                    add(
                        Forecast(
                            title = "Possible next visible event: ${next.replace('_', ' ')}",
                            description = "In recorded ${profile.platform} evidence, this event followed '$lastType' about ${(probability * 100).toInt()}% of weighted observed transitions.",
                            confidence = min(profile.evidenceConfidence, probability).coerceIn(0.05, 0.90),
                            evidenceLabel = if (profile.exactTelemetryShare >= 0.5) EvidenceKind.CORRELATION else EvidenceKind.ESTIMATE,
                            horizon = "next observed event",
                            caveat = standardForecastCaveat()
                        )
                    )
                }
        }

        if (profile.completedSessions >= 3) {
            val low = profile.averageNetCredits - profile.netCreditsStdDev
            val high = profile.averageNetCredits + profile.netCreditsStdDev
            add(
                Forecast(
                    title = "Historical session outcome range",
                    description = "Completed ${profile.platform} sessions centered around ${"%.1f".format(profile.averageNetCredits)} recorded net credits; one historical standard-deviation band is ${"%.1f".format(low)} to ${"%.1f".format(high)}.",
                    confidence = profile.evidenceConfidence.coerceAtMost(0.80),
                    evidenceLabel = EvidenceKind.CORRELATION,
                    horizon = "session-level descriptive forecast",
                    caveat = "This summarizes recorded history. It is not a promised payout range and does not predict a random result."
                )
            )
        }

        if (profile.averageDurationMinutes > 0.0) {
            add(
                Forecast(
                    title = "Likely session-duration pattern",
                    description = "Recorded ${profile.platform} sessions have averaged ${"%.1f".format(profile.averageDurationMinutes)} minutes.",
                    confidence = profile.evidenceConfidence,
                    evidenceLabel = EvidenceKind.CORRELATION,
                    horizon = "session duration",
                    caveat = "This forecasts user/session behavior, not hidden game state."
                )
            )
        }
    }

    private fun advice(profile: LearnedProfile, session: GameplaySession?, phase: Phase): List<Advice> = buildList {
        val metrics = session?.metrics()
        when (phase) {
            Phase.BEFORE -> {
                add(
                    Advice(
                        phase,
                        "Set a session plan",
                        if (profile.averageDurationMinutes > 0.0)
                            "Your recorded ${profile.platform} sessions average ${"%.1f".format(profile.averageDurationMinutes)} minutes. Choose a time limit before starting and keep it visible."
                        else "Choose a time limit before starting so later decisions can be compared against a plan.",
                        max(0.55, profile.evidenceConfidence),
                        EvidenceKind.CORRELATION,
                        "A consistent baseline improves comparisons and reduces purely reactive decisions."
                    )
                )
                if (profile.averageShotsPerMinute > 0.0) {
                    add(
                        Advice(
                            phase,
                            "Start from a known pace",
                            "Your recorded ${profile.platform} baseline is ${"%.1f".format(profile.averageShotsPerMinute)} shots/min. Begin deliberately rather than immediately exceeding it.",
                            profile.evidenceConfidence,
                            EvidenceKind.CORRELATION,
                            "Stable starting conditions make later analysis more meaningful."
                        )
                    )
                }
            }

            Phase.DURING -> {
                if (metrics != null && metrics.shotsPerMinute > max(45.0, profile.averageShotsPerMinute * 1.35)) {
                    add(
                        Advice(
                            phase,
                            "Pace spike detected",
                            "Current recorded pace is ${"%.1f".format(metrics.shotsPerMinute)} shots/min, above the learned ${profile.platform} baseline. Slow the next segment and compare outcomes instead of escalating after losses.",
                            min(0.90, max(profile.evidenceConfidence, 0.65)),
                            EvidenceKind.CORRELATION,
                            "Current pace is being compared with your accumulated history."
                        )
                    )
                }
                if (metrics != null && metrics.netCredits < 0) {
                    add(
                        Advice(
                            phase,
                            "Recorded drawdown",
                            "Recorded net credits are ${metrics.netCredits}. Use that as a stop-and-review signal, not as evidence that a future win is due.",
                            0.95,
                            EvidenceKind.USER_RECORDED,
                            "The drawdown is recorded evidence; the next random outcome is not knowable from it."
                        )
                    )
                }
                if (metrics != null && metrics.durationMinutes >= 30.0) {
                    add(
                        Advice(
                            phase,
                            "Time checkpoint",
                            "This session has reached ${metrics.durationMinutes.toInt()} minutes. Compare pace, credits and decision quality with the opening segment before continuing.",
                            0.95,
                            EvidenceKind.USER_RECORDED,
                            "Session duration is known from the local record."
                        )
                    )
                }
            }

            Phase.AFTER -> {
                if (metrics != null) {
                    add(
                        Advice(
                            phase,
                            "Close the learning loop",
                            "This session recorded ${metrics.events} events, ${metrics.shots} manual/exact shots, ${"%.1f".format(metrics.shotsPerMinute)} shots/min and ${metrics.netCredits} net credits. Compare it with the learned ${profile.platform} baseline before changing strategy.",
                            max(profile.evidenceConfidence, 0.70),
                            EvidenceKind.CORRELATION,
                            "Completed-session evidence becomes part of the next adaptive profile calculation."
                        )
                    )
                }
                add(
                    Advice(
                        phase,
                        "Keep evidence labels intact",
                        "Keep exact F.S.A. telemetry separate from visually inferred third-party signals. Promote an observed pattern only after repeated, independently consistent sessions.",
                        0.95,
                        EvidenceKind.CORRELATION,
                        "Better provenance reduces false patterns and makes future forecasts more trustworthy."
                    )
                )
            }
        }

        add(
            Advice(
                phase,
                "Prediction boundary",
                "EGM4000 can forecast visible event transitions, behavioral/session patterns and evidence-based ranges. It cannot know hidden provider state or make jackpots, payouts, wins or RNG outcomes certain in advance.",
                1.0,
                EvidenceKind.UNKNOWN,
                "Preserving uncertainty is required for truthful analysis."
            )
        )
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
        .replace("game-room", "gameroom")
        .replace("fsa", "f.s.a.")
        .trim()

    private fun Iterable<Double>.averageOrZero(): Double = if (none()) 0.0 else average()

    private fun standardForecastCaveat() =
        "This is a probability derived from recorded evidence, not access to hidden provider state and not a guarantee of a future random result."
}
