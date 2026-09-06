package com.egm4000.app

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.egm4000.app.data.GameplaySession
import com.egm4000.app.data.LocalSessionStore

const val FIRE_KIRIN_URL = "https://play.firekirin.xyz/web_game/firekirin777_pc/index.html"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { EGM4000Theme { EGM4000App() } }
    }
}

enum class Screen(val label: String) {
    TUTORIAL("Guided Tutorial"), COMMAND("Command Center"), SESSION("Live Session"), CAPTURE("Live Capture"),
    EVENTS("Event Stream"), METRICS("Live Metrics"), PATTERN("Pattern Lab"), COACH("AI Coach"),
    TIPS("Tips Center"), ALERTS("Alerts"), REPLAY("Replay Lab"), EXPERIMENT("Experiment Lab"),
    VALIDATION("Capture Validation"), RISK("Risk Monitor"), SIMULATOR("Strategy Simulator"),
    PROFILES("Game Profiles"), COMMUNITY("Community"), SURVEYS("Surveys"), DATA("Data Exchange"),
    RESEARCH("Research Lab"), CHECKLIST("Build Checklist"), SETTINGS("Settings"), FIRE_KIRIN("Fire Kirin Companion")
}

data class EGMState(
    val sessions: List<GameplaySession>,
    val screen: Screen = Screen.COMMAND,
    val selectedSessionId: String? = sessions.lastOrNull()?.id,
    val storageStatus: String = ""
)

@Composable
fun EGM4000Theme(content: @Composable () -> Unit) {
    val scheme = darkColorScheme(
        primary = Color(0xFF00F2FF), secondary = Color(0xFF00D4C8), tertiary = Color(0xFF7A28FF),
        background = Color(0xFF060B14), surface = Color(0xFF0F1116), onBackground = Color(0xFFEEFCFF),
        onSurface = Color(0xFFEEFCFF), error = Color(0xFFFF5C57)
    )
    MaterialTheme(colorScheme = scheme, content = content)
}

@Composable
fun EGM4000App() {
    val context = LocalContext.current
    val store = remember { LocalSessionStore(context.applicationContext) }
    val appPrefs = remember { context.getSharedPreferences("egm4000_app_v1", Context.MODE_PRIVATE) }
    val initialScreen = if (appPrefs.getBoolean("tutorial_complete", false)) Screen.COMMAND else Screen.TUTORIAL
    var state by remember {
        mutableStateOf(
            EGMState(
                sessions = store.loadSessions(),
                screen = initialScreen,
                storageStatus = store.storageStatus()
            )
        )
    }
    var message by remember { mutableStateOf<String?>(null) }

    fun navigate(next: Screen) {
        state = state.copy(screen = next)
    }

    fun persist(next: List<GameplaySession>) {
        val ok = store.saveSessions(next)
        val loaded = if (ok) store.loadSessions() else next
        state = state.copy(
            sessions = loaded,
            selectedSessionId = loaded.lastOrNull()?.id,
            storageStatus = store.storageStatus()
        )
        message = if (ok) "Session data saved and verified on disk." else store.storageStatus()
    }

    val captureLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val svc = Intent(context, ScreenFeedbackService::class.java)
                .putExtra(ScreenFeedbackService.EXTRA_RESULT_CODE, result.resultCode)
                .putExtra(ScreenFeedbackService.EXTRA_RESULT_DATA, result.data)
            context.startForegroundService(svc)
            message = "Authorized screen feedback started. Aggregate signals only; raw frames are not saved."
        } else {
            message = "Screen feedback was not authorized."
        }
    }

    fun startCapture() {
        val mgr = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        captureLauncher.launch(mgr.createScreenCaptureIntent())
    }

    fun stopCapture() {
        context.startService(Intent(context, ScreenFeedbackService::class.java).setAction(ScreenFeedbackService.ACTION_STOP))
        message = "Screen feedback stopped."
    }

    fun openFireKirin() {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(FIRE_KIRIN_URL)))
    }

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            Column(Modifier.background(Color(0xEE071219)).padding(horizontal = 12.dp, vertical = 8.dp)) {
                Text("EGM4000 // EduGameMaster 4000", color = Color(0xFF00F2FF), fontWeight = FontWeight.Black)
                Text("Watch. Measure. Explain. Improve.  •  SV09 Full Intelligence Beta", style = MaterialTheme.typography.bodySmall, color = Color(0xFF8BA3AD))
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Screen.entries.forEach { s ->
                        FilterChip(
                            selected = state.screen == s,
                            onClick = { navigate(s) },
                            label = { Text(s.label) }
                        )
                    }
                }
            }
        }
    ) { pad ->
        Box(
            Modifier.fillMaxSize().padding(pad).background(
                Brush.verticalGradient(listOf(Color(0xFF06101A), Color(0xFF060B14), Color(0xFF0A1018)))
            )
        ) {
            when (state.screen) {
                Screen.TUTORIAL -> TutorialScreen(
                    onComplete = {
                        appPrefs.edit().putBoolean("tutorial_complete", true).commit()
                        message = "Tutorial complete. EGM4000 is ready."
                        navigate(Screen.COMMAND)
                    },
                    onNavigate = ::navigate
                )
                Screen.COMMAND -> CommandCenterScreen(state, onNavigate = ::navigate, onOpenFireKirin = ::openFireKirin)
                Screen.SESSION -> SessionScreen(state.sessions, ::persist, state.storageStatus)
                Screen.CAPTURE -> CaptureScreen(onStart = ::startCapture, onStop = ::stopCapture)
                Screen.EVENTS -> EventStreamScreen(state.sessions)
                Screen.METRICS -> MetricsScreen(state.sessions)
                Screen.PATTERN -> PatternLabScreen(state.sessions)
                Screen.COACH -> CoachScreen(state.sessions)
                Screen.TIPS -> TipsScreen(state.sessions)
                Screen.ALERTS -> AlertsScreen(state.sessions)
                Screen.REPLAY -> ReplayScreen(state.sessions)
                Screen.EXPERIMENT -> ExperimentScreen()
                Screen.VALIDATION -> ValidationScreen()
                Screen.RISK -> RiskScreen(state.sessions)
                Screen.SIMULATOR -> SimulatorScreen()
                Screen.PROFILES -> GameProfilesScreen(state.sessions)
                Screen.COMMUNITY -> CommunityScreen()
                Screen.SURVEYS -> SurveysScreen()
                Screen.DATA -> DataExchangeScreen(state.sessions, store, ::persist)
                Screen.RESEARCH -> ResearchScreen()
                Screen.CHECKLIST -> BuildChecklistScreen(state.sessions, state.storageStatus)
                Screen.SETTINGS -> SettingsScreen(
                    state.storageStatus,
                    onReload = {
                        val loaded = store.loadSessions()
                        state = state.copy(sessions = loaded, storageStatus = store.storageStatus())
                        message = "Reloaded ${loaded.size} saved session(s)."
                    },
                    onClear = {
                        store.clearAll()
                        state = state.copy(sessions = emptyList(), storageStatus = store.storageStatus())
                        message = "Local EGM4000 session data cleared."
                    }
                )
                Screen.FIRE_KIRIN -> FireKirinScreen(onOpen = ::openFireKirin, onCapture = ::startCapture, sessions = state.sessions)
            }
            message?.let {
                Snackbar(Modifier.padding(16.dp).align(androidx.compose.ui.Alignment.BottomCenter)) { Text(it) }
            }
        }
    }
}
