import asyncio
import logging
import os

import anthropic
import httpx

logger = logging.getLogger(__name__)
_client = anthropic.AsyncAnthropic()

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")
_FETCH_LABELS = {"urgent", "action_needed", "calendar", "fyi"}

_SYSTEM = """\
You are writing a morning email briefing for a busy professional.
For each email write a 2-4 sentence summary: what it is about, what action (if any) is needed, and any key details.
Match the language of each individual email in its summary.
Format output exactly as the template specifies.
"""

_TOOL = {
    "name": "create_briefing",
    "description": "Return the complete morning briefing in markdown.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Full markdown briefing following the specified template.",
            }
        },
        "required": ["content"],
    },
}


async def _fetch_body(client: httpx.AsyncClient, email_id: str) -> str:
    try:
        resp = await client.get(f"{MCP_URL}/emails/{email_id}", timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("body", "")
    except Exception as e:
        logger.warning("Failed to fetch body for %s: %s", email_id, e)
        return ""


async def _enrich(emails: list[dict]) -> list[dict]:
    to_fetch = [e for e in emails if e.get("label") in _FETCH_LABELS]
    if not to_fetch:
        return emails

    async with httpx.AsyncClient() as client:
        bodies = await asyncio.gather(*(_fetch_body(client, e["id"]) for e in to_fetch))

    body_by_id = {e["id"]: body for e, body in zip(to_fetch, bodies)}
    return [{**e, "body": body_by_id[e["id"]]} if e["id"] in body_by_id else e for e in emails]


async def generate(
    date_str: str,
    today_emails: list[dict],
    previous_emails: list[dict],
    summary: dict,
) -> str:
    if not today_emails and not previous_emails:
        return f"# Morning Briefing — {date_str}\n\nNo emails to report."

    today_emails, previous_emails = await asyncio.gather(
        _enrich(today_emails),
        _enrich(previous_emails),
    )

    def _fmt(emails: list[dict]) -> str:
        lines = []
        for e in emails:
            line = (
                f'- id="{e["id"]}" from="{e["from"]}" subject="{e["subject"]}"'
                f' label="{e["label"]}" date="{e["date"]}"'
            )
            if e.get("body"):
                line += f'\n  body: {e["body"][:2000]}'
            lines.append(line)
        return "\n".join(lines) or "(none)"

    summary_line = (
        f"Total: {summary['total']}, Urgent: {summary['urgent']}, "
        f"Action needed: {summary['action_needed']}, FYI: {summary['fyi']}, "
        f"Calendar: {summary['calendar']}, Newsletter: {summary['newsletter']}, "
        f"Promo: {summary['promo']}, Spam: {summary['spam']}"
    )

    prompt = (
        f"Generate a morning briefing for {date_str}.\n\n"
        f"Counts: {summary_line}\n\n"
        f"Unresolved from previous days (urgent/action_needed without a draft):\n{_fmt(previous_emails)}\n\n"
        f"Today's emails:\n{_fmt(today_emails)}\n\n"
        "Template:\n"
        "# Morning Briefing — <date>\n"
        "## Summary\n- Total / per-label counts\n"
        "## Unresolved from previous days\n### <Label>\n- **<subject>** from <sender> (<date>)\n  <2-4 sentence summary>\n"
        "## Today\n### <Label>\n- **<subject>** from <sender>\n  <2-4 sentence summary>"
    )

    response = await _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "create_briefing":
            return block.input["content"]

    logger.warning("create_briefing tool not called")
    return f"# Morning Briefing — {date_str}\n\nFailed to generate content."
