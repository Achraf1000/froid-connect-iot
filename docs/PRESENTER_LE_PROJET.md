# Présenter Froid Connect — guide de démonstration

Version du 1er novembre 2026 · Achraf Abdelhedi

## Ce que vous présentez

Froid Connect surveille la température d'un transport et conserve les dépassements. La plage de démonstration est **2 à 8 °C** ; une alarme se déclenche après **30 secondes continues** hors de cette plage.

Pour cette présentation, **Wokwi montre le capteur et l'alarme locale**. Le **tableau de bord reçoit un scénario simulé par Python**, enregistré réellement dans MongoDB et synchronisé avec Firebase local. Le GPS est simulé. La liaison HTTPS directe de Wokwi vers le serveur reste à finaliser ; les deux démonstrations sont indépendantes.

Phrase à dire : « Je vais montrer le fonctionnement du dispositif dans Wokwi, puis la chaîne logicielle avec des mesures simulées envoyées à la vraie API. »

## Préparer en deux minutes

1. Ouvrez `C:\IRM\IOT\cold-chain-iot`.
2. Double-cliquez sur **DEMONSTRATION.cmd**. Gardez sa fenêtre ouverte : c'est le menu de commande de la démonstration.
3. Le navigateur s'ouvre sur le transport **Présentation guidée · HH:MM**. Le mot de passe se trouve dans `.runtime\acces-local.txt`.
4. Dans le menu noir, appuyez sur **1** : le tableau de bord reste à **5 °C** pour commencer. Attendez environ 5 à 8 secondes.
5. Ouvrez [votre projet Wokwi](https://wokwi.com/projects/478408633765115905) dans un autre onglet.

Le mode automatique démarre par défaut : 20 s à température normale, 45 s à 12 °C, puis retour à la normale. Il recommence toutes les 150 s et s'arrête après **4 heures**. Le choix **1** permet d'attendre le professeur sans déclencher d'alarme. Si vous fermez seulement le menu, les mesures continuent ; le choix **7** les arrête. Après expiration, relancez **DEMONSTRATION.cmd** pour créer une nouvelle session.

Le lien **http://127.0.0.1:8000/?transport=latest** sélectionne automatiquement la présentation la plus récente à l'ouverture. Conservez ce lien plutôt que celui d'une ancienne session. S'il était déjà ouvert avant la relance, actualisez la page.

Si vous ouvrez seulement `http://127.0.0.1:8000`, sélectionnez **Présentation guidée · HH:MM** dans **TRANSPORT SUIVI**. L'ancien transport « Démonstration · Tunis → La Marsa » contient un historique différent.

## Déroulé conseillé — environ six minutes

| Étape | Votre manipulation | Ce que vous expliquez |
|---|---|---|
| 1. Objectif — 30 s | Montrez la vue d'ensemble à 5 °C. | « Le but est de repérer une rupture de la chaîne du froid et de conserver sa trace. » |
| 2. Montage Wokwi — 1 min | Montrez ESP32, DS18B20, LED et buzzer. Cliquez sur ▶ si la simulation est arrêtée. | « L'ESP32 lit la température toutes les cinq secondes. L'alarme fonctionne localement. » |
| 3. Alarme locale — 45 s | Avec `"temperature": "12"` dans `diagram.json`, observez `PENDING`, puis `ALARM` après 30 s. Montrez la LED et le buzzer. | « Un dépassement bref ne déclenche pas l'alarme ; il doit durer trente secondes. » |
| 4. Supervision — 45 s | Revenez au tableau de bord. Dans la fenêtre **DEMONSTRATION.cmd**, appuyez sur **2**. Attendez environ 35 à 40 s. | « Ce scénario logiciel envoie 12 °C à l'API. Le serveur calcule l'alerte et la publie dans Firebase local. » |
| 5. Retour à la normale — 30 s | Appuyez sur **1** dans le menu. Attendez 5 à 8 s, puis ouvrez **Alertes**. | « L'alarme est résolue au retour à 5 °C, mais l'événement reste dans l'historique. » |
| 6. Traçabilité — 1 min | Ouvrez **Mesures**, montrez la source **Simulateur Python**, puis **Exporter CSV**. Revenez à la carte. | « Chaque mesure conserve sa date, sa température, sa position et sa source. Le trajet GPS est simulé. » |
| 7. Conclusion — 30 s | Montrez **État du suivi** et le bandeau de démonstration. | « Le stockage MongoDB et Firebase local fonctionnent. Le prochain travail porte sur la liaison HTTPS directe du simulateur Wokwi. » |

**Les touches du menu commandent uniquement les données du tableau de bord. Elles ne changent pas le capteur Wokwi.**

Pour changer la température initiale dans Wokwi : arrêtez la simulation avec ■, ouvrez `diagram.json`, recherchez `"temperature": "12"`, remplacez `12` par `5`, puis relancez ▶. Cela démontre le démarrage à température normale ; ce n'est pas un test de retour à la normale pendant la même exécution.

## Essai supplémentaire si le professeur le demande

Pour montrer Firebase, ouvrez **http://127.0.0.1:4000/database/demo-cold-chain-default-rtdb/data**. Dans **Realtime Database**, développez `transports`, choisissez le transport `PRESENTATION-...` correspondant à votre session, puis `state`. Montrez `temperature_c`, `thermal_status`, `sequence` et `measured_at`. Il s'agit de l'interface officielle des émulateurs Firebase locaux ; l'historique complet reste dans MongoDB.

Dans le menu, appuyez sur **5** pour suspendre les envois. Après environ 20 s, le tableau de bord signale des données anciennes et conserve les dernières valeurs. Appuyez sur **6** pour reprendre ; une mesure récente doit arriver sous 8 s. Cet essai suspend le simulateur Python, il ne coupe pas le Wi-Fi Wokwi et ne teste pas son tampon.

Autres touches : **3** pour 0 °C, **4** pour relancer le scénario automatique, **7** pour arrêter les données. Pour arrêter tous les services après la présentation, double-cliquez sur **ARRETER_PROJET.cmd**. L'historique MongoDB est conservé.

## Captures à joindre au professeur

Des captures déjà vérifiées sont disponibles dans le dossier **`docs\captures`** : alerte, historique, journal des mesures et pause des envois. Elles montrent le scénario Python ; ajoutez votre propre capture Wokwi pour le montage.

1. Wokwi avec le montage, `temp=12.00 state=ALARM elapsed=30s` ou plus, LED allumée.
2. Tableau de bord pendant l'alerte à 12 °C, bandeau de démonstration visible.
3. Historique des alertes après le retour à 5 °C : événement **Résolue**.
4. Journal des mesures avec la colonne **Source** visible.

Ne photographiez pas `coldchain_config.h` ou le fichier contenant le mot de passe.

## Si quelque chose ne s'affiche pas

- Mauvais transport ou anciennes valeurs : choisissez le transport **Présentation guidée** le plus récent ; appuyez sur **1** dans le menu, puis attendez 8 s.
- Page inaccessible : relancez **DEMONSTRATION.cmd** et attendez le message « Démonstration prête ». Le lancement peut prendre une minute si Docker était fermé.
- Aucun son Wokwi : montrez la LED et `state=ALARM`, puis vérifiez le son du navigateur. Le son de Wokwi a déjà été confirmé lors des essais utilisateur.
- Erreur Wi-Fi/HTTPS Wokwi : poursuivez la démonstration locale ci-dessus. N'annoncez pas que les mesures Wokwi arrivent au tableau de bord.

Le guide général est [DEMARRAGE_RAPIDE.md](DEMARRAGE_RAPIDE.md). Le bilan des essais est [VERIFICATION.md](VERIFICATION.md). Le brouillon de mail est [MAIL_PROFESSEUR.txt](MAIL_PROFESSEUR.txt).
