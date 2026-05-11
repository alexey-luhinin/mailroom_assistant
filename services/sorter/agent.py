import asyncio
import logging
import os
import anthropic

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic()

PRIORITY = {
    "urgent": 1,
    "action_needed": 2,
    "calendar": 3,
    "fyi": 4,
    "newsletter": 5,
    "promo": 6,
    "spam": 7,
}

_SYSTEM = """\
You are an email classifier. Use subject and sender only — never guess from missing context.

Labels:
- urgent: requires response within 24h
- action_needed: requires response, not time-critical
- fyi: informational, no reply needed
- newsletter: subscriptions and digests
- promo: discounts, sales, offers
- spam: suspicious or unwanted email
- calendar: meeting invite or scheduling request
"""

_TOOL = {
    "name": "classify_emails",
    "description": "Return classification for every email in the list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":     {"type": "string"},
                        "label":  {"type": "string",
                                   "enum": list(PRIORITY.keys())},
                        "reason": {"type": "string",
                                   "description": "One sentence explaining the label."},
                    },
                    "required": ["id", "label", "reason"],
                },
            }
        },
        "required": ["classifications"],
    },
}


async def classify(emails: list[dict]) -> list[dict]:
    """Return list of {id, label, reason, priority} for each email."""
    if not emails:
        return []

    results = []
    tasks = [_classify_batch(chunk) for chunk in _chunks(emails, 50)]
    for batch_result in await asyncio.gather(*tasks):
        results.extend(batch_result)
    return results


async def _classify_batch(emails: list[dict]) -> list[dict]:
    lines = "\n".join(
        f'{i + 1}. id="{e["id"]}" from="{e["from"]}" subject="{e["subject"]}"'
        for i, e in enumerate(emails)
    )
    response = await _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": f"Classify these emails:\n{lines}"}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "classify_emails":
            return [
                {
                    "id": c["id"],
                    "label": c["label"],
                    "reason": c["reason"],
                    "priority": PRIORITY.get(c["label"], 9),
                }
                for c in block.input["classifications"]
            ]
    lost_ids = [e["id"] for e in emails]
    raise RuntimeError(
        f"classify_emails tool not called; {len(lost_ids)} email(s) lost: {lost_ids}"
    )


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
