package com.egm4000.app

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

data class ExternalGameProvider(
    val id: String,
    val displayName: String,
    val defaultPlayerUrl: String? = null,
    val note: String
)

private val externalGameProviders = listOf(
    ExternalGameProvider("fire_kirin", "Fire Kirin", "https://play.firekirin.xyz/web_game/firekirin777_pc/index.html", "Opens the player portal externally. EGM4000 never sees the login password."),
    ExternalGameProvider("panda_master", "Panda Master", "https://pandamaster.vip:8888", "Player portal may vary by distributor; use the HTTPS address issued for your player account."),
    ExternalGameProvider("orion_stars", "Orion Stars", "https://orionstarsonline.com", "Use only the player URL supplied by your authorized operator/distributor."),
    ExternalGameProvider("juwa", "Juwa", null, "Enter the exact HTTPS player-login URL supplied by your Juwa operator."),
    ExternalGameProvider("game_master", "Game Master", null, "Enter the exact HTTPS player-login URL supplied by your Game Master operator."),
    ExternalGameProvider("gameroom", "GameRoom", null, "Enter the exact HTTPS player-login URL supplied by your GameRoom operator.")
)

@Composable
fun ProviderConnectScreen(onStartCapture: () -> Unit) {
    val context = LocalContext.current
    val providerPrefs = remember { context.getSharedPreferences("egm4000_provider", Context.MODE_PRIVATE) }
    val capturePrefs = remember { context.getSharedPreferences("egm4000_capture_signals", Context.MODE_PRIVATE) }
    val initialId = providerPrefs.getString("selected_provider_id", externalGameProviders.first().id)
        ?.takeIf { id -> externalGameProviders.any { it.id == id } }
        ?: externalGameProviders.first().id
    var selectedId by remember { mutableStateOf(initialId) }
    val selected = externalGameProviders.first { it.id == selectedId }
    var customUrl by remember(selectedId) {
        mutableStateOf(providerPrefs.getString("url_$selectedId", selected.defaultPlayerUrl.orEmpty()) ?: selected.defaultPlayerUrl.orEmpty())
    }
    var status by remember { mutableStateOf("Choose a provider, sign in on the provider page, then authorize only the gameplay you want EGM4000 to observe.") }

    var captureActive by remember { mutableStateOf(false) }
    var brightness by remember { mutableStateOf(0f) }
    var motion by remember { mutableStateOf(0f) }
    var targetActivity by remember { mutableStateOf(0f) }
    var shotRate by remember { mutableStateOf(0f) }
    var confidence by remember { mutableStateOf(0f) }
    var latestEvent by remember { mutableStateOf("") }
    var latestTip by remember { mutableStateOf("Start authorized Live Capture to activate provider-aware coaching.") }
    var overlayAllowed by remember { mutableStateOf(Settings.canDrawOverlays(context)) }
    var creditEstimate by remember { mutableStateOf("") }
    var creditEstimateConfidence by remember { mutableStateOf(0f) }
    var weaponEstimate by remember { mutableStateOf("") }
    var weaponEstimateConfidence by remember { mutableStateOf(0f) }

    LaunchedEffect(selectedId) {
        providerPrefs.edit().putString("selected_provider_id", selectedId).apply()
    }

    LaunchedEffect(Unit) {
        while (true) {
            captureActive = capturePrefs.getBoolean("active", false)
            brightness = capturePrefs.getFloat("brightness", 0f)
            motion = capturePrefs.getFloat("motion", 0f)
            targetActivity = capturePrefs.getFloat("targetActivity", 0f)
            shotRate = capturePrefs.getFloat("shotRateEstimate", 0f)
            confidence = capturePrefs.getFloat("confidence", 0f)
            latestEvent = capturePrefs.getString("latestEventType", "").orEmpty()
            latestTip = capturePrefs.getString("latestTip", latestTip) ?: latestTip
            creditEstimate = capturePrefs.getString("visibleCreditsEstimate", "").orEmpty()
            creditEstimateConfidence = capturePrefs.getFloat("visibleCreditsConfidence", 0f)
            weaponEstimate = capturePrefs.getString("visibleWeaponLevelEstimate", "").orEmpty()
            weaponEstimateConfidence = capturePrefs.getFloat("visibleWeaponLevelConfidence", 0f)
            overlayAllowed = Settings.canDrawOverlays(context)
            delay(750)
        }
    }

    fun openProvider() {
        val raw = customUrl.trim()
        val uri = runCatching { Uri.parse(raw) }.getOrNull()
        if (uri == null || uri.scheme != "https" || uri.host.isNullOrBlank()) {
            status = "Use an HTTPS player URL supplied by the provider/operator. EGM4000 will not open an insecure or malformed login address."
            return
        }
        providerPrefs.edit().putString("url_$selectedId", raw).apply()
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, uri))
            status = "${selected.displayName} opened externally. Sign in there, return to EGM4000, then authorize Live Capture."
        }.onFailure { status = "Could not open that player URL on this device." }
    }

    fun requestOverlayPermission() {
        val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
        runCatching { context.startActivity(intent) }
            .onSuccess { status = "Android opened the floating-window permission page. Enable it only if you want EGM4000 coaching tips over the foreground game." }
            .onFailure { status = "Could not open Android's floating-window permission page on this device." }
    }

    Page(
        "Provider-aware live intelligence",
        "Connect Game Platform",
        "Provider login → authorized capture → visual adapter → normalized events → live coach → durable session history."
    ) {
        Panel("1. Choose platform") {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                externalGameProviders.chunked(2).forEach { row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        row.forEach { provider ->
                            FilterChip(selected = selectedId == provider.id, onClick = { selectedId = provider.id }, label = { Text(provider.displayName) }, modifier = Modifier.weight(1f))
                        }
                    }
                }
            }
        }

        Panel("2. Provider login") {
            Text(selected.note, color = Color(0xFF9DB7C4))
            OutlinedTextField(value = customUrl, onValueChange = { customUrl = it }, label = { Text("Provider/player-issued HTTPS login URL") }, modifier = Modifier.fillMaxWidth())
            Button(onClick = ::openProvider, modifier = Modifier.fillMaxWidth()) { Text("Open ${selected.displayName} login") }
        }

        Panel("3. Authorized live capture") {
            Text("After provider login, return here. Android's system dialog controls what is shared; EGM4000 processes visual signals locally and does not persist raw frames.")
            OutlinedButton(onClick = {
                providerPrefs.edit().putString("selected_provider_id", selectedId).apply()
                onStartCapture()
                status = "Android will ask what screen/app to share. Choose only the gameplay you want EGM4000 to observe."
            }, modifier = Modifier.fillMaxWidth()) { Text(if (captureActive) "Capture active — re-authorize" else "Start authorized Live Capture") }
        }

        Panel("4. Optional floating live tips") {
            Text(if (overlayAllowed) "Floating coaching permission: ENABLED" else "Floating coaching permission: OFF", color = if (overlayAllowed) Color(0xFF38FFC6) else Color(0xFFFFB84A))
            Text("When enabled, EGM4000 can show a small non-touchable coaching strip above the foreground game. Android controls this permission and you can revoke it at any time.", color = Color(0xFF9DB7C4))
            if (!overlayAllowed) OutlinedButton(onClick = ::requestOverlayPermission, modifier = Modifier.fillMaxWidth()) { Text("Enable floating live tips") }
        }

        Panel("5. Provider visual adapter") {
            Text("${selected.displayName} adapter • ${if (captureActive) "LIVE" else "STANDBY"}", color = if (captureActive) Color(0xFF38FFC6) else Color(0xFFFFB84A))
            Text("Capture confidence: ${"%.0f".format(confidence * 100)}%")
            Text("Screen change: ${"%.1f".format(motion * 100)}% • brightness: ${"%.1f".format(brightness * 100)}%")
            Text("Target-field activity: ${"%.1f".format(targetActivity * 100)}%")
            Text("Estimated input/shot bursts in rolling minute: ${"%.0f".format(shotRate)}")
            if (creditEstimate.isNotBlank()) Text("Visible credits OCR estimate: $creditEstimate • ${"%.0f".format(creditEstimateConfidence * 100)}% confidence", color = Color(0xFF38FFC6))
            if (weaponEstimate.isNotBlank()) Text("Visible weapon/bet level OCR estimate: $weaponEstimate • ${"%.0f".format(weaponEstimateConfidence * 100)}% confidence", color = Color(0xFF38FFC6))
            if (latestEvent.isNotBlank()) Text("Latest normalized event: $latestEvent", color = Color(0xFF9DB7C4))
            Text("Bundled on-device OCR alternates between provider-specific credit and weapon HUD regions. A numeric estimate is shown only after repeated recognition clears the confidence gate; incorrect HUD crops can still produce OCR errors and need device/provider calibration.", color = Color(0xFF9DB7C4))
        }

        Panel("6. EGM4000 AI Coach — live tip") {
            Text(latestTip, color = Color(0xFF38FFC6))
            Text("Tips are mirrored to the persistent capture notification and, when separately authorized, to the floating coaching strip.", color = Color(0xFF9DB7C4))
        }

        Panel("7. Session history + post-session analysis") {
            Text("Authorized capture automatically creates a durable local ${selected.displayName} observation session. Confidence-labelled motion and OCR events are appended during capture and the session is closed when capture stops.")
            Text("Open Event Stream, Metrics, Pattern Lab, AI Coach or Replay Lab after the session to review normalized observations alongside recorded history.", color = Color(0xFF9DB7C4))
        }

        Panel("Evidence boundary") {
            Text("EGM4000 does not intercept usernames/passwords, read hidden provider server state, bypass protections, manipulate balances, or promise future random outcomes.")
            Text("Visual/OCR signals are estimates with confidence labels. Use them to improve pacing, recordkeeping and decision discipline—not as guaranteed winning predictions.", color = Color(0xFFFFB84A))
        }

        Text(status, modifier = Modifier.padding(vertical = 4.dp), color = Color(0xFF38FFC6))
    }
}
