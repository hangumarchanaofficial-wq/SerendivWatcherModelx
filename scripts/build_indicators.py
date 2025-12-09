import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.indicator_builder import IndicatorBuilder
from src.analytics.advanced_analytics import AdvancedAnalytics
from datetime import datetime


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Building indicators at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Basic indicators
    builder = IndicatorBuilder()
    
    print("Building national indicators...")
    national = builder.build_national_indicators()
    print(f"  Overall sentiment: {national['overall_sentiment']}")
    print(f"  Total articles: {national['total_articles']}\n")
    
    print("Building sector indicators...")
    sectors = builder.build_sector_indicators()
    print(f"  Analyzed {len(sectors)} sectors\n")
    
    print("Detecting risks & opportunities...")
    insights = builder.detect_risks_opportunities()
    print(f"  Found {insights['total_risks']} risks")
    print(f"  Found {insights['total_opportunities']} opportunities\n")
    
    print("Saving basic indicators...")
    builder.save_indicators()
    
    # Advanced analytics
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
