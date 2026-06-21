#!/usr/bin/env python3
"""Content App Launcher — persistent taskbar window to control server + open Firefox."""

import os, sys, subprocess, time, threading, urllib.request
import tkinter as tk

DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = 'http://localhost:8080'
FIREFOX = '/usr/bin/firefox'
W, H = 340, 220
BG = '#0a0a0a'
BG2 = '#151515'
FG = '#f0f0f0'
RED = '#dc2626'
DIM = '#555'


class Launcher:
    def __init__(self):
        self.root = tk.Tk(className='content-app-launcher')
        self.root.title('Content App')
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{W}x{H}+{(sw-W)//2}+{(sh-H)//2}')

        self.server_proc = None
        self.running = False
        self.app_url = SERVER_URL
        self._build_ui()
        self.start_server()

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill='x', padx=20, pady=(18, 0))
        tk.Label(hdr, text='●', fg=RED, bg=BG, font=('Segoe UI', 10)).pack(side='left')
        tk.Label(hdr, text='  Content App', fg=FG, bg=BG,
                 font=('Segoe UI', 14, 'bold')).pack(side='left')

        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(expand=True)
        self.open_btn = tk.Button(
            btn_frame, text='🦊  Open Content App',
            font=('Segoe UI', 13, 'bold'),
            bg=RED, fg='#fff', activebackground='#ef4444', activeforeground='#fff',
            bd=0, padx=24, pady=10, cursor='hand2',
            command=self.open_app, state='disabled'
        )
        self.open_btn.pack()

        sbar = tk.Frame(self.root, bg=BG)
        sbar.pack(fill='x', padx=20, pady=(0, 14))
        self.status_dot = tk.Label(sbar, text='○', fg=DIM, bg=BG, font=('Segoe UI', 10))
        self.status_dot.pack(side='left')
        self.status_lbl = tk.Label(sbar, text='  Starting server…', fg=DIM, bg=BG,
                                   font=('Segoe UI', 10))
        self.status_lbl.pack(side='left')
        self.stop_btn = tk.Button(
            sbar, text='⏹ Stop Server',
            font=('Segoe UI', 9),
            bg=BG2, fg=DIM, activebackground='#222', activeforeground=RED,
            bd=1, relief='solid', padx=10, pady=3, cursor='hand2',
            command=self.stop_server, state='disabled'
        )
        self.stop_btn.pack(side='right')

    def _set_status(self, text, ok=False):
        self.status_dot.configure(fg=RED if ok else DIM, text='●' if ok else '○')
        self.status_lbl.configure(text='  ' + text, fg=FG if ok else DIM)

    def start_server(self):
        self._set_status('Starting server…')
        self.open_btn.configure(state='disabled')
        self.stop_btn.configure(state='disabled')
        self.server_proc = subprocess.Popen(
            [sys.executable, os.path.join(DIR, 'server.py')],
            cwd=DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        threading.Thread(target=self._wait_for_server, daemon=True).start()

    def _wait_for_server(self):
        deadline = time.time() + 15
        while time.time() < deadline:
            if self.server_proc and self.server_proc.poll() is not None:
                self.root.after(0, self._server_failed, 'Server exited unexpectedly')
                return
            try:
                import json as _json
                with urllib.request.urlopen(SERVER_URL + '/api/status', timeout=1) as resp:
                    status = _json.loads(resp.read())
                    tailscale = next((ip for ip in status.get('ips', []) if ip.startswith('100.')), None)
                    if tailscale:
                        self.app_url = f'http://{tailscale}:{status.get("port", 8080)}'
                self.root.after(0, self._server_ready)
                return
            except Exception:
                time.sleep(0.5)
        self.root.after(0, self._server_failed, 'Server failed to start (timeout)')

    def _server_ready(self):
        self.running = True
        self._set_status('Running', ok=True)
        self.open_btn.configure(state='normal')
        self.stop_btn.configure(state='normal', fg=RED, activeforeground=RED)
        threading.Thread(target=self._poll_badge, daemon=True).start()
        self.open_app()

    def _poll_badge(self):
        import json as _json
        while self.running:
            try:
                with urllib.request.urlopen(SERVER_URL + '/api/badge', timeout=2) as r:
                    data = _json.loads(r.read())
                    count = data.get('count', 0)
                    self.root.after(0, self._update_badge, count)
            except Exception:
                pass
            time.sleep(5)

    def _update_badge(self, count):
        if count > 0:
            self.root.title(f'Content App  ({count} new)')
            self.status_lbl.configure(
                text=f'  \U0001f4f1 {count} project{"s" if count != 1 else ""} saved from phone',
                fg=FG
            )
        else:
            self.root.title('Content App')
            if self.running:
                self.status_lbl.configure(text='  Running', fg=FG)

    def _server_failed(self, msg):
        self.running = False
        self._set_status(msg)
        self.open_btn.configure(state='disabled')
        self.stop_btn.configure(state='disabled', fg=DIM)
        if self.server_proc:
            try:
                self.server_proc.kill()
            except Exception:
                pass

    def open_app(self):
        if not self.running:
            return
        try:
            subprocess.Popen(
                [FIREFOX, '--new-window', self.app_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            self._set_status('Firefox not found at ' + FIREFOX)
        try:
            req = urllib.request.Request(SERVER_URL + '/api/badge/clear', method='POST')
            req.add_header('Content-Length', '0')
            urllib.request.urlopen(req, timeout=1)
            self.root.after(0, self._update_badge, 0)
        except Exception:
            pass

    def stop_server(self):
        try:
            req = urllib.request.Request(SERVER_URL + '/api/shutdown', method='POST')
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass
        if self.server_proc:
            try:
                self.server_proc.terminate()
                self.server_proc.wait(timeout=3)
            except Exception:
                try:
                    self.server_proc.kill()
                except Exception:
                    pass
        self.running = False
        self._set_status('Stopped')
        self.open_btn.configure(state='disabled')
        self.stop_btn.configure(state='disabled', fg=DIM)
        self.server_proc = None

    def on_close(self):
        self.stop_server()
        self.root.destroy()


if __name__ == '__main__':
    Launcher().root.mainloop()
