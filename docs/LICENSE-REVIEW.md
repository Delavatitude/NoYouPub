# Licences, contenu et publication — décision en attente

État au 2026-11-18. **Aucune licence n’a été appliquée au projet.** Ce document prépare une décision ; il n’accorde aucun droit supplémentaire sur du code tiers ou des contenus YouTube.

## Proposition

Envisager **GPL-3.0-or-later** pour le code original, après accord des titulaires des droits (y compris le contributeur initial) et revue des dépendances/ressources réellement distribuées. Cette proposition facilite une politique cohérente avec une distribution comportant des composants GPL ; elle ne signifie pas que lancer un exécutable séparé place automatiquement tout le projet sous sa licence. Une alternative permissive pour le code propre avec composants agrégés séparément nécessite une analyse de la composition et de ses obligations. Ne pas ajouter de fichier LICENSE ni d’étiquette de licence définitive avant validation.

## Inventaire constaté

`dependencies.snapshot.json` enregistre les métadonnées de l’environnement existant, sans chemins personnels. Ce n’est ni une validation juridique, ni une analyse de vulnérabilités. Les licences exactes, exceptions, notices et dépendances embarquées doivent être vérifiées dans les archives correspondant à chaque version.

| Composant | Métadonnées observées | Travail avant distribution |
|---|---|---|
| catt | BSD | Vérifier variante et conserver notices |
| yt-dlp (source) | Unlicense | Distinguer source et exécutables agrégés |
| yt-dlp-ejs | Unlicense AND MIT AND ISC | Conserver les notices de chaque partie |
| PyChromecast, casttube, requests et autres | MIT / Apache / BSD, selon inventaire | Inclure textes et attributions requis |
| zeroconf | LGPL-2.1-or-later | Vérifier obligations de redistribution de la forme embarquée |
| mutagen | GPL-2.0-or-later | Inclus dans l’environnement observé ; évaluer le paquet gelé réel |
| certifi | MPL-2.0 | Préserver notices et conditions des fichiers concernés |
| Python, Node et bibliothèques natives | Audit du futur payload requis | Inclure leurs licences et notices transitives |
| PyInstaller (outil) | GPL avec exception / certains fichiers Apache | Vérifier la version choisie et ses composants |
| Icônes, logo et code original | Droits du projet à confirmer | Vérifier provenance, contributeurs et autorisation de publication |

FFmpeg local observé : 8.1.2, construit avec `--enable-gpl --enable-version3 --enable-shared`, notamment des bibliothèques externes, avec dépendances Homebrew. Il n’est **pas** un exécutable autonome redistribuable tel quel. La licence de FFmpeg dépend des options de compilation ; les parties GPL changent la licence applicable à sa construction. Choisir une construction portable, documenter ses options et fournir les notices et sources correspondantes nécessaires. Ne pas présenter ce binaire comme LGPL uniquement. [FFmpeg : licences et redistribution](https://ffmpeg.org/legal.html).

Les sources yt-dlp sont sous Unlicense ; ses exécutables officiels peuvent embarquer des dépendances imposant d’autres conditions, notamment GPL. Ne pas recopier une étiquette Unlicense sur l’ensemble du runtime. [Licence yt-dlp](https://github.com/yt-dlp/yt-dlp#license).

L’exception de PyInstaller permet de choisir la licence des programmes gelés, sous réserve des licences de leurs dépendances. Elle ne supprime pas les obligations des paquets Python, de FFmpeg ou de Node. [Licence PyInstaller](https://pyinstaller.org/en/stable/license.html).

## Méthode YouTube : blocage de revue avant bêta publique

Le produit extrait des informations/flux avec yt-dlp et relaie des médias dans un lecteur TV externe. Les conditions YouTube restreignent notamment l’accès automatisé et certains usages de téléchargement, transmission ou contournement en dehors des autorisations prévues. Cette méthode et son positionnement « sans publicité » doivent faire l’objet d’une revue avant une publication : le fonctionnement technique n’établit pas une autorisation contractuelle. [Conditions YouTube](https://www.youtube.com/static?template=terms).

Limiter les essais aux contenus et usages autorisés. Ne promettre ni conformité garantie, ni accès à toutes les vidéos, ni contournement de DRM/restrictions. Le code refuse les formats signalés DRM dans la sélection. Une validation de licence du logiciel ne règle pas les droits sur les vidéos. La décision de publication, le texte commercial et les conditions d’usage doivent être approuvés séparément.

## Release gate

Le responsable doit valider : droits du code/logo, licence du projet, notices de chaque composant réellement embarqué, sources correspondantes et instructions de construction, obligations des codecs selon les territoires, conditions YouTube et notices de confidentialité/support. Garder cette liste liée au manifeste exact du runtime et aux empreintes du paquet, pas à une liste générique de dépendances.
