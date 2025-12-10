🇱🇰 SerendivWatcher | National Intelligence Platform
A Real-Time Situational Awareness System for Sri Lankan Business Strategic Decision Making.

📖 Overview
SerendivWatcher is an advanced analytics platform designed to solve the "information overload" problem for business decision-makers in Sri Lanka. Instead of manually monitoring disparate news sources, SerendivWatcher aggregates real-time signals, processes them using Natural Language Processing (NLP) and Local LLMs, and converts them into actionable business intelligence.

It provides a live "pulse" of the nation's socio-economic environment, offering early warnings on risks (strikes, shortages) and identifying emerging opportunities (investments, policy changes).

✨ Key Features
1. 📊 Unified Intelligence Dashboard
National Sentiment Score: A real-time gauge of the country's mood (Positive/Neutral/Negative) based on aggregated news analysis.

Intelligence Volume: Tracks spikes in media coverage to detect breaking events.

Risk & Opportunity Radar: Automatically flags high-impact threats (e.g., "Export drop") and growth areas (e.g., "New trade agreement").

2. 🏭 Sector-Specific Analytics
Performance Clustering: Automatically groups sectors into Trending, Neutral, or Declining based on sentiment velocity.

Drill-Down Views: Detailed pages for Finance, Agriculture, Manufacturing, Transport, and Government sectors.

3. 🤖 AI Analyst (RAG Chatbot)
"Talk to Your Data": A built-in chatbot powered by Retrieval-Augmented Generation (RAG).

Smart Context: Uses a Vector Database (ChromaDB) to find relevant articles and synthesize fact-based answers (e.g., "What are the current risks in the apparel sector?").

General Intelligence Fallback: Handles both specific news queries and general economic concept questions seamlessly.

4. ⚙️ Automated Data Pipeline
Scraper: Automated web scraping of major Sri Lankan news outlets using Playwright and BeautifulSoup.

NLP Enrichment: Entity recognition (NER), keyword extraction, and sentiment scoring using spaCy and TextBlob.

Advanced Analytics: Calculates temporal trends, anomalies (outliers), and sentiment velocity.

🛠️ Tech Stack
Backend: Python, Flask

AI & NLP: Ollama (Gemma 3:1b), Sentence-Transformers (Hugging Face), spaCy, TextBlob

Database: TinyDB (Document Store), ChromaDB (Vector Store)

Frontend: HTML5, Bootstrap 5, Chart.js (Glassmorphism Dark UI)

Automation: Custom Python Scheduler (main.py)

🚀 Installation & Setup
Prerequisites
Python 3.8+ installed.

Ollama installed on your machine (for the local LLM).

Download from ollama.com.

Pull the model: ollama pull gemma3:1b

Step 1: Clone the Repository
Bash

git clone https://github.com/yourusername/serendivwatcher.git
cd serendivwatcher
Step 2: Create Virtual Environment
Bash

# Windows
python -m venv .venv
.venv\Scripts\activate

# Mac/Linux
python3 -m venv .venv
source .venv/bin/activate
Step 3: Install Dependencies
Bash

pip install -r requirements.txt
🖥️ Usage
To run the full system, you will need two separate terminal windows.

Terminal 1: The Data Pipeline (Backend Worker)
This script runs the scraper, AI enrichment, vector DB builder, and analytics generation. It runs continuously on a 6-hour cycle.

Bash

python main.py
Wait for the initial run to complete (scraping & building the vector DB) before starting the web server.

Terminal 2: The Web Interface (Frontend Server)
This launches the Flask application to serve the dashboard and chatbot.

Bash

python src/api/app.py
Access the dashboard at: http://127.0.0.1:5000

📂 Project Structure
Plaintext

serendivwatcher/
├── data/
│   ├── raw/                # JSON storage for scraped articles (TinyDB)
│   ├── indicators/         # Computed metrics (JSON) for the dashboard
│   └── vector_db/          # ChromaDB storage for the AI Chatbot
├── scripts/
│   ├── run_scraper.py      # Triggers the web scraper
│   ├── enrich_articles.py  # Runs NLP & Sentiment analysis
│   ├── build_indicators.py # Generates stats, trends, and clusters
│   └── build_vector_db.py  # Indexes news for RAG search
├── src/
│   ├── analytics/          # Logic for detecting anomalies & trends
│   ├── processing/         # Core NLP processing logic
│   ├── scrapers/           # Web scraping definitions
│   ├── storage/            # Database management class
│   └── api/                # Flask App & Routes
│       ├── templates/      # HTML files (dashboard.html, chatbot.html)
│       └── static/         # CSS & JS assets
├── main.py                 # Master pipeline orchestrator
└── requirements.txt        # Project dependencies
👥 Authors


Kaveesha Vihanga (20233059)
Hangum Archana (20231905)
Chanuka Wijeratna (20232021)

Event: MODE-LX: The Final Hurdle (IEEE CIS)