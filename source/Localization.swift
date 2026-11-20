import AppKit
import Foundation

enum NoYouPubPaths {
    static var dataRoot: URL {
        if let path = ProcessInfo.processInfo.environment["NOYOUPUB_DATA_DIR"] { return URL(fileURLWithPath: path) }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/NoYouPub")
    }
}

final class LanguageStore {
    static let shared = LanguageStore()
    var preference: String {
        let url = NoYouPubPaths.dataRoot.appendingPathComponent("config/preferences.json")
        guard let data = try? Data(contentsOf: url), let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return "system" }
        return value["language"] as? String ?? "system"
    }
    var language: String {
        let choice = preference
        if ["fr", "en"].contains(choice) { return choice }
        return (Locale.preferredLanguages.first ?? "en").hasPrefix("fr") ? "fr" : "en"
    }
    private var catalogs: [String: [String: String]] = [:]
    func catalog(_ language: String) -> [String: String] {
        if let saved = catalogs[language] { return saved }
        let folder = ProcessInfo.processInfo.environment["NOYOUPUB_LOCALES_DIR"].map { URL(fileURLWithPath: $0) } ?? Bundle.main.resourceURL!.appendingPathComponent("locales")
        let value = (try? Data(contentsOf: folder.appendingPathComponent(language + ".json"))).flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: String] } ?? [:]
        catalogs[language] = value
        return value
    }
    func translate(_ value: String) -> String {
        let target = catalog(language), french = catalog("fr"), english = catalog("en")
        if let exact = target[value] { return exact }
        for (key, text) in english where text == value { return target[key] ?? key }
        for origin in [french, english] {
            for (key, text) in origin {
                let slot = try! NSRegularExpression(pattern: #"\{\{[^{}]+\}\}"#)
                let range = NSRange(text.startIndex..., in: text)
                let matches = slot.matches(in: text, range: range)
                if matches.isEmpty { continue }
                var pattern = "", cursor = text.startIndex
                var tokens: [String] = []
                for match in matches {
                    guard let part = Range(match.range, in: text) else { continue }
                    pattern += NSRegularExpression.escapedPattern(for: String(text[cursor..<part.lowerBound])) + "(.*?)"
                    tokens.append(String(text[part])); cursor = part.upperBound
                }
                pattern += NSRegularExpression.escapedPattern(for: String(text[cursor...]))
                guard let regex = try? NSRegularExpression(pattern: "^" + pattern + "$", options: [.dotMatchesLineSeparators]),
                      let match = regex.firstMatch(in: value, range: NSRange(value.startIndex..., in: value)) else { continue }
                var result = target[key] ?? key
                for (index, token) in tokens.enumerated() {
                    if let capture = Range(match.range(at: index + 1), in: value) { result = result.replacingOccurrences(of: token, with: String(value[capture])) }
                }
                return result
            }
        }
        for key in french.keys.sorted(by: { $0.count > $1.count }) {
            for text in [key, english[key] ?? key] where !text.isEmpty && value.hasPrefix(text) && value.count > text.count {
                let suffix = String(value.dropFirst(text.count))
                if text.last?.isWhitespace == true || " :·—→".contains(suffix.first!) { return (target[key] ?? key) + suffix }
            }
        }
        return value
    }
    func save(_ choice: String) throws {
        guard ["system", "fr", "en"].contains(choice) else { return }
        let folder = NoYouPubPaths.dataRoot.appendingPathComponent("config")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        let url = folder.appendingPathComponent("preferences.json")
        var value = (try? Data(contentsOf: url)).flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] } ?? [:]
        value["language"] = choice
        try JSONSerialization.data(withJSONObject: value).write(to: url, options: .atomic)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
        if let menu = NSApp?.mainMenu {
            let app = menu.items.first?.submenu
            app?.items.first?.title = L("Quitter NoYouPub")
            if menu.items.count > 1 {
                let edit = menu.items[1].submenu
                edit?.title = L("Édition")
                for (item, key) in zip(edit?.items ?? [], ["Couper", "Copier", "Coller", "Tout sélectionner"]) { item.title = L(key) }
            }
        }
    }
}

func L(_ value: String) -> String { LanguageStore.shared.translate(value) }
