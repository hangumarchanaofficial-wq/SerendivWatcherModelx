import os
import sys
import time
import subprocess
from datetime import datetime, timedelta

# ---------------------------------------------------------------------
# Paths & Python interpreter
# ---------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PYTHON = sys.executable


def run_step(name: str, script_rel_path: str):
    """
    Helper to run a script as a subprocess and log output.
    """
    script_path = os.path.join(BASE_DIR, script_rel_path)
    
    if not os.path.exists(script_path):
        print(f"\n[ERROR] Could not find script: {script_path}")
        return

    print("\n" + "=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting step: {name}")
    print("=" * 80)
    print(f"Running: {PYTHON} {script_path}\n")

    try:
        subprocess.run([PYTHON, script_path], check=True)
        print(f"\n[{name}] completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n[{name}] FAILED with exit code {e.returncode}.")
    except Exception as e:
        print(f"\n[{name}] FAILED with unexpected error: {e}")


def run_pipeline_once():
    """
    One full pipeline:
      1) Scrape news
      2) Enrich with NLP
      3) Build indicators
      4) Advanced Analytics (Correlations)
      5) Sentiment Velocity
      6) Build Vector Database (For Chatbot)
    """
    # 1. Scraper
    run_step("Scraper", os.path.join("scripts", "run_scraper.py"))

    # 2. NLP enrichment
    run_step("NLP Enrichment", os.path.join("scripts", "enrich_articles.py"))

    # 3. Indicators
    run_step("Build Indicators", os.path.join("scripts", "build_indicators.py"))

    # 4. Correlations
    run_step("Generate Correlations", os.path.join("src", "processing", "generate_correlations.py"))

    # 5. Sentiment Velocity
    run_step("Generate Velocity", os.path.join("src", "processing", "generate_velocity.py"))

    # 6. Build Vector DB (NEW STEP)
    # This ensures the chatbot always has the latest news indexed
    run_step("Build Vector DB", os.path.join("scripts", "build_vector_db.py"))


def main(run_every_6_hours: bool = False):
    """
    Main Loop
    """
    print("\n" + "=" * 80)
    print(" SerendivWatcher – Full Data Pipeline")
    print("=" * 80 + "\n")

    if not run_every_6_hours:
        start_time = datetime.now()
        print(f"[Scheduler] Single pipeline run started at {start_time:%Y-%m-%d %H:%M:%S}")
        run_pipeline_once()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60.0
        print(f"[Scheduler] Finished in {duration:.1f} minutes. Exiting.\n")
        return

    while True:
        start_time = datetime.now()
        print(f"[Scheduler] Pipeline run started at {start_time:%Y-%m-%d %H:%M:%S}")
        run_pipeline_once()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60.0
        print(f"[Scheduler] Pipeline finished in {duration:.1f} minutes.")

        sleep_seconds = 6 * 60 * 60
        next_run = end_time + timedelta(seconds=sleep_seconds)
        print(f"\n[Scheduler] Sleeping for 6 hours. Next run at {next_run:%Y-%m-%d %H:%M:%S}.\n")

        try:
            time.sleep(sleep_seconds)
        except KeyboardInterrupt:
            print("\n[Scheduler] Stopped by user (Ctrl+C). Exiting.")
            break


if __name__ == "__main__":
    # Change to True if you want the continuous loop
    main(run_every_6_hours=False)