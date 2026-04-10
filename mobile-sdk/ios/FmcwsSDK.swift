/**
 * FMCWS iOS SDK v1.0.0
 * Файл: FmcwsSDK.swift
 *
 * Размещение: FMCWS.xcframework (встраивается в проект банка)
 *
 * Подключение (Package.swift / CocoaPods / прямое встраивание XCFramework):
 *   Скопировать FMCWS.xcframework в проект → General → Frameworks → Embed & Sign
 *
 * Swift Package Manager (Package.swift):
 *   .binaryTarget(name: "FMCWS", path: "FMCWS.xcframework")
 *
 * Инициализация (AppDelegate.swift или @main):
 *   FmcwsSDK.shared.initialize(
 *     config: FmcwsConfig(
 *       apiURL:   URL(string: "https://fmcws.bank.by")!,
 *       apiKey:   "YOUR_API_KEY",
 *       clientId: "PSEUDONYMIZED_CLIENT_ID"
 *     )
 *   )
 *
 * Трекинг события:
 *   FmcwsSDK.shared.track("TRANSFER_CREATE", extra: ["amount": 1500.0])
 */

import Foundation
import UIKit
import CryptoKit

// ── Config ────────────────────────────────────────────────────────────────────
public struct FmcwsConfig {
    public let apiURL:         URL
    public let apiKey:         String
    public var clientId:       String
    public let debug:          Bool
    public let flushInterval:  TimeInterval   // секунды между flush (default 5)
    public let maxQueueSize:   Int

    public init(
        apiURL:        URL,
        apiKey:        String,
        clientId:      String,
        debug:         Bool         = false,
        flushInterval: TimeInterval = 5.0,
        maxQueueSize:  Int          = 100
    ) {
        self.apiURL        = apiURL
        self.apiKey        = apiKey
        self.clientId      = clientId
        self.debug         = debug
        self.flushInterval = flushInterval
        self.maxQueueSize  = maxQueueSize
    }
}

// ── Risk / Warning ─────────────────────────────────────────────────────────────
public enum FmcwsRiskLevel: String {
    case low, medium, high, critical
}

public struct FmcwsWarning {
    public let level:          FmcwsRiskLevel
    public let message:        String
    public let recommendation: String
}

public protocol FmcwsWarningDelegate: AnyObject {
    func fmcws(_ sdk: FmcwsSDK, didReceiveWarning warning: FmcwsWarning)
}

// ── SDK ────────────────────────────────────────────────────────────────────────
public final class FmcwsSDK {

    // MARK: – Singleton
    public static let shared = FmcwsSDK()
    private init() {}

    // MARK: – State
    private var config: FmcwsConfig?
    private var sessionId: String = ""
    private var deviceId:  String = ""

    private var queue: [[String: Any]] = []
    private let queueLock = NSLock()
    private var flushTimer: Timer?

    private let session = URLSession(configuration: {
        let c = URLSessionConfiguration.default
        c.timeoutIntervalForRequest  = 10
        c.timeoutIntervalForResource = 10
        return c
    }())

    public weak var warningDelegate: FmcwsWarningDelegate?

    // MARK: – Init
    public func initialize(config: FmcwsConfig) {
        guard self.config == nil else { return }
        self.config    = config
        self.sessionId = getOrCreateSessionId()
        self.deviceId  = makeDeviceId()
        startFlushTimer()
        log("SDK initialized | session=\(sessionId) | device=\(deviceId)")
    }

    // MARK: – Public API

    /// Отправить событие (неблокирующий — кладёт в очередь)
    public func track(_ eventType: String, extra: [String: Any] = [:]) {
        guard let config = config else {
            assertionFailure("[FMCWS] Call initialize(config:) first")
            return
        }
        let payload: [String: Any] = [
            "session_id":         sessionId,
            "client_id":          config.clientId,
            "event_type":         eventType,
            "channel":            "ios",
            "device_fingerprint": deviceId,
            "user_agent":         makeUserAgent(),
            "extra":              extra,
        ]
        queueLock.lock()
        if queue.count >= (config.maxQueueSize) { queue.removeFirst() }
        queue.append(payload)
        queueLock.unlock()
        log("Queued: \(eventType) (queue=\(queue.count))")
    }

    /// Обновить clientId после авторизации
    public func identify(_ clientId: String) {
        config?.clientId = clientId
    }

    /// Сбросить сессию при выходе
    public func reset() {
        UserDefaults.standard.removeObject(forKey: "fmcws_session_id")
        sessionId = createNewSession()
        log("Session reset: \(sessionId)")
    }

    // MARK: – Flush

    private func startFlushTimer() {
        let interval = config?.flushInterval ?? 5.0
        DispatchQueue.main.async {
            self.flushTimer = Timer.scheduledTimer(
                withTimeInterval: interval, repeats: true
            ) { [weak self] _ in self?.flush() }
        }
    }

    private func flush() {
        queueLock.lock()
        guard !queue.isEmpty else { queueLock.unlock(); return }
        let payload = queue.first!
        queueLock.unlock()

        sendEvent(payload) { [weak self] success in
            guard let self = self else { return }
            if success {
                self.queueLock.lock()
                if !self.queue.isEmpty { self.queue.removeFirst() }
                self.queueLock.unlock()
                // Рекурсивно отправляем оставшиеся
                if !self.queue.isEmpty { self.flush() }
            }
        }
    }

    // MARK: – HTTP

    private func sendEvent(_ payload: [String: Any], completion: @escaping (Bool) -> Void) {
        guard let config = config else { return }
        let url = config.apiURL.appendingPathComponent("/v1/events")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(config.apiKey, forHTTPHeaderField: "X-API-Key")
        request.setValue("ios-1.0.0", forHTTPHeaderField: "X-SDK-Version")

        guard let body = try? JSONSerialization.data(withJSONObject: payload) else {
            completion(false); return
        }
        request.httpBody = body

        session.dataTask(with: request) { [weak self] data, response, error in
            if let error = error {
                self?.log("Network error: \(error.localizedDescription)")
                completion(false); return
            }
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                self?.log("HTTP error")
                completion(false); return
            }
            if let data = data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                self?.handleResponse(json)
            }
            completion(true)
        }.resume()
    }

    // MARK: – Response handling

    private func handleResponse(_ json: [String: Any]) {
        guard json["show_warning"] as? Bool == true else { return }
        let levelStr = json["risk_level"] as? String ?? "low"
        let level: FmcwsRiskLevel = FmcwsRiskLevel(rawValue: levelStr) ?? .low
        guard level != .low, let message = json["warning_message"] as? String, !message.isEmpty else { return }

        let warning = FmcwsWarning(
            level:          level,
            message:        message,
            recommendation: json["recommendation"] as? String ?? ""
        )
        log("Warning: \(level.rawValue) — \(message)")
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.warningDelegate?.fmcws(self, didReceiveWarning: warning)
        }
    }

    // MARK: – Device ID (псевдонимизированный SHA-256)

    private func makeDeviceId() -> String {
        let raw = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
        let salted = "fmcws_\(raw)".data(using: .utf8)!
        let hash = SHA256.hash(data: salted)
        let hex = hash.prefix(8).map { String(format: "%02x", $0) }.joined()
        return "idfv_\(hex)"
    }

    // MARK: – Session

    private func getOrCreateSessionId() -> String {
        if let sid = UserDefaults.standard.string(forKey: "fmcws_session_id") { return sid }
        return createNewSession()
    }

    private func createNewSession() -> String {
        let sid = UUID().uuidString
        UserDefaults.standard.set(sid, forKey: "fmcws_session_id")
        return sid
    }

    // MARK: – User-Agent

    private func makeUserAgent() -> String {
        let info = Bundle.main
        let appName    = info.infoDictionary?["CFBundleName"] as? String ?? "BankApp"
        let appVersion = info.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
        let osVersion  = UIDevice.current.systemVersion
        let model      = UIDevice.current.model
        return "FmcwsiOSSDK/1.0.0 \(appName)/\(appVersion) iOS/\(osVersion) \(model)"
    }

    private func log(_ msg: String) {
        if config?.debug == true { print("[FMCWS] \(msg)") }
    }
}
