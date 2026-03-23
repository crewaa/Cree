"""
AI Engine Service - Integrated from AI_Engine/ai_engine.py
Provides creator profiling, brand-creator ranking, and anonymous opportunity generation.
"""

import json
import re
import time
import uuid
from typing import Dict, Any

import google.generativeai as genai
from app.core.config import settings


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

CREATOR_PROFILE_PROMPT = """SYSTEM:
You are an influencer marketing analyst.

STRICT RULES:
- Output ONLY valid JSON
- Do NOT include markdown
- Do NOT include explanations outside JSON
- Do NOT include comments

TASK:
Analyze the creator data and generate a structured profile.

CREATOR DATA:
{creator_data}

OUTPUT:
Return a single valid JSON object with:
- creator_id
- summary
- strengths (array)
- improvement_areas (array)
- best_brand_categories (array)
- recommended_content_formats (array)
"""

BRAND_CREATOR_RANKING_PROMPT = """SYSTEM:
You are an influencer marketing analyst.

STRICT RULES:
- Output ONLY valid JSON
- Do NOT include markdown
- Do NOT include explanations
- Do NOT include comments
- Do NOT include any text before or after JSON

TASK:
Rank the creators for the given brand campaign.

BRAND DATA:
{brand_data}

CREATORS DATA:
{creators_data}

OUTPUT:
Return a single valid JSON object only.

EVALUATE BASED ON:
- Niche relevance
- Engagement quality
- Platform suitability
- Location & language match
- Budget compatibility (qualitative)

OUTPUT JSON FORMAT:
{{
  "ranked_creators": [
    {{
      "creator_id": "string",
      "creator_name": "string",
      "fit_level": "High | Medium | Low",
      "score_reasoning": ["string"],
      "risks": ["string"],
      "recommended_campaign_type": "string"
    }}
  ],
  "final_recommendation": "string"
}}
"""

ANONYMOUS_OPPORTUNITY_PROMPT = """SYSTEM:
You are an influencer marketing platform AI.

STRICT RULES:
- Output ONLY valid JSON
- Do NOT include markdown
- Do NOT include explanations
- Completely remove brand identity details (brand name, contact, website, email)
- Do NOT include any text before or after JSON

TASK:
Analyze the brand campaign and determine whether this creator is a good fit.
Then generate an anonymous opportunity object for the creator.

BRAND DATA (internal only):
{brand_data}

CREATOR DATA:
{creator_data}

EVALUATE:
- Niche match
- Audience requirement match
- Platform suitability
- Budget alignment

OUTPUT REQUIREMENTS:
Return a single valid JSON object containing:
- opportunity_id
- fit_level (High | Medium | Low)
- industry_hint (general industry category, NOT the brand name)
- campaign_type (e.g., "Product Review", "Sponsored Post", "Brand Ambassador")
- campaign_requirements (what they need from the creator)
- compensation (estimated compensation range)
- timeline (campaign timeline)
- deliverables (list of expected deliverables)
- status ("open")
"""


# =============================================================================
# UTILITIES
# =============================================================================

def extract_json(text: str) -> dict:
    """Extracts the first valid JSON object from LLM output."""
    if not text or not text.strip():
        raise ValueError("LLM returned empty response")

    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"No JSON object found in LLM output:\n{text}")

    json_str = match.group()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format:\n{json_str}") from e


# =============================================================================
# GEMINI CLIENT
# =============================================================================

class GeminiClient:
    """
    Gemini client — NO singleton, NO retries.
    Reads the API key fresh from settings on each instantiation so that
    updating GEMINI_API_KEY in .env and restarting the server always
    picks up the new key. Only one API call is made per request.
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        api_key = settings.gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in settings")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        """Call Gemini exactly once per request — no retries to conserve quota."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "exhausted" in err:
                raise RuntimeError(
                    "Gemini API quota exceeded. "
                    "Update GEMINI_API_KEY in .env with a fresh key, then restart the server."
                )
            raise


# =============================================================================
# ENGINE: Brand-Creator Ranking (for Discover Creators)
# =============================================================================

class BrandCreatorRankingEngine:
    def __init__(self):
        self.llm = GeminiClient()

    def rank_creators(self, brand_data: dict, creators_data: list) -> dict:
        prompt = BRAND_CREATOR_RANKING_PROMPT.format(
            brand_data=json.dumps(brand_data, default=str),
            creators_data=json.dumps(creators_data, default=str)
        )

        raw_response = self.llm.generate(prompt)
        return extract_json(raw_response)


# =============================================================================
# ENGINE: Anonymous Opportunity (for Brand Deals)
# =============================================================================

class AnonymousOpportunityEngine:
    def __init__(self):
        self.llm = GeminiClient()

    def generate_opportunity(self, brand_data: dict, creator_data: dict) -> dict:
        prompt = ANONYMOUS_OPPORTUNITY_PROMPT.format(
            brand_data=json.dumps(brand_data, default=str),
            creator_data=json.dumps(creator_data, default=str)
        )

        raw_response = self.llm.generate(prompt)
        result = extract_json(raw_response)

        # Ensure unique opportunity ID
        result["opportunity_id"] = str(uuid.uuid4())

        return result


# =============================================================================
# ENGINE: Creator Profile Summary
# =============================================================================

class CreatorAIEngine:
    def __init__(self):
        self.llm = GeminiClient()

    def generate_creator_profile(self, creator_data: dict) -> dict:
        prompt = CREATOR_PROFILE_PROMPT.format(
            creator_data=json.dumps(creator_data, default=str)
        )

        raw_response = self.llm.generate(prompt)
        return extract_json(raw_response)
