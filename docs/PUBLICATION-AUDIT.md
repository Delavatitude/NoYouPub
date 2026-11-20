# Audit de préparation à la publication

- Copie séparée de sources uniquement : aucun profil Chrome, journal, vidéo, cache, venv, configuration active ou URL média signée n’a été ajouté au dépôt.
- Chemins utilisateur codés en dur et noms/adresses du réseau personnel retirés de la copie initiale. Les exemples utilisent un libellé générique ou TEST-NET ; l’unique exemple RFC1918 autorisé est `192.168.1.100`.
- La clé présente dans le manifeste Chrome est une **clé publique d’identité**, pas un secret. Aucun export de clé privée/certificat n’est inclus.
- `.gitignore` exclut données/config/cache/logs, environnements, paquets, artefacts, clés et secrets usuels. Les exemples de configuration sont dédiés et sans identifiant personnel.
- `scripts/audit_public_tree.py --history` contrôle le contenu et les révisions Git locales sur des motifs ciblés ; il ne constitue pas un scan universel de secrets. Les images binaires, leur provenance et les archives finales restent à revoir.
- L’identité auteur/committer Git locale contient les coordonnées configurées dans Git. Ce n’est pas publié ; un choix d’identité publique et, si approuvé, une réécriture locale de ces métadonnées restent nécessaires avant un push. Les attributions n’ont pas été altérées sans décision.
- Inventaire des métadonnées de 18 dépendances Python dans `dependencies.snapshot.json`, versions dans `requirements-runtime.txt`. Il reste à contrôler les licences exactes, notices, sources, bibliothèques natives et vulnérabilités du futur runtime gelé.
- Les procédés YouTube, le positionnement « sans publicité » et les droits des contenus sont des sujets de validation avant publication ; aucune conformité n’est garantie par ce code.
- Pas de LICENSE définitive appliquée. Proposition et sources primaires dans `LICENSE-REVIEW.md`.
- Aucun remote Git configuré, push, dépôt distant créé, release/tag public, déploiement, upload Apple ou publication Chrome. Aucun changement de l’installation réelle.

Voir `VALIDATION.md` pour les tests réellement exécutés et les blocages.
