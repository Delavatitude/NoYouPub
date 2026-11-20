# Public beta release — manual gate, not executed

No Git remote, GitHub repository, Release, Chrome listing, system installation or external deployment has been created by this preparation. Nothing below runs automatically. Do not publish until the owner explicitly approves the exact reviewed artifacts and project license.

## Before signing

1. Approve original-code/logo rights, project license, the YouTube access/positioning review and complete third-party license/source obligations. Add the approved license only afterward.
2. Finish the frozen runtime with portable Node/FFmpeg/ffprobe/Python and native libraries for each advertised architecture/OS. Preserve all notices and source provenance; produce wheel hashes and a complete runtime manifest.
3. Run the test suite, runtime smoke tests, real Chrome integration in a separate profile, and hardware matrix. Run a clean-Mac installation/removal test without Python, Node, Homebrew or prior registration. Verify FR/EN accessibility and first-configuration flow manually.
4. Scan the full proposed Git history and archives, not only working-tree files. Review author/committer metadata too: these local commits inherit the configured user identity, including a private email; choose an approved public identity and review any local history rewrite before a push. Run the focused audit with `--history`. Review permissions, public key/extension ID, native host origin and future Chrome Store identity. Configure a private security contact and actual support channel.
5. Review bundled signing inventory inside-out and required entitlements for the actual frozen runtime. No blanket entitlements or fabricated certificate are provided. Have a real Developer ID Application identity and notarytool profile in the maintainer's Keychain. Do not commit passwords, Team ID private credentials, keys or certificate exports.

## Apple signing and notarization

The app builder produces a local unsigned production-mode app only from an audited payload. `scripts/release_macos.sh` additionally requires `NOYOUPUB_RELEASE_APPROVED=YES`, a real identity, an existing Keychain profile and reviewed signing inventory. It signs nested code locally, refreshes the exact runtime hashes with `seal_runtime.py` (signatures change Mach-O bytes), rechecks the payload, then signs the outer bundle and verifies code; **it never submits anything**. The guard environment variable is not a replacement for human authorization.

After explicit approval, a maintainer can follow this order, substituting reviewed paths in the local shell:

```sh
# Sign the reviewed app/nested code with release_macos.sh first.
ditto -c -k --keepParent "$APP_PATH" "$APP_ZIP"
xcrun notarytool submit "$APP_ZIP" --keychain-profile "$NOTARY_KEYCHAIN_PROFILE" --wait
# Continue only after Accepted. Inspect rejection logs, never bypass Gatekeeper.
xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"
spctl --assess --type execute --verbose=2 "$APP_PATH"

# Use a new artifacts/ destination, after app stapling.
python3 scripts/package_macos.py --app "$APP_PATH" --output "$DMG_PATH"
codesign --sign "$DEVELOPER_ID_APPLICATION" --timestamp "$DMG_PATH"
xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_KEYCHAIN_PROFILE" --wait
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"
spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG_PATH"
shasum -a 256 "$DMG_PATH"
```

Apple submission is an upload; none of these upload commands has been executed. Every negative result blocks distribution. Recheck the archived app after copying and the final mounted DMG on a clean/quarantined download. Do the same for the Core-only installer if distributed. Local ad-hoc signatures are never presented as public notarization. [Apple notarization documentation](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

The DMG tool offers an explicit `--pre-notarization` option only for a real Developer ID-signed package that still needs the Apple stage. It is not a public-ready artifact. `--development-review` creates a clearly labelled local review DMG and never qualifies as a public beta.

## Prepare GitHub Releases after approval

Use a reviewed source commit/tag such as `v3.0.0-beta.1` **only after tests and approval**. No tag or push has been made. Create the repository under the chosen owner, enable private vulnerability reporting and configure support. Create a draft release first; do not automatically publish on every commit/tag.

Release attachments should contain the notarized/stapled DMG(s), SHA256SUMS, current unpacked extension ZIP and install instructions (or approved Chrome Store link), exact source archive, third-party notices and required corresponding sources/build recipes. Name architecture-specific artifacts accurately; do not claim universal support without checking all binaries. Never attach private configs/logs/test media, signing material, the historical runtime or a development app.

Use `RELEASE-NOTES.template.md`, accurately marking tested hardware/OS, startup limits, queue/Chrome requirements, rate-change reload behavior, current bugs and known exclusions. Manually test each downloadable checksum/artifact. Review the complete draft and obtain final approval before any upload/publication. GitHub/Chrome/Apple policy acceptance and credentials remain external requirements.
