package com.egm4000.app

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlin.math.abs

class ScreenFeedbackService : Service() {
    private var projection: MediaProjection? = null
    private var reader: ImageReader? = null
    private var previousLuma: Double? = null
    private var sampleCount = 0L

    override fun onCreate() {
        super.onCreate()
        val channelId = "egm4000_capture"
        if (Build.VERSION.SDK_INT >= 26) {
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(NotificationChannel(channelId, "EGM4000 screen feedback", NotificationManager.IMPORTANCE_LOW))
        }
        startForeground(4000, NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .setContentTitle("EGM4000 authorized screen feedback")
            .setContentText("Aggregate visual signals only; raw frames are not stored")
            .setOngoing(true).build())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopCapture(); stopSelf(); return START_NOT_STICKY
        }
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED) ?: Activity.RESULT_CANCELED
        val data = if (Build.VERSION.SDK_INT >= 33) intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        else @Suppress("DEPRECATION") intent?.getParcelableExtra(EXTRA_RESULT_DATA)
        if (resultCode == Activity.RESULT_OK && data != null && projection == null) startCapture(resultCode, data)
        return START_STICKY
    }

    private fun startCapture(resultCode: Int, data: Intent) {
        val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        projection = mgr.getMediaProjection(resultCode, data)
        val dm = resources.displayMetrics
        val width = dm.widthPixels.coerceAtLeast(1)
        val height = dm.heightPixels.coerceAtLeast(1)
        reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2).also { imageReader ->
            imageReader.setOnImageAvailableListener({ r ->
                val image = r.acquireLatestImage() ?: return@setOnImageAvailableListener
                try {
                    val plane = image.planes.firstOrNull() ?: return@try
                    val buffer = plane.buffer
                    val pixelStride = plane.pixelStride
                    val rowStride = plane.rowStride
                    val stepX = (width / 24).coerceAtLeast(1)
                    val stepY = (height / 24).coerceAtLeast(1)
                    var sum = 0.0
                    var count = 0
                    var y = 0
                    while (y < height) {
                        var x = 0
                        while (x < width) {
                            val offset = y * rowStride + x * pixelStride
                            if (offset + 2 < buffer.limit()) {
                                val b = buffer.get(offset).toInt() and 0xff
                                val g = buffer.get(offset + 1).toInt() and 0xff
                                val rr = buffer.get(offset + 2).toInt() and 0xff
                                sum += (0.2126 * rr + 0.7152 * g + 0.0722 * b) / 255.0
                                count++
                            }
                            x += stepX
                        }
                        y += stepY
                    }
                    if (count > 0) {
                        val luma = sum / count
                        val motion = previousLuma?.let { abs(luma - it) } ?: 0.0
                        previousLuma = luma
                        sampleCount++
                        getSharedPreferences("egm4000_capture_signals", MODE_PRIVATE).edit()
                            .putFloat("brightness", luma.toFloat())
                            .putFloat("motion", motion.toFloat())
                            .putLong("updatedAtMs", System.currentTimeMillis())
                            .putLong("sampleCount", sampleCount)
                            .apply()
                    }
                } finally { image.close() }
            }, null)
        }
        projection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() { stopCapture(); stopSelf() }
        }, null)
        projection?.createVirtualDisplay(
            "EGM4000Feedback", width, height, dm.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            reader?.surface, null, null
        )
        getSharedPreferences("egm4000_capture_signals", MODE_PRIVATE).edit().putBoolean("active", true).apply()
    }

    private fun stopCapture() {
        getSharedPreferences("egm4000_capture_signals", MODE_PRIVATE).edit().putBoolean("active", false).apply()
        runCatching { reader?.close() }; reader = null
        runCatching { projection?.stop() }; projection = null
    }

    override fun onDestroy() { stopCapture(); super.onDestroy() }
    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val ACTION_STOP = "com.egm4000.app.STOP_CAPTURE"
        const val EXTRA_RESULT_CODE = "resultCode"
        const val EXTRA_RESULT_DATA = "resultData"
    }
}
