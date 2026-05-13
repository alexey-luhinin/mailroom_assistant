import logging

import anthropic

logger = logging.getLogger(__name__)
_client = anthropic.AsyncAnthropic()

_SYSTEM = """\
You are an email summarizer. For each email given, write a 2-3 sentence summary
that captures the key points and any action items. Write each summary in the same
language as the email. Be concise — no filler, no pleasantries.
"""

_TOOL = {
    "name": "summarize_emails",
    "description": "Return a 2-3 sentence summary for each email in the list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summaries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "summary": {
                            "type": "string",
                            "description": "2-3 sentence summary in the email's language.",
                        },
                    },
                    "required": ["id", "summary"],
                },
            }
        },
        "required": ["summaries"],
    },
}

_BODY_LIMIT = 2000


async def summarize(emails: list[dict]) -> list[dict]:
    """Return list of {id, summary} for each email."""
    if not emails:
        return []

    blocks = []
    for i, e in enumerate(emails):
        body = (e.get("body") or e.get("snippet") or "")[:_BODY_LIMIT]
        blocks.append(
            f'{i + 1}. id="{e["id"]}" subject="{e.get("subject", "")}" date="{e.get("date", "")}"\n'
            f"   Body: {body}"
        )

    response = await _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": "Summarize these emails:\n\n" + "\n\n".join(blocks)}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "summarize_emails":
            return block.input["summaries"]

    logger.warning("summarize_emails tool not called; %d email(s) lost", len(emails))
    return []
