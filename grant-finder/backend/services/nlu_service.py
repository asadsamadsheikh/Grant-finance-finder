"""
IBM Watson NLU Service
Uses IBM Watson Natural Language Understanding (Lite - FREE tier)
for keyword extraction, entity detection, and concept analysis on grant texts.
"""

import os
import logging
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class IBMNLUService:
    """
    IBM Watson NLU integration for semantic analysis of grant documents.
    Lite plan: 30,000 NLU items/month FREE.
    """

    PLACEHOLDER_KEYS = {"your_nlu_api_key_here", "", "your-api-key"}

    def __init__(self):
        self.api_key = os.getenv("IBM_NLU_API_KEY", "")
        self.url = os.getenv("IBM_NLU_URL", "")
        self.version = "2022-04-07"

    def _auth_headers(self) -> dict:
        import base64
        credentials = base64.b64encode(f"apikey:{self.api_key}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

    async def analyze_text(self, text: str) -> dict:
        """
        Run NLU analysis: keywords, entities, concepts, categories, sentiment.
        Returns structured NLU result dict.
        """
        if (
            not self.api_key
            or self.api_key in self.PLACEHOLDER_KEYS
            or not self.url
            or "your-instance-id" in self.url
        ):
            return self._fallback_analysis(text)

        endpoint = f"{self.url}/v1/analyze?version={self.version}"
        payload = {
            "text": text[:50000],  # NLU text limit
            "features": {
                "keywords": {"limit": 15, "sentiment": True, "relevance": True},
                "entities": {"limit": 10, "sentiment": True},
                "concepts": {"limit": 8},
                "categories": {"limit": 3},
                "sentiment": {"document": True},
            },
            "language": "en",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    endpoint, json=payload, headers=self._auth_headers()
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_nlu_result(data)
            except httpx.HTTPStatusError as e:
                logger.error(f"NLU API error: {e.response.status_code}")
                return self._fallback_analysis(text)
            except Exception as e:
                logger.error(f"NLU error: {e}")
                return self._fallback_analysis(text)

    def _parse_nlu_result(self, data: dict) -> dict:
        """Parse raw NLU API response into simplified structure."""
        keywords = [
            {"text": kw["text"], "relevance": kw.get("relevance", 0)}
            for kw in data.get("keywords", [])
        ]
        entities = [
            {"text": ent["text"], "type": ent.get("type", ""), "relevance": ent.get("relevance", 0)}
            for ent in data.get("entities", [])
        ]
        concepts = [c["text"] for c in data.get("concepts", [])]
        categories = [cat["label"].split("/")[-1] for cat in data.get("categories", [])]
        sentiment_score = data.get("sentiment", {}).get("document", {}).get("score", 0)

        return {
            "keywords": keywords,
            "entities": entities,
            "concepts": concepts,
            "categories": categories,
            "sentiment_score": sentiment_score,
            "top_keywords": [kw["text"] for kw in keywords[:5]],
        }

    def _fallback_analysis(self, text: str) -> dict:
        """
        Simple keyword extraction fallback when NLU is unavailable.
        Uses frequency-based approach with grant-specific stopwords.
        """
        import re
        from collections import Counter

        grant_stopwords = {
            "the", "and", "for", "are", "this", "that", "with", "from",
            "will", "have", "has", "been", "not", "they", "their", "which",
            "application", "grant", "funding", "may", "must", "shall", "also",
        }
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        filtered = [w for w in words if w not in grant_stopwords]
        top = Counter(filtered).most_common(10)

        return {
            "keywords": [{"text": w, "relevance": c / len(filtered)} for w, c in top],
            "entities": [],
            "concepts": [],
            "categories": [],
            "sentiment_score": 0,
            "top_keywords": [w for w, _ in top[:5]],
        }

    async def compute_similarity_score(
        self, startup_keywords: list[str], grant_keywords: list[str]
    ) -> float:
        """
        Compute keyword-based semantic similarity score between startup and grant.
        Returns float 0.0–1.0.
        """
        if not startup_keywords or not grant_keywords:
            return 0.0
        startup_set = set(kw.lower() for kw in startup_keywords)
        grant_set = set(kw.lower() for kw in grant_keywords)
        intersection = startup_set & grant_set
        union = startup_set | grant_set
        jaccard = len(intersection) / len(union) if union else 0.0
        # Boost for high-value grant terms
        high_value_terms = {"ai", "machine learning", "climate", "healthcare", "deep tech",
                            "sustainability", "fintech", "biotech", "edtech", "clean energy"}
        boost = sum(0.05 for term in intersection if any(hv in term for hv in high_value_terms))
        return min(1.0, jaccard + boost)


# Singleton instance
nlu_service = IBMNLUService()
