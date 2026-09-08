package com.egm4000.app

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
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
import com.egm4000.app.data.GameplaySession
import org.json.JSONArray
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date
import java.util.UUID

@Composable
fun TutorialScreen(onComplete: () -> Unit, onNavigate: (Screen) -> Unit) {
    var page by remember { mutableStateOf(0) }
    val pages = listOf(
        "EGM4000 watches only evidence you record or explicitly authorize. It does not know hidden Fire Kirin server state.",
        "Start a Live Session before play. Record meaningful events, credit movement and breaks. Each change is written to durable local storage.",
        "Live Capture uses Android's system permission. Raw frames are processed in memory and discarded; stored signals are lower-confidence estimates.",
        "Metrics, Pattern Lab and AI Coach explain your recorded history. Correlation is not causation or a prediction of random outcomes.",
        "Replay Lab and Data Exchange let you review and export your evidence. F.S.A. exact telemetry remains separate from third-party observations.",
        "Fire Kirin opens externally at the configured HTTPS portal. EGM4000 never asks for or stores your Fire Kirin credentials."
    )
    Page("First-run guided tutorial", "Welcome to EGM4000", "Watch. Measure. Explain. Improve.") {
        ArtCard(R.drawable.cyber_aquatic_reef, "Cyber-Aquatic Intelligence", "Learn the evidence workflow before your first session.")
        Panel("Step ${page + 1} of ${pages.size}") {
            Text(pages[page])
            Text("Evidence before conclusions. Safety before speculation.", color = Color(0xFF9DB7C4))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { if (page > 0) page-- }, enabled = page > 0, modifier = Modifier.weight(1f)) { Text("Back") }
            if (page < pages.lastIndex) {
                Button(onClick = { page++ }, modifier = Modifier.weight(1f)) { Text("Next") }
            } else {
                Button(onClick = onComplete, modifier = Modifier.weight(1f)) { Text("Finish tutorial") }
            }
        }
        OutlinedButton(onClick = { onNavigate(Screen.COMMAND) }, modifier = Modifier.fillMaxWidth()) { Text("Preview Command Center") }
        SafetyNotice()
    }
}

@Composable
fun CommunityScreen() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("egm4000_community_v1", Context.MODE_PRIVATE) }
    var title by remember { mutableStateOf("") }
    var body by remember { mutableStateOf("") }
    var posts by remember { mutableStateOf(readObjects(prefs.getString("posts", "[]") ?: "[]")) }

    fun savePosts(next: List<JSONObject>) {
        posts = next
        val array = JSONArray()
        next.forEach { array.put(it) }
        prefs.edit().putString("posts", array.toString()).commit()
    }

    Page("Local-first community beta", "Community", "Create private local discussion drafts without pretending generated content is real user activity.") {
        Panel("New local thread") {
            OutlinedTextField(title, { title = it }, label = { Text("Thread title") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(body, { body = it }, label = { Text("Post") }, minLines = 4, modifier = Modifier.fillMaxWidth())
            Button(onClick = {
                if (title.isNotBlank() || body.isNotBlank()) {
                    val post = JSONObject().apply {
                        put("id", UUID.randomUUID().toString())
                        put("title", title.ifBlank { "Untitled thread" })
                        put("body", body)
                        put("authorLabel", "Local user")
                        put("createdAtMs", System.currentTimeMillis())
                        put("moderation", "local_draft")
                    }
                    savePosts(listOf(post) + posts)
                    title = ""
                    body = ""
                }
            }, modifier = Modifier.fillMaxWidth()) { Text("Save local thread") }
        }
        Panel("Privacy / integrity") { Text("This beta stores posts on this device. It does not fabricate registered users, testimonials, engagement counts or moderation outcomes.") }
        if (posts.isEmpty()) Panel("No local threads") { Text("Create a thread above.") }
        else posts.take(40).forEach { post ->
            Panel(post.optString("title", "Thread")) {
                Text(post.optString("body"))
                Text("${post.optString("authorLabel", "Local user")} • ${formatTime(post.optLong("createdAtMs"))}", color = Color(0xFF9DB7C4))
            }
        }
    }
}

@Composable
fun SurveysScreen() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("egm4000_surveys_v1", Context.MODE_PRIVATE) }
    var question by remember { mutableStateOf("") }
    var consent by remember { mutableStateOf(prefs.getBoolean("consent", false)) }
    var surveys by remember { mutableStateOf(readObjects(prefs.getString("surveys", "[]") ?: "[]")) }

    fun saveSurveys(next: List<JSONObject>) {
        surveys = next
        val array = JSONArray()
        next.forEach { array.put(it) }
        prefs.edit().putString("surveys", array.toString()).commit()
    }

    Page("Privacy-preserving feedback", "Surveys", "Owner-style local survey prototype with explicit consent and no cross-site identity tracking.") {
        Panel("Consent") {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Checkbox(checked = consent, onCheckedChange = {
                    consent = it
                    prefs.edit().putBoolean("consent", it).commit()
                })
                Text("Allow this EGM4000 install to store local survey responses on this device.")
            }
        }
        Panel("Create local survey") {
            OutlinedTextField(question, { question = it }, label = { Text("Question") }, modifier = Modifier.fillMaxWidth())
            Button(onClick = {
                if (question.isNotBlank()) {
                    val survey = JSONObject().apply {
                        put("id", UUID.randomUUID().toString())
                        put("question", question)
                        put("yes", 0)
                        put("no", 0)
                        put("createdAtMs", System.currentTimeMillis())
                    }
                    saveSurveys(listOf(survey) + surveys)
                    question = ""
                }
            }, modifier = Modifier.fillMaxWidth()) { Text("Save survey") }
        }
        surveys.take(30).forEachIndexed { index, survey ->
            Panel(survey.optString("question", "Survey")) {
                Text("Local responses: yes ${survey.optInt("yes")} • no ${survey.optInt("no")}")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(enabled = consent, onClick = {
                        val next = surveys.toMutableList()
                        next[index] = JSONObject(survey.toString()).apply { put("yes", optInt("yes") + 1) }
                        saveSurveys(next)
                    }, modifier = Modifier.weight(1f)) { Text("Yes") }
                    OutlinedButton(enabled = consent, onClick = {
                        val next = surveys.toMutableList()
                        next[index] = JSONObject(survey.toString()).apply { put("no", optInt("no") + 1) }
                        saveSurveys(next)
                    }, modifier = Modifier.weight(1f)) { Text("No") }
                }
                if (!consent) Text("Enable consent before recording a response.", color = Color(0xFFFFB84A))
            }
        }
    }
}

@Composable
fun BuildChecklistScreen(sessions: List<GameplaySession>, storageStatus: String) {
    val context = LocalContext.current
    val capturePrefs = context.getSharedPreferences("egm4000_capture_signals", Context.MODE_PRIVATE)
    val appPrefs = context.getSharedPreferences("egm4000_app_v1", Context.MODE_PRIVATE)
    val communityPrefs = context.getSharedPreferences("egm4000_community_v1", Context.MODE_PRIVATE)
    val surveyPrefs = context.getSharedPreferences("egm4000_surveys_v1", Context.MODE_PRIVATE)
    val checks: List<Pair<String, Boolean>> = listOf(
        Pair("Guided tutorial completed", appPrefs.getBoolean("tutorial_complete", false)),
        Pair("Durable session store ready", !storageStatus.startsWith("Storage warning")),
        Pair("At least one session saved", sessions.isNotEmpty()),
        Pair("At least one normalized event saved", sessions.any { it.events.isNotEmpty() }),
        Pair("Capture permission exercised", capturePrefs.getLong("startedAtMs", 0L) > 0L),
        Pair("Community local storage initialized", communityPrefs.contains("posts")),
        Pair("Survey consent choice recorded", surveyPrefs.contains("consent"))
    )
    val passed = checks.count { it.second }
    Page("Launch/readiness visibility", "Build Checklist", "This checklist reports local setup and evidence readiness; it does not substitute for physical-device QA.") {
        Metric("$passed/${checks.size}", "local readiness checks")
        checks.forEach { check ->
            val label = check.first
            val ok = check.second
            Panel(if (ok) "PASS" else "TODO") { Text(label, color = if (ok) Color(0xFF38FFC6) else Color(0xFFFFB84A)) }
        }
        Panel("External gates") { Text("Physical-device testing, signed Play Store release, public HTTPS hosting, legal review and independent security testing remain external release gates.") }
    }
}

private fun readObjects(raw: String): List<JSONObject> = runCatching {
    val array = JSONArray(raw)
    val out = mutableListOf<JSONObject>()
    for (i in 0 until array.length()) array.optJSONObject(i)?.let { out.add(it) }
    out.toList()
}.getOrDefault(emptyList())

private fun formatTime(ms: Long): String = if (ms <= 0L) "unknown time" else DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(ms))
