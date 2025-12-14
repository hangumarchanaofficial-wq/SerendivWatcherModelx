from flask import Flask, render_template, jsonify, request
import json
import os

import chromadb  # For Vector Search
from sentence_transformers import SentenceTransformer  # For Embeddings
from tinydb import TinyDB, Query

# LangChain imports for Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from article_loader import (
    load_sector_articles,
    debug_print_all_articles,
    get_db_path,
    load_article_by_id,
)
from insight_generator import (
    generate_sector_insights,
    save_insights_to_temp,
    load_cached_insights,
    summarize_single_article,
)
from title_insight_generator import generate_title_insights

app = Flask(__name__)

# --- GLOBAL SETUP FOR AI ---
# Load model once at startup to avoid delays on every request
print("Loading AI models...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to Vector Database
chroma_client = chromadb.PersistentClient(path="E:\\serendivWatcher\\data\\vector_db")

try:
    collection = chroma_client.get_collection(name="serendiv_news")
    print("Vector DB connection successful.")
except ValueError:
    print("Vector DB collection not found. Please run 'python scripts/build_vector_db.py' first.")
    collection = None


# ------------ Data loading (JSON indicators) ------------

def load_indicators():
    """Load all indicator JSON files."""
    project_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
    indicators_path = os.path.join(project_root, "data", "indicators")

    data = {}
    files = [
        "national_indicators.json",
        "sector_indicators.json",
        "risk_opportunity_insights.json",
        "temporal_trends.json",
        "anomalies.json",
        "sector_clusters.json",
        "sentiment_velocity.json",
        "sector_correlations.json",
    ]

    for file in files:
        filepath = os.path.join(indicators_path, file)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                key = file.replace(".json", "")
                data[key] = json.load(f)

    return data


def get_sector_block(sector_name: str):
    """Get one sector's block from sector_indicators."""
    data = load_indicators()
    sectors = data.get("sector_indicators", {})

    sector_block = (
        sectors.get(sector_name)
        or sectors.get(sector_name.capitalize())
        or sectors.get(sector_name.title())
    )

    return sector_block


# ------------ Page routes ------------

@app.route("/")
def dashboard():
    data = load_indicators()
    return render_template("dashboard.html", data=data, active_page="overview")


@app.route("/sectors")
def sectors():
    data = load_indicators()
    return render_template("sectors.html", data=data, active_page="sectors")


@app.route("/risks")
def risks():
    data = load_indicators()
    return render_template("risks.html", data=data, active_page="risks")


@app.route("/sector/<sector_name>")
def sector_detail(sector_name):
    """
    Detail page with top 10 DB articles + cached AI business insights.
    """
    print(f"\n[APP] /sector/{sector_name} route called")

    sector_block = get_sector_block(sector_name)
    articles = load_sector_articles(sector_name, limit=10)

    insights = load_cached_insights(sector_name)
    if insights is None:
        print(f"[APP] No cached insights for {sector_name}, generating...")
        insights = generate_sector_insights(sector_name, articles)
        save_insights_to_temp(sector_name, insights)
    else:
        print(f"[APP] Using cached insights for {sector_name}")

    print(f"[APP] Rendering sector_detail.html with {len(articles)} articles")

    return render_template(
        "sector_detail.html",
        sector_name=sector_name,
        sector_data=sector_block,
        articles=articles,
        insights=insights,
    )

@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")


# ------------ JSON APIs ------------

@app.route("/api/indicators")
def api_indicators():
    return jsonify(load_indicators())


@app.route("/api/sector/<sector_name>/articles")
def api_sector_articles(sector_name):
    articles = load_sector_articles(sector_name, limit=10)
    return jsonify(articles)


@app.route("/api/sector/<sector_name>/insights")
def api_sector_insights(sector_name):
    articles = load_sector_articles(sector_name, limit=10)
    insights = load_cached_insights(sector_name)

    if insights is None:
        insights = generate_sector_insights(sector_name, articles)
        save_insights_to_temp(sector_name, insights)

    return jsonify(insights)


@app.route("/api/article/<path:article_id>/summary")
def api_article_summary(article_id):
    """
    Return LLM summary for a single article (used when title is clicked).
    """
    print(f"[APP] /api/article/<id>/summary called with id={article_id}")
    article = load_article_by_id(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404

    summary = summarize_single_article(article)
    return jsonify(summary)


@app.route("/api/title-insights")
def api_title_insights():
    """
    Return LLM-powered high-level insights based ONLY on article title.
    """
    title = request.args.get("title", "").strip()
    sector = request.args.get("sector", "").strip() or None

    print(f"[APP] /api/title-insights called with title='{title}', sector='{sector}'")

    if not title:
        return jsonify({"error": "Missing title"}), 400

    insights = generate_title_insights(title, sector)
    if not insights:
        return jsonify({"error": "Failed to generate title-based insights"}), 500

    return jsonify({"insights": insights})


# Set up Gemini API (Better to use .env file for security)
os.environ["GOOGLE_API_KEY"] = "AIzaSyDogNiPuTjGiwtI1U1aOo0wKUCvttPLHrc"

# Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  
    temperature=0.3,
)


@app.route("/api/chat-with-data", methods=["POST"])
def chat_with_data():
    """
    Semantic Search Endpoint (RAG).
    Uses Vector DB to find meaning-matched articles.
    """
    data = request.json
    user_question = data.get("message", "").strip()
    
    if not user_question:
        return jsonify({"response": "Please ask a question."})
    
    # 1. IMMEDIATE GREETING CHECK (Save resources)
    greetings = ["hi", "hello", "hey", "good morning", "greetings"]
    clean_q = ''.join(e for e in user_question.lower() if e.isalnum() or e.isspace())
    if clean_q in greetings:
        return jsonify({"response": "Hello! I am Serendiv AI. I have analyzed the latest news in our database. How can I help you today?"})
    
    # 2. VECTOR SEARCH (Semantic Search)
    relevant_texts = []
    
    if collection:
        try:
            # Convert user question to numbers (vector)
            query_vector = embedding_model.encode([user_question]).tolist()
            
            # Ask ChromaDB for the 5 closest matches
            results = collection.query(
                query_embeddings=query_vector,
                n_results=5
            )
            
            # Chroma returns a list of lists. We grab the first (and only) query result.
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    meta = results['metadatas'][0][i]
                    # Format context for the LLM
                    snippet = f"Source: {meta['source']} ({meta['date']})\nTitle: {meta['title']}\nExcerpt: {doc[:500]}..."
                    relevant_texts.append(snippet)
        except Exception as e:
            print(f"Vector search error: {e}")
            pass
    else:
        return jsonify({"error": "Database not ready. Please check backend logs."}), 500
    
    # 3. PROMPT ENGINEERING
    if relevant_texts:
        context_block = "\n\n".join(relevant_texts)
        
        prompt_text = f"""You are 'Serendiv AI', a senior Business Analyst for Sri Lanka.

USER QUESTION: "{user_question}"

LATEST INTELLIGENCE (Context):
{context_block}

INSTRUCTIONS:
1. Answer the question using the context above.
2. Synthesize the information; don't just list articles.
3. If the context doesn't fully answer the question, say so, but offer what you do know from the text.
4. Be professional and concise.

ANSWER:"""
    else:
        # Fallback for general questions (No relevant news found)
        prompt_text = f"""You are 'Serendiv AI', a senior Business Analyst.

USER QUESTION: "{user_question}"

SYSTEM NOTE: No specific news articles matched this query in the database.

INSTRUCTIONS:
1. If this is a general business question (e.g. "What is inflation?"), answer it using your general knowledge.
2. If asking about a specific recent event (e.g. "Did the strike end today?"), apologize and state that you don't have that specific report in the database yet.
3. Do NOT make up fake news.

ANSWER:"""
    
    # 4. CALL GEMINI API
    try:
        # Invoke Gemini using LangChain
        response = llm.invoke(prompt_text)
        answer = response.content.strip()
        
        return jsonify({"response": answer})
    
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": "Failed to connect to AI engine."}), 500

        
@app.route("/api/debug/db")
def api_debug_db():
    db_path = get_db_path()
    db = TinyDB(db_path)
    all_docs = db.all()
    db.close()

    return jsonify({
        "db_path": db_path,
        "total_documents": len(all_docs),
        "articles": all_docs[:5],
    })


# ------------ Main ------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Flask app starting in DEBUG mode")
    print("=" * 60)

    debug_print_all_articles()

    print("\n" + "=" * 60)
    print("Starting Flask server on http://127.0.0.1:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5000)
