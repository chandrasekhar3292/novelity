# app/core/idea.py

import json
from typing import Dict, List

from openai import OpenAI
from app.config import settings

client = OpenAI()


SYSTEM_PROMPT = """
You are a strict research-domain classifier.

Given a short research idea, extract:
1. High-level research domains (2–4 max)
2. Key technical concepts / methods
3. Application areas (if any)

Rules:
- Output MUST be valid JSON
- Do NOT explain anything
- Do NOT add extra fields
- Use standard academic domain names
"""

USER_PROMPT_TEMPLATE = """
Research idea:
"{idea}"

Return JSON in this format:
{{
  "domains": [],
  "concepts": [],
  "applications": []
}}
"""


def extract_semantic_tags(idea_text: str) -> Dict[str, List[str]]:
    """
    Uses OpenAI to extract domains and concepts from an idea.
    This is semantic interpretation, not similarity computation.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(idea=idea_text),
            },
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Hard fail is better than silent corruption
        raise ValueError("OpenAI output was not valid JSON")

    # Defensive validation
    return {
        "domains": parsed.get("domains", []),
        "concepts": parsed.get("concepts", []),
        "applications": parsed.get("applications", []),
    }


def process_idea(idea_text: str) -> Dict:
    """
    Step 3 of NOVELTYNET:
    - Clean idea
    - Extract semantic tags via OpenAI
    """

    if not idea_text or len(idea_text.strip()) < 10:
        raise ValueError("Idea text is too short or empty")

    idea_text = idea_text.strip()

    semantic_info = extract_semantic_tags(idea_text)

    return {
        "idea_text": idea_text,
        "domains": semantic_info["domains"],
        "concepts": semantic_info["concepts"],
        "applications": semantic_info["applications"],
    }
