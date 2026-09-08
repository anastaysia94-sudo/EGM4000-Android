package com.egm4000.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.egm4000.app.data.AdaptiveGameplayIntelligence
import com.egm4000.app.data.EvidenceKind
import com.egm4000.app.data.GameplaySession

@Composable
fun AdaptiveCoachScreen(sessions: List<GameplaySession>) {
    var platform by remember {
        mutableStateOf(sessions.lastOrNull()?.platform ?: AdaptiveGameplayIntelligence.supportedPlatforms.first())
    }
    var phase by remember {
        mutableStateOf(
            when {
                sessions.lastOrNull { it.platform.equals(platform, ignoreCase = true) }?.endedAtMs == null &&
                    sessions.any { it.platform.equals(platform, ignoreCase = true) } -> AdaptiveGameplayIntelligence.Phase.DURING
                sessions.any { it.platform.equals(platform, ignoreCase = true) } -> AdaptiveGameplayIntelligence.Phase.AFTER
                else -> AdaptiveGameplayIntelligence.Phase.BEFORE
            }
        )
    }

    val latest = sessions.lastOrNull { it.platform.equals(platform, ignoreCase = true) }
    val analysis = AdaptiveGameplayIntelligence.analyze(
        allSessions = sessions,
        platform = platform,
        activeSession = latest,
        phase = phase
    )

    Page(
        "Adaptive evidence-aware intelligence",
        "EGM4000 AI Coach",
        "Learns from the growing session record across F.S.A., Fire Kirin, Juwa, Game Master, Panda Master, GameRoom and Orion Stars. Forecasts are confidence-labelled patterns, never guarantees."
    ) {
        Panel("Platform") {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                AdaptiveGameplayIntelligence.supportedPlatforms.chunked(2).forEach { pair ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        pair.forEach { option ->
                            FilterChip(
                                selected = platform == option,
                                onClick = {
                                    platform = option
                                    phase = if (sessions.any { it.platform.equals(option, ignoreCase = true) }) {
                                        AdaptiveGameplayIntelligence.Phase.AFTER
                                    } else AdaptiveGameplayIntelligence.Phase.BEFORE
                                },
                                label = { Text(option) },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }
        }

        Panel("Coaching phase") {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                AdaptiveGameplayIntelligence.Phase.entries.forEach { option ->
                    FilterChip(
                        selected = phase == option,
                        onClick = { phase = option },
                        label = { Text(option.name.lowercase().replaceFirstChar { it.uppercase() }) },
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        Panel("Learning state") {
            Text(analysis.modelSummary)
            Text(
                "Completed sessions: ${analysis.profile.completedSessions} • Exact telemetry share: ${(analysis.profile.exactTelemetryShare * 100).toInt()}% • Observed/estimated share: ${(analysis.profile.observedEvidenceShare * 100).toInt()}%",
                color = Color(0xFF9DB7C4)
            )
        }

        analysis.advice.forEach { item ->
            Panel("${item.phase.name.lowercase().replaceFirstChar { it.uppercase() }} • ${item.title}") {
                EvidencePill(item.evidenceLabel, item.confidence)
                Text(item.text)
                Text("Why: ${item.why}", color = Color(0xFF9DB7C4))
            }
        }

        Panel("Forecasts / likely future patterns") {
            if (analysis.forecasts.isEmpty()) {
                Text("No forecast is justified by the current evidence yet.")
            }
        }
        analysis.forecasts.forEach { forecast ->
            Panel(forecast.title) {
                EvidencePill(forecast.evidenceLabel, forecast.confidence)
                Text(forecast.description)
                Text("Horizon: ${forecast.horizon}", color = Color(0xFF38FFC6))
                Text(forecast.caveat, color = Color(0xFFFFB84A))
            }
        }

        Panel("What this AI can and cannot predict") {
            Text("It can learn recurring visible-event sequences, user pacing, session duration, historically observed credit ranges, target-activity patterns and other recorded relationships as the dataset grows.")
            Text("It cannot truthfully know hidden RNG state, server-side outcomes, guaranteed payouts, jackpots or wins before they happen.", color = Color(0xFFFFB84A))
        }
        SafetyNotice()
    }
}
