import os
from tinydb import TinyDB, Query
from datetime import datetime
import hashlib


class DatabaseManager:
    def __init__(self, db_path="data/raw/articles.json"):
        self.db_path = db_path
        self.db = None
        self._init_storage()
    
    def _init_storage(self):
        """Initialize database without deleting old data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.db = TinyDB(self.db_path)
    
    def _generate_content_hash(self, text):
        """Generate hash of article content to detect changes"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def save_article(self, source, section, title, url, full_text):
        """Save or update article in database only if content changed"""
        if not url or not title:
            return False
        
        Article = Query()
        content_hash = self._generate_content_hash(full_text)
        
        # Check if article exists
        existing = self.db.search(Article.url == url)
        
        if existing:
            # Article exists - check if content changed
            old_hash = existing[0].get("content_hash", "")
            if old_hash == content_hash:
                # Content unchanged, skip update
                return False
            
            # Content changed - update with new data
            self.db.update(
                {
                    "source": source,
                    "section": section,
                    "title": title,
                    "url": url,
                    "text": full_text,
                    "content_hash": content_hash,
                    "updated_at": datetime.utcnow().isoformat(),
                    "update_count": existing[0].get("update_count", 0) + 1
                },
                Article.url == url
            )
            print(f"  → Updated (change detected)")
            return True
        else:
            # New article - insert
            self.db.insert(
                {
                    "source": source,
                    "section": section,
                    "title": title,
                    "url": url,
                    "text": full_text,
                    "content_hash": content_hash,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "update_count": 0
                }
            )
            return True
    
    def get_all_articles(self):
        """Get all articles from database"""
        return self.db.all()
    
    def get_recent_articles(self, hours=6):
        """Get articles scraped/updated in last N hours"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        Article = Query()
        recent = []
        for article in self.db.all():
            updated_at = article.get("updated_at", article.get("scraped_at"))
            if updated_at:
                try:
                    article_time = datetime.fromisoformat(updated_at)
                    if article_time >= cutoff:
                        recent.append(article)
                except ValueError:
                    pass
        return recent
    
    def get_stats(self):
        """Get database statistics"""
        articles = self.db.all()
        return {
            "total_articles": len(articles),
            "sources": len(set(a.get("source") for a in articles)),
            "updated_articles": len([a for a in articles if a.get("update_count", 0) > 0])
        }
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
