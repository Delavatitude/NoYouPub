# Changelog

## 3.0.0-beta — local release candidate

- Bundled the Python Core, Node, FFmpeg and ffprobe for Apple Silicon.
- Set the package deployment target to macOS 14.0 and bundled the violet app icon.
- Included the latest Chrome-to-Mac link synchronization and LG acknowledgement fixes, plus regenerated French and English extension catalogs.
- Added local DMG integrity checks and an isolated Native Messaging smoke test.
- Cleared the previous video’s session, title and timeline after a confirmed stop, including when an LG TV retains the previous media URL. Preserved normal queue advancement on natural playback completion.

## 3.0.0-beta.1 — unreleased preparation, 2026-11-18

- Separate V3 repository/branch and private data namespace; preserve the installed 2.5 app.
- Shared French/English resources, system/manual language settings and nonblocking Chrome preference sync.
- On-demand Core CLI, validated Native Messaging registration, copy-only opt-in migration and owned-component removal preserving preferences.
- Native first-configuration/settings and Core-only installer window, explicit runtime verification and missing-runtime instructions.
- Offline app/DMG assembly recipes, portable audited-runtime contract, real signing/notarization preparation without uploads.
- Synthetic and isolated regression coverage for playback state/timeline, formats, seeking, speed, queue/navigation, protocols and setup.
- Bilingual public-repository documentation and preliminary license/privacy audit; project license decision pending.

Public runtime assembly, signing/notarization, clean-Mac/Chrome testing and live-TV regression remain release gates. No public release has been produced.

## 2.5 / extension 2.5.0 — preserved baseline

Native SwiftUI/AppKit controller; Google Cast and LG/DLNA; fast and fully prepared modes; preparation progress/cancel; pause/resume/stop; timeline; supported playback speeds; browser queue/history and independent navigation; diagnostics. Historical hardware observations are context, not a V3 certification.
