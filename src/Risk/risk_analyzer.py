"""
Risk Analyzer - Analyzes business risks and opportunities based on district and operations
"""

class RiskAnalyzer:
    def __init__(self, routes_data, market_data, knowledge_graph, weather_data=None):
        # Handle data structures correctly
        self.routes_data = routes_data if isinstance(routes_data, list) else []
        self.market_data = market_data if isinstance(market_data, dict) else {}
        self.knowledge_graph = knowledge_graph if isinstance(knowledge_graph, list) else []
        self.weather_data = weather_data if isinstance(weather_data, list) else []
    
    def analyze(self, business_name, district, operations):
        """
        Comprehensive risk and opportunity analysis based on district
        
        Returns:
            dict with alerts, insights, and contextual data
        """
        alerts = []
        
        # 1. District-Specific Logistics Risks
        district_logistics = self._check_district_logistics(district, operations)
        alerts.extend(district_logistics)
        
        # 2. Market Trends & Opportunities
        market_alerts = self._check_market_insights(operations)
        alerts.extend(market_alerts)
        
        # 3. Knowledge Graph Business News
        news_alerts = self._check_knowledge_graph(operations)
        alerts.extend(news_alerts)
        
        # 4. District-Specific Risks
        district_alerts = self._check_district_risks(district, operations)
        alerts.extend(district_alerts)
        
        # 5. Weather-Related Risks for District
        weather_alerts = self._check_weather_risks(district, operations)
        alerts.extend(weather_alerts)
        
        return {
            "business_name": business_name,
            "district": district,
            "operations": operations,
            "alerts": alerts,
            "total_alerts": len(alerts),
            "district_summary": self._get_district_summary(district)
        }
    
    def _check_district_logistics(self, district, operations):
        """Check logistics risks specific to the district"""
        alerts = []
        
        # Check if business depends on logistics
        logistics_keywords = [
            'supply chain', 'logistics', 'transport', 'shipping',
            'delivery', 'import', 'export', 'distribution'
        ]
        
        has_logistics = any(
            any(keyword.lower() in op.lower() for keyword in logistics_keywords)
            for op in operations
        )
        
        if not has_logistics or not self.routes_data:
            return alerts
        
        # Find routes connected to this district
        district_routes = [
            r for r in self.routes_data 
            if district.lower() in r.get('district_start', '').lower() 
            or district.lower() in r.get('district_end', '').lower()
        ]
        
        if not district_routes:
            alerts.append({
                'title': f'Limited Transportation Data for {district}',
                'severity': 'medium',
                'description': f'Transportation monitoring data for {district} is limited. Consider alternative route planning.',
                'impact': 'May face challenges in real-time logistics tracking',
                'sources': ['Transportation Data', 'Route Monitoring']
            })
            return alerts
        
        # Check for delays
        delayed_routes = [r for r in district_routes if r.get('delay_minutes', 0) > 15]
        clear_routes = [r for r in district_routes if r.get('delay_minutes', 0) <= 0]
        
        if delayed_routes:
            top_delay = delayed_routes[0]
            alerts.append({
                'title': f"Logistics Delay in {district}: {top_delay['origin']} → {top_delay['destination']}",
                'severity': 'high' if top_delay['delay_minutes'] > 30 else 'medium',
                'description': f"Route experiencing {top_delay['delay_minutes']} minute delay. Live time: {top_delay['time_live']} vs Normal: {top_delay['time_normal']}",
                'impact': f"Shipment delays affecting {district} district. Consider rerouting or scheduling adjustments.",
                'sources': ['Transportation Data', f'{district} Traffic Monitoring']
            })
        
        if clear_routes and len(clear_routes) >= 3:
            alerts.append({
                'title': f'Favorable Logistics Conditions in {district}',
                'severity': 'low',
                'description': f"{len(clear_routes)} routes in {district} are operating ahead of schedule with minimal congestion",
                'impact': 'Excellent window for expedited shipments and inventory movement',
                'sources': ['Transportation Data', f'{district} Route Analysis']
            })
        
        return alerts
    
    def _check_market_insights(self, operations):
        """Analyze market trends for risks and opportunities"""
        alerts = []
        
        if not self.market_data or 'data' not in self.market_data:
            return alerts
        
        market_data = self.market_data['data']
        
        # USD/LKR Analysis
        if 'USD_LKR' in market_data:
            usd_data = market_data['USD_LKR']
            
            forex_sensitive = any(kw in ' '.join(operations).lower() 
                                 for kw in ['import', 'export', 'foreign', 'international'])
            
            if forex_sensitive:
                if 'Upward' in usd_data.get('next_day_bias', ''):
                    alerts.append({
                        'title': 'Currency Risk: LKR Weakening',
                        'severity': 'medium',
                        'description': f"USD/LKR at {usd_data['current_price']}, showing upward momentum. 7-day average: {usd_data['7_day_average']:.2f}",
                        'impact': 'Import costs may increase 2-4% this week; Exporters may benefit from better rates',
                        'sources': ['Forex Market', 'Currency Analytics']
                    })
        
        # Brent Oil Analysis
        if 'Brent_Oil' in market_data:
            oil_data = market_data['Brent_Oil']
            
            logistics_ops = any(kw in ' '.join(operations).lower() 
                               for kw in ['transport', 'logistics', 'delivery', 'shipping'])
            
            if logistics_ops:
                if 'BULLISH' in oil_data.get('trend_status', ''):
                    alerts.append({
                        'title': 'Rising Fuel Costs Alert',
                        'severity': 'high',
                        'description': f"Brent Oil at ${oil_data['current_price']}, trending upward from ${oil_data['7_day_average']:.2f}",
                        'impact': 'Transportation costs expected to rise 8-12% over next month',
                        'sources': ['Commodity Markets', 'Energy Data']
                    })
                elif 'BEARISH' in oil_data.get('trend_status', ''):
                    alerts.append({
                        'title': 'Fuel Cost Opportunity',
                        'severity': 'low',
                        'description': f"Brent Oil declining to ${oil_data['current_price']}. Down from ${oil_data['7_day_average']:.2f}",
                        'impact': 'Lock in fuel contracts now to capitalize on 5-8% lower prices',
                        'sources': ['Commodity Markets', 'Energy Data']
                    })
        
        return alerts
    
    def _check_knowledge_graph(self, operations):
        """Extract relevant business news from knowledge graph"""
        alerts = []
        
        if not self.knowledge_graph:
            return alerts
        
        # Search for relevant clusters
        relevant_clusters = []
        search_terms = [op.lower() for op in operations]
        
        for cluster in self.knowledge_graph:
            category = cluster.get('detected_category', '').lower()
            summary = cluster.get('summary_for_llm', '').lower()
            
            # Check if cluster is relevant
            if any(term in category or term in summary for term in search_terms):
                relevant_clusters.append(cluster)
        
        # Create insights from top clusters
        for cluster in relevant_clusters[:3]:
            sentiment = cluster.get('temporal_velocity_score', 0)
            
            if sentiment > 0.2:
                severity = 'low'  # Opportunity
                title_prefix = '📈 Business Opportunity'
            elif sentiment < -0.2:
                severity = 'high'  # Risk
                title_prefix = '⚠️ Market Challenge'
            else:
                severity = 'medium'
                title_prefix = '📊 Market Update'
            
            alerts.append({
                'title': f"{title_prefix}: {cluster['detected_category']}",
                'severity': severity,
                'description': f"{cluster['article_count']} recent articles detected. Key: {cluster['key_headlines'][0] if cluster['key_headlines'] else 'Industry developments'}",
                'impact': f"Sentiment score: {sentiment:.2f}. {'Positive momentum' if sentiment > 0 else 'Market headwinds'} in this sector.",
                'sources': ['News Analysis', 'Knowledge Graph']
            })
        
        return alerts
    
    def _check_district_risks(self, district, operations):
        """Generate district-specific contextual risks"""
        alerts = []
        
        # District-specific insights
        district_insights = {
            'Colombo': {
                'title': 'High Business Density - Competition Alert',
                'severity': 'medium',
                'description': 'Colombo has the highest concentration of businesses in Sri Lanka',
                'impact': 'Intense competition but access to best infrastructure and talent pool',
                'sources': ['District Analysis', 'Business Registry']
            },
            'Gampaha': {
                'title': 'Industrial Zone Proximity Advantage',
                'severity': 'low',
                'description': 'Gampaha district hosts major Export Processing Zones (Biyagama, Katunayake)',
                'impact': 'Excellent logistics connectivity and export infrastructure',
                'sources': ['District Analysis', 'Industrial Zones']
            },
            'Galle': {
                'title': 'Tourism Sector Dependency',
                'severity': 'medium',
                'description': 'Galle economy heavily influenced by tourism industry fluctuations',
                'impact': 'Monitor seasonal demand patterns and tourist arrivals',
                'sources': ['District Analysis', 'Tourism Board']
            },
            'Kandy': {
                'title': 'Central Hills Transportation Costs',
                'severity': 'medium',
                'description': 'Hill country logistics face higher fuel and maintenance costs',
                'impact': '15-20% higher transportation costs compared to coastal regions',
                'sources': ['District Analysis', 'Logistics Data']
            },
            'Jaffna': {
                'title': 'Emerging Market Opportunity',
                'severity': 'low',
                'description': 'Northern region showing strong economic growth post-conflict',
                'impact': 'First-mover advantage in underpenetrated markets',
                'sources': ['District Analysis', 'Economic Development']
            },
            'Hambantota': {
                'title': 'Port Infrastructure Development',
                'severity': 'low',
                'description': 'Hambantota Port and industrial zones offering new opportunities',
                'impact': 'Access to international shipping and SEZ benefits',
                'sources': ['District Analysis', 'Port Authority']
            },
            'Kurunegala': {
                'title': 'Agricultural Supply Chain Hub',
                'severity': 'low',
                'description': 'Strategic location connecting agricultural regions',
                'impact': 'Ideal for agro-processing and distribution businesses',
                'sources': ['District Analysis', 'Agriculture Ministry']
            },
            'Anuradhapura': {
                'title': 'Agriculture-Centric Economy',
                'severity': 'medium',
                'description': 'Economy primarily driven by agriculture and related industries',
                'impact': 'Weather-dependent risks; consider crop insurance',
                'sources': ['District Analysis', 'Agriculture Data']
            },
            'Trincomalee': {
                'title': 'Port Development Potential',
                'severity': 'low',
                'description': 'Trincomalee deep-water port offers strategic advantages',
                'impact': 'Long-term growth potential in maritime industries',
                'sources': ['District Analysis', 'Port Development']
            }
        }
        
        if district in district_insights:
            alerts.append(district_insights[district])
        else:
            # Generic district insight
            alerts.append({
                'title': f'{district} District Operations',
                'severity': 'medium',
                'description': f'Operating in {district} district with localized market dynamics',
                'impact': 'Monitor regional economic indicators and local infrastructure developments',
                'sources': ['District Analysis', 'Regional Data']
            })
        
        return alerts
    
    def _check_weather_risks(self, district, operations):
        """Check weather-related business risks for specific district"""
        alerts = []
        
        # Weather-sensitive operations
        weather_keywords = [
            'agriculture', 'tourism', 'construction', 'transport',
            'logistics', 'outdoor', 'shipping', 'farming'
        ]
        
        is_weather_sensitive = any(
            any(keyword.lower() in op.lower() for keyword in weather_keywords)
            for op in operations
        )
        
        if is_weather_sensitive and self.weather_data:
            # Find weather data for this district
            district_weather = [w for w in self.weather_data if district.lower() in w.get('District', '').lower()]
            
            if district_weather:
                heavy_rain_days = [w for w in district_weather if float(w.get('rainfall_mm', 0)) > 50]
                
                if heavy_rain_days:
                    alerts.append({
                        'title': f'Weather Risk in {district}: Heavy Rainfall Expected',
                        'severity': 'high',
                        'description': f"{len(heavy_rain_days)} days of heavy rain forecasted in {district} over next 7 days",
                        'impact': 'Potential disruptions to outdoor operations, transport delays, and supply chain bottlenecks',
                        'sources': ['Meteorology Department', f'{district} Weather Forecast']
                    })
        
        return alerts
    
    def _get_district_summary(self, district):
        """Summary of district-specific data"""
        if not self.routes_data:
            return {}
        
        # Find routes in this district
        district_routes = [
            r for r in self.routes_data 
            if district.lower() in r.get('district_start', '').lower() 
            or district.lower() in r.get('district_end', '').lower()
        ]
        
        clear_routes = [r for r in district_routes if r.get('delay_minutes', 0) <= 0]
        delayed_routes = [r for r in district_routes if r.get('delay_minutes', 0) > 0]
        
        return {
            'total_routes': len(district_routes),
            'clear_routes': len(clear_routes),
            'delayed_routes': len(delayed_routes),
            'district': district
        }
