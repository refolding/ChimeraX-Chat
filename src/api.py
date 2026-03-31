import json
import urllib.request
import urllib.error

REQUEST_TIMEOUT_SECONDS = 20

def _build_request(url, api_key, user_text):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-goog-api-key"] = api_key

    system_prompt = (
        "You are an expert assistant for UCSF ChimeraX. "
        "Translate the user's natural language request into a valid ChimeraX command. "
        "CRITICAL: Reply ONLY with the raw command. No markdown, no formatting, no quotes, no explanation."
    )

    data = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {"temperature": 0.0}
    }

    return urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)


def _extract_command(result):
    candidates = result.get("candidates", [])
    if not candidates:
        return "error: API returned no candidates."

    command = candidates[0]["content"]["parts"][0]["text"].strip()
    if command.startswith("```"):
        command = command.replace("```chimerax", "").replace("```bash", "").replace("```", "").strip()
    return command


def get_chimerax_command(user_text, api_key):
    """Sends user text to Google Gemini using the user's provided API key."""
    if not api_key:
        return "error: API key is missing. Please click 'Set API Key' to add it."

    base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"
    
    try:
        req = _build_request(base_url, api_key, user_text)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
            return _extract_command(result)
            
    except urllib.error.HTTPError as e:
        # Compatibility fallback for endpoints that reject header-based keys.
        if e.code in (400, 401, 403):
            try:
                fallback_url = f"{base_url}?key={api_key}"
                fallback_req = _build_request(fallback_url, api_key="", user_text=user_text)
                with urllib.request.urlopen(fallback_req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    return _extract_command(result)
            except Exception:
                pass
        error_info = e.read().decode("utf-8")
        return f"error: HTTP {e.code} - {error_info}"
    except urllib.error.URLError as e:
        return f"error: Network error - {str(e)}"
    except Exception as e:
        return f"error: {str(e)}"
