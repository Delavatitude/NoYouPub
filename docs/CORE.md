# NoYouPub Core — headless use / sans interface permanente

Core is the existing Python media/control engine with a command entry point. Chrome starts the Native Messaging host on demand. A window is not required, but **Chrome alone cannot cast without a locally installed Core**. No server/daemon/launch agent is installed at login.

## Read-only status and preferences

Developer example with an isolated environment and a new data directory:

```sh
NOYOUPUB_DATA_DIR=/private/tmp/noyoupub-v3-review NOYOUPUB_DEVELOPMENT=1 .venv/bin/python source/core.py doctor
NOYOUPUB_DATA_DIR=/private/tmp/noyoupub-v3-review .venv/bin/python source/core.py language en
```

`doctor` checks Python imports, Node >=22, required FFmpeg encoders, ffprobe and Chrome host presence. It initializes only the selected V3 data directory. `language` accepts `system`, `fr`, `en` and preserves other preference keys. Every public CLI action prints JSON. Native host mode uses binary length-framed JSON only; stdout must never contain debug output.

`request` accepts allowlisted media actions (`devices`, `cast`, `status`, `pause`, `play`, `stop`, `seek`, `speed`, `volume`, `mute`), preparation status/cancel and language preferences. It is a command-line API for the local account, not a network endpoint. `cast` requires a supported YouTube URL, allowed quality and validated target/position. Discovery/casting commands contact actual hardware: run only with the TV owner's agreement.

`shutdown` tries the owned playback session's stop command first. The existing LG grace delay remains; a relay can therefore take approximately 30 seconds to exit. The fallback uses the token-authenticated local relay stop route, never an arbitrary saved PID. A disconnected TV may produce an explicit error; do not force-delete live state to claim a clean stop.

## Explicit standalone registration

The future **NoYouPub Core Installer.app** opens configuration/settings only. It is built from the same native UI with a Core-only flag, not a permanent controller. Use Verify Core, Enable Chrome Bridge, then its Chrome extension tab. After enabling the bridge, the installer window can be closed.

Developer CLI alternative (real installation; review first, not run by tests/build):

```sh
.venv/bin/python source/core.py setup install --payload /absolute/path/to/reviewed/Contents/Resources --confirm
```

The payload must pass production verification. No `--allow-development` installer option is exposed; fake payloads are accepted only through the direct test API. Registration copies owned Core/bin/extension/notices into the separate per-user data folder and writes `fr.local.noyoupub_v3.json` into Chrome's per-user NativeMessagingHosts directory. Exactly one extension origin is allowed. The wrapper quotes paths and preserves Chrome's origin argument. No sudo or internet install occurs.

For a simulated clean home use explicit `--home` and `--data-root` pointing to resolved temporary paths. Do not confuse this with a real clean-Mac test.

Opt-in migration, before populating conflicting V3 settings:

```sh
.venv/bin/python source/core.py setup import-legacy --confirm
```

Only allowlisted absent files are copied. Existing destination settings win; historical files are never edited or removed. This command was tested with synthetic old data only, not the personal installation.

## Remove

Stop playback, close the extension's active session, wait for relay shutdown, then use **Disable Chrome bridge** in Settings. This removes owned Core binaries and host registration, retaining preferences. The opened Mac app itself remains in Applications and can still run its bundled engine; removing that app and the Chrome extension completes product removal.

CLI alternative:

```sh
.venv/bin/python source/core.py shutdown
.venv/bin/python source/core.py setup uninstall --confirm
```

Explicit `--remove-data` also removes V3 preferences. It is never automatic. Unknown markers, a foreign host manifest, unsafe paths or an active relay state stop removal. Reinstalling an already owned, complete setup is idempotent; this first V3 preparation deliberately does not implement in-place runtime upgrades. Disable the owned bridge and reinstall the reviewed new package to update, preserving preferences. No 2.5 files are removed.
