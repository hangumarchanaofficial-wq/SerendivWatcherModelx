# advanced_analytics.py
from datetime import datetime
from collections import defaultdict
import os
import json
import numpy as np
from tinydb import TinyDB
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def _parse_iso_dt(ts: str):
    """
    Accepts ISO strings like:
      2025-12-14T01:00:00
      2025-12-14T01:00:00Z
      2025-12-14T01:00:00+05:30
    """
    if not ts:
        return None
    try:
        
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


class AdvancedAnalytics:
    def __init__(self, db_path="data/raw/articles.json"):
        self.db = TinyDB(db_path)

    def temporal_trend_analysis(self):
        articles = self.db.all()
        daily_data = defaultdict(lambda: {"sentiments": [], "article_count": 0, "sectors": defaultdict(int)})

        for a in articles:
            ts = a.get("scraped_at") or a.get("updated_at")
            dt = _parse_iso_dt(ts)
            if not dt:
                continue

            sentiment = a.get("sentiment_score", 0.0)
            sectors = a.get("sectors", [])

            k = str(dt.date())
            daily_data[k]["sentiments"].append(sentiment)
            daily_data[k]["article_count"] += 1
            for s in sectors:
                daily_data[k]["sectors"][s] += 1

        timeline = []
        dates = sorted(daily_data.keys())
        raw_daily_avgs = []  

        for d in dates:
            data = daily_data[d]
            avg = float(np.mean(data["sentiments"])) if data["sentiments"] else 0.0
            raw_daily_avgs.append(avg)

            timeline.append({
                "date": d,
                "avg_sentiment": round(avg, 3),
                "article_count": data["article_count"],
                "top_sectors": sorted(data["sectors"].items(), key=lambda x: x[1], reverse=True)[:3],
            })

        if len(raw_daily_avgs) >= 6:
            recent = float(np.mean(raw_daily_avgs[-3:]))
            prev = float(np.mean(raw_daily_avgs[-6:-3]))
            trend = "improving" if recent > prev else "declining"
            trend_strength = abs(recent - prev)
        else:
            trend = "insufficient_data"
            trend_strength = 0.0

        return {
            "timeline": timeline,
            "trend": trend,
            "trend_strength": round(trend_strength, 3),
            "total_days": len(timeline),
        }

    def detect_anomalies(self):
        articles = self.db.all()
        pts = []
        for a in articles:
            s = a.get("sentiment_score")
            if s is None:
                continue
            pts.append({
                "sentiment": float(s),
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "sectors": a.get("sectors", []),
                "source": a.get("source", ""),
            })

        if len(pts) < 10:
            return {"anomalies": [], "total_anomalies": 0, "message": "Insufficient data for anomaly detection"}

        sentiments = np.array([p["sentiment"] for p in pts], dtype=float)
        mean = float(np.mean(sentiments))
        std = float(np.std(sentiments)) 

        if std <= 0:
            return {"anomalies": [], "total_anomalies": 0, "mean_sentiment": round(mean, 3), "std_sentiment": 0.0}

        z_signed = (sentiments - mean) / std
        z_abs = np.abs(z_signed)

        anomalies = []
        for i in range(len(pts)):
            if z_abs[i] > 2:
                direction = "negative" if z_signed[i] < 0 else "positive"
                anomalies.append({
                    "title": pts[i]["title"][:100],
                    "url": pts[i]["url"],
                    "sentiment": round(pts[i]["sentiment"], 3),

                  
                    "z_score": round(float(z_abs[i]), 2),

                 
                    "z_score_signed": round(float(z_signed[i]), 2),

                    "sectors": pts[i]["sectors"],
                    "source": pts[i]["source"],
                    "anomaly_type": "extremely_negative" if direction == "negative" else "extremely_positive",
                })

        
        anomalies.sort(key=lambda x: x["z_score"], reverse=True)

        return {
            "anomalies": anomalies[:20],
            "total_anomalies": len(anomalies),
            "mean_sentiment": round(mean, 3),
            "std_sentiment": round(std, 3),
        }

    def sector_clustering(self):
        articles = self.db.all()
        sector_features = defaultdict(lambda: {"avg_sentiment": [], "article_count": 0, "org_count": 0, "avg_word_count": []})

        for a in articles:
            sectors = a.get("sectors", [])
            sentiment = a.get("sentiment_score", 0.0)
            word_count = a.get("word_count", 0)
            orgs = len(a.get("entities", {}).get("ORG", []))

            for s in sectors:
                sector_features[s]["avg_sentiment"].append(sentiment)
                sector_features[s]["article_count"] += 1
                sector_features[s]["org_count"] += orgs
                sector_features[s]["avg_word_count"].append(word_count)

        if len(sector_features) < 3:
            return {"clusters": [], "total_sectors": len(sector_features), "message": "Insufficient sectors for clustering"}

        sector_names = list(sector_features.keys())
        X = []
        for s in sector_names:
            d = sector_features[s]
            X.append([
                float(np.mean(d["avg_sentiment"])) if d["avg_sentiment"] else 0.0,
                d["article_count"],
                d["org_count"],
                float(np.mean(d["avg_word_count"])) if d["avg_word_count"] else 0.0,
            ])

        Xs = StandardScaler().fit_transform(X)
        n_clusters = min(3, len(sector_names))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(Xs)

        clusters = defaultdict(list)
        for sector, lab in zip(sector_names, labels):
            clusters[int(lab)].append({
                "sector": sector,
                "avg_sentiment": round(float(np.mean(sector_features[sector]["avg_sentiment"])), 3),
                "article_count": sector_features[sector]["article_count"],
            })

        results = []
        for cid, members in clusters.items():
            avg_cluster_sent = float(np.mean([m["avg_sentiment"] for m in members])) if members else 0.0
            if avg_cluster_sent > 0.2:
                label = "High Performance Sectors"
            elif avg_cluster_sent < -0.1:
                label = "Challenged Sectors"
            else:
                label = "Stable Sectors"

            results.append({
                "cluster_id": cid,
                "label": label,
                "avg_sentiment": round(avg_cluster_sent, 3),
                "sectors": sorted(members, key=lambda x: x["article_count"], reverse=True),
            })

        return {"clusters": sorted(results, key=lambda x: x["avg_sentiment"], reverse=True), "total_sectors": len(sector_names)}
    
    # Add these methods to your AdvancedAnalytics class

    def correlation_analysis(self):
        """Analyze correlations between sectors (co-mentions)."""
        articles = self.db.all()
        sector_pairs = defaultdict(lambda: {"count": 0, "sentiments": []})
        
        for article in articles:
            sectors = article.get("sectors", [])
            sentiment = article.get("sentiment_score", 0)
            
            # For each pair of sectors in the same article
            for i, sector1 in enumerate(sectors):
                for sector2 in sectors[i + 1:]:
                    pair = tuple(sorted([sector1, sector2]))
                    sector_pairs[pair]["count"] += 1
                    sector_pairs[pair]["sentiments"].append(sentiment)
        
        # Find strongest correlations
        correlations = []
        for (sector1, sector2), data in sector_pairs.items():
            if data["count"] >= 2:  # At least 2 co-mentions
                avg_sentiment = float(np.mean(data["sentiments"]))
                correlations.append({
                    "sector1": sector1,
                    "sector2": sector2,
                    "co_occurrence_count": data["count"],
                    "avg_sentiment": round(avg_sentiment, 3),
                    "correlation_strength": "strong" if data["count"] >= 4 else "moderate",
                })
        
        correlations.sort(key=lambda x: x["co_occurrence_count"], reverse=True)
        
        return {
            "top_correlations": correlations[:15],
            "total_correlations": len(correlations),
        }


    def velocity_analysis(self):
        """Analyze rate of change in sentiment (velocity)."""
        articles = self.db.all()
        sector_timeline = defaultdict(lambda: defaultdict(list))
        
        for article in articles:
            timestamp = article.get("scraped_at") or article.get("updated_at")
            if not timestamp:
                continue
            
            try:
                dt = _parse_iso_dt(timestamp)
                if not dt:
                    continue
                date = str(dt.date())
                sentiment = article.get("sentiment_score", 0)
                sectors = article.get("sectors", [])
                
                for sector in sectors:
                    sector_timeline[sector][date].append(sentiment)
            except Exception:
                continue
        
        # Calculate velocity (rate of change)
        velocities = []
        for sector, dates in sector_timeline.items():
            sorted_dates = sorted(dates.keys())
            
            if len(sorted_dates) >= 2:
                recent_avg = float(np.mean(dates[sorted_dates[-1]]))
                previous_avg = float(np.mean(dates[sorted_dates[-2]])) if len(sorted_dates) > 1 else recent_avg
                velocity = recent_avg - previous_avg
                
                velocities.append({
                    "sector": sector,
                    "current_sentiment": round(recent_avg, 3),
                    "previous_sentiment": round(previous_avg, 3),
                    "velocity": round(velocity, 3),
                    "trend": "accelerating" if velocity > 0.1 else "decelerating" if velocity < -0.1 else "stable",
                    "data_points": len(sorted_dates),
                })
        
        velocities.sort(key=lambda x: abs(x["velocity"]), reverse=True)
        
        return {
            "sector_velocities": velocities,
            "fastest_improving": [v for v in velocities if v["velocity"] > 0.05],
            "fastest_declining": [v for v in velocities if v["velocity"] < -0.05],
        }


   

    def save_analytics(self, output_path="data/indicators/"):
        os.makedirs(output_path, exist_ok=True)

        trends = self.temporal_trend_analysis()
        with open(os.path.join(output_path, "temporal_trends.json"), "w", encoding="utf-8") as f:
            json.dump(trends, f, indent=2, ensure_ascii=False)

        anomalies = self.detect_anomalies()
        with open(os.path.join(output_path, "anomalies.json"), "w", encoding="utf-8") as f:
            json.dump(anomalies, f, indent=2, ensure_ascii=False)

        clusters = self.sector_clustering()
        with open(os.path.join(output_path, "sector_clusters.json"), "w", encoding="utf-8") as f:
            json.dump(clusters, f, indent=2, ensure_ascii=False)

        correlations = self.correlation_analysis()
        with open(os.path.join(output_path, "sector_correlations.json"), "w", encoding="utf-8") as f:
            json.dump(correlations, f, indent=2, ensure_ascii=False)

        velocity = self.velocity_analysis()
        with open(os.path.join(output_path, "sentiment_velocity.json"), "w", encoding="utf-8") as f:
            json.dump(velocity, f, indent=2, ensure_ascii=False)

        return {"trends": trends, "anomalies": anomalies, "clusters": clusters, "correlations": correlations, "velocity": velocity}
