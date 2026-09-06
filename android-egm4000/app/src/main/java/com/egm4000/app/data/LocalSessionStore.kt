package com.egm4000.app.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

class LocalSessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("egm4000_sessions_v3", Context.MODE_PRIVATE)
    private val primaryKey = "session_bundle_primary"
    private val backupKey = "session_bundle_backup"
    private val legacyKeys = listOf("sessions", "session_bundle")
    @Volatile private var lastFailure: String? = null

    fun loadSessions(): List<GameplaySession> {
        decodeEnvelope(prefs.getString(primaryKey, null))?.let { return it }
        decodeEnvelope(prefs.getString(backupKey, null))?.let { backup -> saveSessions(backup); return backup }
        for (key in legacyKeys) {
            val raw = prefs.getString(key, null) ?: continue
            decodeLegacy(raw)?.let { migrated -> saveSessions(migrated); return migrated }
        }
        return emptyList()
    }

    @Synchronized
    fun saveSessions(sessions: List<GameplaySession>): Boolean = runCatching {
        val current = prefs.getString(primaryKey, null)
        if (!current.isNullOrBlank()) check(prefs.edit().putString(backupKey, current).commit()) { "Could not write backup" }
        val envelope = encodeEnvelope(sessions)
        check(prefs.edit().putString(primaryKey, envelope).putLong("last_saved_at", System.currentTimeMillis()).putInt("last_saved_count", sessions.size).commit()) { "SharedPreferences commit returned false" }
        val verified = decodeEnvelope(prefs.getString(primaryKey, null)) ?: error("Written session bundle could not be decoded")
        check(verified.size == sessions.size) { "Session count verification failed" }
        if (sessions.isNotEmpty()) check(verified.last().id == sessions.last().id) { "Last session ID verification failed" }
        lastFailure = null; prefs.edit().remove("last_save_error").commit(); true
    }.getOrElse {
        lastFailure = it.message ?: it.javaClass.simpleName; prefs.edit().putString("last_save_error", lastFailure).commit(); false
    }

    fun clearAll(): Boolean = prefs.edit().clear().commit()

    fun storageStatus(): String {
        val count = prefs.getInt("last_saved_count", loadSessions().size); val at = prefs.getLong("last_saved_at", 0L)
        val error = lastFailure ?: prefs.getString("last_save_error", null)
        return when { error != null -> "Storage warning: $error"; at > 0 -> "Durable local storage: $count session(s) verified on disk"; count > 0 -> "Durable local storage: $count session(s) loaded"; else -> "Durable local storage ready; no saved sessions yet" }
    }

    fun exportBundle(sessions: List<GameplaySession>): String = JSONObject().apply {
        put("schema", BUNDLE_SCHEMA); put("exportedAtMs", System.currentTimeMillis()); put("sessions", JSONArray().apply { sessions.forEach { put(it.toJson()) } })
    }.toString(2)

    fun validateBundle(text: String): List<String> = runCatching {
        val root = JSONObject(text); val errors = mutableListOf<String>(); val schema = root.optString("schema")
        if (schema != BUNDLE_SCHEMA && schema != "egm4000.session-bundle.v2") errors += "Unsupported bundle schema: $schema"
        val sessions = root.optJSONArray("sessions") ?: return@runCatching listOf("Missing sessions array")
        for (i in 0 until sessions.length()) {
            val s = sessions.optJSONObject(i)
            if (s == null) { errors += "Session $i is not an object"; continue }
            if (s.optString("sessionId", s.optString("id")).isBlank()) errors += "Session $i missing ID"
            val events = s.optJSONArray("events") ?: JSONArray()
            for (j in 0 until events.length()) {
                val e = events.optJSONObject(j)
                if (e == null) { errors += "Session $i event $j invalid"; continue }
                val confidence = e.optDouble("confidence", -1.0)
                if (confidence !in 0.0..1.0) errors += "Session $i event $j confidence out of range"
            }
        }
        errors
    }.getOrElse { listOf(it.message ?: "Invalid JSON") }

    fun importBundle(text: String): Result<List<GameplaySession>> = runCatching {
        val errors = validateBundle(text); require(errors.isEmpty()) { errors.joinToString("; ") }
        val a = JSONObject(text).getJSONArray("sessions"); buildList { for (i in 0 until a.length()) add(sessionFromJson(a.getJSONObject(i))) }
    }

    private fun encodeEnvelope(sessions: List<GameplaySession>): String {
        val body = JSONObject().apply { put("schema", BUNDLE_SCHEMA); put("savedAtMs", System.currentTimeMillis()); put("sessions", JSONArray().apply { sessions.forEach { put(it.toJson()) } }) }.toString()
        return JSONObject().apply { put("format", "egm4000.local-envelope.v3"); put("sha256", sha256(body)); put("body", body) }.toString()
    }

    private fun decodeEnvelope(raw: String?): List<GameplaySession>? = runCatching {
        if (raw.isNullOrBlank()) return null
        val env = JSONObject(raw); val body = env.getString("body"); require(env.getString("sha256") == sha256(body)) { "Local session checksum mismatch" }
        val a = JSONObject(body).getJSONArray("sessions"); buildList { for (i in 0 until a.length()) add(sessionFromJson(a.getJSONObject(i))) }
    }.getOrNull()

    private fun decodeLegacy(raw: String): List<GameplaySession>? = runCatching {
        val a = if (raw.trim().startsWith("[")) JSONArray(raw) else JSONObject(raw).optJSONArray("sessions") ?: return@runCatching null
        buildList { for (i in 0 until a.length()) add(sessionFromJson(a.getJSONObject(i))) }
    }.getOrNull()

    private fun sha256(text: String): String = MessageDigest.getInstance("SHA-256").digest(text.toByteArray()).joinToString("") { "%02x".format(it) }
}
