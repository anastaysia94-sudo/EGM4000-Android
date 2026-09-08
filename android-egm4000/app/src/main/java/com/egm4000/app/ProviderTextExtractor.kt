package com.egm4000.app

import android.graphics.Bitmap
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions

/**
 * Local, bundled OCR for user-visible provider HUD text.
 *
 * Results remain estimates. A value is surfaced only after it repeats across
 * frames so a single noisy OCR result cannot become an EGM4000 event.
 */
data class HudTextEstimate(
    val field: String,
    val value: String,
    val confidence: Double,
    val rawText: String,
    val stableFrames: Int
)

class ProviderTextExtractor {
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    private val lastValue = mutableMapOf<String, String>()
    private val stableCount = mutableMapOf<String, Int>()
    private var busy = false

    fun close() = recognizer.close()

    @Synchronized
    fun recognize(field: String, bitmap: Bitmap, qualityConfidence: Double, callback: (HudTextEstimate?) -> Unit): Boolean {
        if (busy) {
            bitmap.recycle()
            return false
        }
        busy = true
        recognizer.process(InputImage.fromBitmap(bitmap, 0))
            .addOnSuccessListener { result ->
                val raw = result.text.trim()
                val value = when (field) {
                    "credits" -> parseCreditCandidate(raw)
                    "weapon_level" -> parseWeaponCandidate(raw)
                    else -> null
                }
                val estimate = value?.let {
                    val previous = lastValue[field]
                    val streak = if (previous == it) (stableCount[field] ?: 0) + 1 else 1
                    lastValue[field] = it
                    stableCount[field] = streak

                    val labelBoost = when (field) {
                        "credits" -> if (Regex("(?i)credit|balance|coin|score|wallet").containsMatchIn(raw)) .08 else 0.0
                        "weapon_level" -> if (Regex("(?i)level|lvl|gun|cannon|weapon|bet").containsMatchIn(raw)) .08 else 0.0
                        else -> 0.0
                    }
                    val repetitionBoost = when {
                        streak >= 4 -> .24
                        streak == 3 -> .20
                        streak == 2 -> .14
                        else -> 0.0
                    }
                    val confidence = (.36 + labelBoost + repetitionBoost + qualityConfidence.coerceIn(.0, 1.0) * .22)
                        .coerceIn(.20, .92)
                    HudTextEstimate(field, it, confidence, raw.take(240), streak)
                }
                callback(estimate?.takeIf { it.stableFrames >= 2 && it.confidence >= .62 })
            }
            .addOnFailureListener { callback(null) }
            .addOnCompleteListener {
                bitmap.recycle()
                synchronized(this) { busy = false }
            }
        return true
    }

    companion object {
        internal fun parseCreditCandidate(raw: String): String? {
            if (raw.isBlank()) return null
            val candidates = Regex("(?<![A-Za-z])[-+]?\\$?\\d[\\d,]*(?:\\.\\d{1,2})?(?![A-Za-z])")
                .findAll(raw)
                .map { it.value.trim().removePrefix("$").replace(",", "") }
                .filter { token -> token.count { it.isDigit() } >= 2 }
                .filter { token -> token.toDoubleOrNull()?.let { it >= 0.0 && it < 1_000_000_000.0 } == true }
                .toList()
            return candidates.maxByOrNull { it.count(Char::isDigit) }
        }

        internal fun parseWeaponCandidate(raw: String): String? {
            if (raw.isBlank()) return null
            val explicit = listOf(
                Regex("(?i)(?:lvl|level|gun|cannon|weapon|bet)\\s*[:#x-]?\\s*(\\d{1,4})"),
                Regex("(?i)[x×]\\s*(\\d{1,4})"),
                Regex("(?i)(\\d{1,4})\\s*[x×]")
            ).firstNotNullOfOrNull { regex -> regex.find(raw)?.groupValues?.getOrNull(1) }
            if (explicit != null) return explicit
            val numbers = Regex("(?<!\\d)\\d{1,3}(?!\\d)").findAll(raw).map { it.value }.toList()
            return if (numbers.size == 1) numbers.first() else null
        }
    }
}
