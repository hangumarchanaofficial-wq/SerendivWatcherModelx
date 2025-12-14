import os
import sys
import chromadb
from tinydb import TinyDB
from sentence_transformers import SentenceTransformer

# Setup paths relative to this script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "articles.json")
VECTOR_DB_PATH = os.path.join(PROJECT_ROOT, "data", "vector_db")

def build_database():
    print(f"\n{'='*60}")
    print("Building Vector Database for AI Chat")
    print(f"{'='*60}\n")

    # 1. Load Articles
    if not os.path.exists(RAW_DATA_PATH):
        print(f"Error: {RAW_DATA_PATH} not found. Run scraper first.")
        return

    db = TinyDB(RAW_DATA_PATH)
    articles = db.all()
    print(f"Loaded {len(articles)} articles from TinyDB.")

    if not articles:
        print("Database is empty. Skipping vector build.")
        return

    # 2. Load AI Model (Downloads automatically on first run)
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    # This model is small, fast, and great for semantic search
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 3. Initialize ChromaDB
    print(f"Initializing Vector DB at: {VECTOR_DB_PATH}")
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    
  
    try:
        client.delete_collection(name="serendiv_news")
        print("Deleted existing collection 'serendiv_news'.")
    except Exception:
       
        pass  
   

    collection = client.create_collection(name="serendiv_news")

    # 4. Process & Embed Articles
    print("Generating embeddings (this may take a moment)...")
    
    documents = []
    metadatas = []
    ids = []

    for i, art in enumerate(articles):
        
        text_content = art.get('text', '')[:1000]
        full_content = f"{art.get('title', '')}. {text_content}"
        
        documents.append(full_content)
        
        # Metadata is what we get BACK when we search
        metadatas.append({
            "title": art.get('title', 'No Title'),
            "source": art.get('source', 'Unknown'),
            "date": art.get('published_date', '') or art.get('scraped_at', '')
        })
        
        # ID must be unique string
        ids.append(str(i))

   
    embeddings = model.encode(documents).tolist()

    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print(f"Successfully indexed {len(documents)} articles into Vector DB.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    build_database()