"""
Pydantic data models for the Grant Finder API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class StartupStage(str, Enum):
    IDEA = "idea"
    PRE_SEED = "pre-seed"
    SEED = "seed"
    SERIES_A = "series-a"
    SERIES_B = "series-b"
    SERIES_C = "series-c"
    GROWTH = "growth"


class StartupProfile(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Startup name")
    description: str = Field(..., min_length=20, max_length=1000, description="What your startup does")
    industry: str = Field(..., min_length=2, max_length=100, description="Primary industry/sector")
    stage: StartupStage = Field(..., description="Current funding/development stage")
    location: str = Field(..., min_length=2, max_length=100, description="Country or region (e.g., 'USA', 'India')")
    team_size: Optional[str] = Field(default="1-5", description="Team size range")
    revenue: Optional[str] = Field(default="Pre-revenue", description="Annual revenue (e.g., '$50K', 'Pre-revenue')")
    target_market: Optional[str] = Field(default=None, description="Target customers/market")
    founded_year: Optional[str] = Field(default="2023", description="Year founded")
    problem: Optional[str] = Field(default=None, description="Key problem being solved")
    keywords: list[str] = Field(default_factory=list, description="Technology/domain keywords")

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v or []


class GrantSearchRequest(BaseModel):
    startup_profile: StartupProfile
    max_results: int = Field(default=8, ge=1, le=20)
    use_granite_analysis: bool = Field(default=True, description="Enable deep IBM Granite AI analysis")


class ProposalRequest(BaseModel):
    startup_profile: StartupProfile
    grant_id: str = Field(..., description="ID of the grant to generate proposal for")
    grant_data: Optional[dict] = Field(default=None, description="Full grant data (if available from search results)")
    include_cover_letter: bool = Field(default=True)


class HealthResponse(BaseModel):
    status: str
    ibm_granite: str
    ibm_nlu: str
    ibm_cos: str
    version: str = "1.0.0"
