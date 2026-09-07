#!/usr/bin/env python
"""Minimal local terminal + chat-store backend for EDLLM web UI.
- /exec?cmd=...&cwd=...  streams shell output (SSE)
- /chats  GET -> saved chats JSON,  POST -> save chats JSON
- /ps     GET -> which models are currently loaded in Ollama (server-side proxy)
- /stopmodel?name=...  GET -> unload a model from VRAM (server-side proxy)
Runs locally; working dir = parent of this script's directory (f:\\tmp\\Model).
Do not expose to untrusted networks.
"""
import http.server, subprocess, urllib.parse, json, os, sys, time, urllib.request

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # f:\tmp\Model
CHATS = os.path.join(WORKDIR, "chats.json")

# --- local Ollama process management (started/stopped from the web UI) ---
ollama_proc = None

def ollama_is_up():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def ollama_start():
    global ollama_proc
    if ollama_is_up():
        return True
    env = dict(os.environ)
    env["OLLAMA_MODELS"] = WORKDIR
    try:
        ollama_proc = subprocess.Popen(
            ["ollama", "serve"], cwd=WORKDIR, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x00000200,  # CREATE_NEW_PROCESS_GROUP (Windows)
        )
    except Exception:
        return False
    return True

def ollama_stop():
    global ollama_proc
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["taskkill", "/IM", "ollama.exe", "/F"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
    except Exception:
        pass
    ollama_proc = None
    return True


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/exec"):
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            cmd = params.get("cmd", [""])[0]
            cwd = params.get("cwd", [""])[0] or WORKDIR
            if not os.path.isdir(cwd):
                cwd = WORKDIR
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._cors()
            self.end_headers()
            try:
                p = subprocess.Popen(cmd, shell=True, cwd=cwd,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1)
                for line in p.stdout:
                    self.wfile.write(("data: " + json.dumps(line.rstrip("\n")) + "\n\n").encode("utf-8"))
                    self.wfile.flush()
                rc = p.wait()
                self.wfile.write(("data: " + json.dumps("[exit %d]" % rc) + "\n\n").encode("utf-8"))
                self.wfile.flush()
            except Exception as ex:
                self.wfile.write(("data: " + json.dumps("error: " + str(ex)) + "\n\n").encode("utf-8"))
                self.wfile.flush()
        elif self.path == "/chats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            try:
                with open(CHATS, "r", encoding="utf-8") as f:
                    data = f.read()
            except Exception:
                data = json.dumps({"chats": []})
            self.wfile.write(data.encode("utf-8"))
        elif self.path.startswith("/ps"):
            # server-side proxy to Ollama so the browser doesn't depend on Ollama CORS
            try:
                req = urllib.request.Request("http://127.0.0.1:11434/api/ps")
                with urllib.request.urlopen(req, timeout=10) as r:
                    body = r.read().decode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
            except Exception as ex:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"models": [], "error": str(ex)}).encode("utf-8"))
        elif self.path.startswith("/stopmodel"):
            qs = urllib.parse.urlparse(self.path).query
            name = urllib.parse.parse_qs(qs).get("name", [""])[0]
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/chat",
                    data=json.dumps({"model": name, "messages": [{"role": "user", "content": "x"}], "keep_alive": 0}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "unloaded": name}).encode("utf-8"))
            except Exception as ex:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(("error: " + str(ex)).encode("utf-8"))
        elif self.path.startswith("/ollama/status"):
            up = ollama_is_up()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"running": up, "port": 11434}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/chats":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                obj = json.loads(body.decode("utf-8"))
                with open(CHATS, "w", encoding="utf-8") as f:
                    json.dump(obj, f, ensure_ascii=False, indent=2)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            except Exception as ex:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(("error: " + str(ex)).encode("utf-8"))
        elif self.path.startswith("/ollama/start"):
            ok = ollama_start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "running": ollama_is_up()}).encode("utf-8"))
        elif self.path.startswith("/ollama/stop"):
            ollama_stop()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "running": ollama_is_up()}).encode("utf-8"))
        elif self.path.startswith("/writefile"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                obj = json.loads(self.rfile.read(length) if length else b"{}")
                path = obj.get("path", "")
                content = obj.get("content", "")
                # restrict to WORKDIR tree to avoid arbitrary writes
                if os.path.isabs(path):
                    abspath = os.path.abspath(os.path.normpath(path))
                else:
                    abspath = os.path.abspath(os.path.join(WORKDIR, path))
                root = os.path.normcase(WORKDIR)
                if not (abspath == root or abspath.startswith(root + os.sep)):
                    self.send_response(403); self.end_headers(); return
                os.makedirs(os.path.dirname(abspath), exist_ok=True)
                with open(abspath, "w", encoding="utf-8") as f:
                    f.write(content)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "path": abspath}).encode("utf-8"))
            except Exception as ex:
                self.send_response(500); self.end_headers()
                self.wfile.write(("error: " + str(ex)).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("EDLLM backend on http://127.0.0.1:8001  (cwd=%s)" % WORKDIR)
    http.server.HTTPServer(("127.0.0.1", 8001), Handler).serve_forever()
