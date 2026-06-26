"""
Predictive insights for NagarSeva AI.

Looks at the issues stored so far and asks the LLM to surface useful,
human-readable insights and predictions for the community / authorities.
This is a lightweight 'analytics brain' on top of the raw SQLite data.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def generate_insights(stats: dict, area_stats: list, llm) -> str:
    """
    stats: output of database.get_stats()
    area_stats: output of database.get_area_stats()
    llm: LangChain chat model

    Returns a short, readable insights paragraph (plain text).
    """
    # If there's almost no data, don't bother calling the LLM
    if stats["total"] < 2:
        return ("Not enough data yet to generate insights. "
                "Report a few more issues to unlock predictive analytics.")

    cat_summary = ", ".join(
        f'{c["category"]} ({c["count"]})' for c in stats["by_category"]
    )
    area_summary = ", ".join(
        f'{a["location"]} ({a["issue_count"]} issues)' for a in area_stats[:5]
    )

    prompt = ChatPromptTemplate.from_template("""
You are a civic data analyst for an Indian municipal dashboard.

Here is the current data:
- Total issues: {total}
- Pending: {pending}, Resolved: {resolved}
- Total people affected: {affected}
- Issues by category: {categories}
- Most affected areas: {areas}

Write 3 to 4 short, punchy insights for city authorities. Be specific and
data-driven. Where reasonable, include a light prediction or recommendation
(e.g. seasonal risk, which department is overloaded, which area needs a drive).

Format as plain sentences, each starting with a relevant emoji.
Keep it under 120 words. No headings, no markdown bullets.""")

    try:
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({
            "total": stats["total"],
            "pending": stats["pending"],
            "resolved": stats["resolved"],
            "affected": stats["total_affected"],
            "categories": cat_summary or "none",
            "areas": area_summary or "none",
        }).strip()
    except Exception as e:
        print("INSIGHTS ERROR:", str(e))
        return ("📊 Insights are temporarily unavailable. "
                "The raw dashboard data above is still accurate.")