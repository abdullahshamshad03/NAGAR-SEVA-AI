# 🏙️ NagarSeva AI

**An AI-powered civic issue reporting platform for Delhi NCR.**
Snap a photo → AI detects the issue → a ready-to-send government complaint.



[![Live App](https://img.shields.io/badge/Live-Cloud%20Run-blue)](https://nagar-seva-ai.streamlit.app/)
[![Built with](https://img.shields.io/badge/AI-Google%20Gemini-orange)](https://ai.google.dev/)
[![Framework](https://img.shields.io/badge/Agent-LangGraph-green)](https://langchain-ai.github.io/langgraph/)

> Built for the **BlockseBlock × Google Vibe2Ship Hackathon** — *Community Hero* track.

---

## 🌐 Live Demo

**App (Google Cloud Run):** https://nagarseva-ai-526399274560.asia-south1.run.app

**App (Streamlit backup):** https://nagar-seva-ai.streamlit.app

**Demo Video:** https://youtu.be/fKZbDeOMNAY

> **Note:** The live demo runs on the Gemini API free tier (20 requests/day, 
> about 6 full analyses). If the daily limit is reached during evaluation, 
> it resets the next day. The app is fully functional — this is only an API 
> quota limit, not a bug.

Deployed on Google Cloud Run.
Deployed on **Google Cloud Run**.

---
<img width="750" height="350" alt="image" src="https://github.com/user-attachments/assets/785adff8-0f1a-4c2e-8466-263d09f38e59" />
<img width="750" height="350" alt="image" src="https://github.com/user-attachments/assets/b6b36408-df9a-4d33-a21f-714239617064" />


## 💡 The Problem

Reporting a civic issue in India is harder than it should be. You have to know which
department is responsible, find their contact details, and write a formal complaint.
The process is slow and confusing, so most people simply give up — and genuine
problems never reach the authorities.

**NagarSeva AI removes every one of these barriers. You just take a photo.**

---

## ✨ What It Does

A citizen uploads a photo of a problem — say, a pothole. From there:

1. **Google Gemini Vision** looks at the photo, confirms it is a genuine civic issue,
   rejects irrelevant images (selfies, food, memes), and judges how serious it is.
2. A **LangGraph agentic pipeline** categorises the issue, assigns the correct
   department, and estimates how many people are realistically affected.
3. The system generates a **ready-to-send complaint email** addressed to the correct
   Delhi government department — sent in one click. A WhatsApp message is also created.
4. The complaint is tracked by mobile number. When an officer marks it resolved, the
   **citizen must verify the fix** — if it's not actually done, the issue is reopened.

---

## 🚀 Key Features

### AI & Automation
- **Image-based reporting** — detects the issue directly from a photo using Gemini Vision.
- **Agentic AI pipeline** — a multi-step LangGraph flow: vision → validate → categorise → impact.
- **Spam filter** — automatically rejects irrelevant or fake images.
- **Duplicate detection** — combines the same issue reported by many people into one.
- **Smart severity** — judges severity from what is actually visible in the photo.

### Citizen Experience
- **Community feed** — see issues across Delhi NCR, view photos, and upvote.
- **Live map** — every reported issue pinned by location, coloured by severity.
- **Gamification** — earn points and badges for reporting, upvoting, and confirming fixes.
- **GPS auto-location** + manual entry with Delhi-NCR validation.
- **Multiple photos** per report for stronger proof.
- **Track complaints** anytime using your mobile number.

### Accountability
- **Officer system** — each department has its own login and sees only its own issues.
- **Citizen verification loop** — officers can't falsely close issues; the citizen confirms the fix.
- **Performance insights** — resolution times and department activity per area.

---

## 🏢 Department Routing

Complaints are routed to **10 real Delhi departments** using official government contacts:

| Issue Type | Department |
|---|---|
| Potholes, roads, footpaths | PWD |
| Garbage, sanitation | MCD |
| Water, sewage, drainage | DJB |
| Streetlights, power, wires | BSES |
| Traffic, parking, encroachment | Delhi Police |
| Fire, burnt structures | Fire Service |
| Pollution, river dumping | Environment (DPCC) |
| Health & sanitation hazards | Health Department |
| Public transport, bus stops | Transport Department |
| School infrastructure | Education Department |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI Models | Google Gemini (`gemini-2.5-flash-lite`) — vision + reasoning |
| AI Framework | LangGraph + LangChain (agentic pipeline) |
| Application | Python + Streamlit |
| Database | SQLite |
| Maps | OpenStreetMap (Nominatim) + Plotly |
| Deployment | Google Cloud Run (Docker) |

---

## ⚙️ Run Locally

**Prerequisites:** Python 3.11, a Google Gemini API key.

```bash
# 1. Clone the repo
git clone https://github.com/abdullahshamshad03/NAGAR-SEVA-AI.git
cd NAGAR-SEVA-AI

# 2. Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Gemini API key
# Create a .env file in the project root:
echo GOOGLE_API_KEY=your_gemini_api_key_here > .env

# 5. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 🔑 Officer Demo Logins

Each department has a demo login (for testing the officer side):

| Department | Password |
|---|---|
| PWD | `pwd123` |
| MCD | `mcd123` |
| DJB | `djb123` |
| BSES | `bses123` |
| Delhi Police | `police123` |
| Fire Service | `fire123` |
| Environment | `env123` |
| Health | `health123` |
| Transport | `transport123` |
| Education | `edu123` |

---

## 📁 Project Structure

```
NAGAR-SEVA-AI/
├── app.py              # Main Streamlit app + UI
├── agent.py            # LangGraph agentic pipeline (vision, categorise, impact)
├── database.py         # SQLite database layer
├── styles.py           # Light/dark theme CSS
├── modules/
│   ├── email_gen.py    # Complaint email + WhatsApp generation
│   ├── geocode.py      # Delhi-NCR geocoding & validation
│   ├── duplicate.py    # AI duplicate detection
│   └── insights.py     # Predictive insights
├── requirements.txt
├── Dockerfile          # Cloud Run container
└── .gcloudignore
```

---

## 🔭 Future Scope

- **Multi-city support** beyond Delhi NCR, with city-specific routing.
- **Video reporting** in addition to photos.
- **Full user accounts** with profiles and notifications.
- **Predictive analytics** to flag areas likely to face issues before they grow.

---

## 👤 Author

**Abdullah Shamshad**
GitHub: [@abdullahshamshad03](https://github.com/abdullahshamshad03)

---

*NagarSeva AI — turning one photo into real civic action.*
