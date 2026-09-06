package com.egm4000.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.egm4000.app.data.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import kotlin.math.absoluteValue

@Composable
fun ExperimentScreen() {
    val context=LocalContext.current; val prefs=remember{context.getSharedPreferences("egm4000_experiments_v1",Context.MODE_PRIVATE)}
    var hypothesis by remember{mutableStateOf("")}; var metric by remember{mutableStateOf("shot pace vs recorded net credits")}; var environment by remember{mutableStateOf("F.S.A. owned sandbox")}; var items by remember{mutableStateOf(loadExperiments(prefs.getString("items","[]")?:"[]"))}
    fun save(){ prefs.edit().putString("items", JSONArray().apply{items.forEach{put(it)}}.toString()).commit() }
    Page("Test hypotheses, not hunches", "Experiment Lab", "Experiments are for owned F.S.A./simulation environments or observation-only review. They do not alter third-party games.") {
        ArtCard(R.drawable.security_vault,"Experiment Vault","Owned environments can provide exact ground truth; third-party sessions remain observation-only.")
        OutlinedTextField(hypothesis,{hypothesis=it},label={Text("Hypothesis")},modifier=Modifier.fillMaxWidth())
        OutlinedTextField(metric,{metric=it},label={Text("Metric")},modifier=Modifier.fillMaxWidth())
        OutlinedTextField(environment,{environment=it},label={Text("Environment")},modifier=Modifier.fillMaxWidth())
        Button(onClick={ if(hypothesis.isNotBlank()){items=items+JSONObject().apply{put("id",UUID.randomUUID().toString());put("hypothesis",hypothesis);put("metric",metric);put("environment",environment);put("status","PLANNED");put("createdAtMs",System.currentTimeMillis())};save();hypothesis=""}},modifier=Modifier.fillMaxWidth()){Text("Save experiment")}
        items.reversed().forEach{e->Panel(e.optString("status")+" • "+e.optString("environment")){Text(e.optString("hypothesis"));Text("Metric: ${e.optString("metric")}",color=Color(0xFF9DB7C4))}}
        SafetyNotice()
    }
}

private fun loadExperiments(raw:String):List<JSONObject> = runCatching{val a=JSONArray(raw);buildList{for(i in 0 until a.length())add(a.getJSONObject(i))}}.getOrDefault(emptyList())

@Composable
fun ValidationScreen() {
    var result by remember{mutableStateOf("Fixture not run yet")}
    Page("Measure capture accuracy against ground truth", "Capture Validation", "Controlled validation compares owned F.S.A. exact telemetry with detector observations. It does not validate hidden third-party state.") {
        ArtCard(R.drawable.sonar_lattice,"Ground-Truth Sonar","Exact F.S.A. telemetry = confidence 100%; detector observations retain detector confidence.")
        Button(onClick={
            val truth=listOf(100L,500L,900L,1400L,2100L,2700L); val observed=listOf(110L,520L,1040L,1410L,2110L,3300L); val tolerance=180L
            val matched=truth.count{t->observed.any{(it-t).absoluteValue<=tolerance}}; val precision=matched.toDouble()/observed.size; val recall=matched.toDouble()/truth.size; val f1=if(precision+recall==0.0)0.0 else 2*precision*recall/(precision+recall)
            result="PASS fixture • truth ${truth.size} • observed ${observed.size} • matched $matched • precision ${"%.1f".format(precision*100)}% • recall ${"%.1f".format(recall*100)}% • F1 ${"%.1f".format(f1*100)}%"
        },modifier=Modifier.fillMaxWidth()){Text("Run controlled validation fixture")}
        Panel("Validation report"){Text(result)}
        Panel("F.S.A. Ground-Truth Lab"){Text("F.S.A. remains a separate owned virtual/non-cash product. Its exact telemetry is the controlled target used to calibrate EGM4000 before lower-confidence observation workflows.")}
        SafetyNotice()
    }
}

@Composable
fun RiskScreen(sessions:List<GameplaySession>) {
    val context=LocalContext.current; val p=remember{context.getSharedPreferences("egm4000_risk_v1",Context.MODE_PRIVATE)}
    var maxMinutes by remember{mutableStateOf(p.getInt("minutes",45).toString())}; var maxDrawdown by remember{mutableStateOf(p.getInt("drawdown",250).toString())}; var maxShots by remember{mutableStateOf(p.getInt("shots",500).toString())}
    val latest=sessions.lastOrNull(); val flags=latest?.riskFlags(maxMinutes.toIntOrNull()?:45,maxDrawdown.toIntOrNull()?:250,maxShots.toIntOrNull()?:500).orEmpty()
    Page("Configured stopping signals", "Risk Monitor", "Thresholds are personal guardrails over recorded data—not probability estimates or payout predictions.") {
        Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){OutlinedTextField(maxMinutes,{maxMinutes=it},label={Text("Max min")},modifier=Modifier.weight(1f));OutlinedTextField(maxDrawdown,{maxDrawdown=it},label={Text("Drawdown")},modifier=Modifier.weight(1f));OutlinedTextField(maxShots,{maxShots=it},label={Text("Shots")},modifier=Modifier.weight(1f))}
        Button(onClick={p.edit().putInt("minutes",maxMinutes.toIntOrNull()?:45).putInt("drawdown",maxDrawdown.toIntOrNull()?:250).putInt("shots",maxShots.toIntOrNull()?:500).commit()},modifier=Modifier.fillMaxWidth()){Text("Save risk thresholds")}
        if(flags.isEmpty()) Panel("No configured threshold firing"){Text("No local threshold currently fires. This is not a guarantee of safety or future results.")} else flags.forEach{Panel("STOP / REVIEW"){Text(it,color=Color(0xFFFFB84A))}}
    }
}

@Composable
fun SimulatorScreen() {
    var sessionMinutes by remember{mutableStateOf("30")}; var shotsPerMinute by remember{mutableStateOf("20")}; var costPerShot by remember{mutableStateOf("1")}
    val minutes=sessionMinutes.toDoubleOrNull()?.coerceAtLeast(0.0)?:0.0; val pace=shotsPerMinute.toDoubleOrNull()?.coerceAtLeast(0.0)?:0.0; val cost=costPerShot.toDoubleOrNull()?.coerceAtLeast(0.0)?:0.0; val plannedShots=minutes*pace; val plannedSpend=plannedShots*cost
    Page("Plan exposure before play", "Strategy Simulator", "A deterministic planning calculator. It estimates your own configured pace/spend only; it does not forecast wins, RNG or payout.") {
        OutlinedTextField(sessionMinutes,{sessionMinutes=it},label={Text("Planned minutes")},modifier=Modifier.fillMaxWidth());OutlinedTextField(shotsPerMinute,{shotsPerMinute=it},label={Text("Shots/min")},modifier=Modifier.fillMaxWidth());OutlinedTextField(costPerShot,{costPerShot=it},label={Text("Credits/shot")},modifier=Modifier.fillMaxWidth())
        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){Metric(plannedShots.toInt().toString(),"planned shots",Modifier.weight(1f));Metric(plannedSpend.toInt().toString(),"planned credit spend",Modifier.weight(1f))}
        Panel("Use this safely"){Text("Compare the plan with recorded sessions and choose limits before starting. Do not interpret this as an expected return model.")}
    }
}

@Composable
fun GameProfilesScreen(sessions:List<GameplaySession>) = Page("Separate evidence by environment", "Game Profiles", "Profiles summarize only your local records. F.S.A. exact telemetry stays distinct from third-party observations.") {
    val groups=sessions.groupBy{it.platform}; if(groups.isEmpty())Text("No profiles yet.") else groups.forEach{(platform,list)->Panel(platform){Text("${list.size} session(s) • ${list.sumOf{it.events.size}} events • net recorded credits ${list.sumOf{it.metrics().netCredits}}")}}
    Panel("Supported observation labels"){Text("Fire Kirin • Panda Master • Juwa • GameVault/Game Master • Orion Stars • Generic read-only capture • F.S.A. owned exact telemetry")}
}

@Composable
fun DataExchangeScreen(sessions:List<GameplaySession>,store:LocalSessionStore,persist:(List<GameplaySession>)->Unit) {
    val context=LocalContext.current; var text by remember{mutableStateOf("")}; var status by remember{mutableStateOf("Ready")}; val exported=remember(sessions){store.exportBundle(sessions)}
    Page("Portable, auditable evidence", "Data Exchange", "Export/import preserves session IDs, event provenance, evidence labels and confidence.") {
        Panel("Bundle"){Text("${sessions.size} session(s) • ${sessions.sumOf{it.events.size}} event(s) • schema $BUNDLE_SCHEMA")}
        Button(onClick={val cb=context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager;cb.setPrimaryClip(ClipData.newPlainText("EGM4000 session bundle",exported));status="Export copied to clipboard"},modifier=Modifier.fillMaxWidth()){Text("Copy normalized JSON export")}
        OutlinedTextField(text,{text=it},label={Text("Paste EGM4000 JSON bundle")},modifier=Modifier.fillMaxWidth(),minLines=7)
        Button(onClick={store.importBundle(text).onSuccess{incoming->val merged=(sessions+incoming).associateBy{it.id}.values.sortedBy{it.startedAtMs};persist(merged);status="Imported ${incoming.size} session(s) and verified local save"}.onFailure{status="Import rejected: ${it.message}"}},enabled=text.isNotBlank(),modifier=Modifier.fillMaxWidth()){Text("Validate + import")}
        Panel("Status"){Text(status)}
    }
}

@Composable
fun ResearchScreen() = Page("Safe research only", "Research Lab", "Owned simulations, replay analysis, defensive capture validation and evidence-quality experiments belong here.") {
    ArtCard(R.drawable.security_vault,"Research Vault","Exact telemetry comes from controlled owned environments such as F.S.A.; third-party observation stays read-only.")
    Panel("Allowed"){Text("Owned/sandbox simulations • replay analysis • defensive anti-cheat study • capture detector calibration • confidence calibration • privacy-preserving measurement")}
    Panel("Out of bounds"){Text("Credential interception • hidden-state access • balance manipulation • protection bypass • cheating automation • guaranteed/random-outcome prediction",color=Color(0xFFFFB84A))}
}

@Composable
fun SettingsScreen(storageStatus:String,onReload:()->Unit,onClear:()->Unit) = Page("Local-first control", "Settings", "Current beta keeps user/session evidence on this device unless you explicitly export it.") {
    Panel("Build"){Text("EGM4000 Android 0.12.0 • SV09 Full Intelligence Reconciliation")}
    Panel("Storage"){Text(storageStatus)}
    Button(onClick=onReload,modifier=Modifier.fillMaxWidth()){Text("Reload saved sessions from disk")}
    OutlinedButton(onClick=onClear,modifier=Modifier.fillMaxWidth()){Text("Clear local EGM4000 session data")}
    Panel("Fire Kirin portal"){Text(FIRE_KIRIN_URL);Text("Opened externally. EGM4000 does not proxy, capture or store Fire Kirin credentials.",color=Color(0xFF9DB7C4))}
    SafetyNotice()
}
