"""
IBM Granite LLM Service
Handles all interactions with IBM watsonx.ai using the Granite model family.
Uses IBM Cloud Lite (free tier) - ibm/granite-3-8b-instruct

Endpoints tried in order:
  1. /ml/v1/text/generation  (standard WML inference)
  2. /ml/v1/text/chat        (chat completions — same model, newer endpoint)
Both require: Watson Machine Learning service associated with watsonx project.
Fix 403: https://dataplatform.cloud.ibm.com → your project → Manage →
         Services & integrations → Associate → Watson Machine Learning
"""

import os
import json
import logging
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class IBMGraniteService:
    """
    Core service for IBM Granite model inference via watsonx.ai REST API.
    IBM Cloud Lite plan supports free inference calls (limited quota).
    Tries two endpoints — falls back gracefully when WML is not associated.
    """

    IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

    def __init__(self):
        self.api_key = os.getenv("IBM_WATSONX_API_KEY", "")
        self.project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "")
        self.base_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_id = os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct")
        self._iam_token: Optional[str] = None
        self._token_expiry: float = 0.0
        # Track whether Granite is reachable so we skip retries after first 403
        self._granite_available: Optional[bool] = None

    async def _get_iam_token(self) -> str:
        """Fetch IBM IAM bearer token using API key."""
        import time
        if self._iam_token and time.time() < self._token_expiry - 60:
            return self._iam_token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.IAM_TOKEN_URL,
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            self._iam_token = data["access_token"]
            import time as t
            self._token_expiry = t.time() + data.get("expires_in", 3600)
            return self._iam_token

    async def generate(
        self,
        prompt: str,
        max_new_tokens: int = 800,
        temperature: float = 0.7,
        stop_sequences: Optional[list] = None,
    ) -> str:
        """
        Call IBM Granite model for text generation via watsonx.ai.
        Tries /ml/v1/text/generation first, then /ml/v1/text/chat as fallback.
        Returns the generated text string.

        ⚠️  If you get 403 Forbidden:
            1. Go to https://dataplatform.cloud.ibm.com
            2. Open your project → Manage → Services & integrations
            3. Click 'Associate service' → add Watson Machine Learning (Lite)
            4. Restart the server
        """
        if self._granite_available is False:
            raise RuntimeError(
                "IBM Granite unavailable (403). "
                "Associate Watson Machine Learning with your watsonx project: "
                "dataplatform.cloud.ibm.com -> project -> Manage -> Services & integrations"
            )

        if not self.api_key or not self.project_id:
            raise RuntimeError("IBM_WATSONX_API_KEY and IBM_WATSONX_PROJECT_ID must be set in .env")

        token = await self._get_iam_token()

        # ── Endpoint 1: /ml/v1/text/generation ──────────────────────────────
        url_gen = f"{self.base_url}/ml/v1/text/generation?version=2023-05-29"
        payload_gen = {
            "model_id": self.model_id,
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy" if temperature == 0 else "sample",
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 50,
                "repetition_penalty": 1.1,
                "stop_sequences": stop_sequences or [],
            },
            "project_id": self.project_id,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=90) as client:
            try:
                resp = await client.post(url_gen, json=payload_gen, headers=headers)
                if resp.status_code == 403:
                    # Try chat endpoint before giving up
                    logger.warning("Granite /text/generation returned 403 — trying /text/chat endpoint")
                    return await self._generate_via_chat(client, token, prompt, max_new_tokens, temperature)
                resp.raise_for_status()
                self._granite_available = True
                result = resp.json()
                return result["results"][0]["generated_text"].strip()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning("Granite /text/generation 403 — trying /text/chat endpoint")
                    try:
                        return await self._generate_via_chat(client, token, prompt, max_new_tokens, temperature)
                    except Exception as chat_err:
                        self._granite_available = False
                        logger.error(
                            "Both Granite endpoints returned 403. "
                            "ACTION REQUIRED: Associate Watson Machine Learning with your watsonx project.\n"
                            "  1. Go to https://dataplatform.cloud.ibm.com\n"
                            "  2. Open project -> Manage -> Services & integrations\n"
                            "  3. Click 'Associate service' -> add Watson Machine Learning (Lite plan)\n"
                            "  4. Restart this server"
                        )
                        raise RuntimeError(
                            "IBM Granite 403: Watson Machine Learning service not associated with project. "
                            f"Project ID: {self.project_id}. "
                            "Fix: dataplatform.cloud.ibm.com -> project -> Manage -> Services & integrations -> Associate WML"
                        ) from chat_err
                raise

    async def _generate_via_chat(
        self,
        client: httpx.AsyncClient,
        token: str,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
    ) -> str:
        """
        Secondary endpoint: /ml/v1/text/chat (chat completions format).
        Available on the same WML service, sometimes has different auth scope.
        """
        url_chat = f"{self.base_url}/ml/v1/text/chat?version=2023-05-29"
        # Convert raw prompt to chat message format
        payload_chat = {
            "model_id": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "parameters": {
                "max_tokens": max_new_tokens,
                "temperature": temperature,
            },
            "project_id": self.project_id,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        resp = await client.post(url_chat, json=payload_chat, headers=headers)
        resp.raise_for_status()
        self._granite_available = True
        data = resp.json()
        # Chat completions response format
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        # Fallback: try results format
        results = data.get("results", [])
        if results:
            return results[0].get("generated_text", "").strip()
        return str(data)

    async def analyze_grant_eligibility(
        self, grant_description: str, startup_profile: dict
    ) -> dict:
        """
        Use Granite to analyze if a startup matches a grant's eligibility criteria.
        Returns a structured eligibility assessment.
        """
        prompt = f"""<|system|>
You are an expert grant eligibility analyst. Analyze the match between a grant opportunity and a startup profile.
Respond ONLY with valid JSON. No explanation outside JSON.
<|user|>
Grant Description:
{grant_description[:2000]}

Startup Profile:
- Name: {startup_profile.get('name', 'N/A')}
- Industry: {startup_profile.get('industry', 'N/A')}
- Stage: {startup_profile.get('stage', 'N/A')}
- Location: {startup_profile.get('location', 'N/A')}
- Team Size: {startup_profile.get('team_size', 'N/A')}
- Revenue: {startup_profile.get('revenue', 'N/A')}
- Description: {startup_profile.get('description', 'N/A')}
- Keywords: {', '.join(startup_profile.get('keywords', []))}

Provide eligibility analysis as JSON with these exact keys:
{{
  "match_score": <integer 0-100>,
  "eligible": <true/false>,
  "matched_criteria": [<list of matched criteria strings>],
  "missing_criteria": [<list of unmet criteria strings>],
  "recommendation": "<brief 2-sentence recommendation>",
  "risk_level": "<low|medium|high>"
}}
<|assistant|>
"""
        raw = await self.generate(prompt, max_new_tokens=400, temperature=0.2)
        try:
            # Extract JSON if wrapped in markdown
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Granite returned non-JSON eligibility response; using fallback.")
            return {
                "match_score": 50,
                "eligible": True,
                "matched_criteria": ["Industry alignment"],
                "missing_criteria": [],
                "recommendation": raw[:200],
                "risk_level": "medium",
            }

    async def extract_grant_metadata(self, raw_text: str) -> dict:
        """
        Use Granite to extract structured metadata from unstructured grant text.
        """
        prompt = f"""<|system|>
You are a grant data extraction specialist. Extract structured metadata from grant/funding opportunity text.
Respond ONLY with valid JSON.
<|user|>
Extract key metadata from this grant opportunity text:

{raw_text[:3000]}

Return JSON with these keys:
{{
  "title": "<grant title>",
  "funder": "<funding organization>",
  "amount_min": <number or null>,
  "amount_max": <number or null>,
  "deadline": "<deadline date string or null>",
  "eligible_stages": [<startup stages>],
  "eligible_industries": [<industry sectors>],
  "eligible_locations": [<countries/regions>],
  "grant_type": "<grant|loan|equity|prize|contract>",
  "focus_areas": [<key focus area strings>],
  "requirements": [<key requirement strings>],
  "application_url": "<url or null>"
}}
<|assistant|>
"""
        raw = await self.generate(prompt, max_new_tokens=500, temperature=0.1)
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"title": "Unknown", "funder": "Unknown", "amount_min": None, "amount_max": None}


# Singleton instance
granite_service = IBMGraniteService()
