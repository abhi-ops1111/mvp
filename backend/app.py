import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()  # reads backend/.env

app = Flask(__name__)
CORS(app)      # allow requests from the browser (different port)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CFI_THRESHOLD  = 0.70

# ──────────────────────────────────────────────────────────
# /cfi  –  receives CFI + content, returns simplified version
# ──────────────────────────────────────────────────────────
@app.route("/cfi", methods=["POST"])
def handle_cfi():
    data       = request.get_json(force=True)
    cfi        = float(data.get("cfi", 0))
    section_id = data.get("section_id", "unknown")
    content    = data.get("content", "")

    print(f"[NeuroFlow] CFI={cfi:.2f}  section={section_id}")

    if cfi <= CFI_THRESHOLD:
        return jsonify({"action": "keep", "cfi": cfi})

    if not content.strip():
        return jsonify({"action": "keep", "cfi": cfi, "reason": "no content"})

    # Try Gemini first, fall back to Ollama
    simplified, source = None, None
    if GEMINI_API_KEY and GEMINI_API_KEY != "your_key_here":
        simplified = call_gemini(content)
        source = "gemini"

    if not simplified:
        simplified = call_ollama(content)
        source = "ollama"

    if not simplified:
        # Last resort: rule-based fallback (no LLM needed)
        simplified = rule_based_simplify(content)
        source = "rule-based"

    print(f"[NeuroFlow] Simplified via {source}")
    return jsonify({"action": "simplify", "simplified": simplified, "source": source, "cfi": cfi})


# ──────────────────────────────────────────────────────────
# /health  –  quick sanity check
# ──────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "gemini_configured": bool(GEMINI_API_KEY)})

# ──────────────────────────────────────────────────────────
# LLM HELPERS
# ──────────────────────────────────────────────────────────

SIMPLIFY_PROMPT = """You are an adaptive learning assistant.
A student's eye-tracking data shows signs of cognitive overload (high Cognitive Friction Index).
Your job is to make the following educational content significantly easier to absorb.

OUTPUT FORMAT: Respond ONLY with a valid JSON object. No markdown, no backticks, no preamble.
The JSON must have exactly these keys:
  "summary"     – A single plain-English sentence that captures the core idea (max 25 words).
  "bullets"     – A list of 3 to 5 short bullet strings, each under 12 words.
  "analogy"     – One concrete real-world analogy that a 16-year-old would understand (1-2 sentences).
  "image_query" – A 3-6 word Google Images search query that would visually illustrate this concept.

CONTENT TO SIMPLIFY:
{content}"""


def call_gemini(content: str) -> dict | None:
    """Call Gemini 1.5 Flash API and return parsed simplified dict."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    prompt = SIMPLIFY_PROMPT.format(content=content)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 512,
        },
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        raw = res.json()
        text = raw["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Strip markdown code fences if Gemini wraps with them anyway
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[Gemini] Error: {e}")
        return None


def call_ollama(content: str) -> dict | None:
    """Call a locally running Ollama instance (llama3.2 or any installed model)."""
    url    = "http://localhost:11434/api/generate"
    prompt = SIMPLIFY_PROMPT.format(content=content)
    payload = {
        "model":  "llama3.2",    # change to "mistral" or "phi3" if you pulled those
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 512},
    }
    try:
        res = requests.post(url, json=payload, timeout=30)
        res.raise_for_status()
        text = res.json().get("response", "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[Ollama] Error: {e}")
        return None


def rule_based_simplify(content: str) -> dict:
    """
    Zero-dependency fallback: extracts first sentence as summary
    and splits remaining text into crude bullet points.
    Used when both LLMs are unreachable.
    """
    sentences = [s.strip() for s in content.split(".") if s.strip()]
    summary   = sentences[0] + "." if sentences else "See content above."
    bullets   = [s + "." for s in sentences[1:4]] if len(sentences) > 1 else ["Read the section above carefully."]
    return {
        "summary":     summary,
        "bullets":     bullets,
        "analogy":     "Think of it like breaking a big task into smaller steps.",
        "image_query": "simple diagram concept explanation",
    }
if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")