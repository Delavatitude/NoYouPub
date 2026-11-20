<div align="center">

<img src="assets/hero.svg" alt="NoYouPub — YouTube on your TV, without standard ads" width="100%" />

<br />

**Your YouTube. Your TV. Your rules.**

Choose a video on your Mac. Send it to your TV. Stay in control from your computer.

<br />

[![Website](https://img.shields.io/badge/Website-noyoupub.com-8B5CF6?style=for-the-badge)](https://noyoupub.com)
[![Download](https://img.shields.io/badge/Download-macOS_Beta-181424?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/Delavatitude/NoYouPub/releases)
[![Help](https://img.shields.io/badge/Help-installation_guide-3F345C?style=for-the-badge)](https://noyoupub.com/en/help)

[Français](README.md) · **English**

</div>

---

## ▶ Watch videos. Not ads.

NoYouPub streams YouTube videos to a compatible TV **using the TV's video player instead of its YouTube app**. Find a video on your Mac, send it to the big screen, and control playback from your computer.

This playback approach avoids typical YouTube app ads. Sponsor segments **embedded in the video itself** are not removed.

<table><tr>
<td width="33%" align="center"><h3>📺 Big screen</h3>Play YouTube videos on your TV from your Mac.</td>
<td width="33%" align="center"><h3>⚡ One click</h3>Send videos directly from Chrome.</td>
<td width="33%" align="center"><h3>🎛️ Stay in control</h3>Pause, resume, seek and adjust playback speed.</td>
</tr></table>

## ✨ How it works

<div align="center">
<table>
<tr>
<td align="center" width="30%"><strong>▶️ YouTube</strong><br/><sub>Pick a video in Chrome</sub></td>
<td align="center" width="5%">➜</td>
<td align="center" width="30%"><strong>💜 NoYouPub</strong><br/><sub>One click to start streaming</sub></td>
<td align="center" width="5%">➜</td>
<td align="center" width="30%"><strong>📺 Your TV</strong><br/><sub>Big screen, controls on your Mac</sub></td>
</tr>
</table>
</div>

NoYouPub includes a native macOS application, an optional Chrome extension, and a local streaming engine. **Your Mac must remain powered on, awake, and connected during playback.**

## ⬇️ Get NoYouPub

> [!IMPORTANT]
> **Apple Silicon beta.** This initial build is **not signed with an Apple Developer ID and is not notarized**. macOS may block the first launch and require manual approval. Download only from the official releases page and verify the source.

1. Visit **[GitHub Releases](https://github.com/Delavatitude/NoYouPub/releases)**.
2. Download `NoYouPub-3.0.0-beta-arm64.dmg` once published.
3. Open the DMG and follow the installation instructions.
4. Connect your Mac and TV to the **same local network**, then launch NoYouPub.
5. Paste a YouTube video URL, select your TV, and start playback.

If macOS blocks the unnotarized app, see [Apple's official guidance](https://support.apple.com/guide/mac-help/mh40616/mac). **Do not disable Gatekeeper globally.**

The Chrome extension enables one-click casting directly from YouTube. See the [help center](https://noyoupub.com/en/help) for setup and availability information.

## 📽️ Demo

<div align="center">

**Find a video → click NoYouPub → watch on TV → control from Mac**

[**See NoYouPub in action**](https://noyoupub.com)

</div>

## 🖥️ Compatibility and limitations

| | Beta status |
|---|---|
| **Mac** | Apple Silicon (`arm64`); targets macOS 14.0, locally tested on macOS 14.3 |
| **TVs** | LG/DLNA and Google Cast discovery implemented; playback, pause, resume, seek, speed and stop tested on LG webOS UP7750PTB |
| **Browser** | Chrome with a locally installed extension (release setup instructions pending) |
| **Playback** | Fast and Compatible modes; available quality depends on the video |
| **Network** | Mac and TV on the same network; keep Mac awake |

Some protected or restricted videos may fail. Playback behavior and performance vary by receiver.

## 🧩 For developers

This repository contains the project overview and [installation guide](docs/BETA-INSTALLATION.md). Source code and the DMG are pending distribution clearance.

The streaming engine runs locally: **no cloud relay server is required**.

## 💜 Why NoYouPub?

Finding videos on a Mac is convenient. Watching them on a big screen is better. NoYouPub brings both together without another complicated interface.

## ☕ Support NoYouPub

**NoYouPub is a free, independently developed and maintained project.**

If you find it useful and would like to support its development, you can buy me a coffee. Every contribution helps improve the project and keep it freely available.

<div align="center">
<a href="https://www.buymeacoffee.com/louix" target="_blank">
  <img
    src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
    alt="Buy Me a Coffee"
    style="height: 60px !important; width: 217px !important;"
  >
</a>
</div>

<div align="center">

### Ready for the big screen?

[**Download beta**](https://github.com/Delavatitude/NoYouPub/releases) · [**Website**](https://noyoupub.com) · [**Help**](https://noyoupub.com/en/help)

<sub>Independent project. Not affiliated with YouTube, Google, or LG. Trademarks belong to their respective owners.</sub>

</div>
