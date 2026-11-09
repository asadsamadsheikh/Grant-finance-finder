"""
API Routes — Grant Search & Matching
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.models.schemas import GrantSearchRequest
from backend.services.eligibility_matcher import eligibility_matcher
from backend.services.grant_aggregator import CURATED_GRANTS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/grants", tags=["Grants"])


@router.post("/search")
async def search_grants(request: GrantSearchRequest):
    """
    Search and rank grant opportunities for a startup profile.
    Uses IBM Granite + IBM Watson NLU for intelligent matching.
    Returns ranked list with eligibility scores and AI analysis.
    """
    try:
        profile_dict = request.startup_profile.model_dump(mode="json")
        results = await eligibility_matcher.match_grants_to_startup(
            startup_profile=profile_dict,
            max_results=request.max_results,
            use_granite_deep_analysis=request.use_granite_analysis,
        )
        return {
            "success": True,
            "count": len(results),
            "grants": results,
            "startup_name": request.startup_profile.name,
        }
    except Exception as e:
        logger.error(f"Grant search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Grant search failed: {str(e)}")


@router.get("/all")
async def list_all_grants():
    """Return the full curated grant database."""
    return {"success": True, "count": len(CURATED_GRANTS), "grants": CURATED_GRANTS}


@router.get("/{grant_id}")
async def get_grant_detail(grant_id: str):
    """Fetch details for a specific grant by ID."""
    grant = next((g for g in CURATED_GRANTS if g["id"] == grant_id), None)
    if not grant:
        raise HTTPException(status_code=404, detail=f"Grant '{grant_id}' not found")
    return {"success": True, "grant": grant}
