"""
Email service for notifying claimers (practice) after a call.
Uses direct SMTP by default, or MCP (send_email tool via subprocess) when USE_MCP_EMAIL=true.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from ..core.config import get_settings


def is_email_configured() -> bool:
    """True if SMTP is configured enough to send mail."""
    s = get_settings()
    return bool(s.SMTP_HOST and s.MAIL_FROM_EMAIL)


def _send_email_smtp(
    to_emails: list[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> bool:
    """Send via direct SMTP (original implementation)."""
    settings = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
    msg["To"] = ", ".join(to_emails)
    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))
    try:
        if settings.SMTP_USE_TLS:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.MAIL_FROM_EMAIL, to_emails, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.MAIL_FROM_EMAIL, to_emails, msg.as_string())
        return True
    except Exception:
        return False


def send_email(
    to_emails: list[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> bool:
    """
    Send an email to the given addresses. Returns True if sent, False if skipped or failed.
    Uses MCP (spawned email server subprocess) when USE_MCP_EMAIL=true, else direct SMTP.
    """
    if not to_emails or not is_email_configured():
        return False
    if get_settings().USE_MCP_EMAIL:
        from .mcp_email_client import send_email_via_mcp
        return send_email_via_mcp(to_emails, subject, body_html, body_text)
    return _send_email_smtp(to_emails, subject, body_html, body_text)


def _get_practice_notification_emails(db: Any, practice_id: int) -> list[str]:
    """Return list of emails to notify for this practice: notification_email if set, else active users."""
    from ..models import Practice, User
    practice = db.get(Practice, practice_id)
    if not practice:
        return []
    if getattr(practice, "notification_email", None) and str(practice.notification_email).strip():
        return [practice.notification_email.strip()]
    users = db.query(User).filter(
        User.practice_id == practice_id,
        User.is_active == True,
    ).all()
    return [u.email for u in users if u.email]


def build_claim_call_notification_content(
    claim: Any,
    payer_name: str,
    extracted: Optional[dict] = None,
    call_duration_seconds: Optional[int] = None,
) -> tuple[str, str]:
    """
    Build subject and HTML body for the "call outcome" email.
    Returns (subject, body_html).
    """
    app_name = get_settings().APP_NAME
    claim_number = getattr(claim, "claim_number", "") or "—"
    patient = getattr(claim, "patient_name", None) or "—"
    status = getattr(claim, "status", "") or "—"
    summary = ""
    next_steps = ""
    denial = ""
    if extracted and isinstance(extracted, dict):
        summary = (extracted.get("summary") or "").strip()
        next_steps = (extracted.get("next_steps") or "").strip()
        if extracted.get("denial_reason") or extracted.get("denial_code"):
            denial = f"Denial: {extracted.get('denial_reason') or ''} ({extracted.get('denial_code') or ''})".strip()
    duration = f"{call_duration_seconds}s" if call_duration_seconds else "—"
    subject = f"[{app_name}] Call update: Claim {claim_number} – {status}"
    body_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; line-height: 1.5;">
  <h2>Claim call update</h2>
  <p>Your automated call for this claim has completed. Here is the update.</p>
  <table style="border-collapse: collapse;">
    <tr><td style="padding:4px 8px; font-weight:bold;">Claim #</td><td style="padding:4px 8px;">{claim_number}</td></tr>
    <tr><td style="padding:4px 8px; font-weight:bold;">Patient</td><td style="padding:4px 8px;">{patient}</td></tr>
    <tr><td style="padding:4px 8px; font-weight:bold;">Payer</td><td style="padding:4px 8px;">{payer_name}</td></tr>
    <tr><td style="padding:4px 8px; font-weight:bold;">Status</td><td style="padding:4px 8px;">{status}</td></tr>
    <tr><td style="padding:4px 8px; font-weight:bold;">Call duration</td><td style="padding:4px 8px;">{duration}</td></tr>
  </table>
  {f'<p><strong>Summary:</strong> {summary}</p>' if summary else ''}
  {f'<p><strong>Next steps:</strong> {next_steps}</p>' if next_steps else ''}
  {f'<p><strong>{denial}</strong></p>' if denial else ''}
  <p style="color:#666; font-size:0.9em;">This is an automated message from {app_name}.</p>
</body>
</html>
"""
    return subject, body_html


def send_claim_call_notification(
    db: Any,
    claim_id: int,
    payer_name: str,
    extracted: Optional[dict] = None,
    call_duration_seconds: Optional[int] = None,
) -> bool:
    """
    Send email to the claim's practice (claimer) with the call outcome.
    Returns True if at least one email was sent. Also updates claim.claimer_notified_at when sent.
    """
    from ..models import Claim
    claim = db.get(Claim, claim_id)
    if not claim:
        return False
    practice_id = getattr(claim, "practice_id", None)
    if not practice_id:
        return False
    to_emails = _get_practice_notification_emails(db, practice_id)
    if not to_emails:
        return False
    subject, body_html = build_claim_call_notification_content(
        claim, payer_name, extracted=extracted, call_duration_seconds=call_duration_seconds
    )
    body_text = subject + "\n\n" + ((extracted or {}).get("summary") or "") if extracted else subject
    ok = send_email(to_emails, subject, body_html, body_text=body_text)
    if ok and hasattr(claim, "claimer_notified_at"):
        from datetime import datetime, timezone
        claim.claimer_notified_at = datetime.now(timezone.utc)
    return ok
