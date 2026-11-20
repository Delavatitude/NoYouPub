# Architecture V3 / V3 architecture

The baseline audit is in [ARCHITECTURE-AUDIT.md](ARCHITECTURE-AUDIT.md).

## Boundaries

| Component | Location | Responsibility |
|---|---|---|
| Native UI | `source/YouTubeTV.swift`, `Localization.swift` | SwiftUI/AppKit, settings, preparation, playback timeline |
| Headless entry | `source/core.py` | CLI, native host, media worker dispatch, shutdown |
| Browser UI | `source/extension/` | YouTube controls, queue/history, independent page state |
| Casting | `relay.py`, `cast_control.py`, `dlna.py` | Formats, discovery, media serving, Cast/DLNA control |
| Media | `media_http.py`, `stream_http.py` | MP4 byte ranges, time seeking, on-demand rate adaptation |
| Configuration | `runtime_paths.py`, `preferences.py`, `jobs.py` | Private V3 state, atomic preferences and job progress |
| Setup | `setup_core.py`, `installer.py` | Explicit per-user registration and owned-file removal |

No persistent daemon, launch agent or privileged helper is added. Chrome starts a stdio host as needed; it can stay open for that browser session. Casting starts a separate media worker. Closing a window does not imply stopping playback. Use Stop, or Core shutdown, before removal. The relay keeps the existing LG stop grace (approximately 30 seconds). Worker error/timeout cleanup remains bounded.

The GUI resolves the bundled executable at `Contents/Resources/Core/noyoupub-core`. Only an explicitly supplied `NOYOUPUB_PYTHON` permits the development Python fallback. The engine separates bundled immutable code from private writable data. The production runtime does not fall back to Homebrew/PATH; `NOYOUPUB_DEVELOPMENT=1` explicitly enables developer PATH binaries.

## State and compatibility

Default V3 data: `~/Library/Application Support/NoYouPub`. Historical data under `YouTube-CATT` is never implicitly read or written. The optional migration command copies only allowlisted settings into absent targets; it does not import logs, relay state, credentials, tokens or binary paths. Existing destination preferences win.

The native host is `fr.local.noyoupub_v3`, separate from the legacy host. The extension retains its public key and stable extension ID. **Both versions cannot coexist as extensions in the same Chrome profile**; development requires a separate profile. No installed Chrome profile was changed during preparation.

Preferences use `config/preferences.json`; mode uses `config/playback-mode.json`. Other 2.5 state formats are retained. No remote preference service or telemetry is introduced. Configuration file examples are in `examples/`.

## Localization

`source/locales/fr.json` and `en.json` are the shared source catalogs. Visible literals, interpolated messages and translated labels use exact/template matching at UI boundaries. Provider titles and protocol fields must remain untouched. Python localizes response messages; Swift renders through `L`; Chrome uses generated native catalogs plus an explicit-language resolver because Chrome's built-in locale cannot be overridden by a settings picker.

Run `python3 scripts/generate_locales.py` after edits. It checks key and placeholder parity. To add ES/DE/PT later, provide complete reviewed catalogs, extend each language allowlist/resolver and the build's localizations, regenerate Chrome catalogs and add tests. No incomplete ES/DE/PT locale is advertised now.

The extension can follow the last known app language, use browser language or choose FR/EN. Explicit Chrome choices are saved locally first; Core synchronization is best effort. With follow-app enabled, language is refreshed during available Core communication. No availability dependency is imposed on selecting Chrome's language.

## Network and privacy

Native Messaging is a local pipe, not an HTTP command API. Chrome validates extension ID, top frame, YouTube origin and action arguments. The host verifies the exact allowed extension origin before initializing data, limits incoming frames to 16 KiB, validates numeric ranges and canonicalizes supported YouTube URLs.

The media relay must be reachable from the TV, so it binds a local LAN address and ephemeral port. Requests require both an unpredictable per-session token and a selected TV/Mac peer address. Stop is restricted to the local Mac and token. This is access control on a trusted LAN, not encrypted transport or protection against a compromised local account/LAN observer. Do not expose its port to the Internet. DLNA and Cast discovery traffic remains local.

Video requests go to YouTube/media providers. Local logs/state may contain video titles, URLs, signed media URLs, IPs and tokens. Never publish raw diagnostics. No bundled dependency is downloaded automatically at runtime.
