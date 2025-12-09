import os
import sys
import time
import subprocess
from datetime import datetime, timedelta

# ---------------------------------------------------------------------
# Paths & Python interpreter
# ---------------------------------------------------------------------

# Absolute path to project root (where this main.py lives)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Use the same Python interpreter that's running this script
PYTHON = sys.executable


def run_step(name: str, script_rel_path: str):
    """
    Helper to run a script as a subprocess and log output.
    script_rel_path is relative to project root, e.g. 'scripts/run_scraper.py'.
    """
    script_path = os.path.join(BASE_DIR, script_rel_path)

    print("\n" + "=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting step: {name}")
    print("=" * 80)
    print(f"Running: {PYTHON} {script_path}\n")

    try:
        # Inherit stdout/stderr so you see each script's own logs
        subprocess.run([PYTHON, script_path], check=True)
        print(f"\n[{name}] completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n[{name}] FAILED with exit code {e.returncode}.")
    except Exception as e:
        print(f"\n[{name}] FAILED with unexpected error: {e}")


def run_pipeline_once():
    """
    One full pipeline:
      1) Scrape news → data/raw/articles.json
      2) Enrich with NLP (sentiment, entities, sectors, keywords)
      3) Build indicators + advanced analytics into data/indicators/
    """
    # 1. Scraper
    run_step("Scraper", os.path.join("scripts", "run_scraper.py"))

    # 2. NLP enrichment
    run_step("NLP Enrichment", os.path.join("scripts", "enrich_articles.py"))

    # 3. Indicators + advanced analytics
    run_step("Build Indicators", os.path.join("scripts", "build_indicators.py"))


def main(run_every_6_hours: bool = False):
    """
    If run_every_6_hours is False:
        - Run the pipeline once and exit.
    If True:
        - Run pipeline, then sleep 6 hours, and repeat until Ctrl+C.
    """
    print("\n" + "=" * 80)
    print(" SerendivWatcher – Full Data Pipeline")
    print("=" * 80 + "\n")

    if not run_every_6_hours:
        # Single run, used during development / manual refresh
        start_time = datetime.now()
        print(f"[Scheduler] Single pipeline run started at {start_time:%Y-%m-%d %H:%M:%S}")
        run_pipeline_once()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60.0
        print(f"[Scheduler] Finished in {duration:.1f} minutes. Exiting.\n")
        return

    # Continuous 6-hour scheduler
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
    # For now, run once; change to True to enable 6‑hour loop
    main(run_every_6_hours=False)
