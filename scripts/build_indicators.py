# build_indicators.py
import sys
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.indicator_builder import IndicatorBuilder
from src.analytics.advanced_analytics import AdvancedAnalytics


def check_ollama_running():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def get_available_gemma_model():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code != 200:
            return None

        models = r.json().get("models", [])
        names = [m.get("name", "") for m in models]
        gemmas = [n for n in names if "gemma" in n.lower()]
        if gemmas:
            print(f"Found Gemma models: {', '.join(gemmas)}")
            return gemmas[0]

        print("No Gemma models found.")
        print(f"Available models: {', '.join(names) if names else 'None'}")
        return None
    except Exception as e:
        print(f"Could not check available models: {e}")
        return None


def ensure_ollama_ready(max_wait=30):
    print(f"\n{'='*60}\nChecking Ollama availability...\n{'='*60}\n")

    if check_ollama_running():
        print("Ollama service is already running.")
        return True

    print("Ollama service not detected. Attempting to start...")
    try:
        if os.name == "nt":
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
    ollama_ready = ensure_ollama_ready(max_wait=30)

    use_llm = False
    model_name = None
    if ollama_ready:
        model_name = get_available_gemma_model()
        use_llm = bool(model_name)

    print(f"\n{'='*60}")
    print(f"Building indicators at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LLM Enhancement: {'Enabled' if use_llm else 'Disabled'}")
    if use_llm:
        print(f"LLM Model: {model_name}")
    print(f"{'='*60}\n")

    db_path = "data/raw/articles.json"
    out_dir = "data/indicators"

    builder = IndicatorBuilder(db_path=db_path, output_dir=out_dir)
    if use_llm and model_name:
        builder.set_llm_model(model_name)

    print("Step 1: Building national indicators...")
    national = builder.build_national_indicators()

    print("Step 2: Building sector indicators...")
    sectors = builder.build_sector_indicators(use_llm=use_llm)

    print("Step 3: Detecting risks and opportunities...")
    insights = builder.build_risk_opportunity_insights()

    print("Step 4: Saving basic indicators...")
    builder.save_indicators(output_path=out_dir, national=national, sectors=sectors, insights=insights)

    print(f"{'='*60}")
    print("Step 5: Running advanced analytics...")
    print(f"{'='*60}\n")

    advanced = AdvancedAnalytics(db_path=db_path)
    results = advanced.save_analytics(output_path=out_dir) 

    print("Advanced analytics results:")
    print(f"  Temporal trend: {results['trends']['trend']} (strength: {results['trends']['trend_strength']})")
    print(f"  Anomalies detected: {results['anomalies']['total_anomalies']}")

    print(f"\n{'='*60}")
    print("Indicator Generation Complete")
    print(f"{'='*60}")
    print(f"Output directory: {Path(out_dir).resolve()}")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
