"""
MCP server that exposes a send_email tool.
Run with: python -m app.mcp_email_server
Expects env: SMTP_HOST, MAIL_FROM_EMAIL, (optional) SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS, MAIL_FROM_NAME.
Used by the FastAPI app when USE_MCP_EMAIL=true (spawned as subprocess) or by your IDE MCP config.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anyio
from mcp import types
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server


def _smtp_send(
    to_emails: list[str],
    subject: str,
    body_html: str,
    body_text: str | None,
    from_email: str,
    from_name: str,
    host: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool,
) -> str:
    """Send one email via SMTP. Returns 'ok' or error message."""
    if not to_emails or not host or not from_email:
        return "error: missing to_emails, SMTP_HOST, or MAIL_FROM_EMAIL"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = ", ".join(to_emails)
    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))
    try:
        if use_tls:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_email, to_emails, msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_email, to_emails, msg.as_string())
        return "ok"
    except Exception as e:
        return f"error: {e}"


async def handle_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="send_email",
                title="Send Email",
                description="Send an email to one or more recipients via SMTP (config from env).",
                input_schema={
                    "type": "object",
                    "required": ["receiver", "subject", "body"],
                    "properties": {
                        "receiver": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Recipient email addresses",
                        },
                        "subject": {"type": "string", "description": "Subject line"},
                        "body": {"type": "string", "description": "Email body (plain or HTML)"},
                        "body_text": {"type": "string", "description": "Optional plain-text body"},
                    },
                },
            )
        ]
    )


async def handle_call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    if params.name != "send_email":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Unknown tool: {params.name}")],
            isError=True,
        )
    args = params.arguments or {}
    receiver = args.get("receiver")
    subject = args.get("subject") or ""
    body = args.get("body") or ""
    body_text = args.get("body_text")
    if not receiver:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Missing required argument: receiver")],
            isError=True,
        )
    if isinstance(receiver, str):
        receiver = [receiver]
    from_email = os.environ.get("MAIL_FROM_EMAIL", "")
    from_name = os.environ.get("MAIL_FROM_NAME", "BillingPulse")
    host = os.environ.get("SMTP_HOST", "")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    result = _smtp_send(
        to_emails=receiver,
        subject=subject,
        body_html=body,
        body_text=body_text,
        from_email=from_email,
        from_name=from_name,
        host=host,
        port=port,
        user=user,
        password=password,
        use_tls=use_tls,
    )
    if result == "ok":
        text = "Email sent successfully."
    else:
        text = result
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        isError=(result != "ok"),
    )


def main() -> int:
    app = Server(
        "billingpulse-email",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )

    async def arun() -> None:
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
