"""Chatbot brain: question in -> answer about funding opportunities out.

Pipeline:
  1. load opportunities from the DB (joined with agency name/country)
  2. rank them against the question (retriever.py)
  3. if an LLM is configured, have it write a natural answer using ONLY those rows;
     otherwise return a clean formatted list (always works, no key needed).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agency, Opportunity
from app.chat import retriever


def _load_opps(db: Session) -> list[dict]:
    rows = db.execute(
        select(Opportunity, Agency.name, Agency.country).join(Agency, Opportunity.agency_id == Agency.id)
    ).all()
    opps = []
    for opp, agency_name, country in rows:
        opps.append({
            "program_name": opp.program_name,
            "agency_name": agency_name,
            "country": country,
            "funding_amount": opp.funding_amount,
            "amount_value": float(opp.amount_value) if opp.amount_value is not None else None,
            "research_area": opp.research_area,
            "eligibility": opp.eligibility,
            "deadline": opp.deadline.isoformat() if opp.deadline else None,
            "status": opp.status,
            "summary": opp.summary,
            "tags": opp.tags,
            "link": opp.application_link,
        })
    return opps


def _format_list(matches: list[dict]) -> str:
    if not matches:
        return "I couldn't find any matching opportunities in the database."
    lines = [f"Found {len(matches)} matching opportunit{'y' if len(matches)==1 else 'ies'}:\n"]
    for o in matches:
        amt = o.get("funding_amount") or (f"{o['amount_value']:,.0f}" if o.get("amount_value") else "amount not stated")
        dl = o.get("deadline") or "no deadline listed"
        lines.append(
            f"• {o['program_name']} ({o.get('agency_name','?')})\n"
            f"    Amount: {amt}  |  Deadline: {dl}  |  Status: {o.get('status')}\n"
            f"    Eligibility: {o.get('eligibility') or '—'}\n"
            f"    Apply: {o.get('link') or '—'}"
        )
    return "\n".join(lines)


def _llm_answer(question: str, matches: list[dict], llm) -> str:
    context = "\n".join(
        f"- {o['program_name']} | agency: {o.get('agency_name')} | amount: {o.get('funding_amount') or o.get('amount_value')}"
        f" | deadline: {o.get('deadline')} | status: {o.get('status')} | eligibility: {o.get('eligibility')}"
        f" | area: {o.get('research_area')} | link: {o.get('link')}"
        for o in matches
    )
    prompt = (
        "You are FundRadar's assistant. Answer the user's question using ONLY the funding "
        "opportunities listed below. Be concise and factual. If none are relevant, say so. "
        "Mention amounts, deadlines and how to apply where useful.\n\n"
        f"QUESTION: {question}\n\nOPPORTUNITIES:\n{context}\n\nANSWER:"
    )
    return llm.complete(prompt).strip()


def answer(question: str, db: Session, llm=None) -> str:
    parsed = retriever.parse_query(question)
    matches = retriever.rank(_load_opps(db), parsed)
    if not matches:
        return "I couldn't find any matching opportunities in the database."

    use_llm = settings.llm_provider != "mock"
    if use_llm:
        if llm is None:
            from app.llm.providers import get_llm
            llm = get_llm()
        try:
            return _llm_answer(question, matches, llm)
        except Exception as e:
            return _format_list(matches) + f"\n\n(LLM unavailable: {e})"
    return _format_list(matches)
