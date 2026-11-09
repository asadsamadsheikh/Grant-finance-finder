"""
AI Proposal Generator — Powered by IBM Granite
Generates tailored grant application drafts using few-shot prompting
with IBM granite-3-8b-instruct. Drafts include executive summary,
problem statement, solution narrative, impact metrics, and budget outline.
"""

import uuid
import logging
from datetime import datetime
from .granite_service import granite_service
from .cos_cache import cos_cache

logger = logging.getLogger(__name__)


PROPOSAL_SECTIONS = [
    "executive_summary",
    "problem_statement",
    "proposed_solution",
    "innovation_uniqueness",
    "team_qualifications",
    "implementation_plan",
    "expected_outcomes",
    "budget_outline",
    "sustainability_plan",
]


class ProposalGeneratorService:
    """
    IBM Granite-powered grant proposal generator.
    Generates structured, tailored proposals matching grant requirements
    with startup profile. Human validation strongly recommended before submission.
    """

    def _template_fallback(self, startup: dict, grant: dict) -> dict:
        """
        Template-based proposal when IBM Granite is unavailable (e.g. WML not associated).
        Returns a structured, pre-filled proposal that still provides useful content.
        """
        name = startup.get("name", "Our Startup")
        industry = startup.get("industry", "technology")
        stage = startup.get("stage", "seed")
        location = startup.get("location", "")
        description = startup.get("description", "")
        problem = startup.get("problem", description)
        team_size = startup.get("team_size", "small team")
        keywords = ", ".join(startup.get("keywords", [industry]))
        revenue = startup.get("revenue", "Pre-revenue")

        g_title = grant.get("title", "this grant")
        g_funder = grant.get("funder", "the funder")
        g_focus = ", ".join(grant.get("focus_areas", [industry]))
        amount = grant.get("amount_max") or grant.get("amount_min") or 100000
        requirements = "; ".join(grant.get("requirements", []))

        return {
            "executive_summary": (
                f"{name} is a {stage}-stage {industry} startup based in {location}, "
                f"developing {description} "
                f"We are applying to {g_title} offered by {g_funder} to accelerate our mission. "
                f"Our solution addresses a critical gap in the {industry} sector, leveraging {keywords} "
                f"to deliver measurable impact aligned with {g_funder}'s focus on {g_focus}. "
                f"With a dedicated team of {team_size}, we are uniquely positioned to execute this project "
                f"and deliver results that drive long-term value."
            ),
            "problem_statement": (
                f"The {industry} sector faces significant challenges that {name} is uniquely positioned to solve. "
                f"{problem} "
                f"This problem affects millions of stakeholders globally, resulting in inefficiencies, "
                f"missed opportunities, and substantial economic costs. "
                f"Current solutions are inadequate because they lack the innovation, scalability, and "
                f"accessibility that modern {industry} demands. "
                f"{g_funder}'s focus on {g_focus} directly aligns with addressing this gap, "
                f"making this grant an ideal catalyst for our work."
            ),
            "proposed_solution": (
                f"{name} proposes to {description} "
                f"Our approach leverages cutting-edge {keywords} to build a scalable, "
                f"accessible solution that directly addresses the identified problem. "
                f"Our technical methodology involves three core phases: "
                f"(1) Research and architecture design informed by user needs and market data; "
                f"(2) Rapid prototyping and iterative development with continuous feedback loops; "
                f"(3) Pilot deployment with key stakeholders followed by structured scale-up. "
                f"The solution meets all grant requirements: {requirements}."
            ),
            "innovation_uniqueness": (
                f"{name}'s approach is distinguished by its unique combination of {keywords} "
                f"applied specifically to the {industry} domain. "
                f"Unlike existing solutions, our platform is designed from the ground up to be "
                f"modular, open, and interoperable — enabling rapid adaptation as market needs evolve. "
                f"We have developed proprietary methodologies that create defensible competitive advantages "
                f"and significant barriers to replication. "
                f"Our innovation directly advances {g_funder}'s strategic goals in {g_focus}."
            ),
            "team_qualifications": (
                f"The {name} team comprises {team_size} professionals with deep expertise in {industry}. "
                f"Our founding team brings complementary skills across technology, business development, "
                f"and domain expertise — making us uniquely qualified to execute this project. "
                f"Based in {location}, we have strong connections to the local {industry} ecosystem "
                f"and access to world-class mentors, advisors, and potential customers. "
                f"Our track record at the {stage} stage demonstrates our ability to deliver results "
                f"with lean resources and agile execution."
            ),
            "implementation_plan": (
                f"Phase 1 — Foundation (Months 1–3): Finalize technical architecture, hire key team members, "
                f"establish partnerships, and complete initial prototype. "
                f"Milestone: Working MVP validated with 5 pilot users.\n\n"
                f"Phase 2 — Development (Months 4–8): Iterative product development, user testing, "
                f"regulatory compliance review, and infrastructure buildout. "
                f"Milestone: Beta product launched to 50+ users with measurable KPIs.\n\n"
                f"Phase 3 — Scale (Months 9–12): Full market launch, growth marketing, partnership expansion, "
                f"and grant reporting. "
                f"Milestone: Commercially operational with demonstrated impact metrics for {g_funder} reporting."
            ),
            "expected_outcomes": (
                f"By the end of the grant period, {name} will have achieved the following outcomes:\n"
                f"1. Technical: Fully operational platform with validated {keywords} capabilities\n"
                f"2. Market: 100+ active users / customers demonstrating product-market fit\n"
                f"3. Economic: ${int(amount * 0.3):,} in projected revenue pipeline within 18 months\n"
                f"4. Social: Direct positive impact on the {industry} sector aligned with {g_focus}\n"
                f"5. Scale: Clear pathway to sustainability and next-stage funding (Series A readiness)\n"
                f"Long-term (3–5 years): {name} aims to become a category leader in {industry}, "
                f"generating significant employment and economic impact in {location} and beyond."
            ),
            "budget_outline": (
                f"Total Requested: ${amount:,.0f}\n\n"
                f"1. Personnel & Salaries (45% — ${int(amount * 0.45):,}): "
                f"Core team salaries, contractor fees for specialized {keywords} development.\n"
                f"2. R&D & Technology (25% — ${int(amount * 0.25):,}): "
                f"Cloud infrastructure, tools, licenses, and technical research activities.\n"
                f"3. Equipment & Infrastructure (15% — ${int(amount * 0.15):,}): "
                f"Hardware, lab equipment, and development environment setup.\n"
                f"4. Outreach & Dissemination (10% — ${int(amount * 0.10):,}): "
                f"Pilot user acquisition, conferences, publications, and stakeholder engagement.\n"
                f"5. Indirect/Overhead (5% — ${int(amount * 0.05):,}): "
                f"Administrative costs, accounting, legal compliance.\n"
                f"All expenditures are compliant with {g_funder} grant terms and will be tracked "
                f"with monthly financial reporting."
            ),
        }

    async def generate_full_proposal(
        self, startup_profile: dict, grant: dict
    ) -> dict:
        """
        Generate a complete grant proposal using IBM Granite.
        Falls back to template-based content if Granite is unavailable.
        Returns structured proposal dict with all sections + metadata.
        """
        proposal_id = str(uuid.uuid4())[:8]
        logger.info(f"Generating proposal {proposal_id} for grant: {grant.get('title', '')}")

        sections = {}
        granite_used = True

        # Generate core sections concurrently (3 batches to manage token limits)
        import asyncio

        try:
            # Batch 1: Context-setting sections
            exec_sum, prob_stmt = await asyncio.gather(
                self._generate_executive_summary(startup_profile, grant),
                self._generate_problem_statement(startup_profile, grant),
            )
            sections["executive_summary"] = exec_sum
            sections["problem_statement"] = prob_stmt

            # Batch 2: Solution and innovation
            solution, innovation = await asyncio.gather(
                self._generate_proposed_solution(startup_profile, grant),
                self._generate_innovation_uniqueness(startup_profile, grant),
            )
            sections["proposed_solution"] = solution
            sections["innovation_uniqueness"] = innovation

            # Batch 3: Operational sections
            team, outcomes, budget = await asyncio.gather(
                self._generate_team_qualifications(startup_profile),
                self._generate_expected_outcomes(startup_profile, grant),
                self._generate_budget_outline(startup_profile, grant),
            )
            sections["team_qualifications"] = team
            sections["expected_outcomes"] = outcomes
            sections["budget_outline"] = budget

            # Implementation plan (sequential, references other sections)
            sections["implementation_plan"] = await self._generate_implementation_plan(startup_profile, grant)

        except Exception as e:
            logger.warning(f"Granite proposal generation failed ({e}); using template fallback")
            granite_used = False
            sections = self._template_fallback(startup_profile, grant)

        if granite_used:
            disclaimer = (
                "⚠️ AI-Generated Draft — Requires Human Review. "
                "This proposal was generated by IBM Granite (ibm/granite-3-8b-instruct) via watsonx.ai. "
                "Verify all facts, figures, and compliance requirements before submission. "
                "AI-generated content may contain inaccuracies."
            )
        else:
            disclaimer = (
                "⚠️ Template Draft — IBM Granite Unavailable. "
                "This proposal used a structured template because IBM Granite returned a 403 error. "
                "To enable full AI generation: go to dataplatform.cloud.ibm.com → your project → "
                "Manage → Services & integrations → Associate Watson Machine Learning (Lite). "
                "Review and heavily personalise all sections before submission."
            )

        proposal = {
            "proposal_id": proposal_id,
            "generated_at": datetime.utcnow().isoformat(),
            "startup_name": startup_profile.get("name", "Startup"),
            "grant_title": grant.get("title", ""),
            "grant_funder": grant.get("funder", ""),
            "grant_amount_max": grant.get("amount_max"),
            "sections": sections,
            "word_count": sum(len(s.split()) for s in sections.values()),
            "generated_by": "IBM Granite (watsonx.ai)" if granite_used else "Template fallback",
            "disclaimer": disclaimer,
        }

        # Store in IBM COS for retrieval
        await cos_cache.store_proposal(proposal_id, proposal)
        return proposal

    async def _generate_executive_summary(self, startup: dict, grant: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer with 15 years of experience writing successful grant applications.
Write a compelling, professional executive summary for a grant application.
Be specific, use active voice, and highlight unique value propositions.
<|user|>
Write a 150-200 word Executive Summary for this grant application:

Startup: {startup.get('name', 'Our startup')}
Industry: {startup.get('industry', '')}
Stage: {startup.get('stage', '')}
Description: {startup.get('description', '')}
Key Problem Solved: {startup.get('problem', '')}

Grant: {grant.get('title', '')}
Funder: {grant.get('funder', '')}
Focus Areas: {', '.join(grant.get('focus_areas', []))}
Amount: ${grant.get('amount_max', 'N/A')}

Write ONLY the executive summary text. No headers or labels.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=280, temperature=0.7)

    async def _generate_problem_statement(self, startup: dict, grant: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer. Write a clear, evidence-based problem statement for a grant application.
Use data points where possible. Connect the problem to the grant's focus areas.
<|user|>
Write a 200-250 word Problem Statement for:

Startup: {startup.get('name', 'Our startup')} — {startup.get('description', '')}
Core Problem Being Solved: {startup.get('problem', startup.get('description', ''))}
Industry: {startup.get('industry', '')}
Target Market: {startup.get('target_market', 'SMEs and enterprises')}

Grant Focus Areas: {', '.join(grant.get('focus_areas', []))}
Grant Funder: {grant.get('funder', '')}

Write ONLY the problem statement. Be specific about the market gap and its consequences.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=350, temperature=0.65)

    async def _generate_proposed_solution(self, startup: dict, grant: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer. Describe the proposed solution clearly and compellingly.
Explain the technical approach, methodology, and how it addresses the problem.
<|user|>
Write a 250-300 word Proposed Solution section for:

Startup: {startup.get('name', 'Our startup')}
Technology/Solution: {startup.get('description', '')}
Industry: {startup.get('industry', '')}
Key Features: {', '.join(startup.get('keywords', []))}
Stage: {startup.get('stage', '')}

Grant Requirements: {', '.join(grant.get('requirements', []))}
Grant Focus: {', '.join(grant.get('focus_areas', []))}

Write ONLY the solution description. Include technical methodology and innovation aspects.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=400, temperature=0.7)

    async def _generate_innovation_uniqueness(self, startup: dict, grant: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer. Articulate what makes this innovation unique and why it deserves funding.
Focus on differentiation, barriers to replication, and competitive advantages.
<|user|>
Write a 200-word Innovation & Uniqueness section for:

Startup: {startup.get('name', '')}
Solution: {startup.get('description', '')}
Industry: {startup.get('industry', '')}
Keywords/Tech: {', '.join(startup.get('keywords', []))}
Revenue: {startup.get('revenue', 'Pre-revenue')}

Grant funder cares about: {', '.join(grant.get('focus_areas', []))}

Explain what makes this innovation unique, defensible, and deserving of this specific grant.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=300, temperature=0.75)

    async def _generate_team_qualifications(self, startup: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer. Write a professional team qualifications section.
Emphasize domain expertise, track record, and capability to execute the project.
<|user|>
Write a 180-word Team Qualifications section for:

Startup: {startup.get('name', 'Our startup')}
Team Size: {startup.get('team_size', 'Small team')}
Industry: {startup.get('industry', '')}
Stage: {startup.get('stage', '')}
Location: {startup.get('location', '')}

Describe the founding team's expertise, relevant experience, and why they are uniquely positioned
to execute this project. Make it compelling even without knowing specific names.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=270, temperature=0.7)

    async def _generate_implementation_plan(self, startup: dict, grant: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer. Create a structured, realistic implementation plan with milestones.
Use a timeline format appropriate for the grant duration.
<|user|>
Write a 250-word Implementation Plan for a grant project:

Startup: {startup.get('name', 'Our startup')}
Project: {startup.get('description', '')}
Stage: {startup.get('stage', '')}
Team Size: {startup.get('team_size', '3-5 people')}

Grant: {grant.get('title', '')}
Funding Amount: ${grant.get('amount_max', '100,000')}
Focus: {', '.join(grant.get('focus_areas', []))}

Create a 12-month phased implementation plan with:
- Phase 1 (Months 1-3): Foundation/Research
- Phase 2 (Months 4-8): Development/Testing
- Phase 3 (Months 9-12): Deployment/Scale
Include key milestones and deliverables for each phase.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=380, temperature=0.65)

    async def _generate_expected_outcomes(self, startup: dict, grant: dict) -> str:
        prompt = f"""<|system|>
You are an expert grant writer. Write measurable, specific expected outcomes and impact metrics.
Use quantifiable goals where possible. Align with the grant's objectives.
<|user|>
Write a 200-word Expected Outcomes & Impact section:

Startup: {startup.get('name', 'Our startup')}
Solution: {startup.get('description', '')}
Industry: {startup.get('industry', '')}
Target Market: {startup.get('target_market', '')}

Grant Focus Areas: {', '.join(grant.get('focus_areas', []))}
Grant Funder: {grant.get('funder', '')}

List 5-6 specific, measurable outcomes. Include short-term (1 year) and long-term (3-5 year) impact.
Cover economic, social, and technological impact where applicable.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=300, temperature=0.7)

    async def _generate_budget_outline(self, startup: dict, grant: dict) -> str:
        amount = grant.get("amount_max") or grant.get("amount_min") or 100000
        prompt = f"""<|system|>
You are an expert grant writer. Create a realistic, justified budget outline.
Budget must align with grant requirements and project scope.
<|user|>
Write a detailed Budget Outline for a ${amount:,.0f} grant:

Project: {startup.get('description', '')}
Startup Stage: {startup.get('stage', '')}
Team Size: {startup.get('team_size', '3-5 people')}
Industry: {startup.get('industry', '')}

Grant: {grant.get('title', '')}
Focus: {', '.join(grant.get('focus_areas', []))}
Requirements: {', '.join(grant.get('requirements', []))}

Create a budget breakdown table covering:
1. Personnel (salaries/contractors) - largest portion
2. Equipment & Infrastructure
3. Research & Development costs
4. Travel & Dissemination
5. Indirect/Overhead costs (max 15%)
Show approximate percentages and dollar amounts for each category.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=400, temperature=0.5)

    async def generate_cover_letter(self, startup_profile: dict, grant: dict) -> str:
        """Generate a professional cover letter for the grant application."""
        prompt = f"""<|system|>
You are an expert grant writer. Write a compelling, professional cover letter.
Keep it to 3 paragraphs. Be specific, confident, and aligned with funder priorities.
<|user|>
Write a grant application cover letter from:

Startup: {startup_profile.get('name', 'Our Startup')} ({startup_profile.get('location', '')})
Founded: {startup_profile.get('founded_year', '2023')}
Stage: {startup_profile.get('stage', '')}
Industry: {startup_profile.get('industry', '')}

To: {grant.get('funder', 'The Grant Committee')}
For: {grant.get('title', 'Grant Application')}
Amount Requested: ${grant.get('amount_max', 'N/A')}

Paragraph 1: Introduction and purpose of application
Paragraph 2: Why this startup is the ideal candidate
Paragraph 3: Closing with call to action

Write ONLY the letter body (no date/address). Professional but enthusiastic tone.
<|assistant|>
"""
        return await granite_service.generate(prompt, max_new_tokens=350, temperature=0.72)


# Singleton
proposal_generator = ProposalGeneratorService()
