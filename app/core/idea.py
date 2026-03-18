# app/core/idea.py

import json
import os
import re
from typing import Dict, List

from app.config import settings

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

# Common English stop words to filter out in fallback extraction
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "we", "our", "their", "its", "via", "using", "use",
    "based", "new", "novel", "propose", "proposed", "present", "study",
}


def _fallback_extraction(idea_text: str) -> Dict[str, List[str]]:
    """
    Keyword-based fallback when OpenAI is unavailable.
    Extracts multi-word noun phrases (bigrams/trigrams) as concepts.
    """
    words = re.findall(r"\b[a-zA-Z][a-zA-Z\-]{2,}\b", idea_text.lower())
    tokens = [w for w in words if w not in _STOP_WORDS]

    # Build bigrams as candidate concepts
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
    concepts = list(dict.fromkeys(bigrams[:10]))  # deduplicate, keep order

    return {
        "domains": [],       # can't reliably infer domains without LLM
        "concepts": concepts,
        "applications": [],
    }


def extract_semantic_tags(idea_text: str) -> Dict[str, List[str]]:
    """
    Extract domains and concepts from an idea using OpenAI.
    Falls back to keyword extraction when OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-..."):
        return _fallback_extraction(idea_text)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(idea=idea_text)},
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("OpenAI returned invalid JSON — check model output")

    return {
        "domains": parsed.get("domains", []),
        "concepts": parsed.get("concepts", []),
        "applications": parsed.get("applications", []),
    }


def process_idea(idea_text: str) -> Dict:
    """
    Step 3 of NOVELTYNET pipeline:
    - Validate and clean the idea text
    - Extract semantic tags (domains, concepts, applications)
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
