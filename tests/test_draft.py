import pytest

from conftest import LEAD, poll_until_done

DRAFT_STEPS = {"researching", "drafting", "reviewing", "done", "failed"}


async def _get_email_id(client) -> str:
    """Return the id of the first available email, or skip the test."""
    r = await client.get(f"{LEAD}/emails", params={"days": 7})
    emails = r.json()
    if not emails:
        pytest.skip("No emails in DB — run POST /run first")
    return emails[0]["id"]


# ── Draft job ──────────────────────────────────────────────────────────────────

async def test_draft_returns_202_with_job_id(client):
    email_id = await _get_email_id(client)
    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    assert r.status_code == 202
    data = r.json()
    assert data["job_id"]
    assert data["status"] == "pending"
    assert data["step"] == "researching"


async def test_draft_workflow_completes(client):
    email_id = await _get_email_id(client)

    r = await client.post(
        f"{LEAD}/draft",
        json={"email_id": email_id, "instructions": "be brief"},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)

    assert result["status"] == "done"
    draft = result["draft"]
    assert draft["subject"]
    assert draft["body"]
    assert draft["language"]
    # draft_id is only set after Approve — must not be asserted here


async def test_draft_language_is_iso_code(client):
    email_id = await _get_email_id(client)
    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)
    assert result["status"] == "done"
    # ISO 639-1 codes are 2 characters
    assert len(result["draft"]["language"]) == 2


async def test_draft_poll_before_done_returns_valid_status(client):
    email_id = await _get_email_id(client)
    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    job_id = r.json()["job_id"]

    # First poll — job may still be pending
    poll_r = await client.get(f"{LEAD}/draft/{job_id}")
    assert poll_r.status_code == 200
    data = poll_r.json()
    assert data["status"] in ("pending", "done", "failed")
    assert data["step"] in DRAFT_STEPS


async def test_draft_with_instructions(client):
    email_id = await _get_email_id(client)
    r = await client.post(
        f"{LEAD}/draft",
        json={"email_id": email_id, "instructions": "Reply formally and keep it under 3 sentences."},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)
    assert result["status"] == "done"
    assert result["draft"]["body"]


async def test_draft_without_instructions(client):
    email_id = await _get_email_id(client)
    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id, "instructions": ""})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)
    assert result["status"] == "done"


# ── Approve endpoint ───────────────────────────────────────────────────────────

async def test_approve_saves_to_gmail(client):
    email_id = await _get_email_id(client)

    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    job_id = r.json()["job_id"]
    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)
    assert result["status"] == "done"

    approve_r = await client.post(
        f"{LEAD}/approve/{job_id}",
        json={"subject": result["draft"]["subject"], "body": result["draft"]["body"]},
    )
    assert approve_r.status_code == 200
    assert approve_r.json()["draft_id"]


async def test_approve_with_edited_subject_and_body(client):
    email_id = await _get_email_id(client)

    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    job_id = r.json()["job_id"]
    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)
    assert result["status"] == "done"

    approve_r = await client.post(
        f"{LEAD}/approve/{job_id}",
        json={"subject": "Re: edited subject", "body": "Edited body text."},
    )
    assert approve_r.status_code == 200
    assert approve_r.json()["draft_id"]


async def test_approve_uses_saved_draft_when_body_omitted(client):
    email_id = await _get_email_id(client)

    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    job_id = r.json()["job_id"]
    await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)

    # Empty body — lead-agent should fall back to saved draft values
    approve_r = await client.post(f"{LEAD}/approve/{job_id}", json={})
    assert approve_r.status_code == 200
    assert approve_r.json()["draft_id"]


async def test_approve_rejects_pending_draft(client):
    email_id = await _get_email_id(client)

    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id})
    job_id = r.json()["job_id"]

    # Approve immediately without polling — should be 422 or 200 if it finished instantly
    approve_r = await client.post(f"{LEAD}/approve/{job_id}", json={})
    assert approve_r.status_code in (200, 422)


async def test_approve_not_found(client):
    r = await client.post(f"{LEAD}/approve/nonexistent-job-id", json={})
    assert r.status_code == 404


async def test_draft_job_not_found(client):
    r = await client.get(f"{LEAD}/draft/nonexistent-job-id")
    assert r.status_code == 404
