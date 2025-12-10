import sys
import os
import subprocess
import time
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.indicator_builder import IndicatorBuilder
from src.analytics.advanced_analytics import AdvancedAnalytics
from datetime import datetime


def check_ollama_running():
    """Check if Ollama service is running and accessible."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def get_available_gemma_model():
    """
    Find the first available Gemma model.
    Returns model name or None if no Gemma model found.
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Look for any gemma model
            gemma_models = [m for m in model_names if "gemma" in m.lower()]
            
            if gemma_models:
                print(f"Found Gemma models: {', '.join(gemma_models)}")
                return gemma_models[0]
            else:
                print("No Gemma models found.")
                print(f"Available models: {', '.join(model_names) if model_names else 'None'}")
                return None
    except Exception as e:
        print(f"Could not check available models: {e}")
        return None


def ensure_ollama_ready(max_wait=30):
    """
    Ensure Ollama is running.
    
    Returns:
        bool: True if ready, False otherwise
    """
    print(f"\n{'='*60}")
    print("Checking Ollama availability...")
    print(f"{'='*60}\n")
    
    if check_ollama_running():
        print("Ollama service is already running.")
        return True
    
    print("Ollama service not detected. Attempting to start...")
    
    try:
        if os.name == 'nt':
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        print("Waiting for Ollama to start...")
        for i in range(max_wait):
            time.sleep(1)
            if check_ollama_running():
                print(f"Ollama service started successfully after {i+1} seconds.")
                return True
            if i % 5 == 0:
                print(f"  Still waiting... ({i}/{max_wait}s)")
        
        print(f"\nWarning: Ollama did not start within {max_wait} seconds.")
        return False
        
    except FileNotFoundError:
        print("\nError: 'ollama' command not found.")
        print("Please install Ollama from: https://ollama.ai")
        return False
    except Exception as e:
        print(f"\nError starting Ollama: {e}")
        return False


def main():
    """Main function to build all indicators."""
    
    # Check Ollama availability
    ollama_ready = ensure_ollama_ready(max_wait=30)
    
    use_llm = False
    model_name = None
    
    if ollama_ready:
        model_name = get_available_gemma_model()
        if model_name:
            print(f"\nUsing model: {model_name}")
            use_llm = True
        else:
            print("\nNo Gemma model available. Proceeding without LLM enhancement...")
            print("To install Gemma, run: ollama pull gemma:2b")
    else:
        print("\nOllama not available. Proceeding without LLM enhancement...")
    
    print(f"\n{'='*60}")
    print(f"Building indicators at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LLM Enhancement: {'Enabled' if use_llm else 'Disabled'}")
    if use_llm:
        print(f"LLM Model: {model_name}")
    print(f"{'='*60}\n")

    # Initialize IndicatorBuilder
    builder = IndicatorBuilder(
        db_path="data/raw/articles.json",
        output_dir="data/indicators"
    )
    
    if use_llm and model_name:
        builder.set_llm_model(model_name)
    
    # Build National Indicators
    print("Step 1: Building national indicators...")
    national = builder.build_national_indicators()
    print(f"  Overall sentiment: {national.get('overall_sentiment', 0):.3f}")
    print(f"  Total articles: {national.get('total_articles', 0)}")
    print(f"  Positive articles: {national.get('positive_articles', 0)}")
    print(f"  Negative articles: {national.get('negative_articles', 0)}")
    print(f"  Neutral articles: {national.get('neutral_articles', 0)}\n")

    # Build Sector Indicators
    print("Step 2: Building sector indicators...")
    if use_llm:
        print(f"  Using LLM-enhanced analysis with {model_name}")
    sectors = builder.build_sector_indicators(use_llm=use_llm)
    print(f"  Analyzed {len(sectors)} sectors")
    
    for sector_name in list(sectors.keys())[:5]:
        sector = sectors[sector_name]
        print(f"    - {sector_name}: {sector['article_count']} articles, "
              f"sentiment {sector['avg_sentiment']:.3f}")
    print()

    # Build Risk & Opportunity Insights
    print("Step 3: Detecting risks and opportunities...")
    insights = builder.build_risk_opportunity_insights()
    print(f"  Total risks: {insights.get('total_risks', 0)}")
    print(f"  Total opportunities: {insights.get('total_opportunities', 0)}")
    
    if insights.get('top_risks'):
        print(f"  Top risk: {insights['top_risks'][0].get('title', 'N/A')[:50]}...")
    if insights.get('top_opportunities'):
        print(f"  Top opportunity: {insights['top_opportunities'][0].get('title', 'N/A')[:50]}...")
    print()

    # Save basic indicators
    print("Step 4: Saving basic indicators...")
    builder.save_indicators()
    print("  Saved: national_indicators.json")
    print("  Saved: sector_indicators.json")
    print("  Saved: risk_opportunity_insights.json\n")

    # Run Advanced Analytics
    print(f"{'='*60}")
    print("Step 5: Running advanced analytics...")
    print(f"{'='*60}\n")

    advanced = AdvancedAnalytics(db_path="data/raw/articles.json")
    results = advanced.save_analytics(output_path="data/indicators")

    # Run Advanced Analytics
    print(f"{'='*60}")
    print("Step 5: Running advanced analytics...")
    print(f"{'='*60}\n")

    advanced = AdvancedAnalytics(db_path="data/raw/articles.json")
    results = advanced.save_analytics()  # No parameter needed (uses default)

    print("Advanced analytics results:")
    print(f"  Temporal trend: {results['trends']['trend']} "
        f"(strength: {results['trends']['trend_strength']})")
    print(f"  Anomalies detected: {results['anomalies']['total_anomalies']}")
    if results['anomalies']['total_anomalies'] > 0:
        print(f"    - Positive anomalies: {sum(1 for a in results['anomalies']['anomalies'] if a['anomaly_type'] == 'extremely_positive')}")
        print(f"    - Negative anomalies: {sum(1 for a in results['anomalies']['anomalies'] if a['anomaly_type'] == 'extremely_negative')}")

    print(f"  Sector clusters: {len(results['clusters']['clusters'])}")
    for cluster in results['clusters']['clusters']:
        print(f"    - Cluster {cluster['cluster_id']}: {len(cluster['sectors'])} sectors, "
            f"avg sentiment {cluster['avg_sentiment']:.3f}")

    print(f"  Sector correlations: {results['correlations'].get('total_correlations', 0)}")
    print(f"  Velocity analysis: {len(results['velocity'].get('sector_velocities', []))} sectors")
    print()


    # Summary
    print(f"{'='*60}")
    print("Indicator Generation Complete")
    print(f"{'='*60}")
    print(f"Output directory: data/indicators/")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nGenerated files:")
    print("  - national_indicators.json")
    print("  - sector_indicators.json")
    print("  - risk_opportunity_insights.json")
    print("  - temporal_trends.json")
    print("  - anomalies.json")
    print("  - sector_clusters.json")
    print("  - sector_correlations.json")
    print("  - sentiment_velocity.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
