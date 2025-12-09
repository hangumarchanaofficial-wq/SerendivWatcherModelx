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
                return gemma_models[0]  # Use the first one
            else:
                print(f"No Gemma models found.")
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


if __name__ == "__main__":
    
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
            print("To install Gemma, run: ollama pull gemma:3.1b")
    else:
        print("\nOllama not available. Proceeding without LLM enhancement...")
    
    print(f"\n{'='*60}")
    print(f"Building indicators at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LLM Enhancement: {'Enabled' if use_llm else 'Disabled'}")
    if use_llm:
        print(f"LLM Model: {model_name}")
    print(f"{'='*60}\n")

    # Pass the detected model name to IndicatorBuilder
    builder = IndicatorBuilder()
    if use_llm and model_name:
        builder.set_llm_model(model_name)
    
    print("Building national indicators...")
    national = builder.build_national_indicators()
    print(f"  Overall sentiment: {national['overall_sentiment']}")
    print(f"  Total articles: {national['total_articles']}\n")

    print("Building sector indicators...")
    if use_llm:
        print(f"  Using LLM-enhanced keyword/org selection ({model_name})\n")
    sectors = builder.build_sector_indicators(use_llm=use_llm)
    print(f"  Analyzed {len(sectors)} sectors\n")

    print("Detecting risks & opportunities...")
    insights = builder.detect_risks_opportunities()
    print(f"  Found {insights['total_risks']} risks")
    print(f"  Found {insights['total_opportunities']} opportunities\n")

    print("Saving basic indicators...")
    builder.save_indicators()

    print(f"\n{'='*60}")
    print("Running Advanced Analytics...")
    print(f"{'='*60}\n")

    advanced = AdvancedAnalytics()
    results = advanced.save_analytics()

    print(f"\nTemporal trends: {results['trends']['trend']} (strength: {results['trends']['trend_strength']})")
    print(f"  Anomalies detected: {results['anomalies']['total_anomalies']}")
    print(f"  Sector clusters: {len(results['clusters']['clusters'])}")
    print(f"  Sector correlations: {results['correlations']['total_correlations']}")
    print(f"  Velocity analysis: {len(results['velocity']['sector_velocities'])} sectors")

    print(f"\n{'='*60}")
    print("All indicators saved to data/indicators/")
    print(f"{'='*60}\n")
