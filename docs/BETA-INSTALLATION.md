# NoYouPub 3.0.0-beta · Installation

## Français

Le DMG `NoYouPub-3.0.0-beta-arm64.dmg` contient l’app et son moteur complet. Il cible les Mac Apple Silicon avec macOS 14 ou ultérieur. Le candidat a démarré sur macOS 14.3. Les autres versions de macOS et les modèles de TV restent à confirmer.

1. Vérifier que l’empreinte SHA‑256 du DMG correspond au fichier `SHA256SUMS` de la même release.
2. Ouvrir le DMG et glisser **NoYouPub 3.0 Beta** dans Applications. Ce nom permet de conserver **NoYouPub** V2.5 à côté.
3. Ouvrir l’app et choisir **Connexion et réglages → Installation et langue → Vérifier le moteur**. Si macOS refuse l’ouverture, arrêter l’installation et contacter le responsable de la bêta. Le paquet utilise une signature ad hoc et n’est pas notarié. Garder les protections macOS actives.
4. Allumer la TV et vérifier que les deux appareils peuvent communiquer sur le réseau local. Si macOS le demande, autoriser l’accès au réseau local. Choisir la TV et coller un lien de vidéo dont l’utilisation est autorisée, puis lancer la diffusion. Garder le Mac éveillé.

Chrome est facultatif. Pour un test privé de l’extension, utiliser un profil séparé, activer la passerelle dans les réglages et charger l’extension incluse. V2.5 et V3 partagent l’identifiant d’extension. La validation Chrome Web Store reste distincte.

Si la TV n’apparaît pas, vérifier son état, le réseau local et les permissions avant de relancer la recherche. Si la vidéo ne démarre pas, noter le modèle de TV, la version macOS, le mode choisi et le message d’erreur. Masquer les adresses, jetons et liens privés avant de transmettre des journaux. Voir le [centre d’aide](https://noyoupub.com/fr/aide).

## English

`NoYouPub-3.0.0-beta-arm64.dmg` contains the app and its complete engine. It targets Apple Silicon Macs running macOS 14 or later. The candidate launched on macOS 14.3. Other macOS versions and TV models still need testing.

1. Check that the DMG's SHA‑256 matches `SHA256SUMS` from the same release.
2. Open the DMG and drag **NoYouPub 3.0 Beta** to Applications. Its name lets it sit next to the existing **NoYouPub** V2.5 app.
3. Open **Connection and settings → Setup and language → Check the core**. If macOS blocks the app, stop and contact the beta maintainer. The package is ad hoc signed and is not notarized. Keep macOS protections enabled.
4. Turn on the TV and make sure both devices can reach each other on the local network. Grant local network access if macOS prompts. Select the TV, paste a video URL you are authorized to use, and cast. Keep the Mac awake.

Chrome is optional. For private testing, use a separate profile, enable the Chrome bridge, and load the bundled extension. V2.5 and V3 share an extension ID. Chrome Web Store approval is a separate step.

If the TV is missing, check the TV, the local network and permissions, then refresh. If playback fails, record the TV model, macOS version, playback mode and exact error. Redact private addresses, tokens and URLs before sharing logs. See [help center](https://noyoupub.com/en/help).
