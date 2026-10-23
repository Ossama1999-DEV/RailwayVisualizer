"""Download Houston METRORail OSM route relations and write switch CSV files.
Uses only the Python standard library. No manually entered GPS coordinates.
"""
import csv
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
ROUTES = {'red': 1741729, 'green': 2728566}
UA = 'HoustonMetroRailSwitchViewer/1.0 (educational railway infrastructure study)'


def fetch_osm(relation_id):
    url = f'https://api.openstreetmap.org/api/0.6/relation/{relation_id}/full'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/xml'})
    with urllib.request.urlopen(req, timeout=55) as response:
        return response.read()


def extract_switches(xml_content):
    """Count switch nodes referenced by light_rail ways belonging to this route.
    Relation/full also includes surrounding objects; avoid counting unrelated ways.
    """
    root = ET.fromstring(xml_content)
    rel = root.find('relation')
    if rel is None:
        raise ValueError('Relation absente du resultat OSM')
    member_way_ids = {m.attrib['ref'] for m in rel.findall('member') if m.attrib.get('type') == 'way'}
    if not member_way_ids:
        raise ValueError('Relation sans membres de type way')
    railway_way_count = 0
    track_node_ids = set()
    for way in root.findall('way'):
        if way.attrib.get('id') not in member_way_ids:
            continue
        tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
        if tags.get('railway') != 'light_rail':
            continue
        railway_way_count += 1
        track_node_ids.update(nd.attrib['ref'] for nd in way.findall('nd'))
    if railway_way_count == 0:
        raise ValueError('Aucune voie railway=light_rail dans cette relation')
    switches = []
    for node in root.findall('node'):
        node_id = node.attrib.get('id')
        if node_id not in track_node_ids:
            continue
        tags = {t.attrib['k']: t.attrib['v'] for t in node.findall('tag')}
        if tags.get('railway') == 'switch':
            switches.append((node_id, node.attrib['lat'], node.attrib['lon']))
    switches.sort(key=lambda item: (float(item[1]), float(item[2])))
    return switches, railway_way_count


def atomic_csv(destination, switches):
    DATA.mkdir(exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.sw_', suffix='.csv', dir=DATA, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['OSM_ID', 'Latitude', 'Longitude'])
            writer.writerows(switches)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def update_all():
    results = {}
    for line, relation_id in ROUTES.items():
        destination = DATA / f'switches_{line}.csv'
        print(f'[INFO] {line.upper()} LINE - relation {relation_id}...', flush=True)
        err = None
        for attempt in range(2):
            try:
                xml = fetch_osm(relation_id)
                switches, way_count = extract_switches(xml)
                atomic_csv(destination, switches)
                print(f'[OK] {line.upper()} : {len(switches)} switches, {way_count} voies. CSV : {destination.name}', flush=True)
                results[line] = {'ok': True, 'count': len(switches), 'relation': relation_id}
                err = None
                break
            except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError, OSError) as e:
                err = str(e)
                if attempt == 0:
                    print(f'[ATTENTION] Tentative 1 : {err} ; nouvel essai...', flush=True)
                    time.sleep(2)
        if err is not None:
            cached = destination.exists()
            results[line] = {'ok': False, 'error': err, 'csv_present': cached, 'relation': relation_id}
            print(f'[ERREUR] {line.upper()} : {err}', flush=True)
            if cached:
                print('[INFO] Conservation du dernier CSV valide.', flush=True)
    DATA.mkdir(exist_ok=True)
    status = {'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'lines': results}
    (DATA / 'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    return results


if __name__ == '__main__':
    results = update_all()
    sys.exit(0 if all(r['ok'] for r in results.values()) else 1)
