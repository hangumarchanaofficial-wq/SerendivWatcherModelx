import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.db_manager import DatabaseManager
from src.scrapers.news_scraper import NewsScraper
from datetime import datetime


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Starting scrape at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    db = DatabaseManager("data/raw/articles.json")

    # --- NEW: CLEANUP STEP ---
    # This removes articles older than 3 days before adding new ones.
    print("Cleaning up old articles...")
    removed_count = db.cleanup_old_articles(retention_days=3)
    print(f"Removed {removed_count} old articles.\n")
    # -------------------------
    
    # Get stats before
    stats_before = db.get_stats()
    print(f"Before: {stats_before['total_articles']} articles in database\n")
    
    # Run scraper
    scraper = NewsScraper(db)
    scraper.run_all()
    
    # Get stats after
    stats_after = db.get_stats()
    new_articles = stats_after['total_articles'] - stats_before['total_articles']
    
    print(f"\n{'='*60}")
    print(f"Scrape completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"New articles: {new_articles}")
    print(f"Total articles: {stats_after['total_articles']}")
    print(f"Updated articles: {stats_after['updated_articles']}")
    print(f"{'='*60}\n")
    
    db.close()