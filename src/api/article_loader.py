import os
from tinydb import TinyDB, Query

def get_db_path():
    """Get absolute path to data/raw/articles.json"""
    project_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
    db_path = os.path.join(project_root, "data", "raw", "articles.json")
    return db_path

def load_article_by_id(article_id: str):
    """Load a single article from TinyDB by its id field."""
    db_path = get_db_path()
    db = TinyDB(db_path)
    try:
        Article = Query()
        doc = db.get(Article.id == article_id)
        return doc
    finally:
        db.close()

def load_article_by_url(url: str):
    """Load a single article from TinyDB by its URL field."""
    db_path = get_db_path()
    db = TinyDB(db_path)
    try:
        Article = Query()
        doc = db.get(Article.url == url)
        return doc
    finally:
        db.close()

def load_sector_articles(sector_name: str, limit: int = 10):
    """
    Load top N articles for a given sector from TinyDB.
    
    FILTERS:
    - Only articles with titles > 3 words
    - Sorted by sentiment_score (highest positive first)
    
    Returns list of article dicts with keys:
    - source, title, url, text, scraped_at, sectors, sentiment_score
    """
    db_path = get_db_path()
    print(f"[ARTICLE_LOADER] Loading from: {db_path}")
    db = TinyDB(db_path)
    
    try:
        all_docs = db.all()
        print(f"[ARTICLE_LOADER] Total documents in DB: {len(all_docs)}")
        
        if not all_docs:
            print("[ARTICLE_LOADER] WARNING: Database is empty!")
            return []
        
        Article = Query()
        sector = sector_name.lower()
        
        def matches(sector_field):
            if isinstance(sector_field, str):
                return sector_field.lower() == sector
            if isinstance(sector_field, list):
                return sector in [s.lower() for s in sector_field]
            return False
        
        # Get all articles in this sector
        sector_articles = db.search(Article.sectors.test(matches))
        print(f"[ARTICLE_LOADER] Found {len(sector_articles)} articles for '{sector_name}'")
        
        # FILTER 1: Remove short titles (≤3 words)
        def is_valid_title(article):
            title = article.get("title", "")
            word_count = len(title.split())
            return word_count > 3
        
        filtered_articles = [a for a in sector_articles if is_valid_title(a)]
        print(f"[ARTICLE_LOADER] After filtering short titles: {len(filtered_articles)} articles")
        
        # FILTER 2: Sort by sentiment_score (highest positive first)
        filtered_articles.sort(
            key=lambda a: a.get("sentiment_score", 0.0),
            reverse=True  # Highest sentiment first
        )
        
        # Take top N
        result = filtered_articles[:limit]
        
        print(f"[ARTICLE_LOADER] Returning top {len(result)} articles with highest sentiment")
        
        # Debug: Print sentiment scores
        for i, a in enumerate(result[:3], 1):
            print(f"  {i}. {a.get('title', 'No title')[:50]}... (sentiment: {a.get('sentiment_score', 0.0)})")
        
        return result
        
    finally:
        db.close()

def debug_print_all_articles():
    """Debug helper: print all articles in DB"""
    db_path = get_db_path()
    db = TinyDB(db_path)
    try:
        all_docs = db.all()
        print(f"\n{'=' * 60}")
        print(f"DEBUG: All articles in {db_path}")
        print(f"{'=' * 60}")
        print(f"Total: {len(all_docs)}\n")
        
        for i, doc in enumerate(all_docs, 1):
            print(f"{i}. {doc.get('title', 'No title')}")
            print(f"   Source: {doc.get('source', 'N/A')}")
            print(f"   Sectors: {doc.get('sectors', [])}")
            print(f"   Sentiment: {doc.get('sentiment_score', 'N/A')}")
            print(f"   URL: {doc.get('url', 'N/A')[:80]}...")
            print()
    finally:
        db.close()

if __name__ == "__main__":
    debug_print_all_articles()
    print("\nTesting finance sector load:")
    articles = load_sector_articles("finance", limit=5)
    print(f"Loaded {len(articles)} finance articles")
