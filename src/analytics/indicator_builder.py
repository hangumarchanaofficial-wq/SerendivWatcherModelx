from datetime import datetime
from collections import defaultdict, Counter
from tinydb import TinyDB
import json
import math
import requests
import re


# =====================================================================
# LLM CONFIGURATION
# =====================================================================

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:1b"


# =====================================================================
# COMPREHENSIVE NOISE FILTERING
# =====================================================================

# English stopwords
ENGLISH_STOPWORDS = {
    "that", "this", "these", "those", "they", "them", "their", "there",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "the", "a", "an", "and", "or", "but", "if", "then", "than",
    "such", "some", "any", "all", "both", "each", "few", "more", "most",
    "other", "another", "same", "so", "just", "very", "can", "will",
}

# UI artifacts
UI_ARTIFACTS = {
    "mobile apps", "222 reply", "view results", "this browser", "my name",
    "save my name", "very good article", "internal inquiry rainfall",
    "digital screen", "our journey", "these initiatives", "aftermath",
    "excellence", "operational efficiency", "investor confidence",
    "accessibility", "partnership", "nations", "institutions",
}

# Website/scraping artifacts
NOISY_TOPICS = {
    "marketing manager sales", "this website", "the morning",
    "the sunday times", "sport", "copyright", "ft.lk copyright", "ft.lk",
    "fire", "email", "friend", "addition", "the tamil diaspora",
    "a few sections", "no impact", "the economy", "your old ride",
}

BAD_KEYWORD_FRAGMENTS = [
    "copyright", "ft.lk", "ft.", ".lk", "your old", "the next",
    "this website", "the morning", "sunday times", "daily mirror",
    "email", "friend", "click", "read more", "subscribe",
]

# Generic buzzwords
GENERIC_BUZZWORDS = {
    "growth", "technology", "government", "officials", "efforts",
    "logistics", "innovation", "digital", "development",
    "time", "year", "month", "week", "day", "today", "yesterday",
}

MIN_TOPIC_LENGTH = 5

# Bad organization names
BAD_ORG_NAMES = {
    "INR 2", "YoY", "BBC", "DHS", "U.S. Professor", "Colombos",
    "Unity Plazas", "Colombo", "Digital", "Group", "Groups", "Bank",
    "Committee", "Members", "EFF", "State", "COVID-19", "Sri Lanka",
}

BANNED_ORGANIZATIONS = {
    "International Aid and Government Alerts Security",
    "the Board of Directors", "the Management of Onally Holdings PLC",
    "Capital Goods", "the Central Bank of Sri Lanka", "the World Bank",
    "the Ceylon Chamber of Commerce", "Charming and Co.",
    "the Onally Holdings PLC",
}

# Regex patterns for garbage
GARBAGE_PATTERNS = [
    r'^\d+\s+reply$',
    r'view\s+results?',
    r'this\s+browser',
    r'my\s+name',
    r'save\s+my',
    r'very\s+good',
    r'mobile\s+app',
    r'digital\s+screen',
    r'internal\s+inquiry',
]


class IndicatorBuilder:
    def __init__(self, db_path: str = "data/raw/articles.json", output_dir: str = "data/indicators"):
        """
        Initialize IndicatorBuilder.
        
        Args:
            db_path: Path to TinyDB articles database
            output_dir: Directory to save indicator JSON files
        """
        self.db = TinyDB(db_path)
        self.output_dir = output_dir
        self.llm_model = OLLAMA_MODEL

    def set_llm_model(self, model_name: str):
        """Set the LLM model name to use."""
        self.llm_model = model_name
        print(f"LLM model set to: {model_name}")

    # =================================================================
    # LLM INTEGRATION
    # =================================================================
    def _call_ollama(self, prompt: str, temperature: float = 0.2) -> str:
        """Call Ollama API."""
        try:
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
            }
            
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=90)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except Exception as e:
            print(f"  Warning: LLM error: {e}")
            return ""

    def _extract_sector_text(self, sector: str, articles: list, max_words_per_article: int = 500, max_articles: int = 20) -> str:
        """
        Extract representative text samples from articles in a sector.
        """
        sector_articles = [
            a for a in articles 
            if sector in a.get("sectors", [])
        ]
        
        # Sort by recency
        sector_articles.sort(
            key=lambda x: x.get("scraped_at", ""),
            reverse=True
        )
        
        text_samples = []
        for article in sector_articles[:max_articles]:
            title = article.get("title", "")
            text = article.get("text", "")
            
            # Combine title + body, take first N words
            full_text = f"{title}. {text}"
            words = full_text.split()[:max_words_per_article]
            sample = " ".join(words)
            
            if sample:
                text_samples.append(sample)
        
        return "\n\n---\n\n".join(text_samples)

    def _llm_extract_keywords_from_text(self, sector: str, text_corpus: str, target_count: int = 10) -> list:
        """Use LLM to extract keywords directly from article text."""
        if not text_corpus.strip():
            return []
        
        prompt = f"""You are analyzing Sri Lankan business news articles about the {sector} sector.

TASK: Extract the {target_count} most important and specific KEYWORDS or PHRASES that represent key topics, trends, and issues in this sector.

RULES:
1. Extract multi-word phrases when possible (e.g., "renewable energy", "port expansion")
2. Focus on sector-specific terminology
3. Avoid generic words like "growth", "government", "technology", "officials"
4. Avoid UI artifacts like "click here", "read more", "subscribe", "mobile apps"
5. Choose terms that business analysts would find valuable
6. Prioritize economic/business terms over general news terms

SECTOR: {sector}

ARTICLE EXCERPTS:
{text_corpus[:4000]}

RESPOND WITH: A comma-separated list of EXACTLY {target_count} keywords/phrases. No explanations, no numbering.

FORMAT: keyword1, keyword2, keyword3"""

        response = self._call_ollama(prompt, temperature=0.2)
        
        if not response:
            return []
        
        # Parse response
        keywords = [
            kw.strip() 
            for kw in response.replace("\n", ",").split(",") 
            if kw.strip()
        ]
        
        # Clean numbering if LLM added it
        keywords = [kw.split(". ", 1)[-1].strip() for kw in keywords]
        
        # Final validation
        valid_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            # Skip if it's garbage
            if kw_lower in ENGLISH_STOPWORDS or kw_lower in UI_ARTIFACTS or kw_lower in GENERIC_BUZZWORDS:
                continue
            if len(kw) >= 3:
                valid_keywords.append(kw)
            if len(valid_keywords) >= target_count:
                break
        
        return valid_keywords[:target_count]

    def _llm_extract_organizations_from_text(self, sector: str, text_corpus: str, target_count: int = 10) -> list:
        """Use LLM to extract key organizations directly from article text."""
        if not text_corpus.strip():
            return []
        
        prompt = f"""You are analyzing Sri Lankan business news articles about the {sector} sector.

TASK: Extract the {target_count} most important ORGANIZATIONS (companies, agencies, institutions) that are key players in this sector.

RULES:
1. Extract full organization names (e.g., "Central Bank of Sri Lanka", "John Keells Holdings")
2. Include companies, government agencies, banks, regulatory bodies, industry associations
3. Exclude news media organizations like newspapers and TV channels
4. Avoid generic terms like "Government", "Bank", "Committee", "Group"
5. Focus on organizations with actual business operations or regulatory power
6. Prefer Sri Lankan organizations unless international ones are explicitly mentioned as key players

SECTOR: {sector}

ARTICLE EXCERPTS:
{text_corpus[:4000]}

RESPOND WITH: A comma-separated list of EXACTLY {target_count} organization names. No explanations, no numbering.

FORMAT: Organization1, Organization2, Organization3"""

        response = self._call_ollama(prompt, temperature=0.2)
        
        if not response:
            return []
        
        # Parse response
        orgs = [
            org.strip() 
            for org in response.replace("\n", ",").split(",") 
            if org.strip()
        ]
        
        # Clean numbering
        orgs = [org.split(". ", 1)[-1].strip() for org in orgs]
        
        # Validation
        valid_orgs = []
        for org in orgs:
            # Skip banned/generic orgs
            if org in BANNED_ORGANIZATIONS or org in BAD_ORG_NAMES:
                continue
            if self._is_publisher(org):
                continue
            if len(org) >= 3:
                valid_orgs.append(org)
            if len(valid_orgs) >= target_count:
                break
        
        return valid_orgs[:target_count]

    # =================================================================
    # HELPER: Publisher detection
    # =================================================================
    def _is_publisher(self, org: str) -> bool:
        """Filter news publishers."""
        if not org:
            return False

        o = org.lower().strip()

        media_indicators = [
            "times", "mirror", "news", "newspapers", "newspaper",
            "sunday", "daily", "lmd", "ft.lk", "ft.", "dailymirror",
            "sundaytimes", "the morning", "morningweb", "morning lk",
            "wnl", "wijeya", "publishers", "publishing",
            "macroentertainment", "print ads", "advertising", ".lk",
            "media", "press", "gazette", "observer", "herald",
            "journalist", "editorial", "taj samudra",
        ]

        return any(indicator in o for indicator in media_indicators)

    # =================================================================
    # HELPER: Keyword cleaning (for national indicators)
    # =================================================================
    def _clean_topic(self, text: str) -> str | None:
        """Clean keyword for national-level indicators."""
        if not text:
            return None

        t = " ".join(text.split()).lower().strip()

        if len(t) < MIN_TOPIC_LENGTH:
            return None

        if t in NOISY_TOPICS or t in ENGLISH_STOPWORDS or t in GENERIC_BUZZWORDS or t in UI_ARTIFACTS:
            return None

        if any(frag in t for frag in BAD_KEYWORD_FRAGMENTS):
            return None

        for pattern in GARBAGE_PATTERNS:
            if re.search(pattern, t, re.IGNORECASE):
                return None

        if t.replace(" ", "").isdigit():
            return None

        if len(set(t.replace(" ", ""))) <= 2:
            return None

        return t

    def _clean_organization(self, org: str) -> str | None:
        """Clean organization names."""
        if not org or len(org) < 2:
            return None

        org = org.strip()

        if org in BANNED_ORGANIZATIONS or org in BAD_ORG_NAMES:
            return None

        if self._is_publisher(org):
            return None

        if len(org.split()) == 1 and org.lower() in {"government", "parliament", "cabinet", "treasury", "group", "groups", "state", "bank"}:
            return None

        return org

    # =================================================================
    # HELPER: Build national top topics
    # =================================================================
    def build_top_topics(self, max_topics: int = 10):
        """Aggregate top topics across all articles."""
        articles = self.db.all()

        topic_counts = Counter()
        topic_sectors = defaultdict(lambda: Counter())

        for article in articles:
            keywords = article.get("keywords", [])
            sectors = article.get("sectors", [])

            for kw in keywords:
                kw_clean = self._clean_topic(kw)
                if not kw_clean:
                    continue

                topic_counts[kw_clean] += 1
                for s in sectors:
                    topic_sectors[kw_clean][s] += 1

        top_topics = []
        for topic, count in topic_counts.most_common(max_topics):
            sector_counts = topic_sectors[topic]
            top_sectors = [
                {"sector": s, "count": c}
                for s, c in sector_counts.most_common(3)
            ]
            top_topics.append({
                "topic": topic,
                "count": count,
                "top_sectors": top_sectors,
            })

        return top_topics

    # =================================================================
    # 1) NATIONAL ACTIVITY INDICATORS
    # =================================================================
    def build_national_indicators(self):
        """Build national-level activity indicators."""
        articles = self.db.all()

        sentiments = [a.get("sentiment_score", 0) for a in articles if "sentiment_score" in a]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        sentiment_dist = defaultdict(int)
        for article in articles:
            sentiment_dist[article.get("sentiment_label", "neutral")] += 1

        sector_counts = defaultdict(int)
        for article in articles:
            for sector in article.get("sectors", []):
                sector_counts[sector] += 1
        top_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        org_counts = defaultdict(int)
        for article in articles:
            for org in article.get("entities", {}).get("ORG", []):
                cleaned = self._clean_organization(org)
                if cleaned:
                    org_counts[cleaned] += 1
        top_orgs = sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        location_counts = defaultdict(int)
        for article in articles:
            entities = article.get("entities", {})
            for loc in entities.get("GPE", []) + entities.get("LOC", []):
                location_counts[loc] += 1
        top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        top_topics = self.build_top_topics(max_topics=10)

        return {
            "overall_sentiment": round(avg_sentiment, 3),
            "sentiment_distribution": dict(sentiment_dist),
            "total_articles": len(articles),
            "positive_articles": sentiment_dist.get("positive", 0),
            "negative_articles": sentiment_dist.get("negative", 0),
            "neutral_articles": sentiment_dist.get("neutral", 0),
            "top_sectors": [{"sector": s, "count": c} for s, c in top_sectors],
            "top_organizations": [{"org": o, "count": c} for o, c in top_orgs],
            "top_locations": [{"location": l, "count": c} for l, c in top_locations],
            "top_topics": top_topics,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # =================================================================
    # 2) LLM-ENHANCED SECTOR INDICATORS (FROM TEXT)
    # =================================================================
    def build_sector_indicators(self, use_llm: bool = True):
        """
        Build sector indicators using LLM to directly extract from article text.
        """
        articles = self.db.all()

        sector_data = defaultdict(
            lambda: {
                "article_count": 0,
                "sentiment_scores": [],
            }
        )

        # First pass: collect basic stats
        for article in articles:
            sectors = article.get("sectors", [])
            sentiment = article.get("sentiment_score", 0)

            for sector in sectors:
                sdata = sector_data[sector]
                sdata["article_count"] += 1
                sdata["sentiment_scores"].append(sentiment)

        sector_indicators = {}

        for sector, data in sector_data.items():
            print(f"\nProcessing sector: {sector}")
            
            scores = data["sentiment_scores"]
            avg_sentiment = sum(scores) / len(scores) if scores else 0.0

            if avg_sentiment > 0.1:
                sentiment_label = "positive"
            elif avg_sentiment < -0.1:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"

            # Extract text corpus from sector articles
            if use_llm and data["article_count"] > 0:
                print(f"  Extracting article text for LLM analysis...")
                text_corpus = self._extract_sector_text(sector, articles, max_words_per_article=500, max_articles=15)
                
                print(f"  LLM extracting keywords from {len(text_corpus)} chars of text...")
                keywords = self._llm_extract_keywords_from_text(sector, text_corpus, target_count=10)
                
                print(f"  LLM extracting organizations from text...")
                orgs = self._llm_extract_organizations_from_text(sector, text_corpus, target_count=10)
                
                # Format without counts (LLM extracted, not counted)
                top_keywords = [{"keyword": kw} for kw in keywords]
                top_orgs = [{"org": org} for org in orgs]
            else:
                top_keywords = []
                top_orgs = []

            sector_indicators[sector] = {
                "article_count": data["article_count"],
                "avg_sentiment": round(avg_sentiment, 3),
                "sentiment_label": sentiment_label,
                "top_keywords": top_keywords,
                "top_organizations": top_orgs,
            }

        return sector_indicators

    # =================================================================
    # 3) RISK & OPPORTUNITY INSIGHTS
    # =================================================================
    def detect_risks_opportunities(self):
        """Detect risks and opportunities using sentiment analysis."""
        articles = self.db.all()

        risks = []
        opportunities = []

        for article in articles:
            sentiment = article.get("sentiment_score", 0)
            sectors = article.get("sectors", [])
            title = article.get("title", "")
            url = article.get("url", "")

            if sentiment < -0.3:
                risks.append({
                    "title": title,
                    "url": url,
                    "sectors": sectors,
                    "sentiment": round(sentiment, 3),
                    "severity": "high" if sentiment < -0.5 else "medium",
                    "type": "negative_sentiment",
                })

            if sentiment > 0.3:
                opportunities.append({
                    "title": title,
                    "url": url,
                    "sectors": sectors,
                    "sentiment": round(sentiment, 3),
                    "impact": "high" if sentiment > 0.5 else "medium",
                    "type": "positive_sentiment",
                })

        risks.sort(key=lambda x: x["sentiment"])
        opportunities.sort(key=lambda x: x["sentiment"], reverse=True)

        return {
            "risks": risks[:10],
            "opportunities": opportunities[:10],
            "total_risks": len(risks),
            "total_opportunities": len(opportunities),
            "top_risks": risks[:5],
            "top_opportunities": opportunities[:5],
        }

    def build_risk_opportunity_insights(self):
        """Alias for detect_risks_opportunities() for consistency with build_indicators.py."""
        return self.detect_risks_opportunities()

    # =================================================================
    # SAVE ALL INDICATORS
    # =================================================================
    def save_indicators(self, output_path: str = None, national=None, sectors=None, insights=None):
        """Generate and save all indicators to JSON files."""
        import os
        
        # Use self.output_dir if output_path not provided
        if output_path is None:
            output_path = self.output_dir
        
        os.makedirs(output_path, exist_ok=True)

        if national is None:
            national = self.build_national_indicators()
        if sectors is None:
            sectors = self.build_sector_indicators()
        if insights is None:
            insights = self.detect_risks_opportunities()

        with open(f"{output_path}/national_indicators.json", "w") as f:
            json.dump(national, f, indent=2)
        with open(f"{output_path}/sector_indicators.json", "w") as f:
            json.dump(sectors, f, indent=2)
        with open(f"{output_path}/risk_opportunity_insights.json", "w") as f:
            json.dump(insights, f, indent=2)

        return {"national": national, "sectors": sectors, "insights": insights}
