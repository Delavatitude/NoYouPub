# Validation V3 — 2026-11-18

**Verdict : préparation technique vérifiée localement, pas une bêta publique distribuable.** Aucun test ci-dessous ne vaut certification de toutes les TV, validation juridique ou acceptation Apple.

## Environnement et périmètre

Mac de développement arm64, macOS 14.3, Swift 5.10. Les tests Python utilisent les dépendances de l’environnement existant en lecture ; aucune installation/mise à jour de paquet n’y a été faite. Les écritures des tests sont isolées dans des dossiers temporaires. Le code natif final est compilé avec une cible explicite macOS 13.0, confirmée par `vtool`; l’exécution sur macOS 13 et Intel n’a pas été testée.

Branche : `codex/noyoupub-v3`. Nouveau dépôt séparé, sans remote configuré. Les sources initiales, l’app installée et les réglages statiques protégés ont été comparés par SHA-256 : **63 fichiers contrôlés, 0 changement**. Cette vérification porte sur les fichiers statiques inventoriés, pas sur les données dynamiques qu’une application déjà ouverte peut écrire d’elle-même. Aucun test ne commande la TV, n’ouvre Chrome, n’installe V3 dans le compte réel ni ne remplace l’app.

## Tests exécutés et réussis

| Vérification | Résultat réel |
|---|---|
| `tests/test_core.py` | 24 tests unitaires réussis : préférences conservées/redémarrage, FR/EN système/manuelle, templates, titres préservés, protocole Native Messaging, rejet d’origine sans écriture, bornes des commandes, ancienne installation protégée, installation temporaire/réinstallation/désinstallation, rollback, refus de payload incomplet/scripts/liens sortants/hôte étranger, migration allowlistée, arrêt simulé, découverte simulée et annulation de jobs. |
| `tests/test_packaging.py` | 4 tests réussis : sortie de build confinée, refus de build public incomplet, garde de signature sans accord, empreintes après signature et rejet d’un inventaire modifié. Les octets « signés » de ce test sont synthétiques ; aucune signature Developer ID n’a été réalisée. |
| `tests/test_media_http.py` | HTTP réel sur 127.0.0.1 avec fichier synthétique : GET, HEAD, plages normales/suffixes/fin de fichier, 416 sur plages invalides. Aucun accès LAN/TV. |
| `tests/test_transport_ack.py` | Réponses SOAP simulées : pause/reprise/arrêt confirmés par état, erreur conservée si refus réel, relance Play bornée pendant chargement. |
| `tests/test_stream_http.py` | Flux rapide simulé : time-seek, offset, HEAD sans processus, rejet de seek invalide et nettoyage du sous-processus. |
| `tests/test_speed_timeline.py` | Position et durée originales à 2× après déplacement, cohérence de la timeline et des temps du flux. |
| `tests/test_page_navigation.cjs` | Navigation A→B, mode distant périmé, réponse tardive ignorée, lancement sur la bonne page dans une VM JavaScript. |
| `tests/test_extension.cjs` | File conservée si lancement échoue, consommée si réussi, séparation des sessions, pas de reprise automatique après pause, langue hors ligne et pendant une opération, templates FR/EN et manifeste. Test de logique en VM, pas une instance Chrome réelle. |
| `scripts/test_swift.py` | Compilation du Model réel puis assertions : lecture détectée pendant préparation, ancienne session ignorée, timeline, pause, curseur en glissement, état périmé, arrêt, format des durées et changement FR/EN sans perdre l’état. Aucun lancement de fenêtre ou de TV. |
| `scripts/test_ffmpeg.py` | FFmpeg réel, mire de 8 s et tonalité de 440 Hz : les six vitesses passent, durée conforme et processus terminés. Voir mesures ci-dessous. |
| Syntaxe | Tous les fichiers Python analysés ; `node --check` sur les cinq scripts d’extension ; génération des catalogues avec parité de clés/templates et contrôle des clés Swift simples. 391 entrées FR/EN, manifeste Chrome localisé. |
| Compilation GUI | App macOS et variante Core Installer compilées localement ; signatures ad-hoc de développement vérifiées. Cible native macOS 13.0 confirmée. Aucun runtime autonome inclus. |
| Packaging | DMG local explicitement marqué développement construit ; vérification de somme de contrôle `hdiutil verify` réussie. Ce résultat ne vaut pas notarisation et ne teste pas le parcours d’installation. |
| Sécurité de publication | Audit heuristique du contenu et de l’historique local réussi pour les motifs ciblés (chemins personnels, clés privées, credentials connus, URLs média signées, IP LAN hors exemple générique). `git diff --check` passé. Revue complémentaire requise ci-dessous. |

La suite principale `scripts/test_all.py --swift` a passé les tests Core, flux, extension et Model ensemble. Les quatre nouveaux tests de packaging ont aussi été exécutés séparément et intégrés au même lanceur. Après les dernières ressources linguistiques, la génération contrôlée et les tests ciblés FR/EN ont été repassés. Les compilations finales utilisent ces ressources.

### Mesures synthétiques de vitesse

| Vitesse | Durée du flux obtenu | Tonalité mesurée |
|---|---:|---:|
| 0,75× | 10,69 s | 440 Hz |
| 1× | 8,02 s | 440 Hz |
| 1,25× | 6,44 s | 440 Hz |
| 1,5× | 5,35 s | 440 Hz |
| 1,75× | 4,61 s | 440 Hz |
| 2× | 4,03 s | 440 Hz |

Ce test valide l’adaptation audio/vidéo sur ce Mac, pas la compatibilité de réception sur chaque TV.

## Échecs rencontrés et corrections

- Le test de langue Chrome a d’abord échoué quand `connectNative` levait une erreur immédiatement. La synchronisation est désormais lancée séparément, avec erreur absorbée, et le choix de langue passe aussi pendant une commande média. Test corrigé et réussi.
- Le premier essai HTTP a été refusé par le sandbox (`Operation not permitted` sur le bind loopback). Rejoué avec accès local autorisé : réussi.
- Le premier essai VideoToolbox a été refusé dans le sandbox (`Cannot create compression session: -12908`). Même test synthétique avec accès à l’encodeur : réussi aux six vitesses.
- Le premier assemblage DMG a été bloqué par le sandbox (`Périphérique non configuré`). Rejoué avec accès à hdiutil : création et vérification réussies.
- Le scan initial signalait les motifs de détection du scanner lui-même. Les définitions explicites ont été distinguées des données utilisateur ; contenu/historique repassés sans constat sur les motifs ciblés.
- Le contrôle des clés Swift a révélé un libellé de traitement manquant. Ajout FR/EN et garde de génération empêchant sa réintroduction.

**Aucun test logiciel exécuté ne reste en échec après correction/réexécution.** Les validations non exécutées ci-dessous restent des blocages, pas des tests réussis ou supposés.

## Essai réel de découverte en lecture seule

La découverte Cast/DLNA a aussi été exécutée sur le réseau avec un dossier de données temporaire et un délai global borné, sans appairage ni commande de lecture/contrôle. Le processus s’est terminé sans erreur, mais **0 récepteur a été trouvé**. Cela ne valide donc pas la détection réelle d’une TV. La présence/accessibilité des appareils et les conditions réseau pendant cet essai ne sont pas établies ; ne pas attribuer arbitrairement ce résultat à la TV ou au code. Rejouer avec une TV allumée et accessible avant la bêta publique.

## Matrice fonctionnelle : ce qui reste à vérifier réellement

| Fonction | Couverture locale | Validation encore nécessaire |
|---|---|---|
| Découverte TV | Identités/déduplication simulées, garde d’IP ; essai réseau réel : 0 récepteur | Rejouer la découverte avec matériel accessible ; multicast Cast/DLNA, permissions réseau et ajout IP sur matériel |
| Lancement Rapide | Sélection de formats, TS/seek et codec synthétiques | YouTube autorisé → relais → TV, état et temps de démarrage |
| Lancement Compatible | Sélection de formats et MP4 Range | Préparation complète → TV, tous contrôles pendant/après préparation |
| Pause/reprise/arrêt | SOAP simulé et Model | Télécommande, vrai renderer, pause longue, arrêt/reprise sans erreur média |
| Timeline/vitesses | Model, calculs et FFmpeg réels | Rechargement du lecteur TV, durée/position, six vitesses sur TV |
| File/navigation | VM JavaScript | Chrome réel, onglets SPA, suggestions, fin naturelle et Chrome fermé |
| Langues | Ressources, Python/JS et Model | Inspection visuelle FR/EN complète, VoiceOver, erreurs et dialogues macOS |
| Redémarrage Core | Préférences et protocole en nouveaux processus | Exécutable gelé, déconnexion native host, crash/état périmé et relance |
| Installation propre | Faux home temporaire avec payload de test explicite | Mac vierge sans Homebrew/Python/Node, bundle complet signé, Chrome réel |
| Compatibilité 2.5 | Formats retenus et copie allowlistée synthétique ; fichiers protégés inchangés | Migration volontaire depuis une copie réaliste des données, pas depuis le compte personnel actif |

Les observations LG de la version 2.5 ne constituent pas une revalidation V3. Aucun nouveau modèle Cast/LG n’a été certifié dans cette préparation.

## Livrables locaux et limites

Les derniers artefacts se trouvent dans `artifacts/` : `NoYouPub-3.0-beta1-local.app`, `NoYouPub-Core-Installer-3.0-beta1-local.app`, `NoYouPub-3.0-beta1-local.dmg`. Ils sont exclus de Git. Ils servent à la revue locale, contiennent les sources/ressources et **n’incluent pas Python/Node/FFmpeg autonomes**. Leur signature est ad-hoc. Ne pas les distribuer ni les présenter comme une bêta installable complète.

Le chemin de production exige un vendor audité. PyInstaller n’était pas installé dans l’environnement observé ; aucun gel complet n’a été effectué et aucun paquet n’a été installé pour le faire. Le FFmpeg Homebrew local comporte des dépendances dynamiques et composants GPL : il n’a pas été copié dans un runtime public.

## Blocages avant publication

1. Assembler et tester le runtime autonome portable, ses bibliothèques, notices et sources ; fixer les empreintes de dépendances par architecture. Le scellement final des empreintes doit suivre la signature imbriquée et précéder la signature de l’app.
2. Approuver la licence du code original et ses droits/provenances, les obligations tierces, la méthode d’accès YouTube et le positionnement public. Aucune LICENSE n’a été ajoutée.
3. Valider l’identité Git publique : les commits locaux héritent de l’identité configurée, dont une adresse privée. Ne pas pousser cet historique sans ce choix explicite. Aucun changement d’attribution n’a été imposé.
4. Fournir localement une vraie identité Developer ID et un profil notarytool ; revoir les entitlements, signer, obtenir Accepted, stapler et vérifier le paquet final. Aucun certificat fictif, upload ou contournement Gatekeeper.
5. Effectuer la matrice Mac vierge/Chrome réel/TV et l’examen visuel/accessibilité. Confirmer les OS/architectures effectivement pris en charge.
6. Choisir le dépôt/contact sécurité/support et la distribution de l’extension, préparer une Release brouillon, puis obtenir l’accord explicite sur les fichiers exacts avant tout push, upload ou publication.
