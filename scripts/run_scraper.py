import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.db_manager import DatabaseManager
from src.scrapers.news_scraper import NewsScraper

if __name__ == "__main__":
    print("Initializing database...")
    db = DatabaseManager("data/raw/articles.json")
    
    print("Starting news scraper...")
    scraper = NewsScraper(db)
    scraper.run_all()
    
    print(f"\nTotal articles scraped: {len(db.get_all_articles())}")
    db.close()
