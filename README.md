# EDLLM — Local Models & Web UI — `f:\tmp\Model`

A fully-local LLM setup on Windows 11 (RTX 3070 8GB / 31GB RAM).
Ollama's `OLLAMA_MODELS` points to this folder, so **all model weights live here**
(`blobs/` + `manifests/`) and nothing spills to `~/.ollama`.

---

## 1. What's in this folder

```
f:\tmp\Model\
  start-ollama.bat   # launcher: sets OLLAMA_MODELS + OLLAMA_ORIGINS then starts 4 processes
  README.md          # this file
  chats.json         # saved chat history (empty by default)
  webui\
    index.html       # the single-file web UI (chat + terminal)
    terminal.py      # Terminal API (port 8001) + service/ollama control
    wsserver.py      # WebSocket relay (port 8002)
  blobs/             # model weights (Ollama content-addressed store) — DO NOT COMMIT
  manifests/         # model manifests — DO NOT COMMIT
```

> The `blobs/` and `manifests/` folders hold the actual model weights (≈10 GB).
> They are excluded from git (see `.gitignore`). Re-download with `ollama pull`.

---

## 2. Quick start (one click)

1. Double-click **`start-ollama.bat`**. It starts **4 processes** (see below) and opens
   the UI in a Chrome app window at `http://localhost:8000`.
2. Wait ~3 seconds for Ollama to come up.
3. In the Web UI: pick a model in the left sidebar → click **▶ Run** → start chatting.

> **Do NOT open `webui/index.html` by double-clicking it.** That loads the page as a
> `file://` URL with no backend running, so the **▶ Run** model button, terminal, and the
> code **Save/Run** buttons will do nothing. Always launch via `start-ollama.bat` (it serves
> the page at `http://localhost:8000`). If you do open it directly, the app shows a banner
> explaining this.

---

## 3. The 4 background processes

`start-ollama.bat` launches:

| # | Process | Command | Port | Purpose |
|---|---------|---------|------|---------|
| 1 | **Ollama server** | `ollama serve` (`OLLAMA_MODELS=F:\tmp\Model`, `OLLAMA_ORIGINS=*`) | `11434` | Serves the LLM + model management API |
| 2 | **Web UI** | `python -m http.server 8000` (in `webui/`) | `8000` | Serves `index.html` |
| 3 | **Terminal API** | `python terminal.py` (in `webui/`) | `8001` | Runs shell commands, lists/starts/stops services & models, file writes |
| 4 | **WebSocket relay** | `python wsserver.py` (in `webui/`) | `8002` | Streams terminal output to the browser (`/ws`) |

It also opens `chrome --app=http://localhost:8000` as a standalone window.

### Terminal API (`terminal.py`, port 8001) endpoints
- `POST /exec` — run a shell command, returns stdout/stderr.
- `GET  /chats` — list saved chats.
- `GET  /ps` — running Ollama models.
- `GET  /ollama/status` · `POST /ollama/start` · `POST /ollama/stop` — control the server.
- `GET  /service/status` · `POST /service/all` — control webui/ws/ollama services.
- `POST /writefile` — write a file to disk.

### WebSocket (`wsserver.py`, port 8002)
- Only serves `/ws` — pushes live terminal output to the open browser tab.

---

## 4. Using the models via the Ollama CLI (local)

Everything below talks to the server running in process #1 (`localhost:11434`).

### List what's installed
```bat
ollama list
```
Shows local models, e.g. `qwen2.5vl:7b`, `qwen2.5-coder:7b`.

### Chat / run a model interactively
```bat
ollama run qwen2.5vl:7b       # multimodal (image / video / text)
ollama run qwen2.5-coder:7b   # coding
```
Type your prompt, get a reply, `/bye` to exit. You can also pipe input:
```bat
echo "write a python quicksort" | ollama run qwen2.5-coder:7b
```

### Check what's loaded / running
```bat
ollama ps
```

### Unload (stop) a running model
```bat
ollama stop qwen2.5-coder:7b
```
(In the Web UI this is the **▶ Run / ■ Stop** button next to each model in the sidebar.)

### Pull / update a model (downloads into this folder)
```bat
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b   # bigger, slower, ~9 GB (offloads ~1 GB to RAM)
ollama pull whisper              # audio transcription
```

### Call the REST API directly (no CLI)
```bat
curl http://localhost:11434/api/generate -d "{
  \"model\": \"qwen2.5-coder:7b\",
  \"prompt\": \"def add(a,b):\",
  \"stream\": false
}"
```
Streaming chat:
```bat
curl http://localhost:11434/api/chat -d "{
  \"model\": \"qwen2.5-coder:7b\",
  \"messages\": [{\"role\":\"user\",\"content\":\"explain decorators in python\"}]
}"
```

### Point a different client at the server
Any OpenAI-compatible/Ollama client can use base URL `http://localhost:11434`.

---

## 5. Models

### 1. qwen2.5vl:7b — Multimodal (Vision-Language)
- **Role:** image + video + text understanding (no audio)
- **Size:** 6.0 GB  ·  **VRAM:** ~5 GB (fits 8 GB)
- **Context:** up to 128K tokens
- **Best for:** reading screenshots/diagrams/charts, video-frame Q&A
- **Run:** `ollama run qwen2.5vl:7b`
- **Note:** does not handle audio. For audio use Whisper / Qwen2-Audio.

### 2. qwen2.5-coder:7b — Coding
- **Role:** code generation, Fill-in-the-Middle, debugging, multi-language
- **Size:** 4.7 GB  ·  **VRAM:** ~5 GB (fits 8 GB)
- **Context:** up to 128K tokens
- **Best for:** everyday coding, fast on the laptop GPU
- **Run:** `ollama run qwen2.5-coder:7b`
- **Upgrade:** `ollama pull qwen2.5-coder:14b` (~9 GB; offloads ~1 GB to your 31 GB RAM)

---

## 6. Folder layout (detail)
```
f:\tmp\Model\
  start-ollama.bat   # launcher: sets OLLAMA_MODELS + starts 4 processes
  README.md          # this file
  chats.json         # chat history
  webui/             # front-end + back-end
    index.html       # single-file UI (chat + terminal)
    terminal.py      # Terminal API (port 8001)
    wsserver.py      # WebSocket relay (port 8002)
  blobs/             # model weights (git-ignored)
  manifests/         # model manifests (git-ignored)
```
> `blobs/` is Ollama's shared weight store. This README is the human-readable
> organization layer — edit it to track models, versions, and notes.

---

## 7. Optional additions
- **Audio (transcription):** `ollama pull whisper` → `ollama run whisper "file.mp3"`
- **Stronger coder:** `ollama pull qwen2.5-coder:14b`

## 8. Hardware this was tuned for
RTX 3070 Laptop (8 GB VRAM) · 31.4 GB RAM · ~430 GB free SSD.
Both models run fully in VRAM with context headroom.

## 9. Stopping everything
Close the 4 `cmd` windows opened by `start-ollama.bat`, or from the Web UI
use the terminal panel / service controls. To free VRAM: `ollama stop <model>`.
