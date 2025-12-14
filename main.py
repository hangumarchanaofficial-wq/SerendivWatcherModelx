"""
SerendivWatcher - Main Backend Application
Runs both the data pipeline scheduler and Flask web server
"""

import os
import sys
import time
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

PYTHON = sys.executable

# ---------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"serendivwatcher_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SerendivWatcher")


# ---------------------------------------------------------------------
# Pipeline Functions
# ---------------------------------------------------------------------

def run_step(name: str, script_rel_path: str) -> bool:
    """
    Execute a pipeline step as subprocess
    Output is printed directly to console in real-time
    
    Returns:
        True if successful, False otherwise
    """
    script_path = BASE_DIR / script_rel_path
    
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False

    logger.info(f"{'='*80}")
    logger.info(f"Starting step: {name}")
    logger.info(f"{'='*80}")
    logger.info(f"Running: {PYTHON} {script_path}\n")

    try:
        # Let subprocess print directly to console (no output capture)
        result = subprocess.run(
            [PYTHON, str(script_path)],
            check=True,
            timeout=1800  # 30 minute timeout
        )
        
        logger.info(f"\n[{name}] completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"\n[{name}] TIMEOUT after 30 minutes")
        return False
        
    except subprocess.CalledProcessError as e:
        logger.error(f"\n[{name}] FAILED with exit code {e.returncode}")
        return False
        
    except Exception as e:
        logger.error(f"\n[{name}] FAILED with unexpected error: {e}")
        return False


def run_pipeline_once() -> dict:
    """
    Execute full data pipeline
    Returns dict with status of each step
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("STARTING FULL DATA PIPELINE")
    logger.info("=" * 80)
    
    results = {}
    
    # Define pipeline steps
    steps = [
        ("Scraper", "scripts/run_scraper.py"),
        ("NLP Enrichment", "scripts/enrich_articles.py"),
        ("Build Indicators", "scripts/build_indicators.py"),
        ("Generate Correlations", "src/processing/generate_correlations.py"),
        ("Generate Velocity", "src/processing/generate_velocity.py"),
        ("Build Vector DB", "scripts/build_vector_db.py"),
    ]
    
    # Run each step
    for name, path in steps:
        success = run_step(name, path)
        results[name] = "SUCCESS" if success else "FAILED"
        
        # Optional: Stop pipeline if critical step fails
        if not success and name in ["Scraper", "NLP Enrichment"]:
            logger.warning(f"Critical step '{name}' failed. Continuing anyway...")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60.0
    
    logger.info("=" * 80)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 80)
    for step, status in results.items():
        logger.info(f"  {step:.<40} {status}")
    logger.info(f"\nTotal Duration: {duration:.1f} minutes")
    logger.info("=" * 80)
    
    return results


# ---------------------------------------------------------------------
# Scheduler (Background Thread)
# ---------------------------------------------------------------------

class PipelineScheduler:
    """Background scheduler for data pipeline"""
    
    def __init__(self, interval_hours: int = 6):
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.running = False
        self.thread = None
        self.last_run = None
        self.next_run = None
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"Pipeline scheduler started (runs every {self.interval_hours}h)")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Pipeline scheduler stopped")
    
    def _run_loop(self):
        """Internal loop that runs pipeline periodically"""
        while self.running:
            try:
                self.last_run = datetime.now()
                logger.info(f"Scheduler: Starting pipeline run at {self.last_run:%Y-%m-%d %H:%M:%S}")
                
                run_pipeline_once()
                
                self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
                logger.info(f"Scheduler: Next run scheduled at {self.next_run:%Y-%m-%d %H:%M:%S}")
                logger.info(f"Scheduler: Sleeping for {self.interval_hours} hours...\n")
                
                # Sleep in small intervals to allow clean shutdown
                sleep_until = time.time() + self.interval_seconds
                while self.running and time.time() < sleep_until:
                    time.sleep(60)  # Check every minute
                    
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                time.sleep(300)  # Wait 5 minutes on error


# ---------------------------------------------------------------------
# Flask Web Server
# ---------------------------------------------------------------------

def start_flask_app(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Start Flask web application"""
    try:
        from src.api.app import app
        
        logger.info("=" * 80)
        logger.info("STARTING FLASK WEB SERVER")
        logger.info("=" * 80)
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Debug: {debug}")
        logger.info(f"Access at: http://localhost:{port}")
        logger.info("=" * 80 + "\n")
        
        app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}", exc_info=True)
        sys.exit(1)


# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------

def main(
    mode: str = "all",
    run_pipeline_now: bool = True,
    scheduler_interval: int = 6,
    flask_host: str = "0.0.0.0",
    flask_port: int = 5000,
    flask_debug: bool = False
):
    """
    Main application entry point
    
    Args:
        mode: "all", "pipeline", "scheduler", or "web"
        run_pipeline_now: Run pipeline immediately on startup
        scheduler_interval: Hours between scheduled runs
        flask_host: Flask server host
        flask_port: Flask server port
        flask_debug: Enable Flask debug mode
    """
    
    logger.info("\n" + "=" * 80)
    logger.info("SERENDIVWATCHER - INTELLIGENCE PLATFORM")
    logger.info("=" * 80)
    logger.info(f"Mode: {mode.upper()}")
    logger.info(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    logger.info("=" * 80 + "\n")
    
    scheduler = None
    
    try:
        # MODE 1: Pipeline Only (one-time run)
        if mode == "pipeline":
            logger.info("Running pipeline once and exiting...")
            run_pipeline_once()
            logger.info("Pipeline completed. Exiting.")
            return
        
        # MODE 2: Scheduler Only (background pipeline)
        elif mode == "scheduler":
            scheduler = PipelineScheduler(interval_hours=scheduler_interval)
            if run_pipeline_now:
                logger.info("Running initial pipeline...")
                run_pipeline_once()
            scheduler.start()
            
            logger.info("Scheduler running. Press Ctrl+C to stop.")
            while True:
                time.sleep(60)
        
        # MODE 3: Web Server Only
        elif mode == "web":
            start_flask_app(host=flask_host, port=flask_port, debug=flask_debug)
        
        # MODE 4: All (Scheduler + Web Server)
        elif mode == "all":
            # Start scheduler in background
            scheduler = PipelineScheduler(interval_hours=scheduler_interval)
            
            if run_pipeline_now:
                logger.info("Running initial pipeline before starting services...")
                run_pipeline_once()
            
            scheduler.start()
            
            # Start Flask in main thread
            start_flask_app(host=flask_host, port=flask_port, debug=flask_debug)
        
        else:
            logger.error(f"Invalid mode: {mode}. Use 'all', 'pipeline', 'scheduler', or 'web'")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\n\nReceived interrupt signal (Ctrl+C)")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        if scheduler:
            scheduler.stop()
        logger.info("SerendivWatcher shut down successfully")


# ---------------------------------------------------------------------
# Command Line Interface
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SerendivWatcher Backend")
    
    parser.add_argument(
        "--mode",
        choices=["all", "pipeline", "scheduler", "web"],
        default="all",
        help="Run mode: all (default), pipeline (once), scheduler (background), or web (server only)"
    )
    
    parser.add_argument(
        "--no-initial-run",
        action="store_true",
        help="Skip initial pipeline run on startup"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=6,
        help="Hours between scheduled pipeline runs (default: 6)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Flask server host (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Flask server port (default: 5000)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode"
    )
    
    args = parser.parse_args()
    
    main(
        mode=args.mode,
        run_pipeline_now=not args.no_initial_run,
        scheduler_interval=args.interval,
        flask_host=args.host,
        flask_port=args.port,
        flask_debug=args.debug
    )
