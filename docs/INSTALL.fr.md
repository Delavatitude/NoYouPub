# Installer et utiliser NoYouPub

**Pour le candidat autonome 3.0.0-beta signé localement, lire le [guide de la bêta](BETA-INSTALLATION.md).** Le parcours ci-dessous décrit une distribution signée par un développeur identifié.

## Préparer le Mac et la TV

Il faudra un Mac compatible (cible macOS 13+, versions exactes à confirmer par les tests), Chrome pour l’extension et une TV Google Cast ou un récepteur DLNA compatible. Le Mac et la TV doivent pouvoir communiquer sur le réseau local. L’utilisation sans Chrome depuis l’app Mac reste possible. La prise en charge d’un modèle ne se déduit pas seulement de la présence d’un bouton Cast dans YouTube.

## Installation sans terminal, après publication validée

1. Ouvrir le DMG signé/notarisé, puis glisser **NoYouPub** dans Applications. Pour utiliser uniquement Chrome avec le moteur, choisir plutôt **NoYouPub Core Installer**, qui permet la configuration sans fenêtre permanente.
2. Ouvrir l’app depuis Applications. Si macOS bloque le paquet, ne pas désactiver Gatekeeper : utiliser uniquement une version validée et contacter le responsable de la bêta.
3. Dans **Installation et langue**, choisir la langue, cliquer sur **Vérifier le moteur**, puis **Activer la passerelle Chrome**. Les dépendances de la future version seront incluses ; aucune commande Homebrew/Python ne sera demandée à l’utilisateur.
4. Autoriser le réseau local si macOS le demande. Allumer la TV. Dans la vue principale, cliquer sur Actualiser et choisir le récepteur. Si la découverte échoue, consulter Connexion TV et ajouter son IP locale. Une autorisation TV éventuelle s’accepte avec la télécommande.
5. Pour Chrome, ouvrir l’onglet **Extension Chrome** des réglages. Pendant la bêta locale, ouvrir `chrome://extensions/`, activer Mode développeur, puis Charger l’extension non empaquetée et choisir le dossier indiqué par l’app. Recharger YouTube ensuite. La publication Web Store reste une étape distincte non réalisée.

Le même identifiant d’extension est conservé : pour tester la V3 sans remplacer une extension 2.5 personnelle, utiliser un profil Chrome séparé. L’ancien hôte et les anciennes données restent distincts.

## Première lecture

Coller un lien YouTube dans l’app ou ouvrir une vidéo dans Chrome, choisir TV/qualité et lancer la diffusion. L’app affiche les étapes de préparation. En mode Rapide, elle peut démarrer avant la fin du téléchargement ; le mode Compatible attend le MP4 complet et peut prendre plusieurs minutes. Il n’y a pas de délai garanti.

Une fois l’état confirmé, utiliser Pause/Reprendre, Arrêter, la timeline ou la vitesse. Sur certains récepteurs, déplacement et accélération rechargent le flux. Le volume dépend des commandes proposées par la TV. Chrome permet d’ajouter plusieurs vidéos à la file et de naviguer indépendamment ; garder Chrome ouvert pour l’enchaînement et le Mac éveillé pour le relais.

## Désinstallation

Arrêter la lecture et attendre la fin du relais (environ 30 secondes sur le chemin LG). Fermer la session de l’extension. Dans Installation et langue, cliquer **Désactiver la passerelle Chrome** : seuls ses composants V3 et son enregistrement sont retirés, les préférences sont conservées. Supprimer ensuite l’extension dans Chrome, puis l’app depuis Applications. La version 2.5 n’est pas touchée.

Pour supprimer aussi les préférences V3, utiliser la procédure explicite du [guide Core](CORE.md) ou supprimer uniquement le dossier NoYouPub après avoir vérifié qu’il appartient à V3 et qu’aucun relais ne tourne. Ne pas supprimer le dossier historique YouTube-CATT. En cas d’erreur de propriété ou de relais actif, conserver les fichiers et consulter le diagnostic.
