from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

def load_indicators():
    """Load all indicator JSON files"""
    indicators_path = os.path.join(os.path.dirname(__file__), "../../data/indicators/")
    
    data = {}
    files = [
        'national_indicators.json',
        'sector_indicators.json', 
        'risk_opportunity_insights.json',
        'temporal_trends.json',
        'anomalies.json',
        'sector_clusters.json',
        'sentiment_velocity.json',
        'sector_correlations.json'
    ]
    
    for file in files:
        filepath = os.path.join(indicators_path, file)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                key = file.replace('.json', '')
                data[key] = json.load(f)
    
    return data

@app.route('/')
def dashboard():
    """Main dashboard - National Overview"""
    data = load_indicators()
    return render_template('dashboard.html', data=data, active_page='overview')

@app.route('/sectors')
def sectors():
    """Sector Analysis Page"""
    data = load_indicators()
    return render_template('sectors.html', data=data, active_page='sectors')

@app.route('/risks')
def risks():
    """Risk & Opportunity Page"""
    data = load_indicators()
    return render_template('risks.html', data=data, active_page='risks')

@app.route('/api/indicators')
def api_indicators():
    """API endpoint for all indicators"""
    return jsonify(load_indicators())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
