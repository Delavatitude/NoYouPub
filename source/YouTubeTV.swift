import AppKit
import SwiftUI

struct TV: Identifiable, Hashable {
    let id: String
    let label: String
    var name: String { label.components(separatedBy: " | ").dropLast().joined(separator: " | ") }
}

struct Preparation: Decodable {
    var url: String?
    var job_id: String
    var phase: String
    var message: String
    var busy: Bool
    var started: Double
    var updated: Double
    var fraction: Double?
    var bytes: Int64?
    var title: String?
    var quality: Int?
    var device_name: String?
    var stalled: Bool?
    var streaming: Bool?
}

struct PlaybackSnapshot: Decodable {
    var session_id: String
    var job_id: String?
    var device: String?
    var device_name: String?
    var title: String?
    var position: Double
    var duration: Double
    var state: String
    var updated: Double
    var observed_at: Double?
    var playback_rate: Double?
    var timestamp: Double { max(updated, observed_at ?? 0) }
}

final class Model: ObservableObject {
    @Published var preparation: Preparation?
    @Published var devices: [TV] = []
    @Published var selected = ""
    @Published var link = ""
    @Published var busy = false
    @Published var status = L("Allume ta TV et connecte-la au même Wi-Fi que ce Mac.")
    @Published var failed = false
    @Published var playing = false
    @Published var paused = false
    @Published var playback: PlaybackSnapshot?
    @Published var playbackFresh = false
    @Published var position = 0.0
    @Published var duration = 0.0
    @Published var scrubPosition = 0.0
    @Published var scrubbing = false
    @Published var seekPending = false
    @Published var commandBusy = false
    @Published var playbackRate = 1.0
    private var activeOperations = 0
    private var activeControls = 0
    @Published var quality = 480
    @Published var playbackMode = "fast"
    @Published var diagnostics = L("Clique sur Lancer le diagnostic pour vérifier les récepteurs et l’extension Chrome.")
    @Published var ip = ""
    @Published var settings = false
    @Published var settingsTab = 0
    @Published var languagePreference = LanguageStore.shared.preference
    @Published var setupReport = ""
    let root: URL
    var isPreparing: Bool {
        guard let p = preparation, p.busy else { return false }
        return !(playbackFresh && playing && playback?.job_id == p.job_id)
    }
    var timelinePosition: Double { (scrubbing || seekPending) ? scrubPosition : position }
    var canSeek: Bool { playing && playbackFresh && duration > 0 && !busy && !isPreparing }
    static func clock(_ seconds: Double) -> String {
        let value = Int(max(0, seconds.isFinite ? seconds : 0))
        if value >= 3600 { return String(format: "%d:%02d:%02d", value / 3600, value / 60 % 60, value % 60) }
        return String(format: "%d:%02d", value / 60, value % 60)
    }

    init(root: URL = NoYouPubPaths.dataRoot) {
        self.root = root
        if let data = try? Data(contentsOf: root.appendingPathComponent("config/playback-mode.json")),
           let settings = try? JSONSerialization.jsonObject(with: data) as? [String: String] {
            playbackMode = settings["mode"] ?? "fast"
        }
        if let saved = try? String(contentsOf: root.appendingPathComponent("config/desktop-last-link.txt"), encoding: .utf8) {
            link = saved.trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }

    func changeLanguage(_ value: String) {
        do { try LanguageStore.shared.save(value); languagePreference = value; status = L(status) }
        catch { failed = true; status = error.localizedDescription }
    }

    func setup(_ install: Bool = false) {
        execute([install ? "setup-install" : "setup-doctor"]) { ok, message in
            self.setupReport = message
            self.failed = !ok
            if install && ok { self.status = L(message) }
        }
    }

    func savePlaybackMode(_ value: String) {
        playbackMode = value
        if let data = try? JSONSerialization.data(withJSONObject: ["mode":value]) {
            try? data.write(to: root.appendingPathComponent("config/playback-mode.json"), options: .atomic)
        }
    }

    func execute(_ args: [String], completion: @escaping (Bool, String) -> Void) {
        activeOperations += 1
        let isControl = ["pause", "play", "stop", "seek", "speed"].contains(args.first ?? "")
        if isControl { activeControls += 1 }
        busy = activeOperations > 0
        commandBusy = activeControls > 0
        failed = false
        DispatchQueue.global(qos: .userInitiated).async {
            let process = Process()
            let resources = Bundle.main.resourceURL!
            let core = resources.appendingPathComponent("Core/noyoupub-core")
            if FileManager.default.isExecutableFile(atPath: core.path) {
                process.executableURL = core
                process.arguments = ["desktop"] + args
            } else if let python = ProcessInfo.processInfo.environment["NOYOUPUB_PYTHON"] {
                process.executableURL = URL(fileURLWithPath: python)
                process.arguments = [resources.appendingPathComponent("Source/desktop_app.py").path] + args
            } else {
                DispatchQueue.main.async {
                    self.activeOperations -= 1
                    if isControl { self.activeControls -= 1 }
                    self.busy = self.activeOperations > 0
                    self.commandBusy = self.activeControls > 0
                    completion(false, L("Les composants autonomes ne sont pas inclus dans ce build de développement. Consulte le guide de compilation."))
                }
                return
            }
            process.environment = ProcessInfo.processInfo.environment.merging([
                "NOYOUPUB_DATA_DIR": self.root.path,
                "NOYOUPUB_RESOURCES": resources.path,
                "NOYOUPUB_LANGUAGE": LanguageStore.shared.language,
            ]) { _, new in new }
            let output = Pipe()
            process.standardOutput = output
            process.standardError = output
            do {
                try process.run()
                let data = output.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                let message = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                DispatchQueue.main.async {
                    self.activeOperations -= 1
                    if isControl { self.activeControls -= 1 }
                    self.busy = self.activeOperations > 0
                    self.commandBusy = self.activeControls > 0
                    completion(process.terminationStatus == 0, message)
                }
            } catch {
                DispatchQueue.main.async {
                    self.activeOperations -= 1
                    if isControl { self.activeControls -= 1 }
                    self.busy = self.activeOperations > 0
                    self.commandBusy = self.activeControls > 0
                    completion(false, L("Impossible de lancer le moteur. Ouvre Installation et langue pour vérifier ses composants."))
                }
            }
        }
    }

    // Apply each accepted cast once. Later polling must not overwrite a manual draft.
    func syncRequestedVideo(_ request: Preparation) {
        guard let raw = request.url,
              let components = URLComponents(string: raw),
              components.scheme == "https", components.user == nil, components.password == nil,
              ["www.youtube.com", "youtube.com"].contains(components.host ?? ""),
              components.path == "/watch",
              let id = components.queryItems?.first(where: { $0.name == "v" })?.value,
              id.range(of: "^[A-Za-z0-9_-]{11}$", options: .regularExpression) != nil else { return }
        link = "https://www.youtube.com/watch?v=" + id
        if let requestedQuality = request.quality, [360, 480, 720, 1080].contains(requestedQuality) {
            quality = requestedQuality
        }
        try? link.write(to: root.appendingPathComponent("config/desktop-last-link.txt"), atomically: true, encoding: .utf8)
    }

    func readPreparation() {
        let currentLanguage = LanguageStore.shared.preference
        if languagePreference != currentLanguage { languagePreference = currentLanguage }
        let previous = preparation
        if let data = try? Data(contentsOf: root.appendingPathComponent("config/preparation.json")),
           let p = try? JSONDecoder().decode(Preparation.self, from: data) {
            if previous?.job_id != p.job_id { syncRequestedVideo(p) }
            preparation = p
        }
        // Playback observations must continue while a cast command awaits its reply.
        if let data = try? Data(contentsOf: root.appendingPathComponent("config/playback.json")),
           var snapshot = try? JSONDecoder().decode(PlaybackSnapshot.self, from: data),
           selected.isEmpty || snapshot.device == selected {
            if snapshot.state == "IDLE" {
                snapshot.title = nil
                snapshot.position = 0
                snapshot.duration = 0
                snapshot.playback_rate = 1
            }
            playback = snapshot
            let age = max(0, Date().timeIntervalSince1970 - snapshot.timestamp)
            playbackFresh = age < 15
            playbackRate = snapshot.playback_rate ?? 1
            duration = max(0, snapshot.duration)
            let advance = snapshot.state == "PLAYING" && age < 4 ? age * playbackRate : 0
            position = min(duration, max(0, snapshot.position + advance))
            playing = playbackFresh && ["PLAYING", "PAUSED"].contains(snapshot.state)
            paused = snapshot.state == "PAUSED"
            if !scrubbing && !seekPending { scrubPosition = position }
        } else {
            playbackFresh = false
            playing = false
        }
        if let p = preparation {
            if previous?.job_id != p.job_id || previous?.phase != p.phase {
                if ["error", "cancelled", "ended"].contains(p.phase) && !playing { status = p.message }
                if p.phase == "error" { failed = true }
            }
            if isPreparing { status = p.message; failed = p.phase == "error" }
        }
        if playing && !isPreparing && !commandBusy && !failed {
            status = paused ? L("Lecture en pause sur la TV.") : L("Lecture en cours sur la TV.")
        } else if playbackFresh && !busy && !isPreparing && !failed && playback?.state == "IDLE" {
            status = L("Diffusion arrêtée.")
        } else if playbackFresh && !busy && !isPreparing && !failed && playback?.state == "BUFFERING" {
            status = L("Chargement de la vidéo sur la TV…")
        } else if playback != nil && playback?.state != "IDLE" && !playbackFresh && !busy && !isPreparing && !failed {
            status = L("L’état de la TV n’est plus à jour. Vérifie sa connexion.")
        }
    }

    func finishScrubbing() {
        scrubbing = false
        guard canSeek else { scrubPosition = position; return }
        let target = min(max(0, scrubPosition), max(0, duration - 1))
        scrubPosition = target
        seekPending = true
        status = L("Déplacement à \(Self.clock(target))…")
        execute(["seek", String(target)]) { ok, message in
            self.seekPending = false
            self.failed = !ok
            self.status = message
            self.readPreparation()
        }
    }

    func cancelPreparation() {
        status = L("Annulation de la préparation…")
        DispatchQueue.global(qos: .userInitiated).async {
            let resources = Bundle.main.resourceURL!
            let process = Process()
            let core = resources.appendingPathComponent("Core/noyoupub-core")
            if FileManager.default.isExecutableFile(atPath: core.path) {
                process.executableURL = core; process.arguments = ["desktop", "cancel"]
            } else if let python = ProcessInfo.processInfo.environment["NOYOUPUB_PYTHON"] {
                process.executableURL = URL(fileURLWithPath: python)
                process.arguments = [resources.appendingPathComponent("Source/desktop_app.py").path, "cancel"]
            } else { return }
            process.environment = ProcessInfo.processInfo.environment.merging(["NOYOUPUB_DATA_DIR": self.root.path, "NOYOUPUB_RESOURCES": resources.path]) { _, new in new }
            process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
            do { try process.run(); process.waitUntilExit() } catch { }

        }
    }

    func refresh() {
        status = L("Recherche des TV sur ton réseau…")
        execute(["devices"]) { ok, message in
            if ok {
                self.devices = message.components(separatedBy: .newlines).compactMap { line in
                    guard let last = line.components(separatedBy: " | ").last, UUID(uuidString: last) != nil else { return nil }
                    return TV(id: last, label: line)
                }
                if !self.devices.contains(where: { $0.id == self.selected }) {
                    let preference = self.root.appendingPathComponent("config/desktop-tv.json")
                    let saved = (try? Data(contentsOf: preference)).flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: String] }
                    let preferred = saved?["device"] ?? ""
                    self.selected = self.devices.contains(where: { $0.id == preferred }) ? preferred : (self.devices.first?.id ?? "")
                }
                self.status = self.devices.isEmpty ? L("Aucune TV trouvée. Consulte l’aide ci-dessous, puis réessaie.") : L("TV trouvée. Colle maintenant le lien d’une vidéo YouTube.")
                self.failed = self.devices.isEmpty
            } else {
                self.status = message.isEmpty ? L("Aucune TV Google Cast ou DLNA détectée. Ouvre Connexion et réglages pour lancer le diagnostic.") : message
                self.failed = true
            }
        }
    }

    func cast() {
        readPreparation()
        guard !busy, preparation?.busy != true,
              let tv = devices.first(where: { $0.id == selected }) else { return }
        let requestedLink = link.trimmingCharacters(in: .whitespacesAndNewlines)
        let requestedQuality = quality
        guard !requestedLink.isEmpty else { return }
        try? requestedLink.write(to: root.appendingPathComponent("config/desktop-last-link.txt"), atomically: true, encoding: .utf8)
        status = playbackMode == "fast" ? L("Démarrage du flux sur \(tv.name)…") : L("Préparation complète pour \(tv.name)… Cela peut prendre plusieurs minutes.")
        execute(["select", tv.label]) { ok, message in
            guard ok else { self.status = message; self.failed = true; return }
            self.execute(["cast", requestedLink, String(requestedQuality)]) { ok, message in
                self.failed = !ok && self.preparation?.phase != "cancelled"
                self.status = message
                if ok { self.readPreparation() }
            }
        }
    }

    func control(_ action: String) {
        status = L("Commande envoyée à la TV…")
        execute([action]) { ok, message in
            self.status = message
            self.failed = !ok
            if ok {
                if action == "stop" { self.playing = false; self.paused = false }
                if action == "pause" { self.paused = true }
                if action == "play" { self.paused = false }
                self.readPreparation()
            }
        }
    }

    func changeSpeed(_ value: Double) {
        status = L("Adaptation de la vitesse… La TV va recharger le flux.")
        execute(["speed", String(value)]) { ok, message in
            self.failed = !ok
            self.status = message
            if ok { self.playbackRate = value; self.readPreparation() }
        }
    }

    func diagnose() {
        diagnostics = L("Diagnostic en cours : passerelle, réseau, TV Google Cast / DLNA et extension Chrome…")
        execute(["diagnostics"]) { ok, message in
            self.diagnostics = message
            self.failed = !ok
        }
    }

    func addIP() {
        execute(["add-ip", ip]) { ok, message in
            self.diagnostics = message
            self.status = message
            self.failed = !ok
            if ok { self.refresh() }
        }
    }

    func openChromeExtensions() {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/open")
        process.arguments = ["-a", "Google Chrome", "chrome://extensions/"]
        do { try process.run() } catch { self.diagnostics = error.localizedDescription }
    }

    func openFolder(_ suffix: String) { NSWorkspace.shared.open(root.appendingPathComponent(suffix)) }
}

struct Card<Content: View>: View {
    let number: String
    let title: String
    let subtitle: String
    @ViewBuilder var content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 12) {
                Text(number).font(.headline).foregroundStyle(.purple).frame(width: 28, height: 28).background(.purple.opacity(0.09), in: Circle())
                VStack(alignment: .leading, spacing: 3) {
                    Text(title).font(.headline)
                    Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
                }
            }
            content
        }
        .padding(20).frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(.primary.opacity(0.07)))
    }
}

struct MainView: View {
    @StateObject private var model = Model()
    @State private var showHelp = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 15) {
                    Image(nsImage: NSImage(contentsOf: Bundle.main.url(forResource: "logo", withExtension: "png")!)!)
                        .resizable().renderingMode(.original).scaledToFit().frame(width: 76, height: 76)
                        .accessibilityLabel("Logo NoYouPub")
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 12) {
                            Text("NoYouPub").font(.system(size: 27, weight: .bold))
                            Spacer(minLength: 8)
                            HStack(spacing: 8) {
                                Text(L("TV, Chrome et diagnostic")).font(.caption).foregroundStyle(.secondary)
                                Button { model.settings = true } label: {
                                    Image(systemName: "gearshape")
                                        .font(.system(size: 18))
                                        .frame(width: 32, height: 32)
                                        .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                .help(L("Connexion et réglages…"))
                                .accessibilityLabel(L("Connexion et réglages"))
                            }
                        }
                        Text(L("YouTube sur ta TV, avec un suivi à chaque étape.")).foregroundStyle(.secondary)
                    }
                    Spacer()
                }.padding(.bottom, 4)
                Card(number: "1", title: L("Choisis ta TV"), subtitle: L("Google Cast ou LG/DLNA • Sur le même réseau que ce Mac.")) {
                    HStack(spacing: 12) {
                        Picker(L("Télévision"), selection: $model.selected) {
                            Text(model.devices.isEmpty ? L("Aucune TV trouvée") : L("Choisir une TV")).tag("")
                            ForEach(model.devices) { tv in Text(tv.name).tag(tv.id) }
                        }.labelsHidden().frame(maxWidth: .infinity).disabled(model.busy)
                        Button(action: model.refresh) { Label(L("Actualiser"), systemImage: "arrow.clockwise") }.disabled(model.busy)
                    }.controlSize(.large)
                }
                Card(number: "2", title: L("Ajoute une vidéo"), subtitle: L("Sur YouTube, clique sur Partager → Copier le lien, puis colle-le ici.")) {
                    HStack(spacing: 10) {
                        TextField("https://www.youtube.com/watch?v=…", text: $model.link)
                            .textFieldStyle(.roundedBorder).onSubmit { if !model.busy && !model.selected.isEmpty && !model.link.isEmpty { model.cast() } }
                        Button(L("Coller")) { model.link = NSPasteboard.general.string(forType: .string) ?? "" }
                    }.controlSize(.large).disabled(model.busy)
                    HStack {
                        Picker(L("Qualité"), selection: $model.quality) {
                            Text("1080p").tag(1080)
                            Text("720p").tag(720)
                            Text("480p").tag(480)
                            Text("360p").tag(360)
                        }.frame(width: 170).disabled(model.busy)
                        Spacer()
                    }
                    HStack {
                        Button(action: model.cast) { Label((model.busy || model.preparation?.busy == true) ? L("Traitement en cours…") : L("Diffuser sur la TV"), systemImage: "play.tv").fontWeight(.semibold).padding(.horizontal, 10).frame(maxWidth: .infinity) }
                            .buttonStyle(.borderedProminent).tint(.purple).controlSize(.large)
                            .disabled(model.busy || model.preparation?.busy == true || model.selected.isEmpty || model.link.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        Spacer()
                        Button(L("Ouvrir YouTube ↗")) { NSWorkspace.shared.open(URL(string: "https://www.youtube.com")!) }.buttonStyle(.link)
                    }
                }
                if let p = model.preparation, model.isPreparing {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Label(p.streaming == true ? L("Démarrage rapide") : (p.phase == "sending" ? L("Envoi à la TV") : L("Préparation de la vidéo")), systemImage: "arrow.down.circle")
                                .font(.headline)
                            Spacer()
                            if let fraction = p.fraction { Text("\(Int(fraction * 100)) %").monospacedDigit().fontWeight(.semibold) }
                        }
                        if let title = p.title { Text(title).font(.subheadline).lineLimit(2) }
                        if let quality = p.quality { Text("\(quality)p · \(p.device_name ?? "TV")").font(.caption).foregroundStyle(.secondary) }
                        if let fraction = p.fraction { ProgressView(value: fraction).tint(.purple) }
                        else { ProgressView().controlSize(.small) }
                        HStack {
                            if let bytes = p.bytes { Text(String(format: L("%.1f Mo préparés"), Double(bytes) / 1048576)) }
                            Spacer()
                            Text(L("\(Int(max(0, Date().timeIntervalSince1970 - p.started))) s écoulées")).monospacedDigit()
                        }.font(.caption).foregroundStyle(.secondary)
                        if p.stalled == true { Text(L("Le serveur vidéo répond lentement. Si le téléchargement reste bloqué, il sera arrêté avec un message d’erreur.")).font(.callout).foregroundStyle(.orange) }
                        if Date().timeIntervalSince1970 - p.updated > 90 { Text(L("La préparation ne répond plus. Annule cet essai puis réessaie.")).foregroundStyle(.orange) }
                        HStack {
                            Text(p.streaming == true ? L("La vidéo se charge au fil de la lecture.") : L(p.message)).font(.caption).foregroundStyle(.secondary)
                            Spacer()
                            Button(L("Annuler")) { model.cancelPreparation() }
                        }
                    }.padding(18).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 14))
                }
                if !model.isPreparing {
                HStack(alignment: .top, spacing: 12) {
                    if model.commandBusy || (model.busy && !model.playing) { ProgressView().controlSize(.small).padding(.top, 2) }
                    else { Image(systemName: model.failed ? "exclamationmark.circle.fill" : "info.circle.fill").foregroundStyle(model.failed ? Color.orange : Color.secondary).padding(.top, 2) }
                    Text(L(model.status)).font(.callout).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }.padding(14).frame(maxWidth: .infinity, alignment: .leading)
                    .background((model.failed ? Color.orange : Color.secondary).opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                }
                if model.failed && !model.busy && model.preparation?.busy != true {
                    Button(L("Réessayer cette vidéo")) { model.cast() }.disabled(model.link.isEmpty || model.selected.isEmpty)
                }
                VStack(alignment: .leading, spacing: 8) {
                    if let title = model.playback?.title, model.playbackFresh {
                        Text(title).font(.subheadline).lineLimit(2)
                    }
                    Slider(value: Binding(get: { model.scrubPosition }, set: { model.scrubPosition = $0 }),
                           in: 0...max(1, model.duration), onEditingChanged: { editing in
                        model.scrubbing = editing
                        if !editing { model.finishScrubbing() }
                    }).disabled(!model.canSeek)
                        .accessibilityLabel(L("Position dans la vidéo"))
                        .accessibilityValue("\(Model.clock(model.timelinePosition)) sur \(Model.clock(model.duration))")
                    HStack {
                        Text(Model.clock(model.timelinePosition))
                        Spacer()
                        if model.seekPending { Text(L("Déplacement en cours…")) }
                        else if model.playback?.state == "IDLE" { Text(L("Arrêtée")) }
                        else if !model.playbackFresh && model.playback != nil { Text(L("État à actualiser")) }
                        Text(Model.clock(model.duration))
                    }.font(.caption).monospacedDigit().foregroundStyle(.secondary)
                }
                HStack(spacing: 12) {
                    Text(L("Lecture")).font(.headline)
                    Picker(L("Vitesse"), selection: Binding(get: { model.playbackRate }, set: { model.changeSpeed($0) })) {
                        Text("×0,75").tag(0.75)
                        Text(L("Normale")).tag(1.0)
                        Text("×1,25").tag(1.25)
                        Text("×1,5").tag(1.5)
                        Text("×1,75").tag(1.75)
                        Text("×2").tag(2.0)
                    }.frame(width: 170)
                    Spacer()
                    Button { model.control(model.paused ? "play" : "pause") } label: { Label(model.paused ? L("Reprendre") : L("Pause"), systemImage: model.paused ? "play.fill" : "pause.fill") }
                    Button { model.control("stop") } label: { Label(L("Arrêter"), systemImage: "stop.fill") }
                }.controlSize(.large).disabled(model.busy || !model.playing || model.isPreparing)
                Divider()
                DisclosureGroup(L("Besoin d’un coup de main ?"), isExpanded: $showHelp) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(L("TV introuvable ? Allume le Chromecast, vérifie le Wi-Fi et évite les réseaux invités. Dans Réglages Système → Confidentialité et sécurité → Réseau local, autorise cette application ou Python si macOS le demande."))
                        Text(L("Garde le Mac éveillé pendant la lecture. Les publicités intégrées à la vidéo restent présentes. Certaines vidéos protégées ou réservées aux comptes connectés peuvent échouer."))
                        HStack {
                            Button(L("Ouvrir les journaux")) { model.openFolder("config") }
                            Button(L("Extension Chrome (facultatif)")) {
                                model.settingsTab = 1
                                model.settings = true
                            }
                        }
                    }.font(.callout).foregroundStyle(.secondary).padding(.top, 10)
                }
                Label(L("Le Mac reste allumé pendant la diffusion."), systemImage: "laptopcomputer").font(.caption).foregroundStyle(.secondary)
            }.padding(28).frame(maxWidth: 840)
        }.frame(minWidth: 650, minHeight: 720)
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            model.readPreparation()
            if !FileManager.default.fileExists(atPath: model.root.appendingPathComponent("config/setup-complete.json").path) {
                model.settingsTab = 3; model.settings = true
            } else { model.refresh() }
        }
        .onReceive(Timer.publish(every: 1, on: .main, in: .common).autoconnect()) { _ in model.readPreparation() }
        .sheet(isPresented: $model.settings) { SettingsView(model: model) }
    }
}

struct SettingsView: View {
    @ObservedObject var model: Model
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text(L("Connexion et réglages")).font(.title2).bold()
                Spacer()
                Button(L("Fermer")) {
                    if Bundle.main.object(forInfoDictionaryKey: "NoYouPubCoreOnly") as? Bool == true { NSApp.terminate(nil) }
                    else { model.settings = false }
                }.keyboardShortcut(.cancelAction)
            }
            Picker(L("Section"), selection: $model.settingsTab) {
                Text(L("Connexion TV")).tag(0)
                Text(L("Extension Chrome")).tag(1)
                Text(L("Diagnostic")).tag(2)
                Text(L("Installation et langue")).tag(3)
            }.pickerStyle(.segmented)
            if model.settingsTab == 0 {
                Text(L("Démarrage de la lecture")).font(.headline)
                Picker(L("Mode"), selection: Binding(get: { model.playbackMode }, set: { model.savePlaybackMode($0) })) {
                    Text(L("Rapide — lecture au fil du téléchargement")).tag("fast")
                    Text(L("Compatible — préparation complète du MP4")).tag("compatible")
                }
                Text(L("Le mode Rapide démarre sans attendre la vidéo entière. Sur la LG, une reprise après pause peut encore échouer : utilise alors le mode Compatible pour la prochaine diffusion.")).font(.callout).foregroundStyle(.secondary)
                Text(L("Deux types de TV sont acceptés")).font(.headline)
                Text(L("Google Cast / Chromecast et récepteurs vidéo DLNA, dont la LG détectée sur ton réseau. Le bouton Cast de YouTube peut utiliser un autre protocole : sa présence ne garantit pas Google Cast."))
                Text(L("Ajouter une TV par adresse IP")).font(.headline)
                Text(L("L’adresse se trouve dans les réglages Réseau de la TV. Utile si la découverte automatique est bloquée.")).foregroundStyle(.secondary)
                HStack {
                    TextField(L("Exemple : 192.168.1.100"), text: $model.ip).textFieldStyle(.roundedBorder)
                    Button(L("Tester et ajouter")) { model.addIP() }.disabled(model.busy || model.ip.isEmpty)
                }
                Button(L("Ouvrir les réglages Réseau du Mac")) {
                    NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.Network-Settings.extension")!)
                }
                Text(L(model.diagnostics)).font(.callout).textSelection(.enabled)
            } else if model.settingsTab == 1 {
                Text(L("Ajouter le bouton TV directement dans YouTube")).font(.headline)
                Text(L("L’application fonctionne aussi sans cette extension. L’extension utilise la même passerelle et les mêmes TV compatibles."))
                Text(L("1. Ouvre la page des extensions de Chrome."))
                Button(L("Ouvrir les extensions Chrome")) { model.openChromeExtensions() }
                Text(L("2. Active « Mode développeur », puis « Charger l’extension non empaquetée »."))
                Text(L("3. Dans le sélecteur, appuie sur ⌘⇧G, colle le chemin ci-dessous, puis valide."))
                HStack {
                    Text(model.root.appendingPathComponent("extension").path).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    Button(L("Copier le chemin")) {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(model.root.appendingPathComponent("extension").path, forType: .string)
                    }
                }
                Text(L("4. Recharge YouTube, puis utilise le bouton TV ajouté dans le lecteur. Choisis la TV dans ses réglages."))
                Button(L("Vérifier l’installation")) { model.settingsTab = 2; model.diagnose() }.disabled(model.busy)
            } else if model.settingsTab == 3 {
                Text(L("Configuration initiale")).font(.headline)
                Picker(L("Langue de l’application"), selection: Binding(get: { model.languagePreference }, set: { model.changeLanguage($0) })) {
                    Text(L("Langue du système")).tag("system")
                    Text("Français").tag("fr")
                    Text("English").tag("en")
                }
                if FileManager.default.isExecutableFile(atPath: Bundle.main.resourceURL!.appendingPathComponent("Core/noyoupub-core").path) {
                    Text(L("Le moteur est inclus dans cette application. Chrome peut l’utiliser sans garder cette fenêtre ouverte.")).font(.callout)
                } else {
                    Text(L("Les composants autonomes ne sont pas inclus dans ce build de développement. Consulte le guide de compilation.")).font(.callout).foregroundStyle(.orange)
                }
                HStack {
                    Button(L("Vérifier le moteur")) { model.setup() }
                    Button(L("Activer la passerelle Chrome")) { model.setup(true) }
                }.disabled(model.busy)
                HStack {
                    Button(L("Arrêter le moteur")) {
                        model.execute(["core-shutdown"]) { ok, message in model.setupReport = message; model.failed = !ok }
                    }
                    Button(L("Désactiver la passerelle Chrome")) {
                        model.execute(["setup-uninstall"]) { ok, message in model.setupReport = message; model.failed = !ok }
                    }
                }.disabled(model.busy)
                ScrollView { Text(L(model.setupReport)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
            } else {
                Button(L("Lancer le diagnostic")) { model.diagnose() }.disabled(model.busy)
                ScrollView { Text(L(model.diagnostics)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }.frame(minHeight: 230)
                HStack {
                    Button(L("Ouvrir les journaux")) { model.openFolder("config") }
                    Button(L("Ouvrir l’aide Google Cast")) { NSWorkspace.shared.open(URL(string: "https://support.google.com/chromecast/answer/3249268?hl=\(LanguageStore.shared.language)")!) }
                }
            }
            if model.busy { ProgressView().controlSize(.small) }
            Spacer(minLength: 0)
        }.padding(26).frame(width: 650, height: 520)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        if let iconURL = Bundle.main.url(forResource: "NoYouPub", withExtension: "icns"),
           let icon = NSImage(contentsOf: iconURL) {
            NSApp.applicationIconImage = icon
        }
        let menu = NSMenu()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: L("Quitter NoYouPub"), action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let item = NSMenuItem()
        item.submenu = appMenu
        menu.addItem(item)
        let editMenu = NSMenu(title: L("Édition"))
        editMenu.addItem(withTitle: L("Couper"), action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: L("Copier"), action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: L("Coller"), action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: L("Tout sélectionner"), action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        let edit = NSMenuItem(); edit.submenu = editMenu; menu.addItem(edit)
        NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 760, height: 800), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "NoYouPub"
        window.minSize = NSSize(width: 670, height: 750)
        if Bundle.main.object(forInfoDictionaryKey: "NoYouPubCoreOnly") as? Bool == true {
            let setupModel = Model(); setupModel.settingsTab = 3
            window.contentView = NSHostingView(rootView: SettingsView(model: setupModel))
            window.setContentSize(NSSize(width: 680, height: 600))
        } else {
            window.contentView = NSHostingView(rootView: MainView())
        }
        window.isReleasedWhenClosed = false
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        return true
    }
}

@main
struct YouTubeTVApp {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
