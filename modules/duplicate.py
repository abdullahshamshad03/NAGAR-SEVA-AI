"""
AI-powered duplicate detection for NagarSeva AI.

Instead of exact text matching (which fails when two people describe the
same place differently — e.g. "Okhla Phase 2" vs "Okhla near masjid"),
this uses the LLM to semantically decide whether a new issue refers to the
same real-world problem as an existing one.
"""

import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def check_duplicate(new_issue: dict, pending_issues: list, llm) -> dict:
    """
    new_issue: dict with keys issue_title, category, location, description
    pending_issues: list of dicts from database (pending only)
    llm: the LangChain chat model (Groq now, Gemini at deploy)

    Returns:
        {"is_duplicate": bool, "matched_id": int|None, "reason": str}
    """
    # Only compare against issues in the same category — saves the LLM work
    same_category = [
        i for i in pending_issues
        if i.get("category") == new_issue.get("category")
    ]

    if not same_category:
        return {"is_duplicate": False, "matched_id": None, "reason": "No similar issues"}

    # Build a compact list for the LLM to scan
    candidates = "\n".join(
        f'ID {i["id"]}: "{i["issue_title"]}" at "{i["location"]}" '
        f'— {i["description"][:80]}'
        for i in same_category
    )

    prompt = ChatPromptTemplate.from_template("""
You are a civic issue de-duplication system for an Indian city.

A citizen just reported this NEW issue:
- Title: {title}
- Location: {location}
- Description: {description}

Here are EXISTING open issues in the same category:
{candidates}

Decide if the new issue refers to the SAME real-world problem as any existing one.
Two reports are the SAME if they describe the same type of problem in the same
general area — even if the location wording is different
(e.g. "Okhla Phase 2" and "Okhla near the masjid" are the same area).

Return ONLY this JSON:
{{
  "is_duplicate": true,
  "matched_id": 3,
  "reason": "Same pothole in the Okhla area, just described differently"
}}

If it is NOT a duplicate of any existing issue, return:
{{
  "is_duplicate": false,
  "matched_id": null,
  "reason": "This is a new issue in a different location"
}}

Only JSON, no extra text.""")

    try:
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "title": new_issue.get("issue_title", ""),
            "location": new_issue.get("location", ""),
            "description": new_issue.get("description", ""),
            "candidates": candidates,
        })
        return {
            "is_duplicate": bool(result.get("is_duplicate", False)),
            "matched_id": result.get("matched_id"),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        print("DUPLICATE CHECK ERROR:", str(e))
        return {"is_duplicate": False, "matched_id": None, "reason": "Check failed"}