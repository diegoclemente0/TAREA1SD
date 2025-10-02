import os
import time
import json
import requests
import traceback

HAS_GENAI = False
genai = None
client = None

try:
    from google import genai as google_genai  
    genai = google_genai
    HAS_GENAI = True
except Exception:
    try:
        import genai as google_genai 
        genai = google_genai
        HAS_GENAI = True
    except Exception:
        HAS_GENAI = False

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  

if HAS_GENAI:
    try:
        if hasattr(genai, "Client"):
            client = genai.Client(api_key=API_KEY) if API_KEY else genai.Client()
        elif hasattr(genai, "configure"):
            genai.configure(api_key=API_KEY)
            client = None
        else:
            client = None
    except Exception:
        client = None

def _extract_text(resp) -> str:
    try:
        if resp is None:
            return ""
        if hasattr(resp, "text"):
            return resp.text
        if hasattr(resp, "candidates"):
            cand = getattr(resp, "candidates")
            if isinstance(cand, (list, tuple)) and len(cand) > 0:
                first = cand[0]
                if isinstance(first, dict) and "content" in first:
                    return first["content"]
                if hasattr(first, "content"):
                    return first.content
        if isinstance(resp, dict):
            if "candidates" in resp and isinstance(resp["candidates"], list) and len(resp["candidates"]) > 0:
                c = resp["candidates"][0]
                if isinstance(c, dict) and "content" in c:
                    return c["content"]
            if "output" in resp and isinstance(resp["output"], list) and len(resp["output"]) > 0:
                out = resp["output"][0]
                if isinstance(out, dict) and "content" in out:
                    return out["content"]
        return str(resp)
    except Exception:
        return str(resp)

def _call_rest_generate_content(prompt: str, model: str = MODEL, timeout: int = 30) -> str:
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY no definida en el entorno para el fallback REST.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"REST generateContent falló: status={resp.status_code}, body={resp.text}")
    j = resp.json()
    return _extract_text(j)

def call_gemini_sync(prompt: str, timeout: int = 30) -> str:
    if HAS_GENAI:
        try:
            if hasattr(genai, "generate_text"):
                try:
                    r = genai.generate_text(model=MODEL, prompt=prompt)
                    return _extract_text(r)
                except TypeError:
                    r = genai.generate_text(prompt)
                    return _extract_text(r)
            if client is not None and hasattr(client, "models") and hasattr(client.models, "generate_content"):
                try:
                    r = client.models.generate_content(model=MODEL, contents=prompt)
                    return _extract_text(r)
                except TypeError:
                    r = client.models.generate_content(model=MODEL, contents=[prompt])
                    return _extract_text(r)
            if client is not None and hasattr(client, "models") and hasattr(client.models, "generateContent"):
                r = client.models.generateContent(model=MODEL, contents=[{"parts":[{"text": prompt}]}])
                return _extract_text(r)
        except Exception as e:
            print("SDK invocation failed, falling back to REST:", e)
            traceback.print_exc()

    return _call_rest_generate_content(prompt, model=MODEL, timeout=timeout)


def call_gemini_safe(prompt: str, retries: int = 3, backoff: int = 2, timeout: int = 30) -> str:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return call_gemini_sync(prompt, timeout=timeout)
        except Exception as e:
            last_exc = e
            wait = backoff ** (attempt - 1)
            print(f"[Gemini] intento {attempt} falló: {e}. reintentando en {wait}s...")
            traceback.print_exc()
            time.sleep(wait)
    raise RuntimeError(f"Gemini falló tras {retries} intentos. Último error: {last_exc}")
