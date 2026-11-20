# Install and use NoYouPub

**For the ad hoc-signed standalone 3.0.0-beta candidate, see the [beta installation guide](BETA-INSTALLATION.md).** The guide below describes distribution with an identified developer signature.

## Requirements

A compatible Mac (macOS 13+ target; exact support requires testing), Chrome for the extension and a compatible Google Cast/DLNA receiver. Mac and TV must be reachable on the local network. The Mac app can be used without Chrome. A YouTube Cast button alone does not establish protocol compatibility.

## Future installation without Terminal

1. Open the signed/notarized DMG and drag NoYouPub into Applications. For Chrome-only use, choose NoYouPub Core Installer, which configures the same engine without a permanent controller window.
2. Open it from Applications. If macOS blocks the package, do not disable Gatekeeper; obtain a verified beta from its maintainer.
3. In Installation and language, select the language, Verify Core and Enable Chrome bridge. The future package must include dependencies; end users will not need Homebrew/Python commands.
4. Allow local network access if prompted. Turn on the TV, refresh the receiver list and select it. Connection settings offer a local-IP fallback. Accept a TV pairing prompt with the remote if required.
5. In the Chrome extension settings tab, open `chrome://extensions/`, enable developer mode and Load unpacked from the folder shown by the app for the local beta. Reload YouTube. Web Store publication is separate and pending.

The extension keeps its stable ID. Test V3 in a separate Chrome profile to preserve an existing V2.5 extension. Historical data and native host registration are separate.

## First playback

Paste a YouTube link in the app or open a video in Chrome, choose TV/quality and cast. Preparation stages are displayed. Fast mode may start before the download completes; Compatible mode waits for a complete MP4 and can take minutes. No startup time is guaranteed.

Once playback is confirmed, pause/resume, stop, seek or adjust speed. Some receiver operations reload the stream; volume control depends on TV support. Chrome's queue and independent navigation remain available. Keep Chrome open for queue advancement and the Mac awake for media delivery.

## Removal

Stop playback, wait for relay shutdown (about 30 seconds on the LG path), and close the extension session. In Installation and language select Disable Chrome bridge. Only owned V3 components/registration are removed; preferences remain. Then remove the Chrome extension and the app from Applications. V2.5 is not removed.

To also erase V3 preferences use the explicit [Core removal procedure](CORE.md), or remove only the verified V3 NoYouPub data directory after stopping all relays. Never delete the historical YouTube-CATT directory. If ownership or active-state checks fail, retain the files and diagnose first.
