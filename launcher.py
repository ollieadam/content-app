#!/usr/bin/env python3
"""Content App Launcher — persistent taskbar window to control server + open Chrome."""

import os, sys, subprocess, time, threading, json, urllib.request, socket, signal
import tkinter as tk

DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = 'http://localhost:8080'
CHROME = '/usr/bin/google-chrome-stable'
W, H = 340, 220
BG = '#0a0a0a'
BG2 = '#151515'
FG = '#f0f0f0'
RED = '#dc2626'
DIM = '#555'


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Content App')
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.tk.call('wm', 'class', '.', 'Content-App-Launcher')

        # centre window
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{W}x{H}+{(sw-W)//2}+{(sh-H)//2}')

        self.server_proc = None
        self.running = False
        self._build_ui()
        self.start_server()

    # ── UI ──

    def _build_ui(self):
        # header
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill='x', padx=20, pady=(18, 0))
        dot = tk.Label(hdr, text='●', fg=RED, bg=BG, font=('Segoe UI', 10))
        dot.pack(side='left')
        tt = tk.Label(hdr, text='  Content App', fg=FG, bg=BG,
                      font=('Segoe UI', 14, 'bold'))
        tt.pack(side='left')

        # open button
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(expand=True)

        self.open_btn = tk.Button(
            btn_frame, text='🎬  Open Content App',
            font=('Segoe UI', 13, 'bold'),
            bg=RED, fg='#fff', activebackground='#ef4444', activeforeground='#fff',
            bd=0, padx=24, pady=10, cursor='hand2',
            command=self.open_app, state='disabled'
        )
        self.open_btn.pack()

        # status bar
        sbar = tk.Frame(self.root, bg=BG)
        sbar.pack(fill='x', padx=20, pady=(0, 14))

        self.status_dot = tk.Label(sbar, text='○', fg=DIM, bg=BG,
                                   font=('Segoe UI', 10))
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

    # ── Server ──

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
                with urllib.request.urlopen(SERVER_URL + '/api/status', timeout=1):
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

    # ── Actions ──

    def open_app(self):
        if not self.running:
            return
        try:
            subprocess.Popen(
                [CHROME, f'--app={SERVER_URL}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            self._set_status('Chrome not found at ' + CHROME)

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
