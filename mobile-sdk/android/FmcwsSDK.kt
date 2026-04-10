/**
 * FMCWS Android SDK v1.0.0
 * Файл: FmcwsSDK.kt
 *
 * Размещение: fmcws-android-sdk/src/main/java/by/fmcws/sdk/FmcwsSDK.kt
 *
 * Подключение в build.gradle (app):
 *   implementation(files("libs/fmcws-sdk-1.0.0.aar"))
 *   implementation("com.squareup.okhttp3:okhttp:4.12.0")
 *   implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
 *
 * Инициализация (Application.onCreate или MainActivity):
 *   FmcwsSDK.init(FmcwsConfig(
 *       apiUrl  = "https://fmcws.bank.by",
 *       apiKey  = "YOUR_API_KEY",
 *       clientId = "PSEUDONYMIZED_CLIENT_ID"
 *   ))
 *
 * Отправка события:
 *   FmcwsSDK.track("TRANSFER_CREATE", mapOf("amount" to 1500.0, "currency" to "BYN"))
 */

package by.fmcws.sdk

import android.content.Context
import android.os.Build
import android.provider.Settings
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

// ── Config ────────────────────────────────────────────────────────────────────
data class FmcwsConfig(
    val apiUrl: String,
    val apiKey: String,
    val clientId: String,
    val debug: Boolean = false,
    val flushIntervalMs: Long = 5_000L,     // буферизация событий
    val maxQueueSize: Int = 100,
)

// ── Warning levels ─────────────────────────────────────────────────────────────
enum class FmcwsRiskLevel { LOW, MEDIUM, HIGH, CRITICAL }

data class FmcwsWarning(
    val level: FmcwsRiskLevel,
    val message: String,
    val recommendation: String,
)

// ── Warning callback ───────────────────────────────────────────────────────────
interface FmcwsWarningListener {
    fun onWarning(warning: FmcwsWarning)
}

// ── SDK Singleton ──────────────────────────────────────────────────────────────
object FmcwsSDK {
    private const val TAG = "FMCWS"
    private const val PREF_SESSION = "fmcws_session_id"

    private lateinit var config: FmcwsConfig
    private lateinit var context: Context
    private lateinit var sessionId: String
    private lateinit var deviceId: String

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val queue = LinkedBlockingQueue<JSONObject>(500)
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private var warningListener: FmcwsWarningListener? = null
    private var initialized = false

    // ── Инициализация ──────────────────────────────────────────────────────────
    fun init(appContext: Context, cfg: FmcwsConfig) {
        if (initialized) return
        context = appContext.applicationContext
        config = cfg

        sessionId = getOrCreateSessionId()
        deviceId  = getDeviceId()

        // Запуск фонового воркера отправки
        startFlushWorker()
        initialized = true
        log("SDK initialized | session=$sessionId | device=$deviceId")
    }

    fun setWarningListener(listener: FmcwsWarningListener) {
        warningListener = listener
    }

    // ── Публичное API ──────────────────────────────────────────────────────────
    fun track(eventType: String, extra: Map<String, Any?> = emptyMap()) {
        checkInit()
        val payload = buildPayload(eventType, extra)
        if (queue.size >= config.maxQueueSize) {
            log("Queue full, dropping oldest event")
            queue.poll()
        }
        queue.offer(payload)
        log("Queued: $eventType (queue size=${queue.size})")
    }

    /** Обновить clientId после входа в аккаунт */
    fun identify(clientId: String) {
        config = config.copy(clientId = clientId)
    }

    /** Сбросить сессию (выход из аккаунта) */
    fun reset() {
        context.getSharedPreferences("fmcws", Context.MODE_PRIVATE)
            .edit().remove(PREF_SESSION).apply()
        sessionId = createNewSession()
        log("Session reset: $sessionId")
    }

    // ── Payload builder ────────────────────────────────────────────────────────
    private fun buildPayload(eventType: String, extra: Map<String, Any?>): JSONObject {
        val extraJson = JSONObject()
        extra.forEach { (k, v) -> extraJson.put(k, v) }

        return JSONObject().apply {
            put("session_id",          sessionId)
            put("client_id",           config.clientId)
            put("event_type",          eventType)
            put("channel",             "android")
            put("device_fingerprint",  deviceId)
            put("user_agent",          buildUserAgent())
            put("extra",               extraJson)
        }
    }

    private fun buildUserAgent(): String {
        return "FmcwsAndroidSDK/1.0.0 " +
               "Android/${Build.VERSION.RELEASE} " +
               "SDK/${Build.VERSION.SDK_INT} " +
               "${Build.MANUFACTURER}/${Build.MODEL}"
    }

    // ── Flush worker ───────────────────────────────────────────────────────────
    private fun startFlushWorker() {
        scope.launch {
            while (isActive) {
                delay(config.flushIntervalMs)
                flush()
            }
        }
    }

    private suspend fun flush() {
        while (queue.isNotEmpty()) {
            val payload = queue.peek() ?: break
            val success = sendEvent(payload)
            if (success) {
                queue.poll()
            } else {
                // Не удаляем из очереди — повторим на следующем цикле
                delay(3_000)
                break
            }
        }
    }

    // ── HTTP отправка ──────────────────────────────────────────────────────────
    private suspend fun sendEvent(payload: JSONObject): Boolean = withContext(Dispatchers.IO) {
        val url = config.apiUrl.trimEnd('/') + "/v1/events"
        val body = payload.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(url)
            .post(body)
            .header("X-API-Key", config.apiKey)
            .header("X-SDK-Version", "android-1.0.0")
            .build()

        return@withContext try {
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val json = JSONObject(response.body?.string() ?: "{}")
                    handleResponse(json)
                    true
                } else {
                    log("HTTP error: ${response.code}")
                    false
                }
            }
        } catch (e: IOException) {
            log("Network error: ${e.message}")
            false
        }
    }

    // ── Обработка ответа (предупреждение) ──────────────────────────────────────
    private fun handleResponse(json: JSONObject) {
        val showWarning = json.optBoolean("show_warning", false)
        if (!showWarning) return

        val level = when (json.optString("risk_level")) {
            "critical" -> FmcwsRiskLevel.CRITICAL
            "high"     -> FmcwsRiskLevel.HIGH
            "medium"   -> FmcwsRiskLevel.MEDIUM
            else       -> FmcwsRiskLevel.LOW
        }
        val message = json.optString("warning_message", "")
        if (message.isBlank()) return

        val warning = FmcwsWarning(level, message, json.optString("recommendation", ""))
        log("Warning received: $level — $message")

        // Callback в main thread
        CoroutineScope(Dispatchers.Main).launch {
            warningListener?.onWarning(warning)
        }
    }

    // ── Device ID (псевдонимизированный) ──────────────────────────────────────
    private fun getDeviceId(): String {
        val androidId = Settings.Secure.getString(
            context.contentResolver, Settings.Secure.ANDROID_ID
        ) ?: UUID.randomUUID().toString()

        // SHA-256 для псевдонимизации
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(("fmcws_$androidId").toByteArray())
        return "adv_" + hash.take(8).joinToString("") { "%02x".format(it) }
    }

    // ── Session ID ─────────────────────────────────────────────────────────────
    private fun getOrCreateSessionId(): String {
        val prefs = context.getSharedPreferences("fmcws", Context.MODE_PRIVATE)
        return prefs.getString(PREF_SESSION, null) ?: createNewSession()
    }

    private fun createNewSession(): String {
        val sid = UUID.randomUUID().toString()
        context.getSharedPreferences("fmcws", Context.MODE_PRIVATE)
            .edit().putString(PREF_SESSION, sid).apply()
        return sid
    }

    private fun checkInit() {
        check(initialized) { "[FMCWS] Call FmcwsSDK.init() before tracking events" }
    }

    private fun log(msg: String) {
        if (config.debug) Log.d(TAG, msg)
    }
}
