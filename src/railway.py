"""OSM route ingestion and approximate station-to-station railway switch selection."""
import csv
import heapq
import json
import math
import os
from pathlib import Path
import tempfile
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
USER_AGENT = 'RailwayVisualizer/0.2 (local educational OSM viewer)'
RAIL_TYPES = {'rail', 'light_rail', 'subway', 'tram', 'narrow_gauge', 'monorail'}
EARTH = 6371000.0


def distance(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*EARTH*math.asin(min(1, math.sqrt(h)))


def get_tags(element):
    return {t.get('k'): t.get('v') for t in element.findall('tag')}


def fetch_relation(relation_id):
    url = f'https://api.openstreetmap.org/api/0.6/relation/{relation_id}/full'
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/xml'})
    with urllib.request.urlopen(req, timeout=65) as response:
        return response.read()


def fetch_route_tree(relation_id, max_children=24):
    """Merge OSM /full responses for a route_master and its child routes.

    A /relation/ID/full request supplies only the referenced relations, not the
    ways/nodes belonging to nested relations. Fetch those children explicitly.
    """
    parent = ET.fromstring(fetch_relation(relation_id))
    objects = {(obj.tag, obj.get('id')): obj for obj in parent if obj.get('id')}
    route = next((r for r in parent.findall('relation') if r.get('id') == str(relation_id)), None)
    if route is None:
        raise ValueError(f'Relation OSM {relation_id} introuvable.')
    children = [m.get('ref') for m in route.findall('member') if m.get('type') == 'relation']
    if len(children) > max_children:
        raise ValueError('Trop de sous-relations : ce reseau est trop vaste. Choisis la relation d une ligne.')
    failures = []
    for child_id in dict.fromkeys(children):
        try:
            child_root = ET.fromstring(fetch_relation(int(child_id)))
            for obj in child_root:
                if obj.get('id'):
                    objects[(obj.tag, obj.get('id'))] = obj
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            failures.append(f'{child_id}: {exc}')
    if children and failures and len(failures) == len(set(children)):
        raise ValueError('Aucun itineraire enfant accessible : ' + '; '.join(failures[:3]))
    merged = ET.Element('osm', {'version':'0.6'})
    merged.extend(objects.values())
    return ET.tostring(merged, encoding='utf-8')


def centroid(refs, nodes):
    pts = [nodes[ref] for ref in refs if ref in nodes]
    return [sum(p[i] for p in pts)/len(pts) for i in range(2)] if pts else None


def parse_route(xml_content, relation_id):
    root = ET.fromstring(xml_content)
    relations = {int(r.get('id')): r for r in root.findall('relation')}
    relation = relations.get(int(relation_id))
    if relation is None:
        raise ValueError('Relation OSM non trouvee dans la reponse.')
    rtags = get_tags(relation)
    nodes = {n.get('id'): (float(n.get('lat')), float(n.get('lon'))) for n in root.findall('node')}
    node_elements = {n.get('id'): n for n in root.findall('node')}
    ways = {w.get('id'): w for w in root.findall('way')}
    members = list(relation.findall('member'))
    # A route_master contains route relations rather than railway ways.
    # Collect ways and stations from its immediate child route relations.
    for m in relation.findall('member'):
        if m.get('type') == 'relation':
            child = relations.get(int(m.get('ref')))
            if child is not None:
                members.extend(child.findall('member'))
    way_refs = {m.get('ref') for m in members if m.get('type') == 'way'}
    line_ways = {}
    track_nodes = set()
    adjacency = {}
    for ref in way_refs:
        w = ways.get(ref)
        if w is None or get_tags(w).get('railway') not in RAIL_TYPES:
            continue
        refs = [nd.get('ref') for nd in w.findall('nd') if nd.get('ref') in nodes]
        if len(refs) < 2:
            continue
        line_ways[ref] = refs
        track_nodes.update(refs)
        for a, b in zip(refs, refs[1:]):
            wt = distance(nodes[a], nodes[b])
            adjacency.setdefault(a, []).append((b, wt))
            adjacency.setdefault(b, []).append((a, wt))
    if not line_ways:
        raise ValueError(f"Aucune voie ferroviaire exploitable dans la relation {relation_id} (type={rtags.get('type','?')}, route={rtags.get('route','?')}, route_master={rtags.get('route_master','?')}, {len(way_refs)} voies references). Verifie l'identifiant OSM et les membres de la relation.")
    switches = []
    for nid in track_nodes:
        el = node_elements.get(nid)
        if el is not None and get_tags(el).get('railway') == 'switch':
            lat, lon = nodes[nid]
            switches.append({'id': nid, 'lat': lat, 'lon': lon})
    switches.sort(key=lambda p:(p['lat'],p['lon'],p['id']))
    # Prefer explicitly tagged stop/platform members of this particular relation.
    stations = []
    seen = set()
    for m in members:
        typ, ref, role = m.get('type'), m.get('ref'), (m.get('role') or '').lower()
        element = node_elements.get(ref) if typ == 'node' else ways.get(ref) if typ == 'way' else None
        if element is None:
            continue
        tags = get_tags(element)
        is_stop = ('stop' in role or 'platform' in role or
                   tags.get('railway') in ('station','halt','tram_stop') or
                   tags.get('public_transport') in ('stop_position','platform'))
        name = tags.get('name') or tags.get('local_ref')
        if not is_stop or not name:
            continue
        pt = nodes.get(ref) if typ == 'node' else centroid([n.get('ref') for n in element.findall('nd')], nodes)
        if pt is None:
            continue
        key = name.casefold().strip()
        if key in seen:
            continue
        seen.add(key)
        stations.append({'id': f'{typ}:{ref}', 'name': name, 'lat':pt[0], 'lon':pt[1]})
    # Some route relations list tracks but not explicit stop members. Detect named
    # stop nodes that are already on their member ways as a conservative fallback.
    for nid in track_nodes:
        el = node_elements.get(nid)
        if el is None:
            continue
        tags = get_tags(el)
        if tags.get('railway') not in ('station','halt','tram_stop') and tags.get('public_transport') != 'stop_position':
            continue
        name = tags.get('name')
        if not name or name.casefold().strip() in seen:
            continue
        seen.add(name.casefold().strip())
        lat,lon=nodes[nid]
        stations.append({'id':f'node:{nid}','name':name,'lat':lat,'lon':lon})
    stations.sort(key=lambda s:s['name'].casefold())
    return {'relation_id':int(relation_id), 'name':rtags.get('name') or rtags.get('ref') or f'OSM {relation_id}',
            'track_way_count':len(line_ways), 'switches':switches, 'stations':stations,
            'nodes':nodes, 'track_nodes':track_nodes, 'adjacency':adjacency,
            'line_paths':[[list(nodes[n]) for n in refs] for refs in line_ways.values()]}


def nearest_node(point, candidate_ids, nodes):
    return min(candidate_ids, key=lambda nid:distance(point,nodes[nid]))


def shortest_path(graph, start, end):
    queue = [(0.0,start)]
    distances = {start:0.0}
    previous = {}
    while queue:
        d, node = heapq.heappop(queue)
        if d > distances[node]:
            continue
        if node == end:
            chain = [end]
            while chain[-1] != start:
                chain.append(previous[chain[-1]])
            chain.reverse()
            return chain,d
        for neighbor,w in graph.get(node,[]):
            nd = d+w
            if nd < distances.get(neighbor,float('inf')):
                distances[neighbor]=nd
                previous[neighbor]=node
                heapq.heappush(queue,(nd,neighbor))
    raise ValueError('Pas de chemin continu entre ces deux stations dans cette relation OSM.')


def point_segment_distance_m(point, a, b):
    # Local equirectangular projection, accurate for small railway segments.
    lat0 = math.radians(point[0])
    def xy(p):
        return (math.radians(p[1]-point[1])*EARTH*math.cos(lat0),
                math.radians(p[0]-point[0])*EARTH)
    x1,y1 = xy(a)
    x2,y2 = xy(b)
    dx,dy = x2-x1,y2-y1
    t = max(0,min(1,-(x1*dx+y1*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
    return math.hypot(x1+t*dx,y1+t*dy)


def segment_view(route, start_id, end_id, corridor_m=35):
    locations = {s['id']:s for s in route['stations']}
    if start_id not in locations or end_id not in locations:
        raise ValueError('Station inconnue pour cette ligne.')
    if start_id == end_id:
        raise ValueError('Choisis deux stations differentes.')
    nodes, track_nodes = route['nodes'],route['track_nodes']
    a, b = locations[start_id],locations[end_id]
    src = nearest_node((a['lat'],a['lon']),track_nodes,nodes)
    dst = nearest_node((b['lat'],b['lon']),track_nodes,nodes)
    path,meters = shortest_path(route['adjacency'],src,dst)
    path_points = [nodes[n] for n in path]
    path_set = set(path)
    # Include switches directly on route, and on parallel track within specified corridor.
    # This is a proximity heuristic, not a topology-verified all-track segment.
    selected=[]
    for sw in route['switches']:
        if sw['id'] in path_set:
            selected.append(sw)
        elif len(path_points)>1 and min(point_segment_distance_m((sw['lat'],sw['lon']),p,q)
                                            for p,q in zip(path_points,path_points[1:]))<=corridor_m:
            selected.append(sw)
    return {'switches':selected, 'path':path_points,'distance_m':round(meters),
            'start':a,'end':b,'corridor_m':corridor_m,
            'method':'Plus court chemin sur les voies OSM + aiguillages dans un couloir de proximite (estimation, pas un itineraire d exploitation).'}


def write_csv(path, switches):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp = tempfile.mkstemp(dir=path.parent, prefix='.temp-',suffix='.csv')
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as out:
            writer=csv.writer(out)
            writer.writerow(['OSM_ID','Latitude','Longitude'])
            writer.writerows((s['id'],s['lat'],s['lon']) for s in switches)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def public_route(route):
    return {'relation_id':route['relation_id'],'name':route['name'],
            'track_way_count':route['track_way_count'],'stations':route['stations'],
            'switches':route['switches'],'count':len(route['switches']),
            'updated_at':datetime.now(timezone.utc).isoformat()}


def update_route(relation_id):
    if not str(relation_id).isdigit() or not (0<int(relation_id)<10**12):
        raise ValueError('Identifiant de relation OSM invalide.')
    xml=fetch_route_tree(int(relation_id))
    route=parse_route(xml,int(relation_id))
    DATA.mkdir(exist_ok=True)
    write_csv(DATA/f'switches_{relation_id}.csv',route['switches'])
    (DATA/f'route_{relation_id}.json').write_text(json.dumps(public_route(route),ensure_ascii=False,indent=2),encoding='utf-8')
    return route
