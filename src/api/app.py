from flask import Flask, render_template, jsonify, request, session
import json
import os
import csv
import secrets
from pathlib import Path
import sys

# ============ FIX PYTHON PATH FOR MODULES ============
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

print(f"[PATH] Added to sys.path: {SRC_DIR}")
print(f"[PATH] Added to sys.path: {CURRENT_DIR}")
# =====================================================

import chromadb
from sentence_transformers import SentenceTransformer
from tinydb import TinyDB, Query

# LangChain imports for Ollama (Modern v1.0+ approach)
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage

# Local imports
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
app.secret_key = secrets.token_hex(16)  # Required for sessions

# Risk data paths
RISK_DIR = SRC_DIR / "Risk"
print(f"[PATH] Risk directory: {RISK_DIR}")


# ============================================================
# GLOBAL AI SETUP
# ============================================================

print("Loading AI models...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to Vector Database
chroma_client = chromadb.PersistentClient(path="E:\\serendivWatcher\\data\\vector_db")

try:
    collection = chroma_client.get_or_create_collection(name="serendiv_news")
    print("Vector DB connection successful.")
except Exception as e:
    print(f"Vector DB error: {e}")
    collection = None

# Initialize Ollama with gemma3:4b
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
print(f"[OLLAMA] Connecting to {OLLAMA_HOST}")

llm = ChatOllama(
    model="gemma3:4b",
    base_url=OLLAMA_HOST,
    temperature=0.3,
)

# Store conversation history per user session (simple dict approach)
chat_store = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_json_file(filepath):
    """Load JSON file safely"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[WARNING] File not found: {filepath}")
        return {} if 'market' in str(filepath) else []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {filepath}: {e}")
        return {} if 'market' in str(filepath) else []
    except Exception as e:
        print(f"[ERROR] Failed to load {filepath}: {e}")
        return {} if 'market' in str(filepath) else []


def load_csv_file(filepath):
    """Load CSV file and return as list of dicts"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"[WARNING] CSV file not found: {filepath}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load CSV {filepath}: {e}")
        return []


def load_indicators():
    """Load all indicator JSON files."""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


# ============================================================
# PAGE ROUTES
# ============================================================

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


@app.route('/warning-system')
def warning_system():
    """Warning and Opportunity System page"""
    return render_template('warning_system.html')


# ============================================================
# CHATBOT API WITH MEMORY (Modern LangChain v1.0+ approach)
# ============================================================

@app.route("/api/chat-with-data", methods=["POST"])
def chat_with_data():
    """
    Semantic Search Endpoint with Conversation Memory (RAG + Ollama).
    """
    data = request.json
    user_question = data.get("message", "").strip()
    
    # Create or get session ID
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(8)
        print(f"[CHAT] New session created: {session['session_id']}")
    
    session_id = session['session_id']
    
    if not user_question:
        return jsonify({"response": "Please ask a question."})
    
    # Get chat history (stored in dictionary)
    if session_id not in chat_store:
        chat_store[session_id] = []
    
    history = chat_store[session_id]
    
    # 1. GREETING CHECK
    greetings = ["hi", "hello", "hey", "good morning", "greetings"]
    clean_q = ''.join(e for e in user_question.lower() if e.isalnum() or e.isspace())
    if clean_q in greetings:
        response = "Hello! I am Serendiv AI. I have analyzed the latest news in our database. How can I help you today?"
        
        # Save to history
        history.append({"role": "user", "content": user_question})
        history.append({"role": "assistant", "content": response})
        
        return jsonify({"response": response})
    
    # 2. VECTOR SEARCH
    relevant_texts = []
    
    if collection:
        try:
            query_vector = embedding_model.encode([user_question]).tolist()
            results = collection.query(
                query_embeddings=query_vector,
                n_results=5
            )
            
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    meta = results['metadatas'][0][i]
                    snippet = f"Source: {meta['source']} ({meta['date']})\nTitle: {meta['title']}\nExcerpt: {doc[:500]}..."
                    relevant_texts.append(snippet)
        except Exception as e:
            print(f"Vector search error: {e}")
    else:
        return jsonify({"error": "Database not ready. Please check backend logs."}), 500
    
    # 3. BUILD CONVERSATION HISTORY TEXT
    history_text = ""
    if history:
        recent = history[-6:]  # Last 3 exchanges
        for msg in recent:
            role = "Human" if msg["role"] == "user" else "AI"
            history_text += f"{role}: {msg['content']}\n"
    
    # 4. CREATE CONTEXT-AWARE PROMPT
    if relevant_texts:
        context_block = "\n\n".join(relevant_texts)
        prompt = f"""You are 'Serendiv AI', a senior Business Analyst for Sri Lanka.

CONVERSATION HISTORY:
{history_text}

LATEST INTELLIGENCE:
{context_block}

USER QUESTION: {user_question}

INSTRUCTIONS:
1. Answer using the context and conversation history.
2. Synthesize information professionally and concisely.
3. Reference earlier parts of the conversation when relevant.
4. If context doesn't fully answer, say so but offer what you know.
5. Mention the positive and negative effects of making the decision

ANSWER:"""
    else:
        prompt = f"""You are 'Serendiv AI', a senior Business Analyst for Sri Lanka.

CONVERSATION HISTORY:
{history_text}

USER QUESTION: {user_question}

NOTE: No specific news articles matched this query in the database.

INSTRUCTIONS:
1. Answer general business questions using your knowledge.
2. For specific recent events, apologize and explain they're not in the database.
3. Remember and reference previous conversation context.
4. Do NOT make up fake news.

ANSWER:"""
    
    # 5. GET RESPONSE FROM OLLAMA
    try:
        response = llm.invoke(prompt)
        answer = response.content.strip()
        
        # Save to history
        history.append({"role": "user", "content": user_question})
        history.append({"role": "assistant", "content": answer})
        
        print(f"[CHAT] Session {session_id}: Q: {user_question[:50]}... | A: {answer[:50]}...")
        
        return jsonify({"response": answer})
    
    except Exception as e:
        print(f"Chat Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to connect to Ollama: {str(e)}"}), 500


@app.route("/api/get-chat-history", methods=["GET"])
def get_chat_history_api():
    """Get full conversation history for current session"""
    if 'session_id' not in session:
        return jsonify({"history": []})
    
    session_id = session['session_id']
    history = chat_store.get(session_id, [])
    
    return jsonify({"history": history})


@app.route("/api/clear-chat-history", methods=["POST"])
def clear_chat_history():
    """Clear conversation history for current session"""
    if 'session_id' in session:
        session_id = session['session_id']
        if session_id in chat_store:
            chat_store[session_id] = []
            print(f"[CHAT] Cleared history for session {session_id}")
    
    return jsonify({"status": "Chat history cleared"})


# ============================================================
# INDICATOR APIs
# ============================================================

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
    print(f"[APP] /api/article/<id>/summary called with id={article_id}")
    article = load_article_by_id(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    
    summary = summarize_single_article(article)
    return jsonify(summary)


@app.route('/api/title-insights', methods=['GET'])
def get_title_insights_api():
    title = request.args.get('title', '')
    sector = request.args.get('sector', '')
    
    if not title:
        return jsonify({"error": "Title required"}), 400
    
    try:
        insights = generate_title_insights(title, sector if sector else None)
        return jsonify({
            "insights": insights,
            "title": title,
            "sector": sector
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "insights": f"Analysis failed: {str(e)}"
        }), 500


# ============================================================
# RISK/WARNING SYSTEM APIs
# ============================================================

@app.route('/api/risk/routes-delay')
def get_routes_delay():
    """Get transportation routes delay data"""
    try:
        data = load_json_file(RISK_DIR / "routes_delay.json")
        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] Loading routes_delay.json: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/market-trends')
def get_market_trends():
    """Get market trends data"""
    try:
        data = load_json_file(RISK_DIR / "market_trends.json")
        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] Loading market_trends.json: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/knowledge-graph')
def get_knowledge_graph():
    """Get knowledge graph data"""
    try:
        data = load_json_file(RISK_DIR / "knowledge_graph.json")
        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] Loading knowledge_graph.json: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/local-data')
def get_local_data():
    """Get Sri Lanka local data"""
    try:
        data = load_json_file(RISK_DIR / "sl_expanded_local_data.json")
        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] Loading sl_expanded_local_data.json: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/weather-forecast')
def get_weather_forecast():
    """Get weather forecast data"""
    try:
        weather_data = load_csv_file(RISK_DIR / "sl_weather_forecast_next_week.csv")
        return jsonify(weather_data)
    except Exception as e:
        print(f"[ERROR] Loading weather forecast: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/analyze', methods=['POST'])
def analyze_risks():
    """Comprehensive risk analysis endpoint with district"""
    try:
        data = request.get_json()
        
        business_name = data.get('businessName', '')
        district = data.get('district', '')  # Changed from sector
        operations = data.get('operations', [])
        
        if not business_name or not district:
            return jsonify({'error': 'Business name and district are required'}), 400
        
        print(f"[ANALYZE] Business: {business_name}, District: {district}, Operations: {operations}")
        
        # Load data files
        routes_data = load_json_file(RISK_DIR / 'routes_delay.json')
        market_data = load_json_file(RISK_DIR / 'market_trends.json')
        knowledge_graph = load_json_file(RISK_DIR / 'knowledge_graph.json')
        weather_data = load_csv_file(RISK_DIR / 'sl_weather_forecast_next_week.csv')
        
        print(f"[DATA] Loaded - Routes: {len(routes_data)}, Market: {bool(market_data)}, KG: {len(knowledge_graph)}, Weather: {len(weather_data)}")
        
        # Initialize analyzer
        from Risk.risk_analyzer import RiskAnalyzer
        analyzer = RiskAnalyzer(routes_data, market_data, knowledge_graph, weather_data)
        
        # Perform analysis with district instead of sector
        results = analyzer.analyze(business_name, district, operations)
        
        print(f"[RESULTS] Generated {results.get('total_alerts', 0)} alerts for {district}")
        
        return jsonify(results)
        
    except Exception as e:
        print(f"[ERROR] Risk analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500


# ============================================================
# DEBUG ENDPOINTS
# ============================================================

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


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Flask app starting with Ollama gemma3:4b + Memory")
    print("=" * 60)
    
    debug_print_all_articles()
    
    print("\n" + "=" * 60)
    print("Starting Flask server on http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    
    app.run(debug=True, port=5000)
