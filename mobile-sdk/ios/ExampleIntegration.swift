/**
 * FMCWS iOS SDK — пример интеграции в банковское приложение
 * Файл: ExampleIntegration.swift
 */

import SwiftUI
import FMCWS

// ── 1. Инициализация (SwiftUI @main или AppDelegate) ─────────────────────────
@main
struct BankApp: App {
    init() {
        FmcwsSDK.shared.initialize(
            config: FmcwsConfig(
                apiURL:   URL(string: "https://fmcws.bank.by")!,
                apiKey:   Secrets.fmcwsApiKey,         // из .xcconfig / Keychain
                clientId: "anonymous",                  // обновляется после логина
                debug:    false
            )
        )
    }
    var body: some Scene { WindowGroup { RootView() } }
}

// ── 2. Реакция на предупреждения ───────────────────────────────────────────────
class AppDelegate: NSObject, UIApplicationDelegate, FmcwsWarningDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions _: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        FmcwsSDK.shared.warningDelegate = self
        return true
    }

    func fmcws(_ sdk: FmcwsSDK, didReceiveWarning warning: FmcwsWarning) {
        // Находим активный UIViewController и показываем alert
        guard let vc = UIApplication.shared.connectedScenes
            .compactMap({ ($0 as? UIWindowScene)?.keyWindow?.rootViewController })
            .first else { return }

        let (title, icon): (String, String)
        switch warning.level {
        case .critical: (title, icon) = ("Критическое предупреждение", "🚨")
        case .high:     (title, icon) = ("Подозрительная активность",  "🔶")
        case .medium:   (title, icon) = ("Внимание",                   "⚠️")
        case .low:      return
        }

        let alert = UIAlertController(
            title:   "\(icon) \(title)",
            message: warning.message,
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "Понятно", style: .default))
        if warning.level == .critical {
            alert.addAction(UIAlertAction(title: "Позвонить в банк", style: .destructive) { _ in
                // UIApplication.shared.open(URL(string: "tel:+375XXXXXXXXX")!)
            })
        }
        vc.present(alert, animated: true)
    }
}

// ── 3. Трекинг событий ────────────────────────────────────────────────────────
struct AuthService {
    func onLoginSuccess(pseudoClientId: String, isNewDevice: Bool) {
        FmcwsSDK.shared.identify(pseudoClientId)
        FmcwsSDK.shared.track("LOGIN_SUCCESS", extra: [
            "is_new_device": isNewDevice
        ])
    }
    func onLoginFail() { FmcwsSDK.shared.track("LOGIN_FAIL") }
    func onLogout()    { FmcwsSDK.shared.reset() }
}

struct TransferService {
    func onTransferCreate(amount: Double, currency: String, isNewRecipient: Bool) {
        FmcwsSDK.shared.track("TRANSFER_CREATE", extra: [
            "amount":           amount,
            "currency":         currency,
            "is_new_recipient": isNewRecipient,
        ])
    }
    func onTransferConfirm(transferId: String) {
        FmcwsSDK.shared.track("TRANSFER_CONFIRM", extra: ["transfer_id": transferId])
    }
    func onRecipientAdd(recipientHash: String) {
        FmcwsSDK.shared.track("RECIPIENT_ADD", extra: ["recipient_hash": recipientHash])
    }
}

struct ProfileService {
    func onPhoneChange()     { FmcwsSDK.shared.track("CONTACT_CHANGE", extra: ["field": "phone"]) }
    func onEmailChange()     { FmcwsSDK.shared.track("CONTACT_CHANGE", extra: ["field": "email"]) }
    func onLimitChange()     { FmcwsSDK.shared.track("LIMIT_CHANGE") }
    func onOtpRequest()      { FmcwsSDK.shared.track("OTP_REQUEST") }
    func onVirtualCardIssue(){ FmcwsSDK.shared.track("VIRTUAL_CARD_ISSUE") }
}
