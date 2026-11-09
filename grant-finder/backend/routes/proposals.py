"""
API Routes — Proposal Generation
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ProposalRequest
from backend.services.proposal_generator import proposal_generator
from backend.services.cos_cache import cos_cache
from backend.services.grant_aggregator import CURATED_GRANTS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proposals", tags=["Proposals"])


@router.post("/generate")
async def generate_proposal(request: ProposalRequest):
    """
    Generate a full grant application proposal using IBM Granite AI.
    Covers: Executive Summary, Problem Statement, Solution, Innovation,
    Team, Implementation Plan, Outcomes, Budget Outline.
    ⚠️ Output is AI-generated — human review required before submission.
    """
    try:
        # Resolve grant data
        grant_data = request.grant_data
        if not grant_data:
            grant_data = next((g for g in CURATED_GRANTS if g["id"] == request.grant_id), None)
        if not grant_data:
            raise HTTPException(status_code=404, detail=f"Grant '{request.grant_id}' not found")

        profile_dict = request.startup_profile.model_dump(mode="json")
        proposal = await proposal_generator.generate_full_proposal(profile_dict, grant_data)

        # Generate cover letter if requested
        if request.include_cover_letter:
            try:
                cover_letter = await proposal_generator.generate_cover_letter(profile_dict, grant_data)
            except Exception as cl_err:
                logger.warning(f"Cover letter generation failed: {cl_err}; using template")
                name = profile_dict.get("name", "Our Startup")
                funder = grant_data.get("funder", "Grant Committee")
                g_title = grant_data.get("title", "this grant")
                cover_letter = (
                    f"Dear {funder} Review Committee,\n\n"
                    f"We are pleased to submit this application for {g_title}. "
                    f"{name} is an innovative startup building transformative solutions in the "
                    f"{profile_dict.get('industry', 'technology')} sector. "
                    f"Our work directly aligns with your organisation's mission, and we believe "
                    f"this grant will be a powerful catalyst for our growth and impact.\n\n"
                    f"Our team brings deep domain expertise, a validated approach, and an unwavering "
                    f"commitment to delivering measurable results. We are confident that {name} "
                    f"represents an outstanding investment opportunity for {funder}.\n\n"
                    f"We welcome the opportunity to discuss our proposal further. "
                    f"Thank you for your consideration.\n\nRespectfully,\nThe {name} Team"
                )
            proposal["cover_letter"] = cover_letter

        return {"success": True, "proposal": proposal}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proposal generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Proposal generation failed: {str(e)}")


@router.get("/{proposal_id}")
async def get_proposal(proposal_id: str):
    """Retrieve a previously generated proposal from IBM COS storage."""
    proposal = await cos_cache.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found or expired")
    return {"success": True, "proposal": proposal}
