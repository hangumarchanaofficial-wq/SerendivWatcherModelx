import os
import json
from datetime import datetime, timezone

import requests


def generate_sector_insights(sector_name: str, articles: list):
    """
    Generate business insights for a sector using Ollama (gemma3:1b).
    """
    print(f"\n[INSIGHT_GEN] Generating insights for {sector_name} sector ({len(articles)} articles)")

    if not articles:
        return {
            "sector": sector_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "article_count": 0,
            "insights": f"No recent articles available for {sector_name} sector.",
            "key_themes": [],
            "recommendations": "Insufficient data to generate recommendations.",
        }

    # Build combined article text (titles + truncated body)
    article_texts = []
    for i, art in enumerate(articles[:10], 1):
        title = art.get("title", "Untitled")
        text = art.get("text", "")[:500]
        article_texts.append(f"{i}. {title}\n{text}...")

    combined = "\n\n".join(article_texts)

    prompt = f"""You are a business analyst for Sri Lankan companies.

Analyze these recent {sector_name.upper()} sector news articles and provide:

1. KEY INSIGHTS (2–3 sentences): What are the most important developments?

2. THEMES (bullet points): What recurring topics appear?

3. BUSINESS IMPLICATIONS (2–3 sentences): How should businesses in Sri Lanka respond?

Articles:

{combined}

Provide clear, structured, actionable analysis."""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "gemma3:1b")

    try:
        print(f"[INSIGHT_GEN] Calling Ollama at {ollama_host} with model {model_name}")
        body = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise business analyst. Use plain language.",
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        resp = requests.post(f"{ollama_host}/api/chat", json=body, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        insights_text = data.get("message", {}).get("content", "").strip()
        print(f"[INSIGHT_GEN] Generated {len(insights_text)} chars of insights")

        # Extract bullet-point themes
        lines = insights_text.split("\n")
        themes = [
            line.strip("- *•").strip()
            for line in lines
            if line.strip().startswith(("-", "*", "•", "1", "2", "3"))
        ][:5]

        lower_text = insights_text.lower()
        recommendations = ""
        marker = "business implications"
        if marker in lower_text:
            idx = lower_text.index(marker)
            recommendations = insights_text[idx:].strip()

        return {
            "sector": sector_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "article_count": len(articles),
            "insights": insights_text,
            "key_themes": themes,
            "recommendations": recommendations,
        }

    except Exception as e:
        print(f"[INSIGHT_GEN] ERROR: {e}")
        return {
            "sector": sector_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "article_count": len(articles),
            "insights": f"Could not generate insights: {str(e)}",
            "key_themes": [],
            "recommendations": "AI service unavailable.",
        }


def summarize_single_article(article: dict) -> dict:
    """
    Generate a focused summary for one article using Ollama.
    Returns: {"title": str, "summary": str}
    """
    title = article.get("title", "Untitled")
    text = article.get("text", "")[:1500]

    prompt = f"""You are a business analyst for Sri Lankan companies.

Analyze this news article and provide:

1. SUMMARY (3–4 sentences): What happened and why it matters.

2. KEY POINTS (3–5 bullet points):
- Most important facts.
- Notable developments.
- Any significant figures or data.

3. BUSINESS IMPLICATIONS (2–3 sentences):
How should Sri Lankan businesses respond, and what risks or opportunities exist?

Title: {title}

Text:
{text}
"""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "gemma3:1b")

    body = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise business analyst. Use clear headings and bullet points.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }

    try:
        print(f"[INSIGHT_GEN] Summarising single article with {model_name}")
        resp = requests.post(f"{ollama_host}/api/chat", json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "").strip()
        return {"title": title, "summary": content}
    except Exception as e:
        print(f"[INSIGHT_GEN] ERROR in summarize_single_article: {e}")
        return {"title": title, "summary": f"Could not generate summary: {e}"}


def save_insights_to_temp(sector_name: str, insights: dict):
    """
    Save generated insights to data/temp/ for caching.
    """
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    temp_dir = os.path.join(project_root, "data", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    filename = f"{sector_name}_insights.json"
    filepath = os.path.join(temp_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"[INSIGHT_GEN] Saved insights to {filepath}")
    return filepath


def load_cached_insights(sector_name: str):
    """
    Load cached insights from data/temp/{sector}_insights.json if present.
    """
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    temp_dir = os.path.join(project_root, "data", "temp")
    filepath = os.path.join(temp_dir, f"{sector_name}_insights.json")

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            print(f"[INSIGHT_GEN] Loaded cached insights from {filepath}")
            return json.load(f)
    return None


if __name__ == "__main__":
    # Simple manual test
    test_articles = [
        {
            "title": "IFC backs green economy push",
            "text": "International Finance Corporation pledges $270M for sustainable development...",
        },
        {
            "title": "Banks face liquidity pressure",
            "text": "Sri Lankan banks report tightening conditions amid economic recovery efforts...",
        },
    ]

    insights = generate_sector_insights("finance", test_articles)
    save_insights_to_temp("finance", insights)
    print(json.dumps(insights, indent=2))
