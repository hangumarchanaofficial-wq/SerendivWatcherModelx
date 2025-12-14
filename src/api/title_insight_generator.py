# title_insight_generator.py
import requests

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"


def _call_ollama(prompt: str, model: str = OLLAMA_MODEL, temperature: float = 0.3) -> str:
    """Call Ollama API with error handling"""
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "options": {
                "num_predict": 400,
                "top_k": 40,
                "top_p": 0.9,
            }
        }
        resp = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        print(f"LLM error: {e}")
        return ""


def generate_title_insights(title: str, sector: str | None = None) -> str:
    """
    Generate concise business intelligence insights with emojis
    
    Args:
        title: Article headline
        sector: Business sector (optional)
    
    Returns:
        Formatted analysis with emojis
    """
    sector_context = f" | Sector: {sector}" if sector else ""
    
    prompt = f"""You are a Sri Lankan business intelligence analyst. Analyze this headline.

Title: "{title}"{sector_context}

Provide analysis in this EXACT format (keep it concise):

CORE ISSUE:
[1-2 clear sentences about the main story and its significance for Sri Lanka's economy]

KEY RISKS:
• [Risk 1 - under 15 words]
• [Risk 2 - under 15 words]  
• [Risk 3 - under 15 words]

OPPORTUNITIES:
• [Opportunity 1 - under 15 words]
• [Opportunity 2 - under 15 words]

STRATEGIC QUESTIONS:
• [Question 1]
• [Question 2]
• [Question 3]

Rules:
- Be concise and specific to Sri Lankan context
- Each bullet point must be under 15 words
- Focus on actionable insights
- Professional business language only"""

    result = _call_ollama(prompt, temperature=0.2)
    
    if not result:
        return _generate_fallback(title)
    
    # Add emojis to the output
    formatted = _add_formatting(result)
    return formatted


def _add_formatting(text: str) -> str:
    """Add emojis and formatting to the text"""
    
    # Replace section headers with emoji versions
    text = text.replace("CORE ISSUE:", "💡 CORE ISSUE")
    text = text.replace("KEY RISKS:", "\n⚠️ KEY RISKS")
    text = text.replace("OPPORTUNITIES:", "\n✨ OPPORTUNITIES")
    text = text.replace("STRATEGIC QUESTIONS:", "\n❓ STRATEGIC QUESTIONS")
    
    # Clean up and ensure proper spacing
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Add proper spacing after headers
        if line.startswith(('💡', '⚠️', '✨', '❓')):
            if formatted_lines:  # Add blank line before section
                formatted_lines.append('')
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


def _generate_fallback(title: str) -> str:
    """Generate fallback text when LLM fails"""
    return f"""💡 CORE ISSUE
Analysis temporarily unavailable for: {title}

⚠️ KEY RISKS
• Technical issue with analysis system
• Please try again in a moment

✨ OPPORTUNITIES
• System will retry automatically

❓ STRATEGIC QUESTIONS
• Contact support if issue persists"""


def generate_quick_summary(title: str, sentiment: float = 0.0) -> str:
    """
    Generate ultra-short summary with emoji
    
    Args:
        title: Article headline
        sentiment: Sentiment score (-1 to 1)
    
    Returns:
        One-line summary with emoji
    """
    sentiment_label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
    emoji = "📈" if sentiment > 0.1 else "📉" if sentiment < -0.1 else "➡️"
    
    prompt = f"""Create ONE concise sentence (max 20 words) summarizing business impact.

Title: "{title}"
Sentiment: {sentiment_label}

Format: [What happened] → [Impact]
Example: "Central Bank raises rates → Higher borrowing costs slow expansion"

Your summary:"""

    result = _call_ollama(prompt, temperature=0.1).strip()
    
    if not result:
        return f"{emoji} {title}"
    
    return f"{emoji} {result}"


def generate_sector_impact(title: str, sector: str) -> str:
    """
    Generate sector-specific impact with emojis
    
    Args:
        title: Article headline
        sector: Business sector
    
    Returns:
        Sector impact analysis
    """
    prompt = f"""Analyze impact on Sri Lanka's {sector} sector.

Title: "{title}"

Provide 3 bullet points (each under 15 words):
• Direct impact on {sector}
• Regulatory implications
• Growth outlook

Keep concise, under 80 words total."""

    result = _call_ollama(prompt, temperature=0.25)
    
    if not result:
        return f"🏢 Analysis unavailable for {sector} sector"
    
    # Add sector emoji
    sector_emojis = {
        'finance': '💰',
        'banking': '🏦',
        'agriculture': '🌾',
        'technology': '💻',
        'tourism': '✈️',
        'manufacturing': '🏭',
        'retail': '🛒',
        'energy': '⚡',
        'healthcare': '🏥',
        'education': '📚'
    }
    
    emoji = sector_emojis.get(sector.lower(), '🏢')
    return f"{emoji} {sector.upper()} SECTOR IMPACT\n\n{result}"


# Testing
if __name__ == "__main__":
    test_title = "People's Bank achieves pre-tax profit of Rs.43.7 b in 9mths'25"
    test_sector = "finance"
    
    print("=" * 80)
    print("📊 FULL ANALYSIS")
    print("=" * 80)
    insights = generate_title_insights(test_title, test_sector)
    print(insights)
    
    print("\n" + "=" * 80)
    print("⚡ QUICK SUMMARY")
    print("=" * 80)
    summary = generate_quick_summary(test_title, sentiment=0.65)
    print(summary)
    
    print("\n" + "=" * 80)
    print("🎯 SECTOR IMPACT")
    print("=" * 80)
    impact = generate_sector_impact(test_title, test_sector)
    print(impact)
