import json
import urllib.request
import urllib.error

def get_chimerax_command(user_text, api_key):
    """Sends user text to Google Gemini using the user's provided API key."""
    if not api_key:
        return "error: API key is missing. Please click 'Set API Key' to add it."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
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
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            command = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if command.startswith("```"):
                command = command.replace("```chimerax", "").replace("```bash", "").replace("```", "").strip()
                
            return command
            
    except urllib.error.HTTPError as e:
        error_info = e.read().decode("utf-8")
        return f"error: HTTP {e.code} - {error_info}"
    except Exception as e:
        return f"error: {str(e)}"