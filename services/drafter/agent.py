import logging

import anthropic

logger = logging.getLogger(__name__)
_client = anthropic.AsyncAnthropic()

_SYSTEM = """\
You are a professional email assistant drafting reply emails on behalf of the user.
Read the email thread carefully, then write a reply that:
- Matches the language of the original email
- Follows the user's style profile strictly (unless instructions override it)
- Is clear, direct, and complete — no placeholder text
- Never sends — only writes the draft
"""

_TOOL = {
    "name": "create_draft",
    "description": "Return the complete email draft reply.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "Reply subject line, e.g. 'Re: Original Subject'.",
            },
            "body": {
                "type": "string",
                "description": "Full reply email body, ready to send.",
            },
            "language": {
                "type": "string",
                "description": "ISO 639-1 language code of the reply, e.g. 'en', 'fr', 'de'.",
            },
        },
        "required": ["subject", "body", "language"],
    },
}


async def generate(email: dict, instructions: str, style_profile: str) -> dict:
    """Generate a draft reply. Returns {subject, body, language}."""
    style_block = (
        f"User style profile:\n{style_profile}"
        if style_profile
        else "No style profile provided — use a professional, concise tone."
    )
    instructions_block = (
        f"User instructions: {instructions}"
        if instructions
        else "No specific instructions."
    )

    body_text = email.get("body") or email.get("snippet") or ""
    prompt = (
        f"Email to reply to:\n"
        f'From: {email.get("from", "")}\n'
        f'Subject: {email.get("subject", "")}\n'
        f'Date: {email.get("date", "")}\n'
        f"Body:\n{body_text}\n\n"
        f"{style_block}\n\n"
        f"{instructions_block}\n\n"
        "Write a reply email draft."
    )

    response = await _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "create_draft":
            return block.input

    logger.warning("create_draft tool not called")
    return {"subject": f'Re: {email.get("subject", "")}', "body": "", "language": "en"}
