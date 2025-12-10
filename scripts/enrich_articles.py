import sys
import os
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.db_manager import DatabaseManager
from src.processing.nlp_processor import NLPProcessor
from tinydb import Query


def run_enrichment(db_path: str = "data/raw/articles.json"):
    """
    Run NLP enrichment on all articles in the TinyDB database.

    Adds sentiment, entities, keywords, sectors, language, word_count, enriched_at.
    """
    print(f"\n{'=' * 60}")
    print(f"Starting NLP enrichment at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    print("Loading database...")
    db = DatabaseManager(db_path)

    try:
        print("Initializing NLP processor...")
        nlp = NLPProcessor()

        articles = db.get_all_articles()
        total = len(articles)
        print(f"Found {total} articles to enrich\n")

        if total == 0:
            print("No articles found! Run the scraper first.")
            print(f"{'=' * 60}\n")
            return {"enriched": 0, "failed": 0}

        enriched_count = 0
        failed_count = 0

        for i, article in enumerate(articles, 1):
            try:
                title = article.get("title") or "Untitled"
                text = article.get("text") or ""
                title_short = title[:50]

                print(f"[{i}/{total}] {title_short}...")

                # Run NLP enrichment
                enriched = nlp.enrich_article(title, text)

                # Prepare update document
                update_doc = {
                    "text_cleaned": enriched["text_cleaned"],
                    "sentiment_score": enriched["sentiment_score"],
                    "sentiment_label": enriched["sentiment_label"],
                    "entities": enriched["entities"],
                    "keywords": enriched["keywords"],
                    "sectors": enriched["sectors"],
                    "language": enriched["language"],
                    "word_count": enriched["word_count"],
                    "enriched_at": datetime.utcnow().isoformat(),
                }

                # Update article with enriched data
                Article = Query()
                db.db.update(
                    update_doc,
                    Article.url == article["url"]
                )

                # Debug info
                print(f"  Sentiment: {enriched['sentiment_label']} ({enriched['sentiment_score']})")
                print(f"  Sectors: {', '.join(enriched['sectors'][:3])}")
                print(
                    f"  Entities: {len(enriched['entities']['ORG'])} orgs, "
                    f"{len(enriched['entities']['PERSON'])} people\n"
                )

                enriched_count += 1

            except Exception as e:
                print(f"  Error enriching article: {e}\n")
                failed_count += 1

        print(f"{'=' * 60}")
        print(f"Enrichment completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Successfully enriched: {enriched_count}/{total}")
        print(f"Failed: {failed_count}")
        print(f"{'=' * 60}\n")

        return {"enriched": enriched_count, "failed": failed_count}

    finally:
        db.close()


if __name__ == "__main__":
    run_enrichment()
