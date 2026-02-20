"""
Generate claim-specific context for the voice assistant.
Used when initiating a call so the AI knows what to ask about.
"""

from ..models import Claim, Payer


def build_call_system_prompt(claim: Claim, payer: Payer) -> str:
    """
    Build a system prompt for the voice assistant with claim and IVR context.
    """
    parts = [
        "You are a professional medical billing specialist calling an insurance payer to check on a claim status.",
        "",
        "## Claim Information",
        f"- Claim number: {claim.claim_number}",
        f"- Patient: {claim.patient_name or 'Not specified'}",
        f"- Date of service: {claim.date_of_service or 'Not specified'}",
        f"- Amount: ${claim.amount}" if claim.amount is not None else "- Amount: Not specified",
    ]
    if claim.denial_reason:
        parts.append(f"- Previous denial reason: {claim.denial_reason}")
    if claim.denial_code:
        parts.append(f"- Denial code: {claim.denial_code}")

    parts.extend([
        "",
        "## Your Goals",
        "1. Get the current status of the claim",
        "2. If denied, get the denial reason and code",
        "3. If possible, request reprocessing or escalate to appeals",
        "4. Note any next steps or follow-up required",
        "5. Be professional, concise, and persistent",
        "",
    ])

    # Prefer structured ivr_config; fall back to ivr_notes
    if getattr(payer, "ivr_config", None) and isinstance(payer.ivr_config, dict):
        steps = payer.ivr_config.get("steps") or []
        if steps:
            parts.append("## IVR Navigation (structured)")
            for i, step in enumerate(steps, 1):
                prompt = step.get("prompt") or step.get("message") or ""
                options = step.get("options") or step.get("keys") or {}
                opts_str = ", ".join(f'"{k}": {v}' for k, v in options.items()) if options else "—"
                parts.append(f"Step {i}: {prompt}. Options: {opts_str}")
            parts.append("")
    elif payer.ivr_notes:
        parts.extend([
            "## IVR Navigation (for this payer)",
            payer.ivr_notes,
            "",
        ])
    if payer.department_code:
        parts.append(f"Preferred department code: {payer.department_code}")

    parts.extend([
        "",
        "## Payer",
        f"You are calling: {payer.name}",
        "",
        "Start by greeting and stating you are calling to check on a claim. Provide the claim number when asked.",
    ])

    return "\n".join(parts)


def build_first_message(claim: Claim, payer: Payer) -> str:
    """First thing the AI says when the call connects."""
    return (
        f"Hello, I'm calling from a medical billing office to check on the status of claim number {claim.claim_number} "
        f"for patient {claim.patient_name or 'our patient'}. Could you help me with that?"
    )
