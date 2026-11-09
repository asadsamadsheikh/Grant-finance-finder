"""
Grant Eligibility Matching Engine
Combines IBM Granite LLM semantic reasoning + IBM Watson NLU keyword scoring
+ rule-based heuristics to rank and match grants to a startup profile.
"""

import logging
import asyncio
from typing import Optional
from .granite_service import granite_service
from .nlu_service import nlu_service
from .grant_aggregator import grant_aggregator, CURATED_GRANTS, _location_matches

logger = logging.getLogger(__name__)

# Funding stage hierarchy for compatibility scoring
STAGE_HIERARCHY = {
    "idea": 0, "pre-seed": 1, "seed": 2, "series-a": 3, "series-b": 4, "series-c": 5, "growth": 6
}

INDUSTRY_ALIASES = {
    "artificial intelligence": ["ai", "machine learning", "deep learning", "ml", "nlp"],
    "clean energy": ["renewable energy", "solar", "wind", "battery", "ev", "electric vehicle", "climate tech"],
    "healthtech": ["health", "medical", "medtech", "biotech", "pharma", "digital health"],
    "fintech": ["finance", "financial technology", "payments", "banking", "insurtech"],
    "edtech": ["education technology", "e-learning", "online learning"],
    "agritech": ["agriculture", "farming", "food tech", "precision agriculture"],
    "saas": ["software as a service", "cloud software", "b2b software", "enterprise software"],
    "deep tech": ["quantum", "robotics", "nanotechnology", "semiconductors", "advanced materials"],
}


class EligibilityMatcher:
    """
    Multi-layer grant matching engine:
    Layer 1: Rule-based hard filters (stage, location)
    Layer 2: IBM Watson NLU keyword similarity scoring
    Layer 3: IBM Granite LLM deep eligibility reasoning (for top candidates)
    """

    async def match_grants_to_startup(
        self,
        startup_profile: dict,
        max_results: int = 8,
        use_granite_deep_analysis: bool = True,
    ) -> list[dict]:
        """
        Main matching pipeline. Returns ranked list of grant matches
        with scores, eligibility flags, and Granite AI analysis.
        """
        industry = startup_profile.get("industry", "")
        stage = startup_profile.get("stage", "")
        location = startup_profile.get("location", "")
        query = startup_profile.get("description", "")[:200]

        # Step 1: Aggregate all available grants
        all_grants = await grant_aggregator.aggregate(
            query=query, industry=industry, stage=stage, location=location
        )

        if not all_grants:
            all_grants = CURATED_GRANTS  # Final fallback

        # Step 2: Rule-based pre-filtering
        pre_filtered = self._rule_based_filter(startup_profile, all_grants)

        # Step 3: NLU keyword scoring
        startup_keywords = startup_profile.get("keywords", []) + [industry, query]
        scored_grants = await self._nlu_score_grants(startup_keywords, pre_filtered)

        # Sort by combined score descending
        scored_grants.sort(key=lambda x: x["_score"], reverse=True)
        top_candidates = scored_grants[:max_results]

        # Step 4: IBM Granite deep analysis on top N candidates
        if use_granite_deep_analysis and top_candidates:
            top_candidates = await self._granite_deep_analyze(startup_profile, top_candidates)

        # Clean internal scoring fields
        results = []
        for g in top_candidates:
            grant = {k: v for k, v in g.items() if not k.startswith("_")}
            grant["match_score"] = g.get("_score", 50)
            grant["granite_analysis"] = g.get("_granite_analysis", {})
            results.append(grant)

        return results

    def _rule_based_filter(self, startup: dict, grants: list[dict]) -> list[dict]:
        """Hard filter: stage compatibility + location compatibility."""
        startup_stage = startup.get("stage", "").lower()
        startup_location = startup.get("location", "").lower()
        startup_stage_num = STAGE_HIERARCHY.get(startup_stage, -1)
        results = []

        for grant in grants:
            eligible_stages = [s.lower() for s in grant.get("eligible_stages", ["all"])]
            eligible_locs = [l.lower() for l in grant.get("eligible_locations", ["global"])]

            # Stage check
            if "all" not in eligible_stages and startup_stage:
                grant_stage_nums = [STAGE_HIERARCHY.get(s, -1) for s in eligible_stages]
                if startup_stage_num != -1 and startup_stage_num not in grant_stage_nums:
                    # Allow ±1 stage flexibility
                    close_match = any(abs(startup_stage_num - gn) <= 1 for gn in grant_stage_nums if gn != -1)
                    if not close_match:
                        continue

            # Location check — use smart alias-aware matching (city -> country resolution)
            location_ok = _location_matches(startup_location, grant.get("eligible_locations", ["global"]))
            if not location_ok and startup_location:
                continue

            results.append(grant)

        return results if results else grants  # If too strict, return all

    async def _nlu_score_grants(
        self, startup_keywords: list[str], grants: list[dict]
    ) -> list[dict]:
        """
        Score each grant using IBM Watson NLU keyword similarity.
        Augments grant data with _score and _nlu_keywords fields.
        """
        # Get startup NLU analysis
        startup_text = " ".join(filter(None, startup_keywords))
        startup_nlu = await nlu_service.analyze_text(startup_text)
        startup_kw = startup_nlu.get("top_keywords", startup_keywords[:5])

        scored = []
        for grant in grants:
            grant_text = f"{grant.get('title', '')} {grant.get('description', '')} {' '.join(grant.get('focus_areas', []))}"
            grant_nlu = await nlu_service.analyze_text(grant_text)
            grant_kw = grant_nlu.get("top_keywords", [])

            similarity = await nlu_service.compute_similarity_score(startup_kw, grant_kw)
            base_score = similarity * 60  # NLU contributes up to 60 points

            # Industry alignment bonus (up to 25 points)
            industry_score = self._industry_alignment_score(
                startup_keywords, grant.get("eligible_industries", [])
            )
            # Stage alignment bonus (up to 15 points)
            stage_score = self._stage_alignment_score(
                grant.get("eligible_stages", ["all"])
            )

            total_score = min(100, int(base_score + industry_score + stage_score))
            grant["_score"] = total_score
            grant["_nlu_keywords"] = grant_kw
            scored.append(grant)

        return scored

    def _industry_alignment_score(self, startup_keywords: list[str], grant_industries: list[str]) -> float:
        """Score 0–25 based on industry keyword alignment including aliases."""
        if not grant_industries:
            return 12.5
        if "all sectors" in [gi.lower() for gi in grant_industries]:
            return 15.0

        startup_text = " ".join(kw.lower() for kw in startup_keywords)
        for grant_industry in grant_industries:
            gi_lower = grant_industry.lower()
            if gi_lower in startup_text:
                return 25.0
            # Check aliases
            for canonical, aliases in INDUSTRY_ALIASES.items():
                if gi_lower == canonical or gi_lower in aliases:
                    if canonical in startup_text or any(alias in startup_text for alias in aliases):
                        return 20.0
        return 5.0

    def _stage_alignment_score(self, grant_stages: list[str]) -> float:
        """Score 0–15 based on stage alignment."""
        if "all" in grant_stages or not grant_stages:
            return 10.0
        return 15.0 if len(grant_stages) <= 2 else 12.0  # More specific = better match when matched

    async def _granite_deep_analyze(
        self, startup_profile: dict, top_grants: list[dict]
    ) -> list[dict]:
        """
        Use IBM Granite LLM to deeply analyze eligibility for top 3 candidates.
        Runs concurrently for speed.
        """
        # Only run Granite on top 3 to save API quota
        granite_candidates = top_grants[:3]
        other_grants = top_grants[3:]

        async def analyze_one(grant: dict) -> dict:
            description = f"{grant.get('title', '')}\n{grant.get('description', '')}\nRequirements: {', '.join(grant.get('requirements', []))}"
            try:
                analysis = await granite_service.analyze_grant_eligibility(description, startup_profile)
                grant["_granite_analysis"] = analysis
                # Blend Granite match_score with NLU score
                granite_score = analysis.get("match_score", grant["_score"])
                grant["_score"] = int(grant["_score"] * 0.4 + granite_score * 0.6)
            except Exception as e:
                logger.warning(f"Granite analysis failed for {grant.get('id', '')}: {e}")
                grant["_granite_analysis"] = {}
            return grant

        analyzed = await asyncio.gather(*[analyze_one(g) for g in granite_candidates])
        return list(analyzed) + other_grants


# Singleton
eligibility_matcher = EligibilityMatcher()
