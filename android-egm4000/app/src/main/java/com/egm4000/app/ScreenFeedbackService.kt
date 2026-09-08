package com.egm4000.app

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.egm4000.app.data.EvidenceKind
import com.egm4000.app.data.GameplayEvent
import com.egm4000.app.data.GameplaySession
import com.egm4000.app.data.LocalSessionStore
import kotlin.math.abs

/**
 * User-authorized, local-first screen observation service.
 *
 * Raw frames are never persisted. Frames are downsampled in memory into coarse
 * luminance grids, interpreted through a provider-specific adapter, normalized
 * into confidence-labelled EGM4000 events, and appended to durable local
 * session history. No provider credentials or hidden server state are accessed.
 */
class ScreenFeedbackService : Service() {
    private var projection: MediaProjection? = null
    private var imageReader: ImageReader? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var handlerThread: HandlerThread? = null
    private var handler: Handler? = null
    private var previousGrid: FloatArray? = null
    private var sampleCount = 0L
    private var stopping = false

    private var providerId = "fire_kirin"
    private var profile = ProviderVisualAdapters.profile(providerId)
    private var adapterState = AdapterRuntimeState()
    private var captureStartedAtMs = 0L
    private var activeSessionId: String? = null
    private val pendingEvents = mutableListOf<GameplayEvent>()
    private var lastFlushAtMs = 0L
    private var lastNotificationAtMs = 0L

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("Waiting for authorized gameplay capture"))
        handlerThread = HandlerThread("EGM4000Capture").also { it.start() }
        handler = Handler(handlerThread!!.looper)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopCapture()
            stopSelf()
            return START_NOT_STICKY
        }

        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
            ?: Activity.RESULT_CANCELED
        val resultData: Intent? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra(EXTRA_RESULT_DATA)
        }

        if (resultCode == Activity.RESULT_OK && resultData != null && projection == null) {
            startCapture(resultCode, resultData)
        }
        return START_STICKY
    }

    private fun startCapture(resultCode: Int, resultData: Intent) {
        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val mediaProjection = manager.getMediaProjection(resultCode, resultData) ?: return
        projection = mediaProjection

        providerId = getSharedPreferences("egm4000_provider", MODE_PRIVATE)
            .getString("selected_provider_id", "fire_kirin") ?: "fire_kirin"
        profile = ProviderVisualAdapters.profile(providerId)
        adapterState = AdapterRuntimeState()
        previousGrid = null
        sampleCount = 0L
        captureStartedAtMs = System.currentTimeMillis()
        lastFlushAtMs = captureStartedAtMs
        beginDurableSession()

        val metrics = resources.displayMetrics
        val width = metrics.widthPixels.coerceAtLeast(1)
        val height = metrics.heightPixels.coerceAtLeast(1)
        val density = metrics.densityDpi.coerceAtLeast(1)

        val reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        imageReader = reader

        val listener = ImageReader.OnImageAvailableListener { availableReader ->
            val image = availableReader.acquireLatestImage()
            if (image != null) {
                try {
                    processImage(image, width, height)
                } catch (_: Throwable) {
                    // Transition/malformed frames are ignored; raw frames are never persisted.
                } finally {
                    image.close()
                }
            }
        }
        reader.setOnImageAvailableListener(listener, handler)

        mediaProjection.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                if (!stopping) {
                    stopCapture(stopProjection = false)
                    stopSelf()
                }
            }
        }, handler)

        virtualDisplay = mediaProjection.createVirtualDisplay(
            "EGM4000Feedback",
            width,
            height,
            density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            reader.surface,
            null,
            handler
        )

        capturePrefs().edit()
            .putBoolean("active", true)
            .putString("providerId", providerId)
            .putString("providerName", profile.displayName)
            .putLong("startedAtMs", captureStartedAtMs)
            .apply()
        updateNotification("${profile.displayName}: authorized capture active")
    }

    private fun processImage(image: Image, width: Int, height: Int) {
        val grid = downsampleLuma(image, width, height, GRID_W, GRID_H) ?: return
        val prior = previousGrid
        val now = System.currentTimeMillis()
        val overall = observeRegion(grid, prior, NormalizedRoi(0.0, 0.0, 1.0, 1.0))
        val frame = VisualFrameObservations(
            overall = overall,
            credit = observeRegion(grid, prior, profile.creditHud),
            weapon = observeRegion(grid, prior, profile.weaponHud),
            target = observeRegion(grid, prior, profile.targetField),
            bonus = observeRegion(grid, prior, profile.bonusRegion),
            timestampMs = now
        )
        previousGrid = grid
        sampleCount++

        val output = ProviderVisualAdapters.analyze(profile, frame, adapterState, captureStartedAtMs)
        val normalized = output.events.map { event ->
            GameplayEvent(
                type = event.type,
                timestampMs = now,
                note = event.note,
                evidence = EvidenceKind.DEVICE_SIGNAL,
                confidence = event.confidence,
                payload = event.payload + mapOf(
                    "provider" to providerId,
                    "providerName" to profile.displayName,
                    "source" to "authorized_screen_capture"
                )
            )
        }
        if (normalized.isNotEmpty()) pendingEvents += normalized
        if (now - lastFlushAtMs >= 1500L || pendingEvents.size >= 12) flushPendingEvents()

        capturePrefs().edit()
            .putFloat("brightness", frame.overall.brightness.toFloat())
            .putFloat("motion", frame.overall.motion.toFloat())
            .putFloat("targetActivity", output.targetActivity.toFloat())
            .putFloat("shotRateEstimate", output.shotRateEstimate.toFloat())
            .putFloat("confidence", output.qualityConfidence.toFloat())
            .putString("latestTip", output.tip)
            .putString("latestEventType", output.events.lastOrNull()?.type.orEmpty())
            .putLong("updatedAtMs", now)
            .putLong("sampleCount", sampleCount)
            .apply()

        if (now - lastNotificationAtMs >= 2000L) {
            updateNotification(output.tip)
            lastNotificationAtMs = now
        }
    }

    private fun downsampleLuma(image: Image, width: Int, height: Int, gridW: Int, gridH: Int): FloatArray? {
        val plane = image.planes.firstOrNull() ?: return null
        val buffer = plane.buffer
        val pixelStride = plane.pixelStride
        val rowStride = plane.rowStride
        if (pixelStride <= 0 || rowStride <= 0) return null
        val result = FloatArray(gridW * gridH)
        for (gy in 0 until gridH) {
            val y = ((gy + 0.5) * height / gridH).toInt().coerceIn(0, height - 1)
            for (gx in 0 until gridW) {
                val x = ((gx + 0.5) * width / gridW).toInt().coerceIn(0, width - 1)
                val offset = y * rowStride + x * pixelStride
                if (offset >= 0 && offset + 2 < buffer.limit()) {
                    val r = buffer.get(offset).toInt() and 0xff
                    val g = buffer.get(offset + 1).toInt() and 0xff
                    val b = buffer.get(offset + 2).toInt() and 0xff
                    result[gy * gridW + gx] = ((0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0).toFloat()
                }
            }
        }
        return result
    }

    private fun observeRegion(current: FloatArray, prior: FloatArray?, roi: NormalizedRoi): RegionObservation {
        val x0 = (roi.left * GRID_W).toInt().coerceIn(0, GRID_W - 1)
        val x1 = (roi.right * GRID_W).toInt().coerceIn(x0 + 1, GRID_W)
        val y0 = (roi.top * GRID_H).toInt().coerceIn(0, GRID_H - 1)
        val y1 = (roi.bottom * GRID_H).toInt().coerceIn(y0 + 1, GRID_H)
        var brightness = 0.0
        var motion = 0.0
        var count = 0
        for (y in y0 until y1) {
            for (x in x0 until x1) {
                val i = y * GRID_W + x
                val value = current[i].toDouble()
                brightness += value
                if (prior != null && i < prior.size) motion += abs(value - prior[i].toDouble())
                count++
            }
        }
        if (count == 0) return RegionObservation(0.0, 0.0)
        return RegionObservation(brightness / count, motion / count)
    }

    private fun beginDurableSession() {
        val store = LocalSessionStore(applicationContext)
        val existing = store.loadSessions()
        val session = GameplaySession(
            platform = profile.displayName,
            startedAtMs = captureStartedAtMs,
            title = "${profile.displayName} authorized live observation",
            notes = "Created automatically from user-authorized screen capture. Visual events are confidence-labelled observations, not hidden provider telemetry."
        )
        if (store.saveSessions(existing + session)) activeSessionId = session.id
    }

    private fun flushPendingEvents() {
        if (pendingEvents.isEmpty()) return
        val id = activeSessionId ?: return
        val store = LocalSessionStore(applicationContext)
        val sessions = store.loadSessions().toMutableList()
        val index = sessions.indexOfFirst { it.id == id }
        if (index < 0) return
        val session = sessions[index]
        val batch = pendingEvents.toList()
        sessions[index] = session.copy(events = session.events + batch)
        if (store.saveSessions(sessions)) pendingEvents.clear()
        lastFlushAtMs = System.currentTimeMillis()
    }

    private fun finishDurableSession() {
        flushPendingEvents()
        val id = activeSessionId ?: return
        val store = LocalSessionStore(applicationContext)
        val sessions = store.loadSessions().toMutableList()
        val index = sessions.indexOfFirst { it.id == id }
        if (index >= 0) {
            val session = sessions[index]
            sessions[index] = session.copy(endedAtMs = System.currentTimeMillis())
            store.saveSessions(sessions)
        }
        activeSessionId = null
    }

    private fun capturePrefs() = getSharedPreferences("egm4000_capture_signals", MODE_PRIVATE)

    private fun stopCapture(stopProjection: Boolean = true) {
        if (stopping) return
        stopping = true
        finishDurableSession()
        capturePrefs().edit().putBoolean("active", false).apply()
        runCatching { virtualDisplay?.release() }
        virtualDisplay = null
        runCatching { imageReader?.setOnImageAvailableListener(null, null) }
        runCatching { imageReader?.close() }
        imageReader = null
        val p = projection
        projection = null
        if (stopProjection) runCatching { p?.stop() }
        previousGrid = null
        pendingEvents.clear()
        updateNotification("Capture stopped")
        stopping = false
    }

    private fun buildNotification(text: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setSmallIcon(android.R.drawable.ic_menu_view)
        .setContentTitle("EGM4000 live intelligence")
        .setContentText(text.take(120))
        .setStyle(NotificationCompat.BigTextStyle().bigText(text))
        .setOngoing(true)
        .setOnlyAlertOnce(true)
        .build()

    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "EGM4000 screen feedback", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    override fun onDestroy() {
        stopCapture()
        handlerThread?.quitSafely()
        handlerThread = null
        handler = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val ACTION_STOP = "com.egm4000.app.STOP_CAPTURE"
        const val EXTRA_RESULT_CODE = "resultCode"
        const val EXTRA_RESULT_DATA = "resultData"
        private const val CHANNEL_ID = "egm4000_capture"
        private const val NOTIFICATION_ID = 4000
        private const val GRID_W = 32
        private const val GRID_H = 18
    }
}
