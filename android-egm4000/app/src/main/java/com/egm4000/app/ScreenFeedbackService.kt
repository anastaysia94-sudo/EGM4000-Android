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
import kotlin.math.abs

class ScreenFeedbackService : Service() {
    private var projection: MediaProjection? = null
    private var imageReader: ImageReader? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var handlerThread: HandlerThread? = null
    private var handler: Handler? = null
    private var previousLuma: Double? = null
    private var sampleCount = 0L
    private var stopping = false

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(
            NOTIFICATION_ID,
            NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .setContentTitle("EGM4000 authorized screen feedback")
                .setContentText("Aggregate visual signals only; raw frames are not stored")
                .setOngoing(true)
                .build()
        )
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
                    // A malformed/transition frame is ignored. Raw frames are never persisted.
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
            .putLong("startedAtMs", System.currentTimeMillis())
            .apply()
    }

    private fun processImage(image: Image, width: Int, height: Int) {
        val plane = image.planes.firstOrNull() ?: return
        val buffer = plane.buffer
        val pixelStride = plane.pixelStride
        val rowStride = plane.rowStride
        if (pixelStride <= 0 || rowStride <= 0) return

        val stepX = (width / 24).coerceAtLeast(1)
        val stepY = (height / 24).coerceAtLeast(1)
        var lumaSum = 0.0
        var pixels = 0
        var y = 0

        while (y < height) {
            var x = 0
            while (x < width) {
                val offset = y * rowStride + x * pixelStride
                if (offset >= 0 && offset + 2 < buffer.limit()) {
                    val r = buffer.get(offset).toInt() and 0xff
                    val g = buffer.get(offset + 1).toInt() and 0xff
                    val b = buffer.get(offset + 2).toInt() and 0xff
                    lumaSum += (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
                    pixels++
                }
                x += stepX
            }
            y += stepY
        }

        if (pixels == 0) return
        val luma = lumaSum / pixels.toDouble()
        val motion = previousLuma?.let { abs(luma - it) } ?: 0.0
        previousLuma = luma
        sampleCount++

        capturePrefs().edit()
            .putFloat("brightness", luma.toFloat())
            .putFloat("motion", motion.toFloat())
            .putLong("updatedAtMs", System.currentTimeMillis())
            .putLong("sampleCount", sampleCount)
            .apply()
    }

    private fun capturePrefs() = getSharedPreferences("egm4000_capture_signals", MODE_PRIVATE)

    private fun stopCapture(stopProjection: Boolean = true) {
        if (stopping) return
        stopping = true
        capturePrefs().edit().putBoolean("active", false).apply()
        runCatching { virtualDisplay?.release() }
        virtualDisplay = null
        runCatching { imageReader?.setOnImageAvailableListener(null, null) }
        runCatching { imageReader?.close() }
        imageReader = null
        val p = projection
        projection = null
        if (stopProjection) runCatching { p?.stop() }
        previousLuma = null
        stopping = false
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "EGM4000 screen feedback",
                    NotificationManager.IMPORTANCE_LOW
                )
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
    }
}
