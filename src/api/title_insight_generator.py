# title_insight_generator.py
import requests

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:1b"


def _call_ollama(prompt: str, model: str = OLLAMA_MODEL, temperature: float = 0.3) -> str:
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
        }
        resp = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        print("LLM error in title_insight_generator:", e)
        return ""
    

def generate_title_insights(title: str, sector: str | None = None) -> str:
    """
    Generate insights using ONLY the article title (+ optional sector),
    for use when the user just clicks the title.
    """
    sector_text = f"Sector: {sector}\n" if sector else ""

    prompt = f"""
You are an analytical assistant focused on Sri Lankan business and economic news.

{sector_text}
Article title: {title}

Task: Based ONLY on this title (do not invent specific facts that are not implied),
give a structured, high-level analysis with:
1) Likely core issue
2) Possible risks
3) Possible opportunities
4) Questions a policy or business analyst should ask next

Be concise and clearly use bullet points.
Do not claim that these are confirmed facts; treat them as hypotheses from the title.
"""

    return _call_ollama(prompt)
