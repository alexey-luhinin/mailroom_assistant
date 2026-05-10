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
You are a smart personal assistant writing a spoken-style morning briefing for Alexey.

Rules:
- Sound like a real assistant talking directly to Alexey, not a template filler.
- Be specific: mention deadlines, expiry times, amounts, counterparty names — anything actionable.
- For each urgent or action_needed email write a tight 2-3 sentence block: what happened, what Alexey needs to do, and by when if known.
- ALWAYS start each email entry with the subject in bold markdown: **Subject** from Sender. This is required, never skip the bold formatting.
- The subject must be wrapped in double asterisks like this: **Invoice overdue** from Acme Corp. Never write it as plain text.
- After the bold subject line, write the summary on the next line as plain text.
- Do NOT use bullet points, markdown headers, or any other formatting — only **bold** for email subjects.
- Newsletter, promo, and spam emails: do not summarize them individually, only count them.
- Match the language of each email in its summary (write in Russian if the email is in Russian, etc.).
- The whole briefing should read like one coherent message, not a list.

Example of a correctly formatted email entry:
**Invoice #1234 overdue** from Acme Corp.
Payment of $5,000 was due yesterday. Log into the billing portal and approve it today to avoid a late fee.
"""

_TOOL = {
    "name": "create_briefing",
    "description": "Return the morning briefing as plain structured text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "The full briefing text. Structure:\n"
                    "1. Opening line: 'Good morning, Alexey. You have {total} emails today.'\n"
                    "2. If urgent emails exist — section 'Urgent:' followed by each email on its own paragraph: "
                    "'**[Subject]** from [Sender].\\n[2-3 sentences: context, required action, deadline if known.]'\n"
                    "3. If action_needed emails exist — section 'Action needed:' same format.\n"
                    "4. Closing line: '[fyi] FYI · [newsletter] newsletters · [promo] promos — nothing urgent.' "
                    "(omit any category with count 0).\n"
                    "5. If NO urgent or action_needed emails: replace sections 2-4 with "
                    "'Nothing urgent today. {total} emails, all low priority.'"
                ),
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
        return "Good morning, Alexey. Nothing urgent today. Your inbox is empty."

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

    urgent_emails    = [e for e in today_emails    if e.get("label") == "urgent"]
    urgent_emails   += [e for e in previous_emails if e.get("label") == "urgent"]
    action_emails    = [e for e in today_emails    if e.get("label") == "action_needed"]
    action_emails   += [e for e in previous_emails if e.get("label") == "action_needed"]

    prompt = (
        f"Date: {date_str}\n"
        f"Email counts: {summary_line}\n\n"
        f"Urgent emails (need individual write-up):\n{_fmt(urgent_emails)}\n\n"
        f"Action needed emails (need individual write-up):\n{_fmt(action_emails)}\n\n"
        "Write the briefing following the tool description exactly. "
        "Plain text only — no markdown, no bullet points, no asterisks."
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
    return f"Good morning, Alexey. Failed to generate briefing for {date_str}."
