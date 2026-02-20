"""Apply call outcomes to claims. Shared by webhooks and workflows."""

from sqlalchemy.orm import Session

from ..models import Claim
from ..agents.outcome_extractor import ExtractedOutcome


def apply_extracted_to_claim(
    db: Session, claim_id: int, extracted: ExtractedOutcome, ended_reason: str
) -> None:
    """Update claim with LLM-extracted outcome."""
    claim = db.get(Claim, claim_id)
    if not claim:
        return

    status_map = {
        "paid": "resolved",
        "reprocessing": "in_progress",
        "reprocess_requested": "in_progress",
        "denied": "denied",
        "appeal_required": "appeal_required",
        "unknown": "pending" if "no" in (ended_reason or "").lower() or "busy" in (ended_reason or "").lower() else "pending",
    }
    new_status = status_map.get((extracted.claim_status or "").lower(), "pending")
    if (extracted.claim_status or "").lower() in ("paid", "resolved"):
        new_status = "resolved"
    elif extracted.action_taken and "reprocess" in extracted.action_taken.lower():
        new_status = "in_progress"
    elif extracted.action_taken and "appeal" in extracted.action_taken.lower():
        new_status = "appeal_required"

    claim.status = new_status
    if extracted.denial_reason:
        claim.denial_reason = extracted.denial_reason
    if extracted.denial_code:
        claim.denial_code = extracted.denial_code
    if extracted.next_steps or extracted.summary:
        notes_parts = [s for s in [extracted.summary, extracted.next_steps] if s]
        if notes_parts:
            existing = (claim.notes or "").strip()
            new_notes = "\n".join(notes_parts)
            claim.notes = f"{existing}\n{new_notes}".strip() if existing else new_notes


def apply_ended_reason_to_claim(db: Session, claim_id: int, outcome: str) -> None:
    """Fallback: update claim when no LLM extraction."""
    claim = db.get(Claim, claim_id)
    if not claim:
        return
    if outcome in ("resolved", "reprocess_requested"):
        claim.status = "resolved"
    elif outcome == "no_answer":
        claim.status = "pending"
