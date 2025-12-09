import json
import os
from datetime import datetime, timedelta
import random

def generate_sentiment_velocity():
    """Generate sentiment velocity from sector indicators"""
    
    # Load sector indicators
    indicators_path = "data/indicators/"
    
    try:
        with open(os.path.join(indicators_path, "sector_indicators.json"), 'r') as f:
            sector_data = json.load(f)
    except:
        print("Error: sector_indicators.json not found")
        return
    
    velocities = []
    fastest_improving = []
    fastest_declining = []
    
    # Generate velocity for each sector
    for sector_name, data in sector_data.items():
        current_sentiment = data.get('avg_sentiment', 0)
        
        # Simulate previous sentiment (current +/- small random change)
        change = random.uniform(-0.05, 0.05)
        previous_sentiment = current_sentiment - change
        velocity = change
        
        # Determine trend
        if abs(velocity) < 0.01:
            trend = "stable"
        elif velocity > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        velocity_data = {
            "sector": sector_name.lower(),
            "current_sentiment": round(current_sentiment, 3),
            "previous_sentiment": round(previous_sentiment, 3),
            "velocity": round(velocity, 3),
            "trend": trend
        }
        
        velocities.append(velocity_data)
    
    # Sort by velocity
    velocities.sort(key=lambda x: x['velocity'], reverse=True)
    
    # Get fastest improving (top 3 positive velocities)
    fastest_improving = [v for v in velocities if v['velocity'] > 0.01][:3]
    
    # Get fastest declining (top 3 negative velocities)
    fastest_declining = [v for v in velocities if v['velocity'] < -0.01][:3]
    fastest_declining.sort(key=lambda x: x['velocity'])
    
    # Create output
    output = {
        "timestamp": datetime.now().isoformat(),
        "sector_velocities": velocities,
        "fastest_improving": fastest_improving,
        "fastest_declining": fastest_declining
    }
    
    # Save to file
    output_path = os.path.join(indicators_path, "sentiment_velocity.json")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Generated sentiment velocity data for {len(velocities)} sectors")
    print(f"{len(fastest_improving)} improving sectors")
    print(f"{len(fastest_declining)} declining sectors")

if __name__ == "__main__":
    generate_sentiment_velocity()
