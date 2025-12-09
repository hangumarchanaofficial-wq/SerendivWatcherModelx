import spacy
from spacytextblob.spacytextblob import SpacyTextBlob
import re
import yaml

class NLPProcessor:
    def __init__(self, config_path="config/nlp_config.yaml"):
        # Load spaCy model
        self.nlp = spacy.load("en_core_web_sm")
        self.nlp.add_pipe('spacytextblob')
        
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.sector_keywords = self.config['sectors']
        self.sentiment_thresholds = self.config['sentiment']
    
    def clean_text(self, text):
        """Remove extra whitespace and special characters"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.,!?-]', '', text)
        return text.strip()
    
    def detect_sectors(self, text_lower, keywords):
        """Tag article with relevant business sectors"""
        sectors = []
        combined = text_lower + " " + " ".join(keywords)
        
        for sector, terms in self.sector_keywords.items():
            if any(term in combined for term in terms):
                sectors.append(sector)
        
        return sectors if sectors else ["general"]
    
    def enrich_article(self, title, text):
        """
        Process article and return enriched metadata
        Returns dict with sentiment, entities, keywords, sectors
        """
        # Clean
        text_cleaned = self.clean_text(text)
        
        # Process with spaCy (limit text length)
        doc = self.nlp(text_cleaned[:50000])
        
        # Sentiment
        sentiment_score = doc._.blob.polarity
        pos_thresh = self.sentiment_thresholds['positive_threshold']
        neg_thresh = self.sentiment_thresholds['negative_threshold']
        
        sentiment_label = "positive" if sentiment_score > pos_thresh else (
            "negative" if sentiment_score < neg_thresh else "neutral"
        )
        
        # Named entities
        entities = {"PERSON": [], "ORG": [], "GPE": [], "LOC": []}
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)
        
        # Remove duplicates from entities
        for key in entities:
            entities[key] = list(set(entities[key]))[:10]  # top 10
        
        # Keywords from noun chunks
        keywords = [chunk.text.lower() for chunk in doc.noun_chunks 
                    if len(chunk.text.split()) <= 3]
        keywords = list(set(keywords))[:15]
        
        # Detect sectors
        sectors = self.detect_sectors(text_cleaned.lower(), keywords)
        
        return {
            "text_cleaned": text_cleaned,
            "sentiment_score": round(sentiment_score, 3),
            "sentiment_label": sentiment_label,
            "entities": entities,
            "keywords": keywords,
            "sectors": sectors,
            "language": doc.lang_,
            "word_count": len(text_cleaned.split())
        }


