HOUSTON METRORAIL — SWITCH VIEWER (RED + GREEN)

1. Keep the .bat and .html files in the same folder.
2. Run ouvrir_Houston_Switches.bat (from PowerShell: .\ouvrir_Houston_Switches.bat).
3. Choose 1 (Red), 2 (Green), or 3 (both).
4. The default browser will open the interactive map.
5. To view inside VS Code, open the Command Palette (Ctrl+Shift+P), choose
   'Simple Browser: Show', and enter the address displayed by the .bat:
   http://127.0.0.1:8767/houston_switches_map.html?line=both
6. Use the two checkboxes in the page to toggle lines any time.
7. Keep the .bat terminal open; Ctrl+C stops the local server.

Python 3 is needed for the local HTTP server; Internet is needed for map tiles.
The 25 Red and 12 Green coordinates are the provided OSM snapshot, NOT
refreshed from OSM automatically. OSM data is not guaranteed exhaustive.
