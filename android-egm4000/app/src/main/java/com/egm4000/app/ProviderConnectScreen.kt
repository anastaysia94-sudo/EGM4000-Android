package com.egm4000.app

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

/**
 * Provider connection is intentionally an external-login handoff.
 * EGM4000 does not collect, proxy, inject, inspect, or store third-party credentials.
 * Real-time coaching is based only on user-authorized screen capture and EGM4000's
 * own session/event records. It does not claim access to hidden provider server state.
 */
data class ExternalGameProvider(
    val id: String,
    val displayName: String,
    val defaultPlayerUrl: String? = null,
    val note: String
)

private val externalGameProviders = listOf(
    ExternalGameProvider(
        "fire_kirin",
        "Fire Kirin",
        "https://play.firekirin.xyz/web_game/firekirin777_pc/index.html",
        "Opens the player portal externally. EGM4000 never sees the login password."
    ),
    ExternalGameProvider(
        "panda_master",
        "Panda Master",
        "https://pandamaster.vip:8888",
        "Player portal may vary by distributor; replace this URL if your provider gave you another HTTPS address."
    ),
    ExternalGameProvider(
        "orion_stars",
        "Orion Stars",
        "https://orionstarsonline.com",
        "Use only the player URL supplied by your authorized operator/distributor."
    ),
    ExternalGameProvider(
        "juwa",
        "Juwa",
        null,
        "Enter the exact HTTPS player-login URL supplied by your Juwa operator."
    ),
    ExternalGameProvider(
        "game_master",
        "Game Master",
        null,
        "Enter the exact HTTPS player-login URL supplied by your Game Master operator."
    ),
    ExternalGameProvider(
        "gameroom",
        "GameRoom",
        null,
        "Enter the exact HTTPS player-login URL supplied by your GameRoom operator."
    )
)

@Composable
fun ProviderConnectScreen(onStartCapture: () -> Unit) {
    val context = LocalContext.current
    var selectedId by remember { mutableStateOf(externalGameProviders.first().id) }
    val selected = externalGameProviders.first { it.id == selectedId }
    var customUrl by remember(selectedId) { mutableStateOf(selected.defaultPlayerUrl.orEmpty()) }
    var status by remember { mutableStateOf("Choose a provider, open its official/player-issued login page, sign in there, then start Live Capture.") }

    fun openProvider() {
        val raw = customUrl.trim()
        val uri = runCatching { Uri.parse(raw) }.getOrNull()
        if (uri == null || uri.scheme != "https" || uri.host.isNullOrBlank()) {
            status = "Use an HTTPS player URL supplied by the provider/operator. EGM4000 will not open an insecure or malformed login address."
            return
        }
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, uri))
            status = "${selected.displayName} opened externally. Sign in there, return to EGM4000, then authorize Live Capture."
        }.onFailure {
            status = "Could not open that player URL on this device."
        }
    }

    Page(
        "Authorized external gameplay observation",
        "Connect Game Platform",
        "Sign in with the game provider itself; EGM4000 analyzes only what you explicitly share."
    ) {
        Panel("1. Choose platform") {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                externalGameProviders.chunked(2).forEach { row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        row.forEach { provider ->
                            FilterChip(
                                selected = selectedId == provider.id,
                                onClick = { selectedId = provider.id },
                                label = { Text(provider.displayName) },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }
        }

        Panel("2. Player login URL") {
            Text(selected.note, color = Color(0xFF9DB7C4))
            OutlinedTextField(
                value = customUrl,
                onValueChange = { customUrl = it },
                label = { Text("Provider/player-issued HTTPS login URL") },
                modifier = Modifier.fillMaxWidth()
            )
            Button(onClick = ::openProvider, modifier = Modifier.fillMaxWidth()) {
                Text("Open ${selected.displayName} login")
            }
        }

        Panel("3. Real-time EGM4000 coaching") {
            Text("After you sign in through the provider, return here and start Android's system screen-share permission. EGM4000 can then derive user-visible session signals and combine them with your local session/event history for real-time tips.")
            OutlinedButton(
                onClick = {
                    onStartCapture()
                    status = "Android will ask what screen/app you want to share. Only authorize the gameplay you want EGM4000 to observe."
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Start authorized Live Capture") }
        }

        Panel("Evidence boundary") {
            Text("EGM4000 does not intercept usernames/passwords, read hidden provider server state, bypass protections, manipulate balances, or promise future random outcomes.")
            Text("Coaching should be treated as evidence-aware assistance based on visible gameplay and recorded history, not guaranteed winning advice.", color = Color(0xFFFFB84A))
        }

        Text(status, modifier = Modifier.padding(vertical = 4.dp), color = Color(0xFF38FFC6))
    }
}
