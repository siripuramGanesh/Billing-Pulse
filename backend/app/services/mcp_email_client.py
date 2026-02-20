"""
MCP client that spawns the email MCP server and calls send_email.
Used by email_service when USE_MCP_EMAIL=true.
"""

import asyncio
import os
import sys
from pathlib import Path

from ..core.config import get_settings


async def _send_email_via_mcp(
    to_emails: list[str],
    subject: str,
    body_html: str,
    body_text: str | None,
) -> bool:
    """Call the MCP email server's send_email tool. Returns True if sent successfully."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    settings = get_settings()
    env = os.environ.copy()
    env["SMTP_HOST"] = settings.SMTP_HOST or ""
    env["SMTP_PORT"] = str(settings.SMTP_PORT)
    env["SMTP_USER"] = settings.SMTP_USER or ""
    env["SMTP_PASSWORD"] = settings.SMTP_PASSWORD or ""
    env["SMTP_USE_TLS"] = "true" if settings.SMTP_USE_TLS else "false"
    env["MAIL_FROM_EMAIL"] = settings.MAIL_FROM_EMAIL or ""
    env["MAIL_FROM_NAME"] = settings.MAIL_FROM_NAME or "BillingPulse"

    # Run the MCP server as a subprocess (same Python, app package)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_email_server"],
        env=env,
    )
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "send_email",
                    arguments={
                        "receiver": to_emails,
                        "subject": subject,
                        "body": body_html,
                        "body_text": body_text,
                    },
                )
                if result.isError or not result.content:
                    return False
                text = getattr(result.content[0], "text", "") if result.content else ""
                return text.strip().lower().startswith("email sent")
    except Exception:
        return False


def send_email_via_mcp(
    to_emails: list[str],
    subject: str,
    body_html: str,
    body_text: str | None = None,
) -> bool:
    """Synchronous wrapper: run the async MCP client and return whether email was sent."""
    try:
        return asyncio.run(
            _send_email_via_mcp(to_emails, subject, body_html, body_text)
        )
    except Exception:
        return False
