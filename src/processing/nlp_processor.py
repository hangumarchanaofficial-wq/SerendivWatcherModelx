import spacy
from spacytextblob.spacytextblob import SpacyTextBlob
import re
import yaml
import requests
from collections import Counter


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
        
        # LLM settings
        self.use_llm_validation = True  # Set to False to disable LLM
        self.llm_api_url = "http://localhost:11434/api/generate"
        self.llm_model = "gemma3:1b"
        self.min_confidence = 3  # Higher threshold since LLM will validate
    
    def clean_text(self, text):
        """Remove extra whitespace and special characters"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.,!?-]', '', text)
        return text.strip()
    
    def detect_primary_sector_keywords(self, title, text_lower, keywords):
        """
        Step 1: Keyword-based scoring to find top 2-3 candidate sectors.
        Fast initial filter.
        """
        title_lower = title.lower()
        combined_text = title_lower + " " + text_lower
        keyword_text = " ".join(keywords)
        
        sector_scores = {}
        
        for sector, terms in self.sector_keywords.items():
            score = 0
            
            for term in terms:
                # Title matches worth 3x
                if term in title_lower:
                    score += 3
                # Body text matches
                elif term in combined_text:
                    score += 1
                # Keyword matches
                elif term in keyword_text:
                    score += 1
            
            if score > 0:
                sector_scores[sector] = score
        
        # Sort by score, return top 3 candidates
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_sectors[:3] if sorted_sectors else []
    
    def _call_llm(self, prompt):
        """Call local Ollama LLM."""
        try:
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            }
            response = requests.post(self.llm_api_url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "").strip().lower()
        except Exception as e:
            print(f"  LLM error: {e}")
            return None
    
    def validate_sector_with_llm(self, title, text_sample, candidate_sectors):
        """
        Step 2: Use LLM to pick the BEST sector from top candidates.
        LLM reads context and makes final decision.
        
        Args:
            title: Article title
            text_sample: First 1000 words of article
            candidate_sectors: List of (sector, score) tuples from keyword matching
            
        Returns:
            Best sector name (string)
        """
        if not candidate_sectors:
            return "general"
        
        # If only one strong candidate, no need for LLM
        if len(candidate_sectors) == 1 and candidate_sectors[0][1] >= 5:
            return candidate_sectors[0][0]
        
        # Prepare sector options for LLM
        sector_options = [s[0] for s in candidate_sectors]
        sector_list = ", ".join(sector_options)
        
        prompt = f"""You are classifying Sri Lankan business news articles into sectors.

ARTICLE TITLE: {title}

ARTICLE EXCERPT (first 1000 words):
{text_sample[:5000]}

CANDIDATE SECTORS (from keyword analysis): {sector_list}

TASK: Choose the ONE most relevant primary sector for this article from the candidates above.

RULES:
1. Choose the sector that the article PRIMARILY focuses on
2. If the article is about government policy affecting tourism, choose "government" (the policy maker)
3. If the article is about a company in a specific industry, choose that industry sector
4. Only respond with ONE sector name from the candidate list
5. If none are truly relevant, respond with "general"

RESPOND WITH: Only the sector name, nothing else.

ANSWER:"""

        llm_response = self._call_llm(prompt)
        
        if not llm_response:
            # LLM failed, use keyword-based top choice
            return candidate_sectors[0][0]
        
        # Clean LLM response
        llm_sector = llm_response.strip().lower()
        
        # Validate LLM picked one of our candidates
        if llm_sector in sector_options:
            return llm_sector
        
        # Check if LLM said "general"
        if "general" in llm_sector:
            return "general"
        
        # LLM gave invalid response, fallback to keyword top choice
        print(f"  LLM gave unexpected response: '{llm_response}', using keyword match")
        return candidate_sectors[0][0]
    
    def enrich_article(self, title, text):
        """
        Process article with hybrid approach:
        1. Keyword matching finds top candidates (fast)
        2. LLM validates and picks best one (accurate)
        """
        # Clean
        text_cleaned = self.clean_text(text)
        
        # Process with spaCy
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
        
        for key in entities:
            entities[key] = list(set(entities[key]))[:10]
        
        # Keywords from noun chunks
        keywords = [chunk.text.lower() for chunk in doc.noun_chunks 
                    if len(chunk.text.split()) <= 3]
        keywords = list(set(keywords))[:15]
        
        # STEP 1: Keyword-based candidate detection (fast)
        candidate_sectors = self.detect_primary_sector_keywords(
            title, text_cleaned.lower(), keywords
        )
        
        # STEP 2: LLM validation (accurate)
        if self.use_llm_validation and candidate_sectors:
            text_sample = (title + ". " + text_cleaned)[:1000]
            primary_sector = self.validate_sector_with_llm(
                title, text_sample, candidate_sectors
            )
            confidence = candidate_sectors[0][1]  # Top keyword score
        elif candidate_sectors:
            # No LLM, use top keyword match
            primary_sector = candidate_sectors[0][0]
            confidence = candidate_sectors[0][1]
        else:
            # No matches at all
            primary_sector = "general"
            confidence = 0
        
        return {
            "text_cleaned": text_cleaned,
            "sentiment_score": round(sentiment_score, 3),
            "sentiment_label": sentiment_label,
            "entities": entities,
            "keywords": keywords,
            "sectors": [primary_sector],  # Single sector
            "sector_confidence": confidence,
            "sector_candidates": [s[0] for s in candidate_sectors],  # For debugging
            "language": doc.lang_,
            "word_count": len(text_cleaned.split())
        }

