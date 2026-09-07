#!/usr/bin/env python
"""Local multi-session terminal server for EDLLM web UI.

Each WebSocket connection is its own shell session (own cwd + command queue).
No real PTY (pywin32 absent) -> non-interactive command runner: each command
is a fresh subprocess, like the legacy /exec route, but over WebSocket with
proper per-session tabs, a persistent cwd, and Ctrl-C kill support.

Routes:
  /ws?sid=<id>&cwd=<path>&shell=<powershell|cmd|wsl>

Messages from client:
  {"type":"run","cmd":"..."}     run a command in the session cwd
  {"type":"cd","path":"..."}     change session cwd (relative to current cwd)
  {"type":"kill"}                terminate the running process for this session
  {"type":"resize","cols":..,"rows":..}  (reserved; xterm side sends it)

Messages to client:
  {"type":"ready","cwd":...}
  {"type":"data","data":"..."}   one line of stdout/stderr
  {"type":"exit","code":N}
  {"type":"cwd","cwd":...}
  {"type":"error","msg":"..."}

Runs locally on 127.0.0.1:8002. Do not expose to untrusted networks.
"""
import json
import os
import subprocess
import threading

import tornado.ioloop
import tornado.web
import tornado.websocket

WORKDIR = os.path.dirname(os.path.abspath(__file__))  # f:\tmp\Model\webui
ROOT = os.path.dirname(WORKDIR)  # f:\tmp\Model


def _shell_args(shell, cwd):
    if shell == "cmd":
        return ["cmd", "/c"], "cmd"
    if shell == "wsl":
        return ["wsl", "--"], "wsl"
    # powershell (default)
    return ["powershell", "-NoLogo", "-NoProfile", "-Command"], "powershell"


def _safe_cwd(path):
    if not path:
        return ROOT
    try:
        path = os.path.expanduser(os.path.expandvars(path))
    except Exception:
        return ROOT
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    if os.path.isdir(path):
        return os.path.normpath(path)
    return ROOT


class ShellHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True  # local-only tool

    def open(self):
        qs = tornado.escape.url_unescape
        from urllib.parse import parse_qs
        parsed = parse_qs(self.request.uri.split("?", 1)[-1])
        sid = parsed.get("sid", [""])[0] or "term"
        shell = parsed.get("shell", ["powershell"])[0]
        if shell not in ("powershell", "cmd", "wsl"):
            shell = "powershell"
        cwd = _safe_cwd((parsed.get("cwd", [""])[0] or "").replace("/", os.sep))
        self.sid = sid
        self.shell = shell
        self.cwd = cwd
        self.proc = None
        self.lock = threading.Lock()
        self.main_loop = tornado.ioloop.IOLoop.current()
        SESSIONS[sid] = self
        self._send({"type": "ready", "cwd": cwd, "shell": shell})

    def on_message(self, message):
        try:
            msg = json.loads(message)
        except Exception:
            return
        t = msg.get("type")
        if t == "run":
            self._run(msg.get("cmd", ""))
        elif t == "cd":
            self._cd(msg.get("path", ""))
        elif t == "kill":
            self._kill()
        elif t == "resize":
            # no-op for non-interactive runner; kept for protocol completeness
            pass

    def on_close(self):
        self._kill()
        SESSIONS.pop(self.sid, None)

    # ---- helpers ---------------------------------------------------------
    def _send(self, obj):
        try:
            self.write_message(json.dumps(obj))
        except Exception:
            pass

    def _cd(self, path):
        newdir = _safe_cwd(path if os.path.isabs(path.replace("/", os.sep)) else os.path.join(self.cwd, path))
        self.cwd = newdir
        self._send({"type": "cwd", "cwd": newdir})

    def _kill(self):
        with self.lock:
            p = self.proc
            self.proc = None
        if p and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    def _run(self, cmd):
        if cmd is None:
            return
        cmd = cmd.strip()
        if not cmd:
            self._send({"type": "exit", "code": 0})
            return
        # handle interactive cd locally (so cwd persists)
        low = cmd.lower()
        if low in ("cd", "chdir") or low.startswith("cd ") or low.startswith("chdir "):
            parts = cmd.split(None, 1)
            target = parts[1].strip() if len(parts) > 1 else ""
            if not target or target in ("~", "%userprofile%"):
                self.cwd = _safe_cwd(ROOT if not target else target)
            else:
                self.cwd = _safe_cwd(os.path.join(self.cwd, target) if not os.path.isabs(target.replace("/", os.sep)) else target)
            self._send({"type": "cwd", "cwd": self.cwd})
            self._send({"type": "exit", "code": 0})
            return

        args, _ = _shell_args(self.shell, self.cwd)
        try:
            p = subprocess.Popen(
                args + [cmd],
                shell=False,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as ex:
            self._send({"type": "error", "msg": str(ex)})
            self._send({"type": "exit", "code": -1})
            return

        with self.lock:
            self.proc = p

        loop = self.main_loop
        t = threading.Thread(target=self._reader, args=(p, loop), daemon=True)
        t.start()

    def _reader(self, p, loop):
        try:
            for line in p.stdout:
                loop.add_callback(self._send, {"type": "data", "data": line.rstrip("\n")})
        except Exception as ex:
            try:
                loop.add_callback(self._send, {"type": "error", "msg": str(ex)})
            except Exception:
                pass
        try:
            rc = p.wait()
        except Exception:
            rc = -1
        with self.lock:
            if self.proc is p:
                self.proc = None
        try:
            loop.add_callback(self._send, {"type": "exit", "code": rc})
        except Exception:
            pass


SESSIONS = {}


def make_app():
    return tornado.web.Application([(r"/ws", ShellHandler)])


if __name__ == "__main__":
    app = make_app()
    app.listen(8002, address="127.0.0.1")
    print("EDLLM terminal WS on ws://127.0.0.1:8002/ws")
    tornado.ioloop.IOLoop.current().start()
