from datetime import datetime
from collections import defaultdict, Counter
from tinydb import TinyDB
import json


# ---------------------------------------------------------------------
# Global noise filters
# ---------------------------------------------------------------------

# Phrases that should never appear as "topics" or sector keywords
NOISY_TOPICS = {
    "marketing manager  sales",
    "marketing manager sales",
    "this website",
    "the morning",
    "the sunday times",
    "sport",
    "what",
    "part",
    "who",
    ".",
    "ceo",
}

# Single very-short tokens that are rarely meaningful as topics
MIN_TOPIC_LENGTH = 3  # characters


class IndicatorBuilder:
    def __init__(self, db_path: str = "data/raw/articles.json"):
        self.db = TinyDB(db_path)

    # -----------------------------------------------------------------
    # Helper: filter out publishers / news brands from ORG entities
    # -----------------------------------------------------------------
    def _is_publisher(self, org: str) -> bool:
        """
        Heuristic filter to remove news publishers and media brands
        from organization lists, so 'Key Players' show businesses
        rather than newspapers/websites.
        """
        if not org:
            return False

        o = org.lower().strip()

        bad_fragments = [
            "times",          # sunday times, daily times, etc.
            "mirror",         # daily mirror
            "news",
            "newspapers",
            "sunday",
            "daily",
            "lmd",
            "ft.lk",
            "ft.",
            "dailymirror",
            "sundaytimes",
            "the morning",
            "morningweb",
            "chameendwijeya",
            "wnl",            # Wijeya Newspapers Ltd / WNL
            "publishers",
            "macroentertainment",
            "print ads",
            "advertising",
            ".lk",
        ]

        return any(fragment in o for fragment in bad_fragments)

    # -----------------------------------------------------------------
    # Helper: normalize and filter topic/keyword text
    # -----------------------------------------------------------------
    def _clean_topic(self, text: str) -> str | None:
        """
        Normalize a topic/keyword string and filter out noise.
        Returns cleaned string or None if it should be dropped.
        """
        if not text:
            return None

        t = " ".join(text.split()).lower().strip()  # collapse spaces

        if len(t) < MIN_TOPIC_LENGTH:
            return None

        if t in NOISY_TOPICS:
            return None

        return t

    # -----------------------------------------------------------------
    # Helper: Top topics (national level)
    # -----------------------------------------------------------------
    def build_top_topics(self, max_topics: int = 10):
        """
        Aggregate top topics across all articles using NLP keywords.

        Returns a list:
        [
            {
                "topic": "<phrase>",
                "count": <int>,
                "top_sectors": [
                    {"sector": "tourism", "count": 12},
                    ...
                ]
            },
            ...
        ]
        """
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
            top_topics.append(
                {
                    "topic": topic,
                    "count": count,
                    "top_sectors": top_sectors,
                }
            )

        return top_topics

    # -----------------------------------------------------------------
    # 1) National Activity Indicators
    # -----------------------------------------------------------------
    def build_national_indicators(self):
        """Build National Activity Indicators."""
        articles = self.db.all()

        # Overall sentiment
        sentiments = [
            a.get("sentiment_score", 0)
            for a in articles
            if "sentiment_score" in a
        ]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Sentiment distribution
        sentiment_dist = defaultdict(int)
        for article in articles:
            label = article.get("sentiment_label", "neutral")
            sentiment_dist[label] += 1

        # Top sectors mentioned
        sector_counts = defaultdict(int)
        for article in articles:
            sectors = article.get("sectors", [])
            for sector in sectors:
                sector_counts[sector] += 1
        top_sectors = sorted(
            sector_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Top organizations mentioned (exclude publishers)
        org_counts = defaultdict(int)
        for article in articles:
            entities = article.get("entities", {})
            orgs = entities.get("ORG", [])
            for org in orgs:
                if not self._is_publisher(org):
                    org_counts[org] += 1
        top_orgs = sorted(
            org_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Top locations mentioned
        location_counts = defaultdict(int)
        for article in articles:
            entities = article.get("entities", {})
            locs = entities.get("GPE", []) + entities.get("LOC", [])
            for loc in locs:
                location_counts[loc] += 1
        top_locations = sorted(
            location_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Top topics across all articles
        top_topics = self.build_top_topics(max_topics=10)

        return {
            "overall_sentiment": round(avg_sentiment, 3),
            "sentiment_distribution": dict(sentiment_dist),
            "total_articles": len(articles),
            "top_sectors": [
                {"sector": s, "count": c} for s, c in top_sectors
            ],
            "top_organizations": [
                {"org": o, "count": c} for o, c in top_orgs
            ],
            "top_locations": [
                {"location": l, "count": c} for l, c in top_locations
            ],
            "top_topics": top_topics,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # -----------------------------------------------------------------
    # 2) Operational Environment Indicators (per sector)
    # -----------------------------------------------------------------
    def build_sector_indicators(self):
        """Build sector-specific indicators."""
        articles = self.db.all()

        sector_data = defaultdict(
            lambda: {
                "article_count": 0,
                "sentiment_scores": [],
                "top_keywords": defaultdict(int),
                "top_orgs": defaultdict(int),
            }
        )

        for article in articles:
            sectors = article.get("sectors", [])
            sentiment = article.get("sentiment_score", 0)
            keywords = article.get("keywords", [])
            orgs_raw = article.get("entities", {}).get("ORG", [])

            # Filter out publishers for key players
            orgs = [o for o in orgs_raw if not self._is_publisher(o)]

            for sector in sectors:
                sector_data[sector]["article_count"] += 1
                sector_data[sector]["sentiment_scores"].append(sentiment)

                # Top 5 cleaned keywords per article
                for keyword in keywords[:5]:
                    kw_clean = self._clean_topic(keyword)
                    if not kw_clean:
                        continue
                    sector_data[sector]["top_keywords"][kw_clean] += 1

                for org in orgs:
                    sector_data[sector]["top_orgs"][org] += 1

        # Calculate averages and format
        sector_indicators = {}

        for sector, data in sector_data.items():
            scores = data["sentiment_scores"]
            avg_sentiment = sum(scores) / len(scores) if scores else 0

            if avg_sentiment > 0.1:
                sentiment_label = "positive"
            elif avg_sentiment < -0.1:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"

            top_keywords = sorted(
                data["top_keywords"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]

            top_orgs = sorted(
                data["top_orgs"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]

            sector_indicators[sector] = {
                "article_count": data["article_count"],
                "avg_sentiment": round(avg_sentiment, 3),
                "sentiment_label": sentiment_label,
                "top_keywords": [
                    {"keyword": k, "count": c} for k, c in top_keywords
                ],
                "top_organizations": [
                    {"org": o, "count": c} for o, c in top_orgs
                ],
            }

        return sector_indicators

    # -----------------------------------------------------------------
    # 3) Risk & Opportunity Insights
    # -----------------------------------------------------------------
    def detect_risks_opportunities(self):
        """Detect risks and opportunities at article level."""
        articles = self.db.all()

        risks = []
        opportunities = []

        for article in articles:
            sentiment = article.get("sentiment_score", 0)
            sectors = article.get("sectors", [])
            title = article.get("title", "")
            url = article.get("url", "")

            # Risk: strong negative sentiment
            if sentiment < -0.3:
                risks.append(
                    {
                        "title": title,
                        "url": url,
                        "sectors": sectors,
                        "sentiment": round(sentiment, 3),
                        "severity": "high"
                        if sentiment < -0.5
                        else "medium",
                        "type": "negative_sentiment",
                    }
                )

            # Opportunity: strong positive sentiment
            if sentiment > 0.3:
                opportunities.append(
                    {
                        "title": title,
                        "url": url,
                        "sectors": sectors,
                        "sentiment": round(sentiment, 3),
                        "impact": "high"
                        if sentiment > 0.5
                        else "medium",
                        "type": "positive_sentiment",
                    }
                )

        # Sort by severity/impact
        risks.sort(key=lambda x: x["sentiment"])  # most negative first
        opportunities.sort(
            key=lambda x: x["sentiment"], reverse=True
        )  # most positive first

        return {
            "risks": risks[:10],               # Top 10 risks
            "opportunities": opportunities[:10],  # Top 10 opportunities
            "total_risks": len(risks),
            "total_opportunities": len(opportunities),
        }

    # -----------------------------------------------------------------
    # Save all indicators
    # -----------------------------------------------------------------
    def save_indicators(
        self,
        output_path: str = "data/indicators/",
        national: dict | None = None,
        sectors: dict | None = None,
        insights: dict | None = None,
    ):
        """
        Generate (if needed) and save all indicators.

        Allows passing precomputed national / sector / insights dicts
        so the values printed in the CLI match exactly what is saved.
        """
        import os

        os.makedirs(output_path, exist_ok=True)

        if national is None:
            national = self.build_national_indicators()
        if sectors is None:
            sectors = self.build_sector_indicators()
        if insights is None:
            insights = self.detect_risks_opportunities()

        with open(f"{output_path}national_indicators.json", "w") as f:
            json.dump(national, f, indent=2)

        with open(f"{output_path}sector_indicators.json", "w") as f:
            json.dump(sectors, f, indent=2)

        with open(
            f"{output_path}risk_opportunity_insights.json", "w"
        ) as f:
            json.dump(insights, f, indent=2)

        return {
            "national": national,
            "sectors": sectors,
            "insights": insights,
        }
