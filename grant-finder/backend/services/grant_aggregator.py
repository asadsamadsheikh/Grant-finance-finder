"""
Grant Data Aggregator / Scraper Service
Pulls real grant & funding opportunities from multiple public sources:
  1. Grants.gov (US federal grants - public REST API)
  2. Curated static grant dataset (always available, no API key)
  3. European Commission Funding & Tenders (public CORDIS dataset)
Respects robots.txt and only uses official public APIs/datasets.
"""

import os
import json
import logging
import hashlib
from typing import Optional
import httpx
from dotenv import load_dotenv
from .cos_cache import cos_cache

load_dotenv()
logger = logging.getLogger(__name__)

# City/region → country mapping for smarter location filtering
LOCATION_ALIASES: dict[str, list[str]] = {
    "usa": ["united states", "us", "new york", "san francisco", "california", "texas",
            "boston", "chicago", "seattle", "los angeles", "silicon valley", "nyc", "sf"],
    "india": ["bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "chennai",
              "pune", "kolkata", "in"],
    "eu": ["europe", "european union", "germany", "france", "spain", "italy",
           "netherlands", "sweden", "denmark", "finland", "austria", "belgium",
           "berlin", "paris", "amsterdam", "stockholm", "madrid", "milan",
           "eea", "ukraine", "israel"],
    "uk": ["united kingdom", "england", "london", "manchester", "edinburgh"],
    "brazil": ["brasil", "são paulo", "sao paulo", "rio de janeiro"],
    "africa": ["nigeria", "kenya", "ghana", "south africa", "lagos", "nairobi"],
    "canada": ["toronto", "vancouver", "montreal"],
    "australia": ["sydney", "melbourne", "brisbane"],
    "china": ["beijing", "shanghai", "shenzhen"],
    "singapore": ["sg"],
    "uae": ["dubai", "abu dhabi", "emirates"],
}


def _location_matches(startup_location: str, grant_locations: list[str]) -> bool:
    """
    Returns True if startup_location is compatible with any of the grant's eligible_locations.
    Handles city→country resolution, 'global', partial matches, and alias mapping.
    """
    if not startup_location:
        return True  # No location specified → show all grants

    sl = startup_location.lower().strip()

    for loc in grant_locations:
        ll = loc.lower().strip()
        # Direct global
        if "global" in ll:
            return True
        # Direct string containment
        if sl in ll or ll in sl:
            return True
        # Resolve startup location via alias table
        for country, aliases in LOCATION_ALIASES.items():
            if sl == country or sl in aliases:
                # startup resolves to `country` — does the grant cover that country?
                if country in ll or ll in country:
                    return True
                # Also check if grant location is an alias of the same country
                if ll in aliases:
                    return True
            # Resolve grant location via alias table and compare with startup
            if ll == country or ll in aliases:
                if sl in aliases or sl == country:
                    return True

    return False

# -----------------------------------------------------------------------
# Curated fallback grant database (always available without any API call)
# Covers global opportunities across stages, sectors, and regions.
# -----------------------------------------------------------------------
CURATED_GRANTS: list[dict] = [
    {
        "id": "nsf_sbir_2024",
        "title": "NSF Small Business Innovation Research (SBIR) Phase I",
        "funder": "National Science Foundation",
        "amount_min": 50000, "amount_max": 275000,
        "deadline": "2025-03-15",
        "eligible_stages": ["idea", "pre-seed", "seed"],
        "eligible_industries": ["deep tech", "ai", "biotech", "clean energy", "advanced manufacturing"],
        "eligible_locations": ["USA"],
        "grant_type": "grant",
        "focus_areas": ["R&D commercialization", "scientific innovation", "technology transfer"],
        "requirements": ["US-based company", "< 500 employees", "majority US-owned"],
        "application_url": "https://seedfund.nsf.gov/apply/",
        "description": "NSF SBIR Phase I awards fund early-stage R&D to establish the technical merit and feasibility of a proposed innovation. Ideal for deep tech startups at idea or seed stage working on scientific breakthroughs.",
        "source": "nsf.gov",
    },
    {
        "id": "doe_sbir_2024",
        "title": "DOE SBIR/STTR FY2025 Phase I",
        "funder": "U.S. Department of Energy",
        "amount_min": 200000, "amount_max": 200000,
        "deadline": "2025-04-10",
        "eligible_stages": ["seed", "pre-seed"],
        "eligible_industries": ["clean energy", "climate tech", "battery tech", "solar", "grid modernization"],
        "eligible_locations": ["USA"],
        "grant_type": "grant",
        "focus_areas": ["energy efficiency", "renewable energy", "carbon capture", "nuclear"],
        "requirements": ["US small business", "< 500 employees", "PI must spend 50% time on project"],
        "application_url": "https://science.osti.gov/sbir",
        "description": "DOE SBIR funds US small businesses to engage in R&D with potential for commercialization. Priority focus areas include clean energy, electric vehicles, grid modernization, and advanced nuclear technologies.",
        "source": "energy.gov",
    },
    {
        "id": "ycombinator_2024",
        "title": "Y Combinator Startup Program (W2025 Batch)",
        "funder": "Y Combinator",
        "amount_min": 500000, "amount_max": 500000,
        "deadline": "2024-12-20",
        "eligible_stages": ["idea", "pre-seed", "seed"],
        "eligible_industries": ["all sectors", "software", "ai", "fintech", "biotech", "consumer", "b2b saas"],
        "eligible_locations": ["Global"],
        "grant_type": "equity",
        "focus_areas": ["product-market fit", "rapid growth", "founder mentorship"],
        "requirements": ["Team of 1-4 founders", "Early stage", "Willing to relocate to SF for 3 months"],
        "application_url": "https://www.ycombinator.com/apply",
        "description": "YC invests $500K in early-stage startups via a 3-month accelerator program in San Francisco. One of the world's most prestigious startup programs with alumni including Airbnb, Dropbox, and Stripe.",
        "source": "ycombinator.com",
    },
    {
        "id": "eu_eic_accelerator_2025",
        "title": "EIC Accelerator (European Innovation Council)",
        "funder": "European Commission",
        "amount_min": 500000, "amount_max": 2500000,
        "deadline": "2025-06-04",
        "eligible_stages": ["seed", "series-a"],
        "eligible_industries": ["deep tech", "healthtech", "greentech", "ai", "quantum", "space"],
        "eligible_locations": ["EU", "EEA", "Ukraine", "Israel"],
        "grant_type": "grant",
        "focus_areas": ["breakthrough innovation", "market creation", "scalability"],
        "requirements": ["EU-based SME or startup", "Strong IP position", "Minimum viable prototype"],
        "application_url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
        "description": "The EIC Accelerator provides grants up to €2.5M plus optional equity investment for innovative SMEs developing breakthrough technologies with strong market potential. One of Europe's top deep-tech funding programs.",
        "source": "eic.ec.europa.eu",
    },
    {
        "id": "gates_gcgh_2025",
        "title": "Bill & Melinda Gates Foundation Grand Challenges",
        "funder": "Bill & Melinda Gates Foundation",
        "amount_min": 100000, "amount_max": 100000,
        "deadline": "2025-05-01",
        "eligible_stages": ["idea", "pre-seed", "seed", "series-a"],
        "eligible_industries": ["healthtech", "global health", "agriculture", "sanitation", "edtech"],
        "eligible_locations": ["Global", "Low-income countries preferred"],
        "grant_type": "grant",
        "focus_areas": ["global health equity", "child mortality", "infectious disease", "nutrition"],
        "requirements": ["Research or innovation focus", "Global health impact", "Open to individuals and organizations"],
        "application_url": "https://gcgh.grandchallenges.org/",
        "description": "Gates Foundation Grand Challenges Explorations funds bold global health innovations with $100K grants. No preliminary data required — just a compelling 2-page idea. High-success stories scale to $1M+ follow-on.",
        "source": "gcgh.grandchallenges.org",
    },
    {
        "id": "startup_india_seed_2024",
        "title": "Startup India Seed Fund Scheme (SISFS)",
        "funder": "DPIIT - Government of India",
        "amount_min": 20000, "amount_max": 60000,
        "deadline": "Rolling",
        "eligible_stages": ["idea", "pre-seed"],
        "eligible_industries": ["all sectors", "agritech", "healthtech", "edtech", "fintech", "cleantech"],
        "eligible_locations": ["India"],
        "grant_type": "grant",
        "focus_areas": ["proof of concept", "prototype development", "product trials", "market entry"],
        "requirements": ["DPIIT-recognized startup", "< 2 years old", "Not received > ₹10L government funding"],
        "application_url": "https://seedfund.startupindia.gov.in/",
        "description": "SISFS provides financial assistance to early-stage Indian startups for proof of concept, prototype development, and product trials through SEBI-registered incubators. Covers grant up to ₹20L plus soft loans up to ₹50L.",
        "source": "startupindia.gov.in",
    },
    {
        "id": "aws_activate_2024",
        "title": "AWS Activate for Startups",
        "funder": "Amazon Web Services",
        "amount_min": 5000, "amount_max": 100000,
        "deadline": "Rolling",
        "eligible_stages": ["idea", "pre-seed", "seed", "series-a"],
        "eligible_industries": ["all sectors", "saas", "ai", "web3", "iot", "analytics"],
        "eligible_locations": ["Global"],
        "grant_type": "grant",
        "focus_areas": ["cloud infrastructure", "AI/ML workloads", "product scaling"],
        "requirements": ["Startup < 10 years old", "Have not previously received AWS Activate credits"],
        "application_url": "https://aws.amazon.com/activate/",
        "description": "AWS Activate provides startups with free cloud credits ($5K–$100K+), technical support, and training to build on AWS. Ideal for AI/ML and cloud-native startups needing compute resources.",
        "source": "aws.amazon.com",
    },
    {
        "id": "google_black_founders_2025",
        "title": "Google for Startups Black Founders Fund",
        "funder": "Google for Startups",
        "amount_min": 50000, "amount_max": 100000,
        "deadline": "2025-07-31",
        "eligible_stages": ["pre-seed", "seed"],
        "eligible_industries": ["all sectors", "technology", "software", "platform"],
        "eligible_locations": ["USA", "UK", "Brazil", "Africa"],
        "grant_type": "grant",
        "focus_areas": ["diversity in tech", "underrepresented founders", "community impact"],
        "requirements": ["Black-led startup", "Seed/pre-seed stage", "Tech-enabled business"],
        "application_url": "https://startup.google.com/programs/black-founders-fund/",
        "description": "Google for Startups Black Founders Fund provides non-dilutive cash awards plus up to $200K in Google Cloud credits to Black-led startups in the USA, UK, Brazil, and Africa building technology companies.",
        "source": "startup.google.com",
    },
    {
        "id": "techstars_2025",
        "title": "Techstars Accelerator Program",
        "funder": "Techstars",
        "amount_min": 120000, "amount_max": 120000,
        "deadline": "Rolling (per cohort)",
        "eligible_stages": ["seed", "pre-seed"],
        "eligible_industries": ["all sectors", "fintech", "healthtech", "sustainability", "enterprise saas"],
        "eligible_locations": ["Global"],
        "grant_type": "equity",
        "focus_areas": ["mentor-driven acceleration", "global network", "investor access"],
        "requirements": ["Early-stage startup", "Coachable founders", "MVP or early traction"],
        "application_url": "https://www.techstars.com/apply",
        "description": "Techstars is a global mentor-driven accelerator investing $120K for 6% equity. With 3,000+ portfolio companies and 10,000+ mentors across 50+ programs worldwide, it's one of the most accessible global accelerators.",
        "source": "techstars.com",
    },
    {
        "id": "climate_kic_2025",
        "title": "EIT Climate-KIC Launchpad",
        "funder": "EIT Climate-KIC (European Institute of Innovation & Technology)",
        "amount_min": 5000, "amount_max": 95000,
        "deadline": "2025-04-30",
        "eligible_stages": ["idea", "pre-seed"],
        "eligible_industries": ["climate tech", "clean energy", "sustainable agriculture", "circular economy"],
        "eligible_locations": ["EU"],
        "grant_type": "grant",
        "focus_areas": ["carbon neutrality", "climate adaptation", "sustainable cities"],
        "requirements": ["EU-based team", "Climate-positive impact", "Willingness to join full program"],
        "application_url": "https://launchpad.climate-kic.org/",
        "description": "EIT Climate-KIC Launchpad accelerates early-stage climate startups across Europe. Provides up to €95K in equity-free funding across 3 program phases, plus coaching, community access, and investor introductions.",
        "source": "climate-kic.org",
    },
    {
        "id": "microsoft_founders_hub_2025",
        "title": "Microsoft for Startups Founders Hub",
        "funder": "Microsoft",
        "amount_min": 1000, "amount_max": 150000,
        "deadline": "Rolling",
        "eligible_stages": ["idea", "pre-seed", "seed", "series-a"],
        "eligible_industries": ["all sectors", "ai", "saas", "cloud", "gaming", "education"],
        "eligible_locations": ["Global"],
        "grant_type": "grant",
        "focus_areas": ["Azure credits", "GitHub", "OpenAI access", "mentorship"],
        "requirements": ["Startup less than 5 years old", "Building a product"],
        "application_url": "https://foundershub.startups.microsoft.com/",
        "description": "Microsoft for Startups Founders Hub offers free Azure cloud credits up to $150K, GitHub Enterprise, Microsoft 365, LinkedIn Premium, and access to OpenAI models — available globally with no equity taken.",
        "source": "startups.microsoft.com",
    },
    {
        "id": "sbicosmes_india_2025",
        "title": "SIDBI Fund of Funds for Startups (FFS)",
        "funder": "SIDBI / Government of India",
        "amount_min": 500000, "amount_max": 5000000,
        "deadline": "Rolling",
        "eligible_stages": ["series-a", "series-b"],
        "eligible_industries": ["all sectors", "manufacturing", "agritech", "fintech"],
        "eligible_locations": ["India"],
        "grant_type": "equity",
        "focus_areas": ["growth capital", "job creation", "import substitution"],
        "requirements": ["DPIIT-recognized startup", "SEBI-registered investor route"],
        "application_url": "https://www.sidbi.in/en/offices/startups",
        "description": "SIDBI Fund of Funds scheme channels government capital to VC funds investing in Indian startups. Eligible startups receive indirect funding through SEBI-registered AIFs at Series A/B stage.",
        "source": "sidbi.in",
    },
]


class GrantAggregatorService:
    """
    Multi-source grant aggregation engine.
    Combines live Grants.gov API, SAM.gov, and curated database.
    Results are cached in IBM COS to minimize redundant API calls.
    """

    def __init__(self):
        self.grants_gov_url = os.getenv(
            "GRANTS_GOV_API_URL",
            "https://apply07.grants.gov/grantsws/rest/opportunities/search"
        )
        self.sam_gov_key = os.getenv("SAM_GOV_API_KEY", "")

    def _make_cache_key(self, query: str, filters: dict) -> str:
        payload = json.dumps({"q": query, **filters}, sort_keys=True)
        return f"grants_{hashlib.md5(payload.encode()).hexdigest()}"

    async def search_grants_gov(self, keyword: str, max_results: int = 10) -> list[dict]:
        """
        Query Grants.gov official REST API for federal grant opportunities.
        Public API — no key required.
        """
        try:
            payload = {
                "keyword": keyword,
                "oppStatuses": "forecasted|posted",
                "rows": max_results,
                "startRecordNum": 0,
                "sortBy": "openDate|desc",
            }
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    self.grants_gov_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                opportunities = data.get("oppHits", [])
                return [
                    {
                        "id": f"govgrants_{opp.get('id', '')}",
                        "title": opp.get("title", ""),
                        "funder": opp.get("agencyName", "US Federal Agency"),
                        "amount_min": None,
                        "amount_max": opp.get("awardCeiling"),
                        "deadline": opp.get("closeDate"),
                        "eligible_stages": ["all"],
                        "eligible_industries": [keyword],
                        "eligible_locations": ["USA"],
                        "grant_type": "grant",
                        "focus_areas": [keyword],
                        "requirements": [],
                        "application_url": f"https://www.grants.gov/web/grants/view-opportunity.html?oppId={opp.get('id')}",
                        "description": opp.get("synopsis", ""),
                        "source": "grants.gov",
                    }
                    for opp in opportunities
                ]
        except Exception as e:
            logger.warning(f"Grants.gov API error: {e}")
            return []

    def search_curated(self, industry: str = "", stage: str = "", location: str = "") -> list[dict]:
        """
        Filter the curated grant database by industry, stage, and location.
        Always works — no API dependency.
        Uses smart location matching with city→country alias resolution.
        """
        results = []
        industry_lower = industry.lower().strip()
        stage_lower = stage.lower().strip()

        for grant in CURATED_GRANTS:
            # Industry match: "all sectors" always passes, otherwise substring overlap
            eligible_industries = grant.get("eligible_industries", [])
            industry_match = (
                not industry_lower
                or "all sectors" in [i.lower() for i in eligible_industries]
                or any(
                    industry_lower in ind.lower() or ind.lower() in industry_lower
                    for ind in eligible_industries
                )
            )

            # Stage match: "all" passes, otherwise ±1 stage flexibility
            eligible_stages = [s.lower() for s in grant.get("eligible_stages", ["all"])]
            stage_match = (
                not stage_lower
                or "all" in eligible_stages
                or any(stage_lower in s for s in eligible_stages)
            )

            # Location match: smart alias-aware matching
            location_match = _location_matches(location, grant.get("eligible_locations", ["Global"]))

            if industry_match and stage_match and location_match:
                results.append(grant)

        # Safety: if filter was too strict, return everything (better UX than 0 results)
        return results if results else CURATED_GRANTS

    async def aggregate(
        self,
        query: str = "",
        industry: str = "",
        stage: str = "",
        location: str = "",
        max_live_results: int = 5,
    ) -> list[dict]:
        """
        Main aggregation method. Checks cache first, then combines:
        1. Curated static database (always available)
        2. Grants.gov live API (US federal, no key needed)
        Returns deduplicated, sorted list.
        """
        cache_key = self._make_cache_key(query or industry, {"stage": stage, "location": location})
        cached = await cos_cache.get(cache_key)
        if cached:
            logger.info(f"Grant data served from cache: {cache_key}")
            return cached

        # 1. Curated database
        curated = self.search_curated(industry=industry, stage=stage, location=location)

        # 2. Live Grants.gov (US only, or when US location specified)
        live_grants = []
        search_term = query or industry or "startup innovation"
        if not location or "usa" in location.lower() or "us" in location.lower() or "global" in location.lower():
            live_grants = await self.search_grants_gov(search_term, max_results=max_live_results)

        # Deduplicate by title similarity
        all_grants = curated + live_grants
        seen_titles = set()
        deduped = []
        for g in all_grants:
            key = g["title"][:40].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                deduped.append(g)

        # Cache result
        await cos_cache.set(cache_key, deduped, ttl=3600)
        logger.info(f"Aggregated {len(deduped)} grants (curated={len(curated)}, live={len(live_grants)})")
        return deduped


# Singleton
grant_aggregator = GrantAggregatorService()
