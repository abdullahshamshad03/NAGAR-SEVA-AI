"""
Email + WhatsApp generation for NagarSeva AI.

Replaces the old printed-letter flow with a ready-to-send EMAIL: real Delhi
department email IDs, an AI-drafted body the citizen can edit inline, and a
one-click mailto link that opens their own mail app pre-filled.
"""

import urllib.parse
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Official Delhi department contacts (helpline + public complaint email).
# Sourced from each department's official Delhi-government grievance/contact pages.
DEPARTMENT_CONTACTS = {
    "PWD":          {"phone": "1800-11-0093", "email": "complaint@pwddelhi.gov.in"},
    "MCD":          {"phone": "155305",       "email": "mcd-ithelpdesk@mcd.nic.in"},
    "DJB":          {"phone": "1916",         "email": "grievances-djb@delhi.gov.in"},
    "BSES":         {"phone": "19123",        "email": "brpl.customercare@reliancegroupindia.com"},
    "Delhi Police": {"phone": "112",          "email": "delpol.service@delhipolice.gov.in"},
    "Fire Service": {"phone": "101",          "email": "doed.dlfire@nic.in"},
    "Environment":  {"phone": "011-23392306", "email": "msdpcc@nic.in"},
    "Health":       {"phone": "011-22302441", "email": "dghs@delhi.gov.in"},
    "Transport":    {"phone": "011-23930763", "email": "commtpt@nic.in"},
    "Education":    {"phone": "011-23890172", "email": "ddeedu@nic.in"},
}


def get_department_email(department: str) -> str:
    return DEPARTMENT_CONTACTS.get(department, {}).get("email", "")


def generate_email(issue_title, description, location, severity,
                   department, name, llm) -> dict:
    """
    Returns a dict: {"to": ..., "subject": ..., "body": ...}
    The body is AI-drafted and meant to be shown in an editable text area.
    """
    dept_email = get_department_email(department)
    subject = f"Civic Complaint: {issue_title} at {location}"

    prompt = ChatPromptTemplate.from_template("""
Write a polite but firm complaint EMAIL body to the {department} department in Delhi, India.
This will be sent over email by a citizen, so write it in email style (not a formal postal letter).

Issue: {issue_title}
Details: {description}
Location: {location}
Severity: {severity}
Citizen name: {name}
Date: {date}

Requirements:
- Start with "Dear {department} Team," (no postal address block)
- 2 short paragraphs: (1) what the problem is + exact location + who it affects,
  (2) a clear request for action with a reasonable timeline
- Polite, civic-minded, but firm
- 120-160 words
- End with "Regards," then the citizen's name on the next line
- Plain text only, no markdown, no subject line (subject is handled separately)

Return only the email body text.""")

    chain = prompt | llm | StrOutputParser()
    body = chain.invoke({
        "issue_title": issue_title,
        "description": description,
        "location": location or "the location shown in the attached photo",
        "severity": severity,
        "department": department,
        "name": name or "Concerned Citizen",
        "date": datetime.now().strftime("%d %B %Y"),
    }).strip()

    return {"to": dept_email, "subject": subject, "body": body}


def build_mailto(to: str, subject: str, body: str) -> str:
    """Construct a mailto: URL that opens the user's mail app pre-filled."""
    params = urllib.parse.urlencode(
        {"subject": subject, "body": body},
        quote_via=urllib.parse.quote,
    )
    return f"mailto:{to}?{params}"


def build_whatsapp_message(r: dict, location: str) -> str:
    """Ready-to-share WhatsApp message (no API call — pure string)."""
    dept = r.get("department", "")
    contact = DEPARTMENT_CONTACTS.get(dept, {})
    helpline = contact.get("phone", "")
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