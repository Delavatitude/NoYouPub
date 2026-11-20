# Architecture audit — 2026-11-18

## Findings
- Native GUI: SwiftUI hosted in AppKit; macOS 13 minimum; compiled with swiftc.
- Engine: Python modules relay, DLNA/Cast control, HTTP ranges/TS, jobs and URL validation.
- Chrome Manifest V3 uses Native Messaging over stdin/stdout. Origin and page/frame/action are validated. No local HTTP control API. Media server binds a LAN address on an ephemeral port with token and peer allowlist.
- Runtime: Python >=3.11, pinned catt/yt-dlp/yt-dlp-ejs/PyChromecast, Node >=22, FFmpeg (VideoToolbox used for speed changes). External Homebrew paths currently leak into runtime resolution.
- Existing installer creates a venv and registers Native Messaging in the real user account. Existing GUI calls an absolute legacy Application Support location. Legacy build bundles only the GUI bridge, not Python/Node/FFmpeg. Ad-hoc signing is not public signing/notarization.
- Current core already runs without the GUI: Chrome launches the native host on demand; media worker is a separate process. Keep this design. A permanently listening daemon would add attack surface without benefit.
- Existing tests are development scripts outside the sources; several depend on signed YouTube URLs, a particular TV, local fixtures, or absolute developer paths. These must not enter a public repository.
- Known limits: LG/DLNA was the principal hardware tested for 2.5; unknown Google Cast hardware is not certified. Queue natural completion is dependent on renderer end reporting. Public distribution and clean-machine Gatekeeper flow have not been validated.

## Least invasive evolution
Preserve source module layout and media algorithms. Add a runtime-path module, bilingual resource catalogs shared across Python/Swift/Chrome, on-demand core CLI, explicit installer/uninstaller and an offline assembled runtime contract. Keep migration copy-only and opt-in. Build a new V3 bundle without launching or installing it. Provide a GUI setup assistant, reproducible staging/DMG scripts, signing and notarization commands requiring real external credentials. Do not fetch or install binaries implicitly.

## Safety boundary
Work occurs in a separate repository and V3 branch. Original sources, installed app, Native Messaging registration and user settings are untouched. Tests use temporary homes. No external publication or remote Git operations. No playback/control command is sent to a TV during this preparation; the real discovery probe is read-only and uses temporary state.
