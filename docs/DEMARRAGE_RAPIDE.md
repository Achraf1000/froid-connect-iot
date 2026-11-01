# Lancer Froid Connect sur votre PC

**Pour la présentation immédiate : double-cliquez sur `DEMONSTRATION.cmd` et suivez [PRESENTER_LE_PROJET.md](PRESENTER_LE_PROJET.md).** Ce mode anime le tableau de bord avec des mesures simulées, sans dépendre du tunnel Wokwi. Firebase reste local, conformément au choix retenu.

Ce guide concerne le poste déjà préparé : `C:\IRM\IOT\cold-chain-iot`.
La démonstration utilise MongoDB et les émulateurs Firebase locaux. Aucun compte Firebase cloud ni jeton Wokwi n'est nécessaire.

## 1. Démarrer le tableau de bord

1. Ouvrez le dossier `C:\IRM\IOT\cold-chain-iot` dans l'Explorateur Windows.
2. Double-cliquez sur **LANCER_PROJET.cmd**.
3. Attendez le message `Tableau de bord : http://127.0.0.1:8000` et l'ouverture du navigateur.
4. Ouvrez `.runtime\acces-local.txt` avec le Bloc-notes et utilisez le mot de passe indiqué pour vous connecter.

Le lanceur démarre Docker Desktop si nécessaire, MongoDB, Firebase, l'API et le tunnel ngrok. Il actualise également la configuration Wokwi. Au premier démarrage après un arrêt du PC, Docker peut prendre une minute.

Si la fenêtre affiche une erreur, copiez ce message. Ne relancez pas l'installation complète. Les journaux se trouvent dans `.runtime`.

## 2. Ouvrir votre simulation Wokwi

1. Ouvrez votre projet **coldchain** dans Wokwi. Si vous avez perdu son lien, utilisez [vos projets Wokwi](https://wokwi.com/dashboard/projects).
2. Arrêtez la simulation avec **■** avant de remplacer un fichier.
3. Copiez le contenu du fichier local `firmware\sketch.ino` dans l'onglet Wokwi **sketch.ino** avec `Ctrl+A`, puis `Ctrl+V`.
4. Copiez de même `firmware\coldchain_config.h` dans l'onglet Wokwi **coldchain_config.h**. C'est ce fichier qu'il faut actualiser après le redémarrage du tunnel.
5. Vérifiez que **libraries.txt** contient exactement :

```text
OneWire@2.3.8
DallasTemperature@3.9.0
ArduinoJson@6.21.5
```

Le montage local de référence se trouve dans `firmware\diagram.json`. La température initiale y est fixée à 5 °C. Vous pouvez conserver la disposition des composants que vous avez ajustée dans Wokwi.

**Attention :** `Upload file(s)...` convient pour ajouter un fichier manquant, mais notre essai a montré qu'il pouvait conserver l'ancien contenu d'un fichier déjà présent. Pour remplacer un onglet existant, utilisez le copier-coller.

Le fichier `coldchain_config.h` contient une clé de connexion. Ne l'incluez pas dans vos captures ni dans le mail au professeur.

## 3. Vérifier le premier envoi

1. Cliquez sur **▶**.
2. Le moniteur doit afficher `FROID CONNECT` et la version du firmware, puis des lignes `MEASURE`.
3. La connexion Wi-Fi et la synchronisation de l'heure peuvent prendre quelques secondes. Une ligne `TLS_WAIT` au démarrage n'est pas à elle seule une erreur.
4. Une mesure envoyée et enregistrée produit `HTTP ... status=201`. Un renvoi déjà enregistré peut produire `status=200`.
5. Revenez sur [le tableau de bord](http://127.0.0.1:8000), sélectionnez le transport de démonstration et vérifiez la source **Wokwi**.

`net=active` signifie seulement que les envois ne sont pas suspendus. Il faut une réponse HTTP réussie pour confirmer la réception. Les anciennes valeurs issues du simulateur Python ne prouvent pas la connexion Wokwi.

Les essais de température, d'alarme et de coupure réseau sont détaillés dans [TEST_WOKWI.md](TEST_WOKWI.md). Les résultats réellement vérifiés figurent dans [VERIFICATION.md](VERIFICATION.md).

## 4. Arrêter le projet

Arrêtez la simulation Wokwi, puis double-cliquez sur **ARRETER_PROJET.cmd**. L'historique MongoDB est conservé.

## Si vous préférez les commandes

Dans PowerShell, à la racine du projet :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Tunnel
```

Pour arrêter :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1 -WithMongo
```

Le [README](../README.md) contient l'installation sur un autre poste, l'architecture et les commandes de vérification.
