import json
import re
import os
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from PIL import Image
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Text + Vision ke liye alag models
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

# ─── State ────────────────────────────────────────────────────────────────────
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

# ─── Node 1: Vision ───────────────────────────────────────────────────────────
def vision_node(state: IssueState) -> IssueState:
    print("🔍 Vision Node chal raha hai...")
    try:
        # Vision ke liye google-generativeai directly use karo
        vision_model = genai.GenerativeModel("gemini-2.5-flash-lite")
        
        prompt = """Analyze this image. Return ONLY this JSON:
{
  "issue_title": "short title",
  "description": "2-3 sentence description",
  "location_hints": "any visible location clues or Not visible",
  "is_civic_issue": true
}
No extra text. Only JSON."""
        
        response = vision_model.generate_content([prompt, state["image"]])
        text = response.text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        
        return {
            **state,
            "is_civic_issue": data.get("is_civic_issue", False),
            "issue_title": data.get("issue_title", ""),
            "description": data.get("description", ""),
            "location_hints": data.get("location_hints", "Not visible"),
            "error": ""
        }
    except Exception as e:
        return {**state, "error": str(e), "is_civic_issue": False}

# ─── Node 2: Validate ─────────────────────────────────────────────────────────
def validate_node(state: IssueState) -> IssueState:
    print("✅ Validate Node chal raha hai...")
    return state

def is_civic(state: IssueState) -> str:
    if state.get("is_civic_issue") and not state.get("error"):
        return "yes"
    return "no"

# ─── Node 3: Categorize — JsonOutputParser use kar raha hai ───────────────────
def categorize_node(state: IssueState) -> IssueState:
    print("🏷️ Categorize Node chal raha hai...")
    try:
        prompt = ChatPromptTemplate.from_template("""
You are a civic issue classifier for Indian cities.

Issue: {issue_title}
Description: {description}

Return ONLY this JSON:
{{
  "category": "Road/Water Supply/Garbage/Electricity/Street Lighting/Waterlogging/Other",
  "severity": "Low/Medium/High/Critical",
  "severity_score": 7,
  "department": "PWD/MCD/DJB/BSES/Delhi Police",
  "urgency": "Immediate/Within 3 days/Within a week",
  "affected_people": 100
}}
Only JSON, no explanation.""")

        # LangChain chain — prompt | model | JsonOutputParser
        chain = prompt | llm | JsonOutputParser()
        
        data = chain.invoke({
            "issue_title": state["issue_title"],
            "description": state["description"]
        })
        
        return {
            **state,
            "category": data.get("category", "Other"),
            "severity": data.get("severity", "Medium"),
            "severity_score": int(data.get("severity_score", 5)),
            "department": data.get("department", "MCD"),
            "urgency": data.get("urgency", "Within a week"),
            "affected_people": int(data.get("affected_people", 50))
        }
    except Exception as e:
        print("CATEGORIZE ERROR:", str(e))
        return {
            **state,
            "category": "Other",
            "severity": "Medium",
            "severity_score": 5,
            "department": "MCD",
            "urgency": "Within a week",
            "affected_people": 50
        }

# ─── Node 4: Impact — JsonOutputParser ────────────────────────────────────────
def impact_node(state: IssueState) -> IssueState:
    print("📊 Impact Node chal raha hai...")
    try:
        prompt = ChatPromptTemplate.from_template("""
Calculate impact scores for this civic issue.

Issue: {issue_title}
Category: {category}
Severity: {severity_score}/10
Affected People: {affected_people}

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
Only JSON, no explanation.""")

        chain = prompt | llm | JsonOutputParser()
        
        data = chain.invoke({
            "issue_title": state["issue_title"],
            "category": state["category"],
            "severity_score": state["severity_score"],
            "affected_people": state["affected_people"]
        })
        
        return {
            **state,
            "impact_score": int(data.get("impact_score", 50)),
            "public_safety": int(data.get("public_safety", 50)),
            "health_risk": int(data.get("health_risk", 50)),
            "economic_impact": int(data.get("economic_impact", 50)),
            "inconvenience": int(data.get("inconvenience", 50)),
            "environmental": int(data.get("environmental", 50)),
            "escalation_needed": bool(data.get("escalation_needed", False))
        }
    except Exception as e:
        print("IMPACT ERROR:", str(e))
        return {
            **state,
            "impact_score": 50,
            "public_safety": 50,
            "health_risk": 50,
            "economic_impact": 50,
            "inconvenience": 50,
            "environmental": 50,
            "escalation_needed": False
        }

# ─── Node 5: Hinglish — StrOutputParser ───────────────────────────────────────
def hinglish_node(state: IssueState) -> IssueState:
    print("🗣️ Hinglish Node chal raha hai...")
    try:
        prompt = ChatPromptTemplate.from_template("""
Yeh civic issue ki summary casual Hinglish mein likho (Roman script, WhatsApp style):

Issue: {issue_title}
Category: {category}
Severity: {severity}
Department: {department}

2-3 lines mein likho. Kya problem hai, kitni serious hai, kya karna chahiye.""")

        # Hinglish plain text hai — StrOutputParser use karo
        chain = prompt | llm | StrOutputParser()
        
        summary = chain.invoke({
            "issue_title": state["issue_title"],
            "category": state["category"],
            "severity": state["severity"],
            "department": state["department"]
        })
        
        return {**state, "hinglish_summary": summary.strip()}
    
    except Exception as e:
        print("HINGLISH ERROR:", str(e))
        return {
            **state,
            "hinglish_summary": f"Bhai {state['issue_title']} ki problem hai. {state['department']} ko complain karo!"
        }

# ─── Graph ────────────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(IssueState)
    
    graph.add_node("vision_node", vision_node)
    graph.add_node("validate_node", validate_node)
    graph.add_node("categorize_node", categorize_node)
    graph.add_node("impact_node", impact_node)
    graph.add_node("hinglish_node", hinglish_node)
    
    graph.add_edge(START, "vision_node")
    graph.add_edge("vision_node", "validate_node")
    graph.add_conditional_edges(
        "validate_node",
        is_civic,
        {"yes": "categorize_node", "no": END}
    )
    graph.add_edge("categorize_node", "impact_node")
    graph.add_edge("impact_node", "hinglish_node")
    graph.add_edge("hinglish_node", END)
    
    return graph.compile()

nagarseva_graph = build_graph()
print("✅ NagarSeva AI Graph ready!")