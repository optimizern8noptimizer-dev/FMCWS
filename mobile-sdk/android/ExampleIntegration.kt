/**
 * FMCWS Android SDK — пример интеграции в банковское приложение
 * Файл: ExampleIntegration.kt
 */

package by.fmcws.example

import android.app.Application
import android.app.AlertDialog
import android.content.Context
import by.fmcws.sdk.*

// ── 1. Инициализация в Application ────────────────────────────────────────────
class BankApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        FmcwsSDK.init(
            appContext = this,
            cfg = FmcwsConfig(
                apiUrl   = "https://fmcws.bank.by",
                apiKey   = BuildConfig.FMCWS_API_KEY,   // из gradle.properties
                clientId = "anonymous",                  // обновляется после логина
                debug    = BuildConfig.DEBUG,
            )
        )
    }
}

// ── 2. Реакция на предупреждения ───────────────────────────────────────────────
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Регистрируем listener
        FmcwsSDK.setWarningListener(object : FmcwsWarningListener {
            override fun onWarning(warning: FmcwsWarning) {
                showFraudWarningDialog(warning)
            }
        })
    }

    private fun showFraudWarningDialog(warning: FmcwsWarning) {
        val (title, icon) = when (warning.level) {
            FmcwsRiskLevel.CRITICAL -> "Критическое предупреждение" to "🚨"
            FmcwsRiskLevel.HIGH     -> "Подозрительная активность"  to "🔶"
            FmcwsRiskLevel.MEDIUM   -> "Внимание"                   to "⚠️"
            FmcwsRiskLevel.LOW      -> return   // LOW не показываем
        }
        AlertDialog.Builder(this)
            .setTitle("$icon $title")
            .setMessage(warning.message)
            .setPositiveButton("Понятно") { d, _ -> d.dismiss() }
            .apply {
                if (warning.level == FmcwsRiskLevel.CRITICAL) {
                    setNeutralButton("Позвонить в банк") { _, _ ->
                        // startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:+375XXXXXXXXX")))
                    }
                }
            }
            .setCancelable(warning.level != FmcwsRiskLevel.CRITICAL)
            .show()
    }
}

// ── 3. Трекинг событий в нужных местах ────────────────────────────────────────
class AuthRepository {
    fun onLoginSuccess(pseudoClientId: String, isNewDevice: Boolean) {
        FmcwsSDK.identify(pseudoClientId)
        FmcwsSDK.track("LOGIN_SUCCESS", mapOf(
            "is_new_device" to isNewDevice,
        ))
    }
    fun onLoginFail() = FmcwsSDK.track("LOGIN_FAIL")
    fun onLogout()    { FmcwsSDK.reset() }
}

class TransferRepository {
    fun onTransferCreate(amount: Double, currency: String, isNewRecipient: Boolean) {
        FmcwsSDK.track("TRANSFER_CREATE", mapOf(
            "amount"          to amount,
            "currency"        to currency,
            "is_new_recipient" to isNewRecipient,
        ))
    }
    fun onTransferConfirm(transferId: String) {
        FmcwsSDK.track("TRANSFER_CONFIRM", mapOf("transfer_id" to transferId))
    }
    fun onRecipientAdd(recipientHash: String) {
        FmcwsSDK.track("RECIPIENT_ADD", mapOf("recipient_hash" to recipientHash))
    }
}

class ProfileRepository {
    fun onPhoneChange()  = FmcwsSDK.track("CONTACT_CHANGE", mapOf("field" to "phone"))
    fun onEmailChange()  = FmcwsSDK.track("CONTACT_CHANGE", mapOf("field" to "email"))
    fun onLimitChange()  = FmcwsSDK.track("LIMIT_CHANGE")
    fun onOtpRequest()   = FmcwsSDK.track("OTP_REQUEST")
    fun onOtpConfirm()   = FmcwsSDK.track("OTP_CONFIRM")
    fun onVirtualCardIssue() = FmcwsSDK.track("VIRTUAL_CARD_ISSUE")
}
