import google.generativeai as genai
from datetime import datetime
from prompts.templates import LETTER_PROMPT

def generate_letter(issue_title, description, location, severity, department, name):
    model = genai.GenerativeModel("gemini-3-flash-preview")
    
    prompt = LETTER_PROMPT.format(
        issue_title=issue_title,
        description=description,
        location=location,
        severity=severity,
        department=department,
        name=name,
        date=datetime.now().strftime("%d %B %Y")
    )
    
    response = model.generate_content(prompt)
    return response.text.strip()