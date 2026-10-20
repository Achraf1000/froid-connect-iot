# Vérification de la première version

Date : 20 octobre 2026.

Ce rapport distingue les essais exécutés sur le poste des essais qui nécessitent encore une manipulation dans Wokwi ou un compte Firebase cloud.

## Résultats obtenus

| Vérification | Résultat constaté |
|---|---|
| Tests Python/API et intégration | **45 tests réussis** |
| Tests navigateur Playwright | **4 tests réussis** |
| Contrôle Python Ruff | Réussi |
| Construction React/Vite | Réussie, sorties séparées pour graphiques, carte et Firebase |
| Compilation firmware ESP32 | Réussie avec PlatformIO / plateforme espressif32 6.10.0 et DallasTemperature 3.9.0 |
| Empreinte du firmware compilé | RAM statique : 52 292 octets ; flash : 940 841 octets, hors allocation dynamique pendant l’exécution |
| MongoDB du projet | Conteneur dédié, accessible localement sur 27018 |
| Émulateurs Firebase | Realtime Database et Authentication opérationnels |
| Parcours de démonstration Python | 100 mesures envoyées via HTTP, enregistrées et publiées ; une excursion prolongée résolue au retour à la normale |
| Droits Firebase | Lecture non authentifiée refusée ; lecture de l’utilisateur autorisé acceptée ; écriture de ce lecteur refusée |
| Panne de publication Firebase | Essai vers un port inaccessible, conservation MongoDB puis reprise vers l’émulateur vérifiée |
| Reprise après perte du contenu Firebase | Republication périodique des états couverte par un test |
| Tunnel HTTPS | `/health` accessible à travers le tunnel ; configuration et CA du firmware générées |
| Carte | Tuiles OpenStreetMap reçues avec HTTP 200 lors du contrôle visuel |
| Secrets locaux | Configuration et fichiers contenant des secrets exclus de Git |
| Docker | Configuration Compose et construction des deux images réussies ; API, interface, MongoDB et Firebase vérifiés ensemble en conteneurs |

Les mesures injectées par Python sont marquées `source=simulator`. Elles ne sont pas présentées comme des mesures issues de Wokwi.

Le premier essai utilisateur dans Wokwi a échoué à l’installation de `DallasTemperature@3.11.0`. Cette version existe dans le registre PlatformIO, mais est absente de l’index Arduino consulté. Les dépendances ont été alignées sur `3.9.0`, présente dans cet index ; PlatformIO utilise l’archive officielle Arduino correspondante. La compilation locale avec cette correction a réussi (`firmware-build-dallas-3.9.0.log`).

L’essai utilisateur suivant confirme la compilation et le démarrage du programme complet dans Wokwi : le moniteur affiche `FROID CONNECT`, puis six mesures `seq=0` à `seq=5`, à `5.00 °C`, avec l’état `NORMAL`. La lecture du DS18B20 est donc observée. Aucune ligne HTTP n’est présente dans cet extrait. Au contrôle effectué après réception, MongoDB ne contient encore aucune mesure de source `wokwi`, alors que l’API locale, MongoDB, Firebase et le tunnel HTTPS répondent correctement. L’indication `net=active` du firmware signifie que les envois ne sont pas mis en pause ; elle ne prouve pas une connexion Wi-Fi ou un envoi réussi.

Le contrôle Docker a utilisé des conteneurs temporaires, une base séparée et les ports 8001/9001/9100 afin de conserver le tableau de bord de l’utilisateur sur 8000. Les 100 mesures de démonstration ont été acceptées, puis les quatre scénarios navigateur ont réussi sur cette instance, y compris la connexion Firebase. Les conteneurs temporaires ont ensuite été arrêtés. La commande Compose de démarrage du profil complet sur ses ports habituels n’a pas été exécutée simultanément aux services natifs.

Après le dernier ajustement des ports d’émulation configurables, le contrôle Ruff et les 44 tests Python sans services externes ont également réussi ; le test d’intégration externe avait réussi lors du passage complet de 45 tests précédent.

## Couverture des essais Python

Les tests contrôlent les limites 2 et 8 °C, les seuils haut et bas, le passage exact à 30 secondes, les excursions brèves successives, le retour à la normale, les trous de séquence, les redémarrages de session et les mesures arrivées dans le désordre.

Ils vérifient également l’authentification, les types de données et horodatages, les coordonnées invalides, les champs absents, `NaN`, les doublons et conflits d’identité, le cycle de vie d’un transport, les erreurs MongoDB, la récupération des projections, la pagination, le CSV et la déconnexion.

Le test d’intégration utilise une vraie instance MongoDB et les deux émulateurs Firebase. Les autres tests utilisent une base de test en mémoire ou le moteur pur pour isoler les comportements.

## Couverture navigateur

Les quatre scénarios vérifient :

1. Connexion au tableau de bord, affichage des données enregistrées, écoute Firebase, alerte résolue, pagination et téléchargement CSV.
2. Rejet d’un mauvais mot de passe, filtres des alertes et déconnexion.
3. Affichage mobile à 390 × 844 pixels, navigation et absence de débordement horizontal de la page.
4. Interruption des requêtes d’état vers l’API, maintien de l’affichage précédent, signalement et reprise.

Le contrôle visuel a été effectué sur les captures desktop et mobile. Le fond de carte initial a été remplacé après constat d’une demande de clé par le fournisseur ; la version livrée utilise OpenStreetMap avec attribution.

## Preuves locales

Les fichiers suivants sont générés dans `.runtime`, qui n’est pas versionné :

- `pytest-results.xml` : résultats des tests Python ;
- `browser-results.json` : résultats Playwright ;
- `dashboard-desktop.png`, `dashboard-mobile.png`, `dashboard-map.png` : captures ;
- `firmware-build.log` : compilation ESP32 ;
- `docker-build.log` : construction des conteneurs ;
- `simulation-demo.log` : réponses HTTP du scénario injecté ;
- `simulation-docker.log` : réponses HTTP du scénario injecté dans l’instance Docker ;
- journaux `api`, `firebase` et `ngrok` selon le mode de lancement.

## Essais restant à observer

| Essai | Statut |
|---|---|
| Compilation, démarrage et lecture du DS18B20 dans le navigateur Wokwi | Confirmés par la capture et les six mesures à 5 °C transmises par l’utilisateur |
| Envoi Wokwi réel vers le tunnel et affichage de ces mesures | À confirmer ; aucune mesure Wokwi reçue au dernier contrôle |
| Buzzer effectivement audible et LED lors d’un dépassement prolongé | À réaliser avec l’utilisateur |
| Pause réseau Wokwi avec commande `n`, alarme autonome et reprise du tampon | À réaliser avec l’utilisateur |
| Redémarrage réel du firmware, perte du tampon RAM et débordement de 120 mesures | À compléter pendant la recette Wokwi |
| Démonstration complète de 30 minutes | Non exécutée à ce stade |
| Lecture/écriture sur un vrai projet Firebase cloud | En attente des paramètres du projet et des droits locaux |
| Validation du sujet, de l’IA et de la grille pédagogique | En attente de l’énoncé ou du retour de l’enseignant |

La compilation firmware ne constitue pas une preuve d’exécution de la simulation ni du fonctionnement audible du buzzer. Le [guide Wokwi](TEST_WOKWI.md) précise les manipulations et les captures à transmettre.

## Limites documentées

Le tampon de l’ESP32 est en mémoire vive. Les états et alertes sont reconstruits depuis les mesures MongoDB ; les deux bases n’utilisent pas de transaction distribuée. Une lacune de mesure interrompt la preuve de dépassement continu.

La projection relit l’historique du transport et l’API utilise un seul processus de projection. Le dimensionnement correspond à un prototype, pas à une flotte en production.

Les polices et le fond de carte dépendent d’Internet ; les coordonnées et les mesures restent disponibles quand le fond de carte échoue. Le fournisseur de tuiles ne fournit pas de garantie de disponibilité.

Le volet IA demeure facultatif, conformément à la proposition source, et n’est pas implémenté dans cette version.
