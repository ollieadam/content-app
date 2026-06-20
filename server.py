#!/usr/bin/env python3
"""Content App server — serves index.html with ON/OFF control via Tailscale."""

import os, sys, json, socket, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

HOST = '0.0.0.0'
PORT = 8080
DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/status':
            self.send_json({'status': 'running', 'ips': get_ips(), 'port': PORT})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/shutdown':
            self.send_json({'status': 'shutting_down'})
            self.server._shutdown = True
            self.server.shutdown()
        else:
            self.send_error(404)

    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quiet

    def translate_path(self, path):
        p = super().translate_path(path)
        # Ensure we serve from the app directory
        if not p.startswith(DIR):
            return os.path.join(DIR, 'index.html')
        return p


def get_ips():
    """Return all non-loopback IPv4 addresses."""
    ips = []
    try:
        import subprocess
        r = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            ips.append(r.stdout.strip())
    except Exception:
        pass
    # Fallback: detect local IPs
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
    server._shutdown = False

    print(f'╔══════════════════════════════════════╗')
    print(f'║        Content App Server            ║')
    print(f'╠══════════════════════════════════════╣')
    print(f'║  Local:  http://localhost:{PORT}')
    for ip in get_ips():
        print(f'║  Net:    http://{ip}:{PORT}')
    print(f'║                                      ║')
    print(f'║  Press Ctrl+C to stop the server     ║')
    print(f'║  Or click "Stop Server" in the app   ║')
    print(f'╚══════════════════════════════════════╝')

    webbrowser.open(f'http://localhost:{PORT}')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
        server.server_close()


if __name__ == '__main__':
    main()
