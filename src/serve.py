"""Local-only HTTP server serving HTML/CSV; refresh endpoint re-fetches OSM."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
from update_switches import update_all

BASE = Path(__file__).resolve().parent
UPDATE_LOCK = threading.Lock()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE), **kwargs)

    def do_POST(self):
        if self.path != '/api/refresh':
            self.send_error(404)
            return
        if not UPDATE_LOCK.acquire(blocking=False):
            self._respond(409, {'error': 'Actualisation deja en cours'})
            return
        try:
            results = update_all()
            self._respond(200, {'results': results})
        except Exception as exc:
            self._respond(500, {'error': str(exc)})
        finally:
            UPDATE_LOCK.release()

    def _respond(self, status, payload):
        content = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8767
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    except OSError as exc:
        print(f'[ERREUR] Port {port} indisponible : {exc}')
        print('Ferme le serveur deja actif (Ctrl+C) avant de relancer.')
        sys.exit(1)
    print(f'[OK] Serveur local : http://127.0.0.1:{port}/houston_switches_map.html?line=both', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServeur arrete.')
    finally:
        server.server_close()
