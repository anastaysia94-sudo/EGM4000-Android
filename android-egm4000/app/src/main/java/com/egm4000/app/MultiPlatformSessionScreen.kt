package com.egm4000.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import com.egm4000.app.data.GameplayEvent
import com.egm4000.app.data.GameplaySession
import com.egm4000.app.data.metrics
import com.egm4000.app.data.riskFlags

@Composable
fun MultiPlatformSessionScreen(
    sessions: List<GameplaySession>,
    persist: (List<GameplaySession>) -> Unit,
    storageStatus: String
) {
    val currentActive = sessions.lastOrNull { it.endedAtMs == null }
    var platform by remember(currentActive?.id) { mutableStateOf(currentActive?.platform ?: "F.S.A.") }
    var note by remember { mutableStateOf("") }

    fun replaceSession(updated: GameplaySession): List<GameplaySession> =
        sessions.map { if (it.id == updated.id) updated else it }

    fun startSession() {
        if (currentActive != null) return
        val isFsa = platform == "F.S.A."
        persist(
            sessions + GameplaySession(
                platform = platform,
                title = "$platform session",
                notes = if (isFsa)
                    "F.S.A. session. Owned-environment telemetry may be recorded as exact only when supplied by the F.S.A. telemetry integration."
                else
                    "$platform session. Third-party observations remain confidence-labelled and separate from hidden provider state."
            )
        )
    }

    fun addEvent(type: String, delta: Int = 0) {
        val active = sessions.lastOrNull { it.endedAtMs == null }
        val session = active ?: GameplaySession(platform = platform, title = "$platform session")
        val event = GameplayEvent(
            type = type,
            creditDelta = delta,
            note = note.trim(),
            evidence = EvidenceKind.USER_RECORDED,
            confidence = 1.0,
            payload = mapOf("platform" to session.platform, "source" to "manual_session_logger")
        )
        val updated = session.copy(events = session.events + event)
        persist(if (active == null) sessions + updated else replaceSession(updated))
        note = ""
    }

    Page(
        "Seven-platform learning record",
        "Live Session",
        "Log F.S.A., Fire Kirin, Juwa, Game Master, Panda Master, GameRoom or Orion Stars. Every completed session becomes additional evidence for EGM4000's adaptive intelligence."
    ) {
        Panel("Platform") {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                AdaptiveGameplayIntelligence.supportedPlatforms.chunked(2).forEach { pair ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        pair.forEach { option ->
                            FilterChip(
                                selected = platform == option,
                                enabled = currentActive == null,
                                onClick = { platform = option },
                                label = { Text(option) },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }
        }

        Panel("Persistence") {
            Text(storageStatus)
            if (currentActive != null) {
                Text("Active: ${currentActive.platform} • ${currentActive.id.take(8)}…")
            } else {
                Text("No active session")
            }
        }

        if (currentActive == null) {
            Button(onClick = ::startSession, modifier = Modifier.fillMaxWidth()) {
                Text("Start $platform session")
            }
        }

        OutlinedTextField(
            value = note,
            onValueChange = { note = it },
            label = { Text("Event note") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2
        )

        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = { addEvent("shot", -1) }, modifier = Modifier.weight(1f)) { Text("Shot") }
            Button(onClick = { addEvent("credit_up", 10) }, modifier = Modifier.weight(1f)) { Text("Credit +") }
            Button(onClick = { addEvent("credit_down", -10) }, modifier = Modifier.weight(1f)) { Text("Credit −") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = { addEvent("break") }, modifier = Modifier.weight(1f)) { Text("Break") }
            OutlinedButton(onClick = { addEvent("target_change") }, modifier = Modifier.weight(1f)) { Text("Target change") }
            OutlinedButton(onClick = { addEvent("round_transition") }, modifier = Modifier.weight(1f)) { Text("Round change") }
        }

        currentActive?.let { active ->
            Button(
                onClick = {
                    persist(replaceSession(active.copy(endedAtMs = System.currentTimeMillis())))
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Finish + save session") }
        }

        val latest = sessions.lastOrNull()
        latest?.let { session ->
            val sessionMetrics = session.metrics()
            Panel("Latest learning sample") {
                Text("${session.platform} • ${sessionMetrics.events} events • ${sessionMetrics.shots} shots • ${sessionMetrics.netCredits} recorded net credits • ${"%.1f".format(sessionMetrics.durationMinutes)} min")
                Text("After the session is closed, the adaptive model automatically includes it in future baselines and forecasts.", color = Color(0xFF38FFC6))
                session.riskFlags().forEach { flag -> Text("⚠ $flag", color = Color(0xFFFFB84A)) }
            }
        }

        Panel("Evidence rule") {
            Text("Manual entries are user-recorded evidence. F.S.A. events should be labeled exact telemetry only when they actually come from the owned F.S.A. telemetry contract. Third-party visual observations remain estimates/device signals.")
        }
    }
}
