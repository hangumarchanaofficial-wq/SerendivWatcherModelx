from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy import stats
from tinydb import TinyDB
import json


class AdvancedAnalytics:
    def __init__(self, db_path="data/raw/articles.json"):
        self.db = TinyDB(db_path)
    
    def temporal_trend_analysis(self):
        """Analyze sentiment trends over time"""
        articles = self.db.all()
        
        # Group articles by date
        daily_data = defaultdict(lambda: {
            'sentiments': [],
            'article_count': 0,
            'sectors': defaultdict(int)
        })
        
        for article in articles:
            timestamp = article.get('scraped_at', article.get('updated_at'))
            if not timestamp:
                continue
            
            try:
                date = datetime.fromisoformat(timestamp).date()
                sentiment = article.get('sentiment_score', 0)
                sectors = article.get('sectors', [])
                
                daily_data[str(date)]['sentiments'].append(sentiment)
                daily_data[str(date)]['article_count'] += 1
                
                for sector in sectors:
                    daily_data[str(date)]['sectors'][sector] += 1
            except:
                continue
        
        # Calculate daily averages and trends
        timeline = []
        dates = sorted(daily_data.keys())
        
        for date in dates:
            data = daily_data[date]
            avg_sentiment = np.mean(data['sentiments']) if data['sentiments'] else 0
            
            timeline.append({
                'date': date,
                'avg_sentiment': round(avg_sentiment, 3),
                'article_count': data['article_count'],
                'top_sectors': sorted(data['sectors'].items(), key=lambda x: x[1], reverse=True)[:3]
            })
        
        # Calculate trend direction (last 3 days vs previous 3 days)
        if len(timeline) >= 6:
            recent_sentiment = np.mean([t['avg_sentiment'] for t in timeline[-3:]])
            previous_sentiment = np.mean([t['avg_sentiment'] for t in timeline[-6:-3]])
            trend = "improving" if recent_sentiment > previous_sentiment else "declining"
            trend_strength = abs(recent_sentiment - previous_sentiment)
        else:
            trend = "insufficient_data"
            trend_strength = 0
        
        return {
            'timeline': timeline,
            'trend': trend,
            'trend_strength': round(trend_strength, 3),
            'total_days': len(timeline)
        }
    
    def detect_anomalies(self):
        """Detect anomalous sentiment patterns using statistical methods"""
        articles = self.db.all()
        
        # Collect sentiment scores with metadata
        data_points = []
        for article in articles:
            sentiment = article.get('sentiment_score')
            if sentiment is not None:
                data_points.append({
                    'sentiment': sentiment,
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'sectors': article.get('sectors', []),
                    'source': article.get('source', '')
                })
        
        if len(data_points) < 10:
            return {'anomalies': [], 'message': 'Insufficient data for anomaly detection'}
        
        sentiments = np.array([d['sentiment'] for d in data_points])
        
        # Calculate z-scores (statistical outliers)
        mean = np.mean(sentiments)
        std = np.std(sentiments)
        z_scores = np.abs((sentiments - mean) / std) if std > 0 else np.zeros(len(sentiments))
        
        # Detect anomalies (z-score > 2 = unusual)
        anomalies = []
        for i, z_score in enumerate(z_scores):
            if z_score > 2:
                anomalies.append({
                    'title': data_points[i]['title'][:100],
                    'url': data_points[i]['url'],
                    'sentiment': round(data_points[i]['sentiment'], 3),
                    'z_score': round(z_score, 2),
                    'sectors': data_points[i]['sectors'],
                    'source': data_points[i]['source'],
                    'anomaly_type': 'extremely_negative' if data_points[i]['sentiment'] < mean else 'extremely_positive'
                })
        
        # Sort by z-score (most anomalous first)
        anomalies.sort(key=lambda x: x['z_score'], reverse=True)
        
        return {
            'anomalies': anomalies[:20],
            'total_anomalies': len(anomalies),
            'mean_sentiment': round(mean, 3),
            'std_sentiment': round(std, 3)
        }
    
    def sector_clustering(self):
        """Cluster sectors by similar patterns using KMeans"""
        articles = self.db.all()
        
        # Build sector feature matrix
        sector_features = defaultdict(lambda: {
            'avg_sentiment': [],
            'article_count': 0,
            'org_count': 0,
            'avg_word_count': []
        })
        
        for article in articles:
            sectors = article.get('sectors', [])
            sentiment = article.get('sentiment_score', 0)
            word_count = article.get('word_count', 0)
            orgs = len(article.get('entities', {}).get('ORG', []))
            
            for sector in sectors:
                sector_features[sector]['avg_sentiment'].append(sentiment)
                sector_features[sector]['article_count'] += 1
                sector_features[sector]['org_count'] += orgs
                sector_features[sector]['avg_word_count'].append(word_count)
        
        if len(sector_features) < 3:
            return {'clusters': [], 'message': 'Insufficient sectors for clustering'}
        
        # Prepare feature vectors
        sector_names = list(sector_features.keys())
        feature_matrix = []
        
        for sector in sector_names:
            data = sector_features[sector]
            feature_matrix.append([
                np.mean(data['avg_sentiment']),
                data['article_count'],
                data['org_count'],
                np.mean(data['avg_word_count']) if data['avg_word_count'] else 0
            ])
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(feature_matrix)
        
        # KMeans clustering
        n_clusters = min(3, len(sector_names))  # 3 clusters or less if few sectors
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        # Group sectors by cluster
        clusters = defaultdict(list)
        for sector, label in zip(sector_names, cluster_labels):
            clusters[int(label)].append({
                'sector': sector,
                'avg_sentiment': round(np.mean(sector_features[sector]['avg_sentiment']), 3),
                'article_count': sector_features[sector]['article_count']
            })
        
        # Label clusters based on characteristics
        cluster_results = []
        for cluster_id, members in clusters.items():
            avg_cluster_sentiment = np.mean([m['avg_sentiment'] for m in members])
            
            if avg_cluster_sentiment > 0.2:
                label = "High Performance Sectors"
            elif avg_cluster_sentiment < -0.1:
                label = "Challenged Sectors"
            else:
                label = "Stable Sectors"
            
            cluster_results.append({
                'cluster_id': cluster_id,
                'label': label,
                'avg_sentiment': round(avg_cluster_sentiment, 3),
                'sectors': sorted(members, key=lambda x: x['article_count'], reverse=True)
            })
        
        return {
            'clusters': sorted(cluster_results, key=lambda x: x['avg_sentiment'], reverse=True),
            'total_sectors': len(sector_names)
        }
    
    def correlation_analysis(self):
        """Analyze correlations between sectors"""
        articles = self.db.all()
        
        # Build co-occurrence matrix
        sector_pairs = defaultdict(lambda: {'count': 0, 'sentiments': []})
        
        for article in articles:
            sectors = article.get('sectors', [])
            sentiment = article.get('sentiment_score', 0)
            
            # For each pair of sectors in the same article
            for i, sector1 in enumerate(sectors):
                for sector2 in sectors[i+1:]:
                    pair = tuple(sorted([sector1, sector2]))
                    sector_pairs[pair]['count'] += 1
                    sector_pairs[pair]['sentiments'].append(sentiment)
        
        # Find strongest correlations
        correlations = []
        for (sector1, sector2), data in sector_pairs.items():
            if data['count'] >= 3:  # At least 3 co-occurrences
                avg_sentiment = np.mean(data['sentiments'])
                correlations.append({
                    'sector1': sector1,
                    'sector2': sector2,
                    'co_occurrence_count': data['count'],
                    'avg_sentiment': round(avg_sentiment, 3),
                    'correlation_strength': 'strong' if data['count'] >= 5 else 'moderate'
                })
        
        correlations.sort(key=lambda x: x['co_occurrence_count'], reverse=True)
        
        return {
            'top_correlations': correlations[:15],
            'total_correlations': len(correlations)
        }
    
    def velocity_analysis(self):
        """Analyze rate of change in sentiment (velocity)"""
        articles = self.db.all()
        
        # Group by sector and time
        sector_timeline = defaultdict(lambda: defaultdict(list))
        
        for article in articles:
            timestamp = article.get('scraped_at', article.get('updated_at'))
            if not timestamp:
                continue
            
            try:
                date = datetime.fromisoformat(timestamp).date()
                sentiment = article.get('sentiment_score', 0)
                sectors = article.get('sectors', [])
                
                for sector in sectors:
                    sector_timeline[sector][str(date)].append(sentiment)
            except:
                continue
        
        # Calculate velocity (rate of change)
        velocities = []
        
        for sector, dates in sector_timeline.items():
            sorted_dates = sorted(dates.keys())
            
            if len(sorted_dates) >= 2:
                # Compare most recent to previous
                recent_avg = np.mean(dates[sorted_dates[-1]])
                previous_avg = np.mean(dates[sorted_dates[-2]]) if len(sorted_dates) > 1 else recent_avg
                
                velocity = recent_avg - previous_avg
                
                velocities.append({
                    'sector': sector,
                    'current_sentiment': round(recent_avg, 3),
                    'previous_sentiment': round(previous_avg, 3),
                    'velocity': round(velocity, 3),
                    'trend': 'accelerating' if velocity > 0.1 else ('decelerating' if velocity < -0.1 else 'stable'),
                    'data_points': len(sorted_dates)
                })
        
        velocities.sort(key=lambda x: abs(x['velocity']), reverse=True)
        
        return {
            'sector_velocities': velocities,
            'fastest_improving': [v for v in velocities if v['velocity'] > 0][:5],
            'fastest_declining': [v for v in velocities if v['velocity'] < 0][:5]
        }
    
    def save_analytics(self, output_path="data/indicators/"):
        """Generate and save all advanced analytics"""
        import os
        os.makedirs(output_path, exist_ok=True)
        
        print("Running temporal trend analysis...")
        trends = self.temporal_trend_analysis()
        with open(f"{output_path}temporal_trends.json", "w") as f:
            json.dump(trends, f, indent=2)
        
        print("Running anomaly detection...")
        anomalies = self.detect_anomalies()
        with open(f"{output_path}anomalies.json", "w") as f:
            json.dump(anomalies, f, indent=2)
        
        print("Running sector clustering...")
        clusters = self.sector_clustering()
        with open(f"{output_path}sector_clusters.json", "w") as f:
            json.dump(clusters, f, indent=2)
        
        print("Running correlation analysis...")
        correlations = self.correlation_analysis()
        with open(f"{output_path}sector_correlations.json", "w") as f:
            json.dump(correlations, f, indent=2)
        
        print("Running velocity analysis...")
        velocity = self.velocity_analysis()
        with open(f"{output_path}sentiment_velocity.json", "w") as f:
            json.dump(velocity, f, indent=2)
        
        return {
            'trends': trends,
            'anomalies': anomalies,
            'clusters': clusters,
            'correlations': correlations,
            'velocity': velocity
        }
