let directory = FileManager.default.temporaryDirectory.appendingPathComponent("noyoupub-model-" + UUID().uuidString)
try FileManager.default.createDirectory(at: directory.appendingPathComponent("config"), withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: directory) }
let model = Model(root: directory)
model.selected = "tv-one"
let now = Date().timeIntervalSince1970
func put(_ file: String, _ object: [String: Any]) throws {
    try JSONSerialization.data(withJSONObject: object).write(to: directory.appendingPathComponent("config/" + file), options: .atomic)
}
try put("preparation.json", ["job_id":"new", "phase":"sending", "message":"Envoi", "busy":true, "started":now-15, "updated":now])
func snapshot(job: String = "new", state: String = "PLAYING", age: Double = 0, position: Double = 42) throws {
    try put("playback.json", ["session_id":"session", "job_id":job, "device":"tv-one", "title":"Old video", "position":position, "duration":600, "state":state, "updated":now-age, "playback_rate":1.5])
}
model.busy = true
try snapshot()
model.readPreparation()
assert(model.playing && !model.isPreparing && !model.canSeek)
model.busy = false
assert(model.canSeek)
assert(model.position >= 42 && model.position < 44)
print("Lecture détectée pendant l’attente ; timeline active après confirmation du lancement : OK")
try snapshot(job: "old")
model.readPreparation()
assert(model.isPreparing && !model.canSeek)
print("Une ancienne vidéo ne masque pas une nouvelle préparation : OK")
try snapshot(state: "PAUSED")
model.readPreparation()
assert(model.paused && model.position == 42)
model.scrubbing = true; model.scrubPosition = 180
try snapshot(position: 50)
model.readPreparation()
assert(model.scrubPosition == 180 && model.timelinePosition == 180)
print("Pause synchronisée ; actualisation sans déplacer le curseur pendant le glissement : OK")
model.scrubbing = false
try snapshot(age: 30)
model.readPreparation()
assert(!model.playbackFresh && !model.canSeek && model.position == 42)
assert(Model.clock(3671) == "1:01:11" && Model.clock(65) == "1:05")
print("État périmé : timeline figée et commandes désactivées ; durées formatées : OK")

model.busy = false
try put("preparation.json", ["job_id":"new", "phase":"playing", "message":"Lecture", "busy":false, "started":now-15, "updated":now])
try snapshot(state: "IDLE")
model.readPreparation()
assert(!model.playing && model.status == "Diffusion arrêtée.")
assert(model.playback?.title == nil && model.position == 0 && model.duration == 0 && model.playbackRate == 1)
print("Arrêt : boutons désactivés et message synchronisé : OK")

try LanguageStore.shared.save("en")
assert(L("Diffusion arrêtée.") == "Casting stopped.")
assert(L("Déplacement à 1:05…").contains("1:05"))
assert(model.canSeek == false)
try LanguageStore.shared.save("fr")
assert(L("Casting stopped.") == "Diffusion arrêtée.")
print("FR/EN language switching without losing model state: OK")

let chromeURL = "https://www.youtube.com/watch?v=uNhQk7JeCj0"
let nextURL = "https://www.youtube.com/watch?v=WaQSvQfmCHo"
model.link = "https://www.youtube.com/watch?v=4XzhMRmbUcw"
try put("preparation.json", ["job_id":"chrome-one", "url":chromeURL, "quality":720, "phase":"extracting", "message":"Analyse", "busy":true, "started":now, "updated":now])
model.readPreparation()
assert(model.link == chromeURL && model.quality == 720)
let savedChromeURL = try String(contentsOf: directory.appendingPathComponent("config/desktop-last-link.txt"), encoding: .utf8)
assert(savedChromeURL == chromeURL)
model.link = nextURL; model.quality = 480
model.readPreparation()
assert(model.link == nextURL && model.quality == 480)
print("Demande Chrome synchronisée et persistée ; le polling ne remplace pas un brouillon manuel : OK")
try put("preparation.json", ["job_id":"chrome-two", "url":nextURL, "quality":1080, "phase":"error", "message":"TV indisponible", "busy":false, "started":now, "updated":now])
model.link = chromeURL
model.readPreparation()
assert(model.link == nextURL && model.quality == 1080)
let reopened = Model(root: directory)
assert(reopened.link == nextURL)
print("Nouvelle demande même en échec : lien exact conservé et retrouvé au redémarrage : OK")
try put("preparation.json", ["job_id":"invalid", "url":"https://example.org/watch?v=WaQSvQfmCHo", "phase":"starting", "message":"Analyse", "busy":true, "started":now, "updated":now])
model.readPreparation()
assert(model.link == nextURL)
try put("preparation.json", ["job_id":"legacy", "phase":"playing", "message":"Lecture", "busy":false, "started":now, "updated":now])
model.readPreparation()
assert(model.preparation?.job_id == "legacy" && model.link == nextURL)
print("URL étrangère ignorée et ancien format de statut toujours accepté : OK")
