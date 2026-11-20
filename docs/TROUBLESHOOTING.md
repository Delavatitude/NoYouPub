# Dépannage / Troubleshooting

| Symptôme / Symptom | Vérification / Check |
|---|---|
| Passerelle absente / Bridge unavailable | Vérifier le moteur et activer la passerelle dans les réglages V3. L’extension dépend toujours de Core. / Verify Core and enable the V3 Chrome bridge. Chrome still needs Core. |
| Build de développement incomplet / Incomplete dev build | Attendu sans runtime embarqué ; suivre BUILD.md, pas une réinstallation de 2.5. / Expected without bundled runtime; follow BUILD.md, do not modify V2.5. |
| Aucune TV / No TV | TV allumée, réseau local autorisé, même LAN, pas d’isolation invités/VPN bloquant le multicast ; essayer son IP locale et lancer le diagnostic. / Check power, local network permission, reachable LAN, guest isolation/VPN and manual local IP. |
| Deux noms semblables / Similar names | Les identités identiques sont dédupliquées, mais deux identités réelles conservent leur adresse pour les distinguer. / Identical identities are deduplicated; different identities keep address labels. |
| Préparation longue / Slow preparation | Compatible prépare tout le MP4 ; Rapide dépend des formats disponibles. Vérifier qualité et connexion ; annuler explicitement si nécessaire. / Compatible waits for a complete MP4; Fast depends on formats. Check quality/connection and cancel if needed. |
| HLS incompatible / Incompatible HLS | Le chemin Cast peut exiger H.264/AAC HLS. DLNA a aussi des chemins MP4/DASH compatibles ; aucune garantie sur toutes les vidéos. / Cast may require H.264/AAC HLS. DLNA also supports compatible MP4/DASH paths; not every video is guaranteed. |
| Pause/seek/vitesse refusé / Control rejected | Le récepteur doit confirmer son état. Certaines LG rechargent le flux ; essayer Compatible pour la prochaine lecture. / The receiver must confirm state; some LG operations reload media. Try Compatible for the next cast. |
| Timeline grisée / Disabled timeline | Attendre un état TV récent et une durée connue ; une ancienne session ne doit pas masquer une nouvelle préparation. / Wait for fresh state and known duration. Old sessions must not override a new job. |
| Ancienne vidéo dans Chrome / Old browser video state | Distinguer vidéo TV et page consultée. Remplacer explicitement, ou regarder localement. Après une mise à jour d’extension, recharger YouTube. / Distinguish remote session from current page. Replace explicitly or watch locally; reload YouTube after extension updates. |
| Langue différente / Different language | Chrome : suivre l’app, langue du navigateur ou FR/EN explicite. Sans Core, dernière valeur connue ; le choix local reste disponible. / Chrome can follow app, browser or explicit FR/EN; offline retains the last known language. |
| Désinstallation refusée / Removal refused | Arrêter le relais et attendre son délai ; ne pas effacer un dossier inconnu ou une configuration appartenant à une autre installation. / Stop and wait for the relay; never delete unknown or foreign-owned files. |
| Gatekeeper bloque / Gatekeeper blocks | Utiliser une bêta signée/notarisée validée ; ne pas désactiver la protection. / Obtain a verified signed/notarized beta; do not disable protection. |

Diagnostics may contain personal network/media data. Redact locally before sharing. No bug report should include Chrome profiles, tokens, live signed URLs or downloaded videos. Include app/extension version, macOS/architecture, TV model/protocol, mode, quality, action and a synthetic/authorized reproduction.
