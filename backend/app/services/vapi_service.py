"""Vapi.ai integration for outbound calls."""

import httpx
from typing import Optional, Any

from ..core.config import get_settings


VAPI_BASE = "https://api.vapi.ai"


async def create_outbound_call(
    customer_phone: str,
    assistant_id: Optional[str] = None,
    assistant_overrides: Optional[dict] = None,
    metadata: Optional[dict] = None,
    claim_context: Optional[dict] = None,
) -> dict:
    """
    Create an outbound phone call via Vapi.
    Returns Vapi call response with id, status, etc.
    """
    settings = get_settings()
    if not settings.VAPI_API_KEY:
        raise ValueError("VAPI_API_KEY is not configured")

    assistant_id = assistant_id or settings.VAPI_ASSISTANT_ID
    phone_number_id = settings.VAPI_PHONE_NUMBER_ID

    if not phone_number_id:
        raise ValueError("VAPI_PHONE_NUMBER_ID is not configured")
    if not assistant_id and not assistant_overrides and not claim_context:
        raise ValueError("Either VAPI_ASSISTANT_ID, assistant_overrides, or claim_context is required")

    payload: dict = {
        "phoneNumberId": phone_number_id,
        "customer": {"number": _normalize_phone(customer_phone)},
    }

    if assistant_id and not assistant_overrides and not claim_context:
        payload["assistantId"] = assistant_id
    else:
        # Use transient assistant with claim-specific context
        assistant = assistant_overrides or {}
        if claim_context:
            system_prompt = claim_context.get("system_prompt") or "You are a medical billing specialist checking claim status."
            first_message = claim_context.get("first_message") or "Hello, I'm calling to check on a claim status."
            assistant["model"] = {
                "provider": "openai",
                "model": "gpt-4o",
                "messages": [{"role": "system", "content": system_prompt}],
            }
            assistant["firstMessage"] = first_message
        payload["assistant"] = assistant if assistant else {"firstMessage": "Hello, I'm calling about a claim."}

    if metadata:
        payload["metadata"] = metadata

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{VAPI_BASE}/call/phone",
            headers={
                "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def _normalize_phone(phone: str) -> str:
    """Ensure phone has +1 for US numbers if missing."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone and not phone.startswith("+"):
        if len(phone) == 10 and phone.isdigit():
            return f"+1{phone}"
        if len(phone) == 11 and phone.startswith("1"):
            return f"+{phone}"
    return phone
