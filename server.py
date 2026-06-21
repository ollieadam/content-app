#!/usr/bin/env python3
"""Content App server — serves index.html with ON/OFF control via Tailscale."""

import os, sys, json, socket, urllib.request, urllib.error, base64, threading, gzip, io
from http.server import HTTPServer, SimpleHTTPRequestHandler

_GZIP_TYPES = {'.html', '.js', '.css', '.json', '.svg', '.txt'}

HOST = '0.0.0.0'
PORT = 8080
DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE  = os.path.join(DIR, 'settings.json')
PROJECTS_FILE  = os.path.join(DIR, 'projects.json')

_badge_lock  = threading.Lock()
_badge_count = 0


class Handler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/status':
            settings_data = self._load_settings()
            pw_hash = settings_data.get('appPassword', '')
            https_url = get_magicdns_url()
            self.send_json({'status': 'running', 'ips': get_ips(), 'port': PORT, 'passwordSet': bool(pw_hash), 'passwordHash': pw_hash, 'httpsUrl': https_url})
        elif self.path == '/api/settings':
            if not self._check_auth():
                return
            self.send_json(self._load_settings())
        elif self.path == '/api/projects':
            try:
                with open(PROJECTS_FILE) as f:
                    self.send_json(json.load(f))
            except FileNotFoundError:
                self.send_json([])
        elif self.path == '/api/badge':
            self.send_json({'count': _badge_count})
        else:
            self._do_static()

    def do_POST(self):
        global _badge_count
        if self.path == '/api/shutdown':
            self.send_json({'status': 'shutting_down'})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        elif self.path == '/api/settings':
            if not self._check_auth():
                return
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f)
            self.send_json({'ok': True})
        elif self.path == '/api/projects':
            length = int(self.headers.get('Content-Length', 0))
            project = json.loads(self.rfile.read(length))
            try:
                with open(PROJECTS_FILE) as f:
                    projects = json.load(f)
            except FileNotFoundError:
                projects = []
            projects = [p for p in projects if p.get('id') != project.get('id')]
            projects.insert(0, project)
            with open(PROJECTS_FILE, 'w') as f:
                json.dump(projects, f)
            with _badge_lock:
                _badge_count += 1
            self.send_json({'ok': True})
        elif self.path.startswith('/api/projects/delete/'):
            proj_id = self.path.split('/')[-1]
            self.rfile.read(int(self.headers.get('Content-Length', 0)))
            try:
                with open(PROJECTS_FILE) as f:
                    projects = json.load(f)
                projects = [p for p in projects if p.get('id') != proj_id]
                with open(PROJECTS_FILE, 'w') as f:
                    json.dump(projects, f)
            except FileNotFoundError:
                pass
            self.send_json({'ok': True})
        elif self.path == '/api/badge/clear':
            self.rfile.read(int(self.headers.get('Content-Length', 0)))
            with _badge_lock:
                _badge_count = 0
            self.send_json({'ok': True})
        elif self.path == '/api/proxy':
            if not self._check_auth():
                return
            length = int(self.headers.get('Content-Length', 0))
            self._handle_proxy(self.rfile.read(length))
        elif self.path == '/api/chat':
            length = int(self.headers.get('Content-Length', 0))
            self._handle_chat(self.rfile.read(length))
        else:
            self.send_error(404)

    def _do_static(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            super().do_GET()
            return
        ext = os.path.splitext(path)[1].lower()
        accept = self.headers.get('Accept-Encoding', '')
        if 'gzip' in accept and ext in _GZIP_TYPES:
            with open(path, 'rb') as f:
                data = f.read()
            compressed = gzip.compress(data, compresslevel=6)
            ctype = self.guess_type(path)
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(compressed)))
            self.send_header('Cache-Control', 'public, max-age=60')
            self._cors()
            self._add_csp()
            self.end_headers()
            self.wfile.write(compressed)
        else:
            path2 = self.translate_path(self.path)
            if os.path.isfile(path2):
                ctype = self.guess_type(path2)
                with open(path2, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'public, max-age=60')
                self._cors()
                self._add_csp()
                self.end_headers()
                self.wfile.write(data)
            else:
                super().do_GET()

    def _handle_proxy(self, body_bytes):
        """Proxy external API requests to avoid browser CORS restrictions."""
        try:
            req = json.loads(body_bytes)
            url = req['url']
            method = req.get('method', 'POST').upper()
            extra_headers = req.get('headers', {})

            if 'multipart' in req:
                boundary = b'----ContentAppBoundary7x4q'
                parts = []
                for key, val in req['multipart'].items():
                    if key == '_image_b64':
                        file_data = base64.b64decode(val)
                        parts.append(
                            b'--' + boundary + b'\r\n'
                            b'Content-Disposition: form-data; name="source"; filename="post.png"\r\n'
                            b'Content-Type: image/png\r\n\r\n' + file_data + b'\r\n'
                        )
                    else:
                        parts.append(
                            b'--' + boundary + b'\r\n'
                            b'Content-Disposition: form-data; name="' + key.encode() + b'"\r\n\r\n'
                            + str(val).encode() + b'\r\n'
                        )
                parts.append(b'--' + boundary + b'--\r\n')
                body = b''.join(parts)
                extra_headers['Content-Type'] = f'multipart/form-data; boundary={boundary.decode()}'
            elif 'json_body' in req:
                body = json.dumps(req['json_body']).encode()
                extra_headers.setdefault('Content-Type', 'application/json')
            else:
                body = None

            request = urllib.request.Request(url, data=body, headers=extra_headers, method=method)
            with urllib.request.urlopen(request, timeout=30) as resp:
                result = json.loads(resp.read())
            self.send_json(result)

        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read())
            except Exception:
                err = {'error': str(e)}
            self._send_raw(json.dumps(err).encode(), e.code)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)

    def _handle_chat(self, body_bytes):
        """Stream LLM responses from OpenRouter or Venice AI."""
        import http.client, ssl
        try:
            req = json.loads(body_bytes)
        except Exception:
            self.send_json({'error': 'bad request'}, 400)
            return

        provider = req.get('provider', 'openrouter')
        model    = req.get('model', '')
        history  = req.get('history', [])
        message  = req.get('message', '')

        cfg = self._load_settings()

        if provider == 'venice':
            api_key = cfg.get('veniceKey', '')
            host, path = 'api.venice.ai', '/api/v1/chat/completions'
            referer = 'http://localhost:8080'
        else:
            api_key = cfg.get('openrouterKey', '')
            host, path = 'openrouter.ai', '/api/v1/chat/completions'
            referer = 'http://localhost:8080'

        if not api_key:
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'[Error: API key not set in Settings]')
            return

        messages = [{'role': 'system', 'content': req.get('system', 'You are a helpful content creation assistant.')}]
        messages += history
        messages.append({'role': 'user', 'content': message})

        payload = json.dumps({
            'model': model,
            'messages': messages,
            'stream': True,
            'max_tokens': 2000,
        }).encode()

        hdrs = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': referer,
            'X-Title': 'Content App',
        }

        try:
            ctx  = ssl.create_default_context()
            conn = http.client.HTTPSConnection(host, context=ctx, timeout=60)
            conn.request('POST', path, body=payload, headers=hdrs)
            resp = conn.getresponse()

            if resp.status != 200:
                body = resp.read().decode(errors='replace')
                self.send_response(200)
                self._cors()
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'[API Error: {resp.status} {resp.reason}]'.encode())
                return

            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            while True:
                line = resp.readline()
                if not line:
                    break
                line = line.decode(errors='replace').strip()
                if not line.startswith('data: '):
                    continue
                raw = line[6:]
                if raw == '[DONE]':
                    break
                try:
                    delta = json.loads(raw)['choices'][0]['delta'].get('content', '')
                    if delta:
                        self.wfile.write(delta.encode('utf-8'))
                        self.wfile.flush()
                except Exception:
                    pass

        except Exception as e:
            try:
                self.wfile.write(f'\n[Error: {e}]'.encode())
                self.wfile.flush()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _add_csp(self):
        self.send_header('Content-Security-Policy',
            "default-src 'self'; "
            "media-src 'self' blob:; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' https://api.venice.ai https://www.googleapis.com https://api.buzzsprout.com https://graph.facebook.com https://api.github.com; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline';"
        )

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _check_auth(self):
        settings_data = self._load_settings()
        stored_hash = settings_data.get('appPassword', '')
        if not stored_hash:
            return True
        header_hash = self.headers.get('X-App-Key', '')
        if header_hash == stored_hash:
            return True
        self.send_json({'error': 'unauthorized'}, 401)
        return False

    def send_json(self, data, code=200):
        self._send_raw(json.dumps(data).encode(), code)

    def _send_raw(self, body, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self._add_csp()
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-App-Key')

    def log_message(self, fmt, *args):
        pass

    def translate_path(self, path):
        p = super().translate_path(path)
        if not p.startswith(DIR):
            return os.path.join(DIR, 'index.html')
        return p


def get_magicdns_url():
    try:
        import subprocess as _sp
        r = _sp.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            cur = data.get('CurrentNode', {})
            dns = cur.get('DNSName', '').rstrip('.')
            if dns:
                return f'https://{dns}'
    except Exception:
        pass
    return None

def get_ips():
    ips = []
    try:
        import subprocess
        r = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            ips.append(r.stdout.strip())
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return list(set(ips))


def main():
    os.chdir(DIR)
    server = HTTPServer((HOST, PORT), Handler)

    print('╔══════════════════════════════════════╗')
    print('║        Content App Server            ║')
    print('╠══════════════════════════════════════╣')
    print(f'║  Local:  http://localhost:{PORT}')
    for ip in get_ips():
        print(f'║  Net:    http://{ip}:{PORT}')
    print('║                                      ║')
    print('║  Press Ctrl+C to stop the server     ║')
    print('║  Or click "Stop Server" in the app   ║')
    print('╚══════════════════════════════════════╝')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
        server.server_close()


if __name__ == '__main__':
    main()
