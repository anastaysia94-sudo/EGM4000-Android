package com.egm4000.app

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.egm4000.app.data.*
import kotlinx.coroutines.delay

@Composable
fun CommandCenterScreen(state: EGMState, onNavigate: (Screen) -> Unit, onOpenFireKirin: () -> Unit) {
    val latest = state.sessions.lastOrNull()
    val m = latest?.metrics()
    Page("Founder-grade gameplay intelligence", "Command Center", "The full EGM4000 evidence surface: capture, normalized events, metrics, patterns, coaching, replay, experiments and safe research.") {
        SafetyNotice()
        ArtCard(R.drawable.cyber_aquatic_reef, "Cyber-Aquatic Intelligence Reef", "PLAY → WATCH → MEASURE → ANALYZE → EXPLAIN → LEARN")
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric("${state.sessions.size}", "saved sessions", Modifier.weight(1f))
            Metric("${m?.events ?: 0}", "latest events", Modifier.weight(1f))
            Metric("${m?.netCredits ?: 0}", "recorded net credits", Modifier.weight(1f))
        }
        Panel("Quick launch") {
            Button(onClick = onOpenFireKirin, modifier = Modifier.fillMaxWidth()) { Text("Open Fire Kirin securely") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { onNavigate(Screen.SESSION) }, modifier = Modifier.weight(1f)) { Text("Session Logger") }
                Button(onClick = { onNavigate(Screen.CAPTURE) }, modifier = Modifier.weight(1f)) { Text("Live Capture") }
            }
            Button(onClick = { onNavigate(Screen.METRICS) }, modifier = Modifier.fillMaxWidth()) { Text("Open full intelligence modules") }
        }
        ArtCard(R.drawable.sonar_lattice, "Evidence Sonar", "Exact telemetry stays distinct from observations, estimates, correlations and hypotheses.")
        ArtCard(R.drawable.security_vault, "Research Vault", "Owned F.S.A. telemetry and controlled validation are the safe ground-truth lab.")
        Panel("Storage") { Text(state.storageStatus); Text("Nothing is called saved until the local store writes and verifies the session bundle.", color = Color(0xFF9DB7C4)) }
    }
}

@Composable
fun SessionScreen(sessions: List<GameplaySession>, persist: (List<GameplaySession>) -> Unit, storageStatus: String) {
    var note by remember { mutableStateOf("") }
    val active = sessions.lastOrNull()?.takeIf { it.endedAtMs == null }
    fun start() = persist(sessions + GameplaySession(title = "Fire Kirin session"))
    fun add(type: String, delta: Int = 0, evidence: EvidenceKind = EvidenceKind.USER_RECORDED) {
        val session = active ?: GameplaySession(title = "Fire Kirin session")
        val event = GameplayEvent(type = type, creditDelta = delta, note = note.trim(), evidence = evidence, confidence = if (evidence == EvidenceKind.USER_RECORDED) 1.0 else .55)
        val updated = session.copy(events = session.events + event)
        persist(if (active == null) sessions + updated else sessions.dropLast(1) + updated)
        note = ""
    }
    Page("Record what actually happened", "Live Session", "Every action writes to durable local storage immediately. Session saves are reloaded and verified after commit.") {
        Panel("Persistence") { Text(storageStatus); if (active != null) Text("Active session: ${active.id.take(8)}…") else Text("No active session") }
        if (active == null) Button(onClick = ::start, modifier = Modifier.fillMaxWidth()) { Text("Start Fire Kirin session") }
        OutlinedTextField(note, { note = it }, label = { Text("Event note") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Button(onClick = { add("shot", -1) }, modifier = Modifier.weight(1f)) { Text("Shot") }
            Button(onClick = { add("credit_up", 10) }, modifier = Modifier.weight(1f)) { Text("Credit +") }
            Button(onClick = { add("credit_down", -10) }, modifier = Modifier.weight(1f)) { Text("Credit −") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedButton(onClick = { add("break", 0) }, modifier = Modifier.weight(1f)) { Text("Break") }
            OutlinedButton(onClick = { add("target_change", 0) }, modifier = Modifier.weight(1f)) { Text("Target change") }
        }
        Button(onClick = { persist(sessions) }, modifier = Modifier.fillMaxWidth()) { Text("Save checkpoint + verify") }
        if (active != null) Button(onClick = { persist(sessions.dropLast(1) + active.copy(endedAtMs = System.currentTimeMillis())) }, modifier = Modifier.fillMaxWidth()) { Text("Finish + save session") }
        val latest = sessions.lastOrNull()
        latest?.let { s ->
            val m = s.metrics(); Panel("Current session summary") {
                Text("${m.events} events • ${m.shots} shots • ${m.netCredits} net recorded credits • ${"%.1f".format(m.durationMinutes)} min")
                s.riskFlags().forEach { Text("⚠ $it", color = Color(0xFFFFB84A)) }
            }
        }
    }
}

@Composable
fun CaptureScreen(onStart: () -> Unit, onStop: () -> Unit) {
    val context = LocalContext.current
    var active by remember { mutableStateOf(false) }; var brightness by remember { mutableStateOf(0f) }; var motion by remember { mutableStateOf(0f) }; var samples by remember { mutableStateOf(0L) }
    LaunchedEffect(Unit) { while (true) {
        val p = context.getSharedPreferences("egm4000_capture_signals", Context.MODE_PRIVATE)
        active = p.getBoolean("active", false); brightness = p.getFloat("brightness", 0f); motion = p.getFloat("motion", 0f); samples = p.getLong("sampleCount", 0L); delay(750)
    } }
    Page("Authorized device sensing", "Live Capture", "Android shows the system MediaProjection permission. Raw frames are processed in memory and discarded; EGM4000 stores aggregate visual activity signals only.") {
        ArtCard(R.drawable.sonar_lattice, "Capture Sonar", "User-authorized screen activity becomes lower-confidence observed evidence, never hidden-state telemetry.")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Metric(if (active) "ACTIVE" else "OFF", "capture", Modifier.weight(1f)); Metric("${(brightness*100).toInt()}%", "brightness", Modifier.weight(1f)); Metric("${"%.3f".format(motion)}", "motion", Modifier.weight(1f))
        }
        Text("Samples: $samples")
        Button(onClick = onStart, modifier = Modifier.fillMaxWidth()) { Text("Start authorized screen feedback") }
        OutlinedButton(onClick = onStop, modifier = Modifier.fillMaxWidth()) { Text("Stop screen feedback") }
        SafetyNotice()
    }
}

@Composable
fun EventStreamScreen(sessions: List<GameplaySession>) {
    val events = sessions.flatMap { s -> s.events.map { s to it } }.sortedByDescending { it.second.timestampMs }
    Page("Normalized gameplay evidence", "Event Stream", "Every event retains source label, confidence, timestamp and session provenance.") {
        if (events.isEmpty()) Panel("Empty stream") { Text("Record a session event first.") }
        events.take(100).forEach { (s,e) -> Panel("${e.type} • ${s.platform}") { EvidencePill(e.evidence,e.confidence); Text("Δ credits ${e.creditDelta} • ${java.text.DateFormat.getDateTimeInstance().format(java.util.Date(e.timestampMs))}"); if(e.note.isNotBlank()) Text(e.note) } }
    }
}

@Composable
fun MetricsScreen(sessions: List<GameplaySession>) {
    val events = sessions.sumOf { it.events.size }; val shots = sessions.sumOf { it.metrics().shots }; val net = sessions.sumOf { it.metrics().netCredits }; val minutes = sessions.sumOf { it.metrics().durationMinutes }
    Page("Measure before you explain", "Live Metrics", "Rolling local metrics summarize recorded evidence without claiming future outcomes.") {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { Metric("$events","events",Modifier.weight(1f)); Metric("$shots","shots",Modifier.weight(1f)); Metric("$net","net credits",Modifier.weight(1f)) }
        Panel("Pace") { Text("${"%.1f".format(if(minutes>0) shots/minutes else 0.0)} shots/min across saved sessions") }
        Panel("Evidence quality") { val all=sessions.flatMap{it.events}; Text("Exact telemetry: ${all.count{it.evidence==EvidenceKind.EXACT_TELEMETRY}} • estimates/device signals: ${all.count{it.evidence==EvidenceKind.ESTIMATE||it.evidence==EvidenceKind.DEVICE_SIGNAL}}") }
    }
}

@Composable
fun PatternLabScreen(sessions: List<GameplaySession>) {
    val complete = sessions.filter { it.endedAtMs != null && it.events.isNotEmpty() }
    val points = complete.map { it.metrics().shotsPerMinute to it.metrics().netCredits.toDouble() }
    val corr = pearson(points)
    Page("Find patterns without inventing causes", "Pattern Lab", "Compares completed sessions. Correlation is labeled correlation—not causation, RNG prediction or hidden-state discovery.") {
        Metric(complete.size.toString(), "completed samples")
        Panel("Shot pace ↔ recorded net credits") { Text(if(corr==null) "Need at least 3 varied completed sessions." else "Pearson r = ${"%.3f".format(corr)}"); Text("Small samples and selection effects can make correlations unstable.", color=Color(0xFF9DB7C4)) }
        complete.takeLast(12).forEach { val m=it.metrics(); Panel(it.title) { Text("${"%.1f".format(m.shotsPerMinute)} shots/min • net ${m.netCredits} • ${m.events} events") } }
    }
}

fun pearson(points: List<Pair<Double,Double>>): Double? {
    if (points.size < 3) return null; val xs=points.map{it.first}; val ys=points.map{it.second}; val mx=xs.average(); val my=ys.average(); var top=0.0; var dx=0.0; var dy=0.0
    points.forEach { (x,y) -> val a=x-mx; val b=y-my; top+=a*b; dx+=a*a; dy+=b*b }
    return if(dx==0.0||dy==0.0) null else top/kotlin.math.sqrt(dx*dy)
}

@Composable
fun CoachScreen(sessions: List<GameplaySession>) = Page("Evidence before advice", "AI Coach", "Local evidence coach explains what the session record supports and refuses to turn uncertainty into certainty.") {
    val latest=sessions.lastOrNull(); if(latest==null) Panel("No session") { Text("Record a session first.") } else latest.coachingTips().forEachIndexed { i,t -> Panel("Coach ${i+1}") { Text(t) } }; SafetyNotice()
}

@Composable
fun TipsScreen(sessions: List<GameplaySession>) = Page("Actionable, evidence-labeled review", "Tips Center", "Tips are derived from recorded pace, credits, session length and evidence quality.") {
    val tips=sessions.lastOrNull()?.coachingTips().orEmpty(); if(tips.isEmpty()) Text("No tips yet.") else tips.forEach { Panel("Review signal") { Text(it) } }
}

@Composable
fun AlertsScreen(sessions: List<GameplaySession>) = Page("Serious signals only", "Alerts", "Risk and data-quality warnings stay plain and non-joking.") {
    val alerts=sessions.lastOrNull()?.riskFlags().orEmpty(); if(alerts.isEmpty()) Panel("No active risk flags") { Text("This is not a guarantee of safety or profit; it only means configured local thresholds have not fired.") } else alerts.forEach { Panel("Risk flag") { Text(it,color=Color(0xFFFFB84A)) } }
}

@Composable
fun ReplayScreen(sessions: List<GameplaySession>) = Page("Reconstruct recorded timelines", "Replay Lab", "Replay is a timeline of stored evidence, not a reconstruction of hidden game state.") {
    val s=sessions.lastOrNull(); if(s==null) Text("No session available.") else { Panel("${s.title} • ${s.events.size} events") { Text("Session ${s.id}") }; s.events.sortedBy{it.timestampMs}.forEachIndexed { i,e -> Panel("${i+1}. ${e.type}") { EvidencePill(e.evidence,e.confidence); Text("Δ ${e.creditDelta} • ${e.note.ifBlank{"no note"}}") } } }
}

@Composable
fun FireKirinScreen(onOpen:()->Unit,onCapture:()->Unit,sessions:List<GameplaySession>) = Page("Credential-safe companion", "Fire Kirin", "EGM4000 opens the configured Fire Kirin login externally. Sign in directly there, return here, authorize capture if desired, then log/review your own session evidence.") {
    ArtCard(R.drawable.cyber_aquatic_reef,"Fire Kirin Companion","Configured external login: $FIRE_KIRIN_URL")
    Button(onClick=onOpen,modifier=Modifier.fillMaxWidth()){Text("Open Fire Kirin securely")}
    Button(onClick=onCapture,modifier=Modifier.fillMaxWidth()){Text("Start authorized screen feedback")}
    Panel("Local history"){Text("${sessions.size} saved session(s) available to EGM4000.")}
    SafetyNotice()
}
