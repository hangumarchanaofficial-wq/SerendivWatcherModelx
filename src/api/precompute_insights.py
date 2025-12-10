# scripts/precompute_insights.py

import os
from article_loader import load_sector_articles
from insight_generator import generate_sector_insights, save_insights_to_temp

SECTORS = [
    "finance",
    "government",
    "healthcare",
    "agriculture",
    "manufacturing",
    "energy",
    "construction",
    "tourism",
    "technology",
    "general",
]

if __name__ == "__main__":
    print("\n[PRECOMPUTE] Starting sector insights precomputation...\n")

    for sector in SECTORS:
        articles = load_sector_articles(sector, limit=10)
        if not articles:
            print(f"[PRECOMPUTE] Skipping {sector}: no articles")
            continue

        print(f"[PRECOMPUTE] Generating insights for {sector} ({len(articles)} articles)")
        insights = generate_sector_insights(sector, articles)
        save_insights_to_temp(sector, insights)

    print("\n[PRECOMPUTE] Done. All sector insights cached in data/temp/\n")
