# Premier test Wokwi — à réaliser ensemble

**Présentation du 1er novembre 2026 :** le [projet Wokwi enregistré](https://wokwi.com/projects/478408633765115905) permet de montrer le montage et l'alarme locale. Pour une démonstration immédiate du tableau de bord, utiliser [PRESENTER_LE_PROJET.md](PRESENTER_LE_PROJET.md). La liaison HTTPS directe Wokwi → serveur n'est pas encore validée.

Le firmware local `netfix-2` corrige le redémarrage dû à la tâche réseau et ajoute les diagnostics `wifi=connected`, `clock=ready` et `TLS_ERROR`. Une erreur HTTPS ne doit plus arrêter les mesures et l'alarme locale. La version est affichée après `FROID CONNECT` au démarrage. Ne pas confondre un Wi-Fi connecté avec une réponse `HTTP ... status=201`.

Les fichiers sont prêts. Aucune clé API du site Wokwi n’est nécessaire pour utiliser le simulateur dans le navigateur. Un compte Wokwi sert à sauvegarder votre projet. Une licence d’extension VS Code ou un jeton de CI ne sont pas nécessaires pour ce premier essai.

## Préparer le poste

Dans `C:\IRM\IOT\cold-chain-iot` :

```powershell
.\scripts\start.ps1 -Tunnel
.\.venv\Scripts\python.exe scripts\configure_wokwi.py
```

Ouvrir le tableau de bord sur **http://127.0.0.1:8000** et utiliser le mot de passe de `.runtime/acces-local.txt`.

Le script de configuration récupère l’URL du tunnel actif et prépare le certificat HTTPS et la clé locale. Si le tunnel change, relancer ce script et recopier le fichier de configuration dans Wokwi.

L’archive `.runtime/wokwi-import.zip` regroupe les quatre fichiers pour faciliter leur transfert. Si votre éditeur ne propose pas l’import d’une archive, les copier séparément comme indiqué ci-dessous.

## Créer le projet dans le navigateur

Ouvrir [un nouveau projet ESP32 Wokwi](https://wokwi.com/projects/new/esp32).

| Fichier dans Wokwi | Contenu local à utiliser |
|---|---|
| `sketch.ino` | `firmware/sketch.ino` |
| `diagram.json` | `firmware/diagram.json` |
| `libraries.txt` | `firmware/libraries.txt` |
| `coldchain_config.h` | `firmware/coldchain_config.h`, généré localement |

Remplacer le contenu des deux onglets existants et ajouter les fichiers manquants avec le menu de fichiers de l’éditeur. Le gestionnaire de bibliothèques peut également servir à installer OneWire 2.3.8, DallasTemperature 3.9.0 et ArduinoJson 6.21.5.

Pour les onglets déjà présents (`sketch.ino` et `diagram.json`), copier-coller le contenu local dans l’éditeur avec `Ctrl+A`, puis `Ctrl+V`. L’essai d’import par `Upload file(s)...` a conservé les fichiers existants : ce menu convient aux deux fichiers manquants, mais ne suffit pas à remplacer le programme d’exemple. Le bon `sketch.ino` commence par les inclusions `Arduino.h`, `WiFi.h`, etc. ; il ne doit plus contenir `Hello, ESP32!`.

La version DallasTemperature 3.11.0, disponible dans PlatformIO, n’est pas référencée dans l’index Arduino utilisé pour ce parcours Wokwi. Le fichier `libraries.txt` et la compilation locale utilisent donc la version 3.9.0. Si Wokwi affiche `Library 'DallasTemperature@3.11.0' not found`, remplacer cette ligne par `DallasTemperature@3.9.0`.

Si l’interface d’ajout de fichiers diffère, envoyer une capture de la barre des onglets et du menu de l’éditeur. Ne pas inclure le contenu de `coldchain_config.h`, car il contient la clé de démonstration.

Le montage doit montrer un ESP32, un DS18B20 réglé initialement à 5 °C, un buzzer, une LED rouge et deux résistances. Le trajet GPS est fourni par le programme.

## Test 1 : première mesure — commencer par celui-ci

1. Lancer la simulation avec le bouton de lecture.
2. Ouvrir le moniteur série à 115200 bauds.
3. Attendre la connexion réseau et la synchronisation de l’horloge.
4. Vérifier une ligne `MEASURE ... temp=5.00 state=NORMAL`.
5. Vérifier ensuite une ligne `HTTP ... status=201` ou `status=200`.
6. Sur le tableau de bord, sélectionner le transport de démonstration et vérifier une température proche de 5 °C, une mesure récente et la source Wokwi.

À transmettre : une capture du montage avec le moniteur série, une capture du tableau de bord, et éventuellement le lien du projet sauvegardé. Indiquer aussi si une erreur apparaît.

La simulation Wokwi peut s’exécuter moins vite que le temps réel. Dans ce cas, une mise à jour tardive peut être signalée « ancienne » même si la simulation est encore active. Les journaux distinguent les temps de mesure et la réception.

## Test 2 : excursion courte

Cliquer sur le DS18B20 et régler 12 °C. Revenir à 5 °C après environ 20 secondes de simulation. Le moniteur doit indiquer `PENDING`, puis `NORMAL`. Le buzzer ne doit pas sonner et aucune nouvelle alerte prolongée ne doit apparaître.

À transmettre : les lignes de transition ou une capture du moniteur série.

## Test 3 : excursion prolongée et retour à la normale

Régler à nouveau 12 °C. Attendre que le moniteur indique une durée `elapsed` d’au moins 30 secondes et l’état `ALARM`.

Résultats attendus : buzzer audible, LED allumée, alerte active dans le tableau de bord. Revenir à 5 °C : le buzzer et la LED s’arrêtent ; l’événement reste dans l’historique avec l’état « Résolue ».

À transmettre : capture de l’alerte active, capture après résolution et confirmation textuelle « buzzer entendu » ou description du problème. Une capture seule ne permet pas de vérifier le son.

## Test 4 : coupure et reprise

1. Dans l’entrée du moniteur série, envoyer la lettre `n`.
2. Vérifier `NETWORK_PAUSED`. L’acquisition continue, seuls les envois HTTP sont suspendus.
3. Régler 12 °C pendant plus de 30 secondes de simulation.
4. Vérifier que le buzzer fonctionne localement et que le tableau de bord signale des données anciennes après environ 15 secondes réelles.
5. Envoyer à nouveau `n`. Vérifier `NETWORK_RESUMED`, puis la reprise des réponses HTTP.
6. Vérifier que les mesures mémorisées réapparaissent sans doublon.

Garder la coupure inférieure à 10 minutes pour ce premier essai. Les mesures sont mémorisées en RAM ; ne pas arrêter ni redémarrer la simulation pendant la coupure.

À transmettre : capture du moniteur série pendant la pause, capture du tableau de bord signalant les données anciennes et capture après reconnexion.

## Si une étape échoue

| Observation | Vérification utile |
|---|---|
| Erreur de compilation | Copier le texte complet de l’erreur et le nom du fichier concerné |
| Icône Wi-Fi barrée, menu `Error`, 0 octet reçu | Arrêter la simulation, enregistrer le projet, actualiser avec `Ctrl+F5`, puis relancer. Si l’erreur persiste, transmettre les messages rouges de la console du navigateur liés à `netwi.wokwi.com` ou `WebSocket`. |
| `TLS_WAIT` | Vérifier que le fichier de configuration a été créé et attendre la synchronisation UTC |
| HTTP négatif | Vérifier que le tunnel et l’API fonctionnent ; transmettre le code négatif |
| HTTP 401 | La clé copiée dans Wokwi ne correspond pas à la configuration locale |
| HTTP 404 | Le transport configuré n’existe pas dans l’API |
| HTTP 409 | Transport terminé ou identifiant de mesure réutilisé avec un contenu différent |
| HTTP 422 | Mesure rejetée par la validation ; transmettre la ligne de diagnostic |
| HTTP 503 | MongoDB est indisponible ; le firmware réessaie |
| `SENSOR_ERROR` | Vérifier le montage DS18B20 et sa liaison au GPIO 18 |
| Buzzer silencieux avec `ALARM` | Vérifier le volume du navigateur, celui de Wokwi et la connexion au GPIO 19 |

L’envoi du premier résultat suffit pour poursuivre le diagnostic. Les quatre tests constituent la recette manuelle initiale ; ils ne sont pas déclarés réussis tant que leur exécution n’a pas été observée.

Le bouton `Enable Private Gateway` ne répare pas automatiquement une erreur de la passerelle publique. La [documentation réseau Wokwi](https://docs.wokwi.com/guides/esp32-wifi) indique que la passerelle publique est disponible pour tous les utilisateurs ; la passerelle privée est une option payante distincte. Le parcours de ce projet utilise la passerelle publique et le tunnel HTTPS.
