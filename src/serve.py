"""Local web API for RailwayVisualizer. No third-party Python dependencies."""
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from railway import update_route,segment_view,public_route,write_csv,DATA

BASE=Path(__file__).resolve().parent
CACHE={}
LOCK=threading.Lock()
DEFAULTS={'Houston Red Line':1741729,'Houston Green Line':2728566}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kw):
        super().__init__(*args,directory=str(BASE),**kw)

    def json_response(self,status,data):
        raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url=urlparse(self.path)
        if url.path=='/api/config':
            return self.json_response(200,{'defaults':DEFAULTS})
        if url.path=='/api/status':
            return self.json_response(200,{'loaded':[public_route(r) for r in CACHE.values()]})
        return super().do_GET()

    def do_POST(self):
        url=urlparse(self.path)
        if url.path not in ('/api/route','/api/segment'):
            return self.json_response(404,{'error':'Route inconnue'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>20000:
                raise ValueError('Requete trop grande ou vide.')
            params=json.loads(self.rfile.read(length).decode('utf-8'))
            relation_id=int(params['relation_id'])
            if relation_id<=0 or relation_id>=10**12:
                raise ValueError('Relation ID invalide')
            if not LOCK.acquire(blocking=False):
                return self.json_response(409,{'error':'Mise a jour deja en cours. Reessaie apres.'})
            try:
                if url.path=='/api/route':
                    route=update_route(relation_id)
                    CACHE[relation_id]=route
                    return self.json_response(200,public_route(route))
                route=CACHE.get(relation_id)
                if route is None:
                    raise ValueError('Charge la ligne avant de choisir un troncon.')
                segment=segment_view(route,str(params['start']),str(params['end']))
                write_csv(DATA/f'segment_{relation_id}.csv',segment['switches'])
                return self.json_response(200,segment)
            finally:
                LOCK.release()
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as err:
            return self.json_response(400,{'error':str(err)})
        except Exception as err:
            return self.json_response(502,{'error':f'OSM ou traitement indisponible : {err}'})

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

if __name__=='__main__':
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8767
    try:
        server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    except OSError as err:
        sys.exit(f'Port {port} indisponible : {err}')
    print(f'RailwayVisualizer : http://127.0.0.1:{port}/',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
