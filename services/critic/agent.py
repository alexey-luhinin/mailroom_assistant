import logging

import anthropic

logger = logging.getLogger(__name__)
_client = anthropic.AsyncAnthropic()

_SYSTEM = """\
You are a strict email quality reviewer. Your job is to evaluate draft reply emails
against the user's personal style profile and return a score with honest feedback.

Scoring criteria (each worth up to 2 points):
1. Conciseness — no filler words, unnecessary padding, or repetition
2. Tone — matches the style profile (e.g. friendly-but-direct, casual, formal)
3. Language — reply is in the same language as specified
4. Relevance — directly addresses the content of the email
5. Instructions — follows any user-provided instructions

Score 1-10. Score >= 7 means the draft is approved as-is.
Be specific in your feedback: quote the exact phrase or section that needs work.
Do NOT rewrite the draft — only evaluate and explain.
"""

_TOOL = {
    "name": "review_draft",
    "description": "Return the quality evaluation of the draft email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Quality score from 1 to 10.",
            },
            "feedback": {
                "type": "string",
                "description": (
                    "One paragraph explaining the score. "
                    "If score < 7, include specific actionable improvements."
                ),
            },
        },
        "required": ["score", "feedback"],
    },
}


async def review(
    draft: dict,
    instructions: str,
    iteration: int,
    style_profile: str,
) -> dict:
    style_block = (
        f"User style profile:\n{style_profile}"
        if style_profile
        else "No style profile provided — use a professional, concise tone as the baseline."
    )
    instructions_block = (
        f"User instructions: {instructions}"
        if instructions
        else "No specific user instructions."
    )

    prompt = (
        f"Draft email to review (iteration {iteration}/3):\n"
        f'Subject: {draft["subject"]}\n'
        f'Language: {draft["language"]}\n'
        f"Body:\n{draft['body']}\n\n"
        f"{style_block}\n\n"
        f"{instructions_block}\n\n"
        "Evaluate this draft and call the review_draft tool with your score and feedback."
    )

    response = await _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "review_draft":
            score = int(block.input["score"])
            return {"score": score, "feedback": block.input["feedback"]}

    logger.warning("review_draft tool not called")
    return {"score": 5, "feedback": "Unable to evaluate the draft."}
