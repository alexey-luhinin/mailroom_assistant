from dotenv import load_dotenv

load_dotenv("config/.env")

import logging
import os

from fastapi import FastAPI

import agent
from models import ReviewRequest, ReviewResponse

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.abspath(__file__))
_STYLE_PROFILE_PATH = os.path.join(_ROOT, "config", "style_profile.md")

app = FastAPI(title="Critic")


def _load_style_profile() -> str:
    try:
        with open(_STYLE_PROFILE_PATH) as f:
            return f.read()
    except FileNotFoundError:
        return ""


@app.get("/health")
def health():
    return {"status": "ok", "service": "critic"}


@app.post("/review", response_model=ReviewResponse)
async def post_review(request: ReviewRequest):
    style_profile = _load_style_profile()
    result = await agent.review(
        draft=request.draft.model_dump(),
        instructions=request.instructions,
        iteration=request.iteration,
        style_profile=style_profile,
    )
    score = result["score"]
    return ReviewResponse(
        score=score,
        approved=score >= 7,
        feedback=result["feedback"],
        improved_draft=None,
    )
