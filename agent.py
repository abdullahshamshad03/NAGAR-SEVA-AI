"""
LangGraph agent pipeline for NagarSeva AI.

Flow:
  START → vision → validate ─(civic?)─→ categorize → impact → hinglish → END
                              └(not civic)──────────────────────────────→ END

Model setup:
  - Vision  : Gemini (google-generativeai) — handles the image directly.
  - Text    : Groq (testing) — categorize / impact / hinglish.
  ⚠️ DEPLOY: switch `llm` to ChatGoogleGenerativeAI("gemini-2.5-flash-lite").

Duplicate detection runs OUTSIDE the graph (in app.py at save time), because
it needs the database which is a UI-side concern.
"""

import json
import os
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import google.generativeai as genai

# ── Testing model (Groq). DEPLOY: comment this out, use the Gemini line below. ──
from langchain_groq import ChatGroq

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# TESTING — Groq for text nodes
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# DEPLOY — uncomment these two lines and remove the Groq line above:
# from langchain_google_genai import ChatGoogleGenerativeAI
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)

VISION_MODEL = "gemini-2.5-flash-lite"


# ─── State ─────────────────────────────────────────────────────────────────────
class IssueState(TypedDict):
    image: object
    is_civic_issue: bool
    issue_title: str
    description: str
    location_hints: str
    category: str
    severity: str
    severity_score: int
    department: str
    urgency: str
    affected_people: int
    impact_score: int
    public_safety: int
    health_risk: int
    economic_impact: int
    inconvenience: int
    environmental: int
    escalation_needed: bool
    hinglish_summary: str
    error: str


def _extract_json(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        text = text[start:end]
    return json.loads(text)


# ─── Node 1: Vision (Gemini) ───────────────────────────────────────────────────
def vision_node(state: IssueState) -> IssueState:
    print("🔍 Vision Node...")
    try:
        model = genai.GenerativeModel(VISION_MODEL)
        prompt = """Analyze this image for a civic issue reporting system in India.
Return ONLY this JSON, no extra text:
{
  "issue_title": "short title",
  "description": "2-3 sentence description of the problem",
  "location_hints": "any visible location clues, or 'Not visible'",
  "is_civic_issue": true
}
If there is no civic issue in the image, set is_civic_issue to false."""
        response = model.generate_content([prompt, state["image"]])
        data = _extract_json(response.text)
        return {
            **state,
            "is_civic_issue": data.get("is_civic_issue", False),
            "issue_title": data.get("issue_title", ""),
            "description": data.get("description", ""),
            "location_hints": data.get("location_hints", "Not visible"),
            "error": "",
        }
    except Exception as e:
        return {**state, "error": str(e), "is_civic_issue": False}


# ─── Node 2: Validate ──────────────────────────────────────────────────────────
def validate_node(state: IssueState) -> IssueState:
    print("✅ Validate Node...")
    return state


def is_civic(state: IssueState) -> str:
    if state.get("is_civic_issue") and not state.get("error"):
        return "yes"
    return "no"


# ─── Node 3: Categorize (Groq/Gemini) ──────────────────────────────────────────
def categorize_node(state: IssueState) -> IssueState:
    print("🏷️ Categorize Node...")
    try:
        prompt = ChatPromptTemplate.from_template("""
You are a civic issue classifier for Delhi, India.

Issue: {issue_title}
Description: {description}

Use this STRICT department mapping:
- Potholes, road damage, broken roads, footpaths → "PWD"
- Garbage, waste, sanitation, dirty areas → "MCD"
- Water leakage, pipe burst, sewage, drainage → "DJB"
- Streetlight, electricity, power, wires → "BSES"
- Traffic, illegal parking, encroachment → "Delhi Police"

Category mapping:
- Potholes/roads/footpaths → "Road"
- Garbage/waste → "Garbage"
- Water/sewage → "Water Supply"
- Streetlight/power → "Electricity"
- Waterlogging → "Waterlogging"
- Anything else → "Other"

Return ONLY this JSON:
{{
  "category": "pick from above",
  "severity": "Low/Medium/High/Critical",
  "severity_score": 7,
  "department": "pick from the mapping",
  "urgency": "Immediate/Within 3 days/Within a week",
  "affected_people": 100
}}
Only JSON.""")
        chain = prompt | llm | JsonOutputParser()
        data = chain.invoke({
            "issue_title": state["issue_title"],
            "description": state["description"],
        })
        return {
            **state,
            "category": data.get("category", "Other"),
            "severity": data.get("severity", "Medium"),
            "severity_score": int(data.get("severity_score", 5)),
            "department": data.get("department", "MCD"),
            "urgency": data.get("urgency", "Within a week"),
            "affected_people": int(data.get("affected_people", 50)),
        }
    except Exception as e:
        print("CATEGORIZE ERROR:", str(e))
        return {
            **state, "category": "Other", "severity": "Medium",
            "severity_score": 5, "department": "MCD",
            "urgency": "Within a week", "affected_people": 50,
        }


# ─── Node 4: Impact (Groq/Gemini) ──────────────────────────────────────────────
def impact_node(state: IssueState) -> IssueState:
    print("📊 Impact Node...")
    try:
        prompt = ChatPromptTemplate.from_template("""
Calculate community impact scores (0-100 each) for this civic issue.

Issue: {issue_title}
Category: {category}
Severity: {severity_score}/10
Affected people: {affected_people}

Return ONLY this JSON:
{{
  "impact_score": 75,
  "public_safety": 80,
  "health_risk": 60,
  "economic_impact": 70,
  "inconvenience": 85,
  "environmental": 55,
  "escalation_needed": true
}}
Only JSON.""")
        chain = prompt | llm | JsonOutputParser()
        data = chain.invoke({
            "issue_title": state["issue_title"],
            "category": state["category"],
            "severity_score": state["severity_score"],
            "affected_people": state["affected_people"],
        })
        return {
            **state,
            "impact_score": int(data.get("impact_score", 50)),
            "public_safety": int(data.get("public_safety", 50)),
            "health_risk": int(data.get("health_risk", 50)),
            "economic_impact": int(data.get("economic_impact", 50)),
            "inconvenience": int(data.get("inconvenience", 50)),
            "environmental": int(data.get("environmental", 50)),
            "escalation_needed": bool(data.get("escalation_needed", False)),
        }
    except Exception as e:
        print("IMPACT ERROR:", str(e))
        return {
            **state, "impact_score": 50, "public_safety": 50,
            "health_risk": 50, "economic_impact": 50, "inconvenience": 50,
            "environmental": 50, "escalation_needed": False,
        }


# ─── Node 5: Hinglish (Groq/Gemini) ────────────────────────────────────────────
def hinglish_node(state: IssueState) -> IssueState:
    print("🗣️ Hinglish Node...")
    try:
        prompt = ChatPromptTemplate.from_template("""
Write a casual Hinglish summary (Roman script, WhatsApp style) of this civic issue:

Issue: {issue_title}
Category: {category}
Severity: {severity}
Department: {department}

In 2-3 lines: what the problem is, how serious it is, and who to complain to.
Write it the way you'd message a friend on WhatsApp.""")
        chain = prompt | llm | StrOutputParser()
        summary = chain.invoke({
            "issue_title": state["issue_title"],
            "category": state["category"],
            "severity": state["severity"],
            "department": state["department"],
        })
        return {**state, "hinglish_summary": summary.strip()}
    except Exception as e:
        print("HINGLISH ERROR:", str(e))
        return {
            **state,
            "hinglish_summary": (
                f"Bhai {state['issue_title']} ki problem hai. "
                f"{state['department']} ko complain karo!"
            ),
        }


# ─── Graph ─────────────────────────────────────────────────────────────────────
def build_graph():
    g = StateGraph(IssueState)
    g.add_node("vision_node", vision_node)
    g.add_node("validate_node", validate_node)
    g.add_node("categorize_node", categorize_node)
    g.add_node("impact_node", impact_node)
    g.add_node("hinglish_node", hinglish_node)

    g.add_edge(START, "vision_node")
    g.add_edge("vision_node", "validate_node")
    g.add_conditional_edges(
        "validate_node", is_civic,
        {"yes": "categorize_node", "no": END},
    )
    g.add_edge("categorize_node", "impact_node")
    g.add_edge("impact_node", "hinglish_node")
    g.add_edge("hinglish_node", END)
    return g.compile()


nagarseva_graph = build_graph()

# Expose the llm so app.py can reuse it for duplicate detection + insights
text_llm = llm

print("✅ NagarSeva AI Graph ready!")