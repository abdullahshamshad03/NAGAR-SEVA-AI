VISION_PROMPT = """
You are an AI assistant for a civic issue reporting system in India.

Analyze this image and identify the problem.

Respond in EXACT JSON format only:
{
  "issue_title": "Short title in English",
  "description": "What you see in 2-3 sentences",
  "location_hints": "Any visible location clues or 'Not visible'",
  "is_civic_issue": true
}

No extra text. Only JSON.
"""

CATEGORIZE_PROMPT = """
You are a civic issue classifier for Indian cities.

Issue: {issue_title}
Description: {description}

Respond in EXACT JSON format only:
{
  "category": "Road/Water Supply/Garbage/Electricity/Street Lighting/Waterlogging/Other",
  "severity": "Low/Medium/High/Critical",
  "severity_score": 7,
  "department": "PWD/MCD/DJB/BSES/Delhi Police",
  "urgency": "Immediate/Within 3 days/Within a week",
  "affected_people": 100
}

No extra text. Only JSON.
"""

LETTER_PROMPT = """
Write a formal complaint letter to the {department} department.

Issue: {issue_title}
Description: {description}
Location: {location}
Severity: {severity}
Reporter: {name}
Date: {date}

Write a professional 200-250 word letter. Address it to the department head.
"""

HINGLISH_PROMPT = """
Yeh civic issue ki summary casual Hinglish mein likho (Roman script):

Issue: {issue_title}
Category: {category}
Severity: {severity}
Department: {department}

2-3 lines mein batao kya problem hai aur kya karna chahiye.
Bilkul WhatsApp style mein likho.
"""

IMPACT_PROMPT = """
Calculate impact score for this civic issue.

Issue: {issue_title}
Category: {category}
Severity Score: {severity_score}/10
Affected People: {affected_people}

Respond in EXACT JSON format only:
{
  "impact_score": 75,
  "public_safety": 80,
  "health_risk": 60,
  "economic_impact": 70,
  "inconvenience": 85,
  "environmental": 55,
  "escalation_needed": true
}

No extra text. Only JSON.
"""