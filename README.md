# RailwayVisualizer v0.4 (prototype)

Explore les aiguillages (`railway=switch`) des lignes de train/tram présentes dans OpenStreetMap.

## Windows / VS Code

1. Installer Python 3.
2. Double-cliquer `launch.bat` ou exécuter `./launch.bat` dans PowerShell.
3. VS Code : `Ctrl+Maj+P` > **Simple Browser: Show** > `http://127.0.0.1:8767/`.
4. Choisir Houston Red, Houston Green, ou saisir **un identifiant OSM de relation d'itinéraire**.
5. Cliquer « Télécharger la ligne » ; choisir « Toute la ligne » ou « Entre deux stations ».
6. Télécharger le CSV exporté (`OSM_ID,Latitude,Longitude`).

## Ce qui est automatique

- Téléchargement de `https://api.openstreetmap.org/api/0.6/relation/<ID>/full` et, pour `route_master`, des relations enfants à chaque chargement.
- Recherche des voies rail/light_rail/subway/tram/narrow_gauge/monorail appartenant à la relation ou à ses sous-relations directes.
- Extraction des switches sur les nœuds de ces voies et export CSV.
- Recherche des stations *nommées, présentes parmi les membres de la relation*, avec tags de station, d'arrêt ou rôle stop/platform.
- Sélection d'un tronçon via plus court chemin entre les nœuds proches des stations, avec sélection des switches sur la trajectoire **et à moins de 35 m de la trajectoire** pour couvrir approximativement les voies parallèles.

## Limites importantes

- Nécessite une **relation route** contenant directement les ways (les `route_master` avec sous-relations directes sont acceptées, mais les relations incomplètes ou atypiques restent possibles).
- Certaines relations ne contiennent pas de stations nommées ; le mode « Entre deux stations » y est indisponible.
- Le plus court chemin est géométrique : il ne tient pas compte des sens de circulation, signaux, restrictions ou branchements autorisés.
- **Le mode tronçon est approximatif**. Le couloir de 35 m peut omettre des voies ou inclure des aiguillages voisins. Les multiples itinéraires et voies parallèles ne sont pas reconstruits de façon exhaustive.
- Les switches ne sont pas un inventaire officiel ; OSM est collaboratif et incomplet. La numérotation suit la latitude, pas les PK ni l'ordre ferroviaire.
- Pas encore de recherche par nom de ville ni de sélection automatique d'une relation par nom ; il faut l'ID OSM.
- Leaflet et les fonds de carte OSM/OpenRailwayMap nécessitent Internet. Licence ODbL d'OSM à respecter pour les redistributions.

## Détails techniques

Standard Python uniquement, serveur lié à `127.0.0.1`, pas d'installation de packages Python. L'API locale propose `POST /api/route`, `POST /api/segment`. Données générées dans `data/`.

### Tests

`python -m unittest discover -s tests -v` (8 tests).

## Changement v0.4

Prise en charge des relations dont les membres sont des relations filles (route_master), et erreurs de diagnostic plus explicites. Cette correction ne garantit pas que les relations et leur topologie OSM soient complètes.

## Nouveau : mode « Entre deux PK relatifs » (v0.4)

1. Télécharger une ligne comportant **au moins deux stations reconnues** dans OSM.
2. Choisir « Entre deux PK relatifs ».
3. Sélectionner **Station origine (PK 0)** et **Station fin de référence**, puis cliquer « Calculer la référence PK ».
4. Les distances sont calculées par cumul des segments sur le **plus court chemin géométrique du graphe OSM**, depuis l'origine. Entrer deux valeurs en **km** (ex. `0.5` et `1.2`).
5. Cliquer « Visualiser entre ces PK ». Le CSV `data/pk_segment_<relation_id>.csv` contient les switches choisis (colonnes ID/lat/lon). Pour montrer/cacher les libellés, cocher « Afficher les PK sur la carte ».

**Attention** : il ne s'agit **pas des PK officiels** de Houston ou des exploitants. Le calcul dépend de la topologie OSM, de la paire de stations de référence et d'un couloir de proximité de 35 m. Les aiguillages sur d'autres voies ou itinéraires peuvent manquer, et les PK affichés sont des positions projetées sur la référence, pas des mesures de chaînage officielles. Aucune relation directe n'est établie avec les identifiants du fichier Excel Houston du type `100499.27`. Une future version pourra importer des PK officiels via des données d'infrastructure externes.

### Endpoints locaux

- `POST /api/pk/reference` : `{"relation_id":1741729,"start":"node:...","end":"node:..."}` calcule la référence et ses switches proches.
- `POST /api/pk/segment` : `{"relation_id":1741729,"pk_from":0.5,"pk_to":1.2}` sélectionne l'intervalle relatif (km).
