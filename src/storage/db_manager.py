import os
from tinydb import TinyDB, Query
from datetime import datetime, date

class DatabaseManager:
    def __init__(self, db_path="data/raw/articles.json"):
        self.db_path = db_path
        self.db = None
        self._init_storage()
    
    def _init_storage(self):
        """Initialize database and clean old data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.db = TinyDB(self.db_path)
        
        # Clean data from previous days
        all_docs = self.db.all()
        if all_docs:
            first = all_docs[0]
            scraped_at = first.get("scraped_at")
            if scraped_at:
                try:
                    old_date = datetime.fromisoformat(scraped_at).date()
                except ValueError:
                    old_date = None
            else:
                old_date = None
            
            if old_date is None or old_date != date.today():
                self.db.truncate()
    
    def save_article(self, source, section, title, url, full_text):
        """Save or update article in database"""
        if not url or not title:
            return False
        
        Article = Query()
        self.db.upsert(
            {
                "source": source,
                "section": section,
                "title": title,
                "url": url,
                "text": full_text,
                "scraped_at": datetime.utcnow().isoformat()
            },
            Article.url == url
        )
        return True
    
    def get_all_articles(self):
        """Get all articles from database"""
        return self.db.all()
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
