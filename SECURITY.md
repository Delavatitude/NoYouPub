# Security / Sécurité

V3 is an unpublished preparation branch, not an independently audited security release. No telemetry or remote control service is added. Supported security versions and a private reporting contact must be designated before publication. Until then, report privately to the project owner; do not open a public issue containing secrets or personal diagnostics. No email address or response SLA is invented here.

The Chrome bridge uses stdio Native Messaging with one exact allowed origin. Sender/top-frame/YouTube-origin/action validation is retained. Incoming host frames are bounded; media commands do not invoke a user-provided shell. HTTP exists only for TV media delivery, with a session token and selected-peer checks on an ephemeral LAN port. It is not encrypted and assumes a trusted LAN/local user. Do not forward the media port to the Internet. The architecture is not a sandbox against a compromised user account or malicious LAN administrator.

Installation validates the payload before mutation, confines symlinks and verifies extension identity. Production payloads require Mach-O executables, complete file hashes and audited notice paths. The builder additionally rejects nonportable absolute binary links. These are not authenticity guarantees: a trusted supply chain, real Developer ID signatures, notarization and a reviewed source/dependency manifest remain necessary. SHA-256 of an untrusted manifest does not establish trust.

Never publish raw `config/`, Chrome storage, relay state, downloaded media, signed provider URLs, logs, tokens, private IP mappings, browser preferences, signing keys, Keychain exports or certificates. Use synthetic reproductions. Extension public keys are public identity material; private signing keys are excluded and were not copied.

Run `python3 scripts/audit_public_tree.py --history` before a proposed source release, inspect the complete Git history and final archive, and independently review dependencies. The script is a focused heuristic, not a guarantee that every possible secret is found. No automated dependency vulnerability scan or penetration test has yet been completed. See the validation report.

Français : les journaux peuvent contenir des titres, URLs temporaires signées, adresses réseau et jetons. Les masquer avant tout partage. Ne pas désactiver Gatekeeper. La suppression conserve les préférences sauf demande explicite et refuse les dossiers dont la propriété V3 ne peut pas être prouvée.

Technical reference: [Chrome Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).
