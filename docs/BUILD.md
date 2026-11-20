# Build and developer installation

These are developer commands, not end-user prerequisites. Nothing here has been installed into the existing user account during V3 preparation. Commands assume the repository root as the working directory. Paths are relative to that checkout, never a particular developer's home.

## Prerequisites

macOS 13+; Xcode command line tools and a compatible Swift compiler; Python 3.11+; Node 22+; FFmpeg/ffprobe with H.264, AAC, MPEG-TS, MP4, filters `setpts`, `fps`, `asetpts`, `atempo`, and `h264_videotoolbox` for rate adaptation. Only the current Apple Silicon development machine has compiled this GUI. Intel and macOS 13 runtime execution remain untested. Build each architecture separately on a suitable SDK/machine before claiming universal support. The Python distribution and every native library must support the advertised minimum OS.

## Isolated development environment

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
python3 scripts/generate_locales.py
.venv/bin/python scripts/test_all.py --swift
```

Dependency versions are a snapshot of the existing working environment. This is **not yet a wheel-hash lock**: generate and verify architecture-specific hashes, provenance and matching source archives before a public build. The recipe does not silently upgrade the installed runtime. The local standalone ARM64 build described below verified the PyInstaller recipe.

The HTTP range test binds only `127.0.0.1` and can be blocked by an execution sandbox. Record that as an environment failure, then rerun that focused test with permitted loopback access. VideoToolbox can likewise require permission to access the OS encoder. No test in `test_all.py` needs a real TV or YouTube.

Optional real synthetic codec checks:

```sh
.venv/bin/python scripts/test_ffmpeg.py --ffmpeg /absolute/path/to/ffmpeg --ffprobe /absolute/path/to/ffprobe
```

## Compile a local development app

```sh
python3 source/build_app.py --development --output artifacts/NoYouPub-3-dev.app
python3 source/build_app.py --development --core-only --output artifacts/NoYouPub-Core-Installer-dev.app
```

Outputs must be new paths inside `artifacts/`; existing outputs are never overwritten. A development app is ad-hoc signed for local review, **not** Developer ID signed/notarized and **not distributable**. It includes sources and locales, but not an autonomous runtime. Opening it normally shows the missing-runtime explanation. To run its Python bridge locally, launch its executable with explicit `NOYOUPUB_PYTHON`, `NOYOUPUB_DEVELOPMENT=1`, and `NOYOUPUB_DATA_DIR` set to a new temporary directory. Never point V3 data at the historical installation. Do not load the development extension into the existing personal Chrome profile.

## Assemble the future self-contained payload

A standalone Apple Silicon test DMG is available locally in
`artifacts/autonomous-arm64/NoYouPub-V3-autonome-arm64-test.dmg`.
Its runtime sets the deployment target to macOS 14.0 because the bundled Python
framework and native libraries require it. The machine used for testing ran
macOS 14.3. This DMG uses local ad hoc signing for Apple Silicon.
Its build inputs, logs, SHA-256 manifest and validation scripts are in
`artifacts/autonomous-arm64/`. The app includes dependency notices, FFmpeg's
exact source archive and compiler configuration in `Contents/Resources/Notices/`.

For a local package with the complete runtime, pass both `--development` and
`--runtime-vendor` to the app builder, set `--minimum-macos` to the highest
deployment target found in the runtime, then use `--development-review` for
the DMG. The frozen Core locates the sibling `bin/` directory without
development environment variables.

Freeze in the isolated venv:

```sh
python3 scripts/freeze_core.py --python "$PWD/.venv/bin/python"
```

This freezes the existing modules, including dynamic dispatch and yt-dlp resources. It does not obtain Node, FFmpeg, licenses or Python sources, nor does it install/register the result. The recipe still requires an actual freeze/smoke test. Collect the resulting complete onedir output as `Core/` with executable `Core/noyoupub-core` (keep PyInstaller's `_internal` directory). Add audited, portable Node/FFmpeg/ffprobe binaries and all their bundled libraries:

```text
vendor/
  Core/noyoupub-core
  Core/_internal/...
  bin/node
  bin/ffmpeg
  bin/ffprobe
  Extension/manifest.json
  Extension/...   # current source/extension, including generated locales/icons
  Notices/...    # complete notices, licenses, build provenance/source references
  runtime-manifest.json
```

`runtime-manifest.json` is an explicit JSON object: `files` maps every file under Core/bin/Extension (and all notice files) to a SHA-256 hex digest; `notices` lists the relative notice filenames. No sample hashes are accepted as production data. Keep this vendor folder under `artifacts/`, not in Git. `scripts/audit_runtime.py` validates this contract before compilation. The builder verifies hashes, public extension identity, relative confined symlinks (absolute links are rejected), executable Mach-O headers and `otool -L` portability. Absolute Homebrew/developer library links are rejected. These checks are necessary, but do not replace provenance/license review or runtime testing.

```sh
python3 scripts/audit_runtime.py --vendor artifacts/vendor
python3 source/build_app.py --runtime-vendor artifacts/vendor --output artifacts/NoYouPub-3-beta.app
python3 source/build_app.py --runtime-vendor artifacts/vendor --core-only --output artifacts/NoYouPub-Core-Installer-beta.app
```

The resulting production-mode app still needs real signing/notarization. Builds never call the installer, replace an installed app, invoke Gatekeeper bypasses or publish anything. Build recipes are repeatable with fixed inputs; compiler output, timestamps and Apple signatures are not claimed to be byte-identical.
