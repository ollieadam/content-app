#!/usr/bin/env python3
"""Content App server — serves index.html with ON/OFF control via Tailscale."""

import os, sys, json, socket, urllib.request, urllib.error, base64, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

HOST = '0.0.0.0'
PORT = 8080
DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(DIR, 'settings.json')


class Handler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/status':
            self.send_json({'status': 'running', 'ips': get_ips(), 'port': PORT})
        elif self.path == '/api/settings':
            try:
                with open(SETTINGS_FILE) as f:
                    self.send_json(json.load(f))
            except FileNotFoundError:
                self.send_json({})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/shutdown':
            self.send_json({'status': 'shutting_down'})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        elif self.path == '/api/settings':
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f)
            self.send_json({'ok': True})
        elif self.path == '/api/proxy':
            length = int(self.headers.get('Content-Length', 0))
            self._handle_proxy(self.rfile.read(length))
        else:
            self.send_error(404)

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

    def send_json(self, data, code=200):
        self._send_raw(json.dumps(data).encode(), code)

    def _send_raw(self, body, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, fmt, *args):
        pass

    def translate_path(self, path):
        p = super().translate_path(path)
        if not p.startswith(DIR):
            return os.path.join(DIR, 'index.html')
        return p


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
