"""Computed (non-official) linear reference along a selected OSM track path.

PK values represent cumulative distance in km from the user-selected reference
station. They are NOT operator chainages and are not guaranteed to represent
possible train movements or every parallel track.
"""
from railway import nearest_node, shortest_path, distance, EARTH
import math


def _projection(point, a, b):
    """Return distance to segment (meters), projection factor (0..1)."""
    lat0 = math.radians(point[0])
    def xy(p):
        return (math.radians(p[1] - point[1]) * EARTH * math.cos(lat0),
                math.radians(p[0] - point[0]) * EARTH)
    x1, y1 = xy(a)
    x2, y2 = xy(b)
    dx, dy = x2 - x1, y2 - y1
    div = dx * dx + dy * dy
    factor = min(1.0, max(0.0, -(x1 * dx + y1 * dy) / div)) if div else 0.0
    return math.hypot(x1 + factor * dx, y1 + factor * dy), factor


def build_reference(route, start_id, end_id, corridor_m=35):
    stations = {s['id']: s for s in route['stations']}
    if start_id not in stations or end_id not in stations:
        raise ValueError('Stations de reference introuvables dans cette ligne.')
    if start_id == end_id:
        raise ValueError('Choisis deux stations de reference differentes.')
    nodes = route['nodes']
    track_nodes = route['track_nodes']
    a = stations[start_id]
    b = stations[end_id]
    start = nearest_node((a['lat'], a['lon']), track_nodes, nodes)
    end = nearest_node((b['lat'], b['lon']), track_nodes, nodes)
    if start == end:
        raise ValueError('Les stations pointent vers le meme noeud ferroviaire.')
    path_ids, total_m = shortest_path(route['adjacency'], start, end)
    points = [nodes[n] for n in path_ids]
    cumulative = [0.0]
    for p, q in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + distance(p, q))
    # Project each switch onto the reference line and keep its nearest location.
    annotated = []
    for sw in route['switches']:
        pt = (sw['lat'], sw['lon'])
        best = None
        for i, (p, q) in enumerate(zip(points, points[1:])):
            d, ratio = _projection(pt, p, q)
            if best is None or d < best[0]:
                best = (d, (cumulative[i] + ratio * (cumulative[i+1] - cumulative[i])) / 1000)
        if best and best[0] <= corridor_m:
            annotated.append({**sw, 'pk_km': round(best[1], 4), 'offset_m': round(best[0], 1)})
    annotated.sort(key=lambda sw: (sw['pk_km'], sw['id']))
    return {'start': a, 'end': b, 'total_km': round(total_m / 1000, 4),
            'path': points, 'pk_nodes_km': [x / 1000 for x in cumulative],
            'switches': annotated, 'corridor_m': corridor_m,
            'method': 'PK relatif calcule depuis la station origine sur un plus court chemin OSM ; '
                      'switches projetes dans un couloir de proximite. NON officiel.'}


def pk_view(reference, pk_from, pk_to):
    try:
        low = float(pk_from)
        high = float(pk_to)
    except (TypeError, ValueError):
        raise ValueError('Saisis des PK numeriques en kilometres (ex. 1.5 et 3.2).')
    if not (math.isfinite(low) and math.isfinite(high)) or low < 0 or high <= low:
        raise ValueError('Le PK de fin doit etre superieur au PK de debut (minimum 0).')
    if high > reference['total_km'] + 1e-5:
        raise ValueError(f'PK de fin hors reference : maximum {reference["total_km"]:.3f} km.')
    cum = reference['pk_nodes_km']
    pts = reference['path']
    def interpolate(km):
        for i in range(len(cum) - 1):
            if cum[i] <= km <= cum[i + 1]:
                ratio = (km-cum[i]) / (cum[i+1]-cum[i]) if cum[i+1]>cum[i] else 0
                return [pts[i][j] + ratio*(pts[i+1][j]-pts[i][j]) for j in range(2)]
        return pts[-1]
    part = [interpolate(low)]
    part.extend(list(p) for p, km in zip(pts[1:-1], cum[1:-1]) if low < km < high)
    part.append(interpolate(high))
    switches = [s for s in reference['switches'] if low <= s['pk_km'] <= high]
    return {'switches': switches, 'path': part, 'start_pk': low, 'end_pk': high,
            'distance_m': round((high-low)*1000), 'total_km': reference['total_km'],
            'method': reference['method'], 'corridor_m': reference['corridor_m']}
