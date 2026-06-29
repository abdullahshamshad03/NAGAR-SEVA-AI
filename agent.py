
import json
import os
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import google.generativeai as genai

# ── Text model: Gemini (deployment). ──
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# DEPLOY — Gemini for all text nodes (categorize / impact)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)

# TESTING ONLY (Groq, to save Gemini quota) — keep commented for deploy:
# from langchain_groq import ChatGroq
# llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

VISION_MODEL = "gemini-2.5-flash-lite"


# ─── State ─────────────────────────────────────────────────────────────────────
class IssueState(TypedDict):
    image: object
    is_civic_issue: bool
    confidence: int
    visual_severity: str
    rejection_reason: str
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
        prompt = """You are the gatekeeper for a civic issue reporting system in India.

YOUR CORE RULE (think about this, don't match a list):
A civic issue is ANY problem in a PUBLIC space that a citizen would reasonably
report to a government body or local authority (municipal, public works, water,
electricity, traffic police, etc.) so it can be fixed or managed.

So instead of checking against a fixed list, ask yourself:
1. Is this a PUBLIC place (street, road, park, footpath, public building, market,
   drain, public transport, etc.) — NOT someone's private indoor/home space?
2. Is there a PROBLEM, hazard, damage, obstruction, or mismanagement visible —
   something that is wrong and should be addressed by authorities?
If BOTH are yes → it IS a civic issue (set is_civic_issue=true), even if it is an
unusual type you haven't seen described before. Use your own judgement.

Examples that ARE civic issues (non-exhaustive — the principle matters more):
potholes, broken roads/footpaths, garbage/waste, overflowing or blocked drains,
water leakage/sewage, broken/damaged streetlights, exposed/hanging wires, fallen
trees, waterlogging/flooding, illegal encroachment, damaged public property,
traffic jams/congestion, illegal parking, road blockages, stray-animal hazards,
open manholes, broken public toilets, damaged bus stops, air/noise pollution
sources, illegal dumping, and similar PUBLIC problems.

ONLY reject (set is_civic_issue=false) when the image is clearly NOT a public
problem, such as: selfies or people posing, portraits/faces, food, pets,
memes/jokes, screenshots, private indoor/home rooms, products or shopping items,
documents/text, or a normal scene with nothing actually wrong.
When the image genuinely shows a public problem, DO NOT reject it just because it
doesn't match a familiar label. Default to accepting real public problems.

SEVERITY — judge from what you actually SEE (size + danger), not the type:
- "Low": small/minor (small crack, slightly sunken manhole, little litter). Safe.
- "Medium": noticeable (moderate pothole, visible garbage pile, bent streetlight,
  moderate congestion). Some inconvenience.
- "High": serious (large/deep pothole, big garbage dump, sewage overflow, broken
  streetlight, exposed wires, heavy traffic jam). Real risk or major disruption.
- "Critical": dangerous/emergency (huge crater, major flooding, live exposed
  wires, road collapse). Immediate danger.
Be honest: a small crack or minor manhole is "Low", NOT "Medium".

Return ONLY this JSON, no extra text:
{
  "is_civic_issue": true,
  "confidence": 85,
  "issue_title": "short title",
  "description": "2-3 sentence description of the problem",
  "location_hints": "visible location clues, or 'Not visible'",
  "visual_severity": "Low/Medium/High/Critical",
  "rejection_reason": ""
}

Rules:
- If it is clearly NOT a public problem, set is_civic_issue=false, and fill
  rejection_reason with a short friendly reason.
- When in doubt about a real public problem, ACCEPT it (set is_civic_issue=true).
  It is better to accept a borderline real issue than to wrongly reject a citizen's
  genuine complaint. Only reject the obvious non-civic cases listed above."""
        response = model.generate_content([prompt, state["image"]])
        data = _extract_json(response.text)

        is_civic = data.get("is_civic_issue", False)
        confidence = int(data.get("confidence", 0))
        # Only override the model's decision if it is VERY unsure (avoids wrongly
        # rejecting genuine but unusual issues). The prompt already handles obvious junk.
        if is_civic and confidence < 40:
            is_civic = False

        return {
            **state,
            "is_civic_issue": is_civic,
            "confidence": confidence,
            "issue_title": data.get("issue_title", ""),
            "description": data.get("description", ""),
            "location_hints": data.get("location_hints", "Not visible"),
            "visual_severity": data.get("visual_severity", "Medium"),
            "rejection_reason": data.get("rejection_reason", ""),
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
Location: {location}
Visual severity (judged from the actual photo by our vision system): {visual_severity}

Use this STRICT department mapping (pick the single best fit):
- Potholes, road damage, broken roads, footpaths, bridges → "PWD"
- Garbage, waste piles, sanitation, dirty public areas, dead animals → "MCD"
- Water leakage, pipe burst, sewage, drainage, water supply → "DJB"
- Streetlight not working, electricity, power lines, exposed/hanging wires → "BSES"
- Traffic jam, illegal parking, encroachment, road obstruction → "Delhi Police"
- Fire, burnt building, fire hazard, smoke, gas leak → "Fire Service"
- Large garbage dumps polluting rivers/drains, industrial pollution, air/noise
  pollution, open dumping into water bodies, hazardous waste → "Environment"
- Public hospital/clinic issues, disease outbreak, mosquito breeding, unsanitary
  food/health hazard, medical waste → "Health"
- Broken/damaged public buses, bus stops, auto/taxi issues, vehicle-related
  public transport problems → "Transport"
- Government school building damage, school infrastructure problems → "Education"

Category mapping:
- Potholes/roads/footpaths → "Road"
- Garbage/waste → "Garbage"
- Water/sewage → "Water Supply"
- Streetlight/power → "Electricity"
- Waterlogging → "Waterlogging"
- Traffic jam/congestion/illegal parking/encroachment → "Traffic"
- Fire/burnt structure → "Fire Hazard"
- Pollution/dumping into water/air pollution → "Pollution"
- Health/sanitation hazard → "Health"
- Public transport → "Transport"
- School/education infrastructure → "Education"
- Anything else → "Other"

SEVERITY: Trust the visual severity above — it was judged from the real photo.
Set "severity" equal to the visual severity, and set severity_score to match:
Low → 2-3, Medium → 4-6, High → 7-8, Critical → 9-10.
Do NOT inflate a small/minor issue.

AFFECTED PEOPLE: estimate REALISTICALLY. Think about how many people this
SPECIFIC issue actually inconveniences day-to-day - not the whole city.

Key idea: most civic issues are LOCAL. A single pothole, one broken streetlight,
one damaged building, or a garbage pile affects the people who pass through or
live right around that spot - usually tens to a few hundred, NOT thousands.

Use the issue TYPE and SCOPE to pick a realistic number:
- Very local, single-point issue (one pothole, one streetlight, one manhole,
  one damaged building, small garbage pile): roughly 20 to 200 people.
  Even a damaged/burnt building mainly affects its residents + immediate
  neighbours + passers-by - think 30 to 250, not thousands.
- Street-level issue (a stretch of broken road, blocked drain on a lane,
  garbage along a street): roughly 100 to 600 people.
- Area-wide issue (water supply cut for a colony, major sewage overflow,
  power outage for a block, large dump polluting a canal): 500 to 3000.
- Major/widespread (flooding across a neighbourhood, a jammed main arterial
  road, contamination affecting a large zone): 2000 to 8000.

Then nudge within the range by how busy the location is (quiet lane = lower,
busy market/main road/near school-hospital-metro = higher).
A small issue stays SMALL even if severity is High and the area is busy -
severity is about danger, not headcount. Return a specific, believable number.

Return ONLY this JSON:
{{
  "category": "pick from above",
  "severity": "Low/Medium/High/Critical",
  "severity_score": 7,
  "department": "pick from the mapping",
  "urgency": "Immediate/Within 3 days/Within a week",
  "affected_people": 120
}}
Only JSON.""")
        chain = prompt | llm | JsonOutputParser()
        data = chain.invoke({
            "issue_title": state["issue_title"],
            "description": state["description"],
            "location": state.get("location_hints", "a residential area"),
            "visual_severity": state.get("visual_severity", "Medium"),
        })
        return {
            **state,
            "category": data.get("category", "Other"),
            "severity": data.get("severity", state.get("visual_severity", "Medium")),
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

    g.add_edge(START, "vision_node")
    g.add_edge("vision_node", "validate_node")
    g.add_conditional_edges(
        "validate_node", is_civic,
        {"yes": "categorize_node", "no": END},
    )
    g.add_edge("categorize_node", "impact_node")
    g.add_edge("impact_node", END)
    return g.compile()


nagarseva_graph = build_graph()

# Expose the llm so app.py can reuse it for duplicate detection + insights
text_llm = llm

print("✅ NagarSeva AI Graph ready!")