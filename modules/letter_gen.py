"""
Complaint letter + WhatsApp share message generation for NagarSeva AI.
Letter uses the LLM; WhatsApp message is built from existing data (no API call).
"""

from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

DEPARTMENT_CONTACTS = {
    "PWD": "1800-11-0084",
    "MCD": "155304",
    "DJB": "1916",
    "BSES": "19123",
    "Delhi Police": "100",
}


def generate_letter(issue_title, description, location, severity,
                    department, name, llm) -> str:
    prompt = ChatPromptTemplate.from_template("""
Write a formal complaint letter to the {department} department in India.

Issue: {issue_title}
Description: {description}
Location: {location}
Severity: {severity}
Reported by: {name}
Date: {date}

Requirements:
- Address it to the concerned department head
- State the problem clearly with location and impact on residents
- Request urgent action with a reasonable timeline
- Professional yet firm tone
- 200-250 words
- End with the reporter's name

Return only the letter text.""")

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "issue_title": issue_title,
        "description": description,
        "location": location or "as shown in the attached photo",
        "severity": severity,
        "department": department,
        "name": name or "Concerned Citizen",
        "date": datetime.now().strftime("%d %B %Y"),
    }).strip()


def build_whatsapp_message(r: dict, location: str) -> str:
    """
    Build a ready-to-share WhatsApp message (no API call — pure string).
    Uses the Hinglish summary if available.
    """
    dept = r.get("department", "")
    helpline = DEPARTMENT_CONTACTS.get(dept, "")
    helpline_line = f"\n📞 {dept} Helpline: {helpline}" if helpline else ""

    summary = r.get("hinglish_summary", "")
    loc = location or r.get("location_hints", "our area")

    return (
        f"🚨 *Civic Issue Alert — NagarSeva AI*\n\n"
        f"📍 *Location:* {loc}\n"
        f"⚠️ *Issue:* {r.get('issue_title', '')}\n"
        f"🔴 *Severity:* {r.get('severity', '')} ({r.get('severity_score', '')}/10)\n"
        f"🏢 *Department:* {dept}{helpline_line}\n\n"
        f"{summary}\n\n"
        f"Agar aapko bhi yeh dikha hai toh report karo aur is message ko aage bhejo! 🙏"
    )