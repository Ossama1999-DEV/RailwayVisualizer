HOUSTON METRORAIL — SWITCH VIEWER AUTOMATIQUE

1) Decompresser le dossier dans C:\dev\test\Houston_Switches_Auto
2) Ouvrir un terminal VS Code dans ce dossier.
3) Lancer : .\ouvrir_Houston_Switches.bat 3
   Choix 1=Red, 2=Green, 3=les deux. Sans argument : menu.
4) Dans VS Code : Ctrl+Shift+P > Simple Browser: Show
5) Entrer : http://127.0.0.1:8767/houston_switches_map.html?line=both

![
   
](config/image.png)

AU DEMARRAGE :
- update_switches.py recupere les relations OSM Red (1741729), Green (2728566).
- Genere data\switches_red.csv et data\switches_green.csv.
- Le HTML charge les CSV en HTTP local, aucune coordonnee codee en dur.
- Le bouton "Actualiser depuis OSM" retélécharge les donnees ET recharge la carte.
- Le bouton "Relire CSV" recharge les CSV du disque sans consulter OSM.
- Les cases Red/Green filtrent les points affiches.

NECESSAIRE : Python 3 et acces Internet. Aucun module Python a installer.
La carte utilise Leaflet et des tuiles Internet OpenStreetMap/OpenRailwayMap.
Arreter le serveur local : Ctrl+C dans le terminal du .bat.

LIMITES : OSM peut etre incomplet, les voies partagees peuvent apparaitre
sur plusieurs lignes. Les switches trouves sur les membres directs des relations
OSM sont comptabilises, pas necessairement l'ensemble des aiguillages reels.
La numerotation est selon la latitude croissante (sud -> nord), et non l'ordre
ferroviaire reel pour une ligne qui n'est pas monotone nord-sud.
