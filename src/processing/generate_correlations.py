import os
import json
from collections import defaultdict
from itertools import combinations

import numpy as np
from tinydb import TinyDB


DB_PATH = "data/raw/articles.json"
INDICATORS_PATH = "data/indicators/"


def generate_super_sector_correlations(
    min_co_mentions_base: int = 2,
    min_global_fraction: float = 0.02,
    min_jaccard: float = 0.05,
):
    """
    Build sector correlations from raw articles using several signals:

    - co-mention frequency (how often two sectors appear together)
    - relative frequency (pair count vs total articles where either appears)
    - Jaccard similarity (pair_count / union_mentions)
    - sentiment similarity (optional; can be extended)

    Pairs must pass dynamic thresholds so we avoid random one-off co-mentions.
    """

    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found")
        return

    db = TinyDB(DB_PATH)
    articles = db.all()
    db.close()

    if not articles:
        print("No articles found in DB")
        _write_empty()
        return

    # Track how often each sector appears and in which articles
    sector_article_sets = defaultdict(set)   # sector -> set(article_idx)
    pair_counts = defaultdict(int)          # (s1,s2) -> co-mentions
    pair_sentiments = defaultdict(list)     # (s1,s2) -> list of sentiments

    for idx, art in enumerate(articles):
        sectors = list({s.lower() for s in art.get("sectors", [])})
        if len(sectors) < 2:
            continue

        sentiment = art.get("sentiment_score", 0.0)

        for s in sectors:
            sector_article_sets[s].add(idx)

        for s1, s2 in combinations(sorted(sectors), 2):
            key = (s1, s2)
            pair_counts[key] += 1
            pair_sentiments[key].append(sentiment)

    if not pair_counts:
        print("No sector pairs found in same article")
        _write_empty()
        return

    total_articles = len(articles)

    # Dynamic thresholds based on data
    max_pair_count = max(pair_counts.values())
    dynamic_min_co_mentions = max(min_co_mentions_base, int(0.01 * max_pair_count) or 1)

    print(f"Total articles: {total_articles}")
    print(f"Unique sectors: {len(sector_article_sets)}")
    print(f"Raw sector pairs: {len(pair_counts)}")
    print(f"Dynamic min co-mentions: {dynamic_min_co_mentions}")

    correlations = []

    for (s1, s2), pair_count in pair_counts.items():
        if pair_count < dynamic_min_co_mentions:
            continue

        # Article counts for each sector
        a1 = len(sector_article_sets[s1])
        a2 = len(sector_article_sets[s2])

        # Jaccard similarity of article sets
        union_size = len(sector_article_sets[s1] | sector_article_sets[s2])
        jaccard = pair_count / union_size if union_size > 0 else 0.0

        # Global fraction: how often this pair appears compared to all articles
        global_fraction = pair_count / total_articles

        if jaccard < min_jaccard:
            continue
        if global_fraction < min_global_fraction:
            continue

        avg_sent = float(np.mean(pair_sentiments[(s1, s2)])) if pair_sentiments[(s1, s2)] else 0.0

        # Combined score favouring high co-mentions and tight relationship
        score = (
            0.5 * (pair_count / max_pair_count)
            + 0.3 * jaccard
            + 0.2 * global_fraction
        )

        if pair_count >= 8 and jaccard >= 0.15:
            strength = "very_strong"
        elif pair_count >= 4 and jaccard >= 0.10:
            strength = "strong"
        else:
            strength = "moderate"

        correlations.append({
            "sector1": s1,
            "sector2": s2,
            "co_occurrence_count": int(pair_count),
            "sector1_article_count": a1,
            "sector2_article_count": a2,
            "jaccard": round(jaccard, 3),
            "global_fraction": round(global_fraction, 3),
            "avg_sentiment": round(avg_sent, 3),
            "score": round(score, 3),
            "correlation_strength": strength,
        })

    correlations.sort(key=lambda x: x["score"], reverse=True)

    output = {
        "top_correlations": correlations[:20],
        "total_correlations": len(correlations),
    }

    os.makedirs(INDICATORS_PATH, exist_ok=True)
    out_path = os.path.join(INDICATORS_PATH, "sector_correlations.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(correlations)} sector correlation pairs")
    if correlations:
        top = correlations[0]
        print(
            f"Top pair: {top['sector1']} <-> {top['sector2']} | "
            f"count={top['co_occurrence_count']}, "
            f"jaccard={top['jaccard']}, "
            f"strength={top['correlation_strength']}"
        )
    else:
        print("No pairs passed the significance thresholds")


def _write_empty():
    os.makedirs(INDICATORS_PATH, exist_ok=True)
    out_path = os.path.join(INDICATORS_PATH, "sector_correlations.json")
    with open(out_path, "w") as f:
        json.dump({"top_correlations": [], "total_correlations": 0}, f, indent=2)


if __name__ == "__main__":
    generate_super_sector_correlations()
