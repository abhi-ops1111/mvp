# ⚡ NeuroFlow (Flozen) — MVP

> An AI-driven closed-loop feedback system that dynamically simplifies educational content in real-time based on a student's eye-tracking data.

---

## What it does

NeuroFlow monitors where and how stably a student's eyes move while reading a lesson. It computes a **Cognitive Friction Index (CFI)** from gaze variance and pupil data. When CFI crosses a stress threshold (default: 0.7), it automatically calls an LLM to rewrite the current section — swapping dense technical prose for bullet points, a plain-English summary, a real-world analogy, and an image search suggestion — all without the student having to do anything.

```
Student reads lesson
       ↓
WebGazer.js tracks gaze (30fps)
       ↓
CFI = (gaze instability × 0.6) + (pupil variance × 0.4)
       ↓
CFI > 0.7 → POST /cfi → Flask → Gemini / Ollama / fallback
       ↓
Simplified HTML injected into the lesson, inline
```

---

## Repo structure

```
neuroflow-mvp/
├── frontend/
│   └── index.html          # Single-page app: eye tracking + CFI engine + lesson UI
├── backend/
│   ├── app.py              # Flask server: /cfi endpoint + LLM calls
│   ├── requirements.txt    # Python dependencies
│   └── .env                # API keys — never commit this
├── .gitignore
└── README.md
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://python.org) |
| pip | any | bundled with Python |
| Chrome | latest | required for WebGazer camera access |
| VS Code | any | recommended editor |
| Ollama | latest | [ollama.com](https://ollama.com) — optional, offline LLM |

No npm, no Node, no build step. The frontend is a plain HTML file served by Python's built-in HTTP server.

---

## Quick start

### 1. Clone and set up

```bash
git clone https://github.com/your-username/neuroflow-mvp.git
cd neuroflow-mvp
```

### 2. Add your API key

```bash
# Create the env file — replace the value with your real key
echo "GEMINI_API_KEY=your_key_here" > backend/.env
```

Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com) → "Get API key".
If you skip this, the backend falls back to Ollama (local) or a rule-based simplifier.

### 3. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Start the backend

```bash
# From the backend/ directory
python app.py
```

You should see: `* Running on http://0.0.0.0:5000`

### 5. Serve the frontend (new terminal)

```bash
cd frontend
python -m http.server 3000
```

### 6. Open in Chrome

```
http://localhost:3000/index.html
```

Allow camera access when prompted, or use the **Demo stress slider** in the top bar to simulate high CFI without a camera.

---

## Demo flow (no camera needed)

1. Open the page — HUD shows live CFI metrics at the top.
2. Drag the **"Demo stress"** slider past 70%.
3. Within ~2 seconds the first visible section will shimmer, then replace with simplified content.
4. Click **"Show original"** on any section to restore the dense text.
5. Press **`S`** on your keyboard to spike CFI to 0.9 for 5 seconds (quick demo shortcut).

---

## Architecture

### Frontend (`index.html`)

- **WebGazer.js** — browser-based eye tracking via webcam, 30fps gaze callbacks.
- **CFI engine** — pure JavaScript. Maintains a 30-frame rolling buffer of `(x, y)` gaze points, computes standard deviation as gaze instability, blends with pupil variance (slider in MVP, real iris data in v2).
- **Chart.js** — sparkline in the HUD showing CFI over time, colour-coded green → yellow → red.
- **Content swap** — each lesson section has a `dense-view` and a `simplified-view` div. On simplification, the dense div is hidden and the simplified div is animated in.
- **Polling loop** — `setInterval` every 2 seconds. Only fires a backend POST if CFI > threshold AND the current section hasn't been simplified yet.

### Backend (`app.py`)

- **Flask** with `flask-cors` to accept requests from the browser.
- **`POST /cfi`** — receives `{ cfi, section_id, content }`. If CFI exceeds threshold, calls the LLM chain.
- **LLM chain** — tries Gemini 1.5 Flash first, then Ollama (`llama3.2`), then a zero-dependency rule-based fallback. All three return the same JSON shape.
- **`GET /health`** — quick check that the server is up and Gemini is configured.

### LLM prompt

The simplification prompt asks for a strict JSON response with four keys:

```
summary     – One sentence, max 25 words
bullets     – 3–5 short bullet strings
analogy     – One real-world analogy a 16-year-old would understand
image_query – A 3–6 word Google Images search query
```

Temperature is set to 0.4 to keep outputs consistent and factual.

---

## Configuration

| Variable | Where | Default | Effect |
|----------|-------|---------|--------|
| `GEMINI_API_KEY` | `backend/.env` | `""` | Enables Gemini calls. Leave blank to use Ollama. |
| `CFI_THRESHOLD` | `backend/app.py` line 12 | `0.70` | CFI level that triggers simplification. |
| `CFI_THRESHOLD` | `frontend/index.html` line ~line 160 | `0.70` | Must match backend. |
| `SEND_INTERVAL` | `frontend/index.html` | `2000` ms | How often the frontend polls. Increase if hitting Gemini rate limits. |
| `GAZE_BUFFER_SIZE` | `frontend/index.html` | `30` frames | Larger = smoother but slower CFI response. |
| `model` in `call_ollama()` | `backend/app.py` | `"llama3.2"` | Change to `"mistral"` or `"phi3"` if you pulled a different model. |

---

## Using Ollama (offline, no API key)

```bash
# Install Ollama from https://ollama.com, then:
ollama serve          # start the local server (keep this running)
ollama pull llama3.2  # ~2 GB download, one-time
```

The backend automatically tries Ollama if `GEMINI_API_KEY` is missing or blank. First response may take 10–20 seconds while the model loads into memory; subsequent calls are faster.

---

## Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Eye tracking | WebGazer.js | Works in-browser, no install, free |
| Frontend | Vanilla HTML/JS | No build step, beginner-friendly |
| Charts | Chart.js 4 | CDN, easy API |
| Backend | Flask + flask-cors | Minimal Python, easy to read |
| LLM (primary) | Gemini 1.5 Flash API | Free tier, fast, JSON-mode reliable |
| LLM (fallback) | Ollama + Llama 3.2 | Fully offline, no key needed |
| Env management | python-dotenv | Keeps keys out of source code |

---

## Troubleshooting

**Camera blocked / WebGazer black screen**
The page must be served over HTTP (not opened as a `file://` URL). Always use `python -m http.server 3000` and open `http://localhost:3000`, not the file path directly.

**CORS error in browser console**
Confirm Flask is running on port 5000 and check that `CORS(app)` is present at the top of `app.py`. On Windows, check no firewall rule is blocking port 5000.

**Gemini 400 "API key not valid"**
Open `backend/.env` and make sure the line reads exactly `GEMINI_API_KEY=AIza...` with no quotes, no spaces around the `=`, and no trailing newline issues. Test with:
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"
```

**Gemini 429 rate limit**
The free tier allows 15 requests per minute. Increase `SEND_INTERVAL` to `5000` in `index.html` to reduce call frequency.

**Ollama "connection refused"**
Run `ollama serve` in a separate terminal before starting Flask. Make sure the model is pulled: `ollama list` should show `llama3.2`.

**LLM returns malformed JSON**
Add this debug line in `app.py` just before `json.loads(text)` in either LLM function:
```python
print(f"[DEBUG] Raw response: {repr(text[:400])}")
```
Both functions already strip markdown code fences. If the model keeps wrapping output, add `"Please output only raw JSON, no backticks."` to the end of `SIMPLIFY_PROMPT`.

---

## Roadmap (post-MVP)

- [ ] **Real pupil dilation** via MediaPipe Face Mesh iris landmarks in a Web Worker.
- [ ] **WebSocket streaming** (Flask-SocketIO) so simplified content streams in token-by-token instead of appearing all at once.
- [ ] **Session replay dashboard** — store `(timestamp, cfi, section_id, action)` to SQLite, visualise where in lessons students hit overload.
- [ ] **Multi-subject content** — add more lesson pages (physics, history) with section IDs; the backend is already content-agnostic.
- [ ] **Calibration UX** — guided 9-point WebGazer calibration screen before the lesson starts.
- [ ] **Mobile support** — replace WebGazer with MediaPipe selfie segmentation for devices without reliable `getUserMedia`.

---

## Team

Built by a 3-person team:
- 2 × AI/ML developers (Python, Flask, LLM integration)
- 1 × web developer (HTML, JS, CSS)

Timeline: 1–2 week MVP sprint.

---

## License

MIT — free to use, modify, and distribute.