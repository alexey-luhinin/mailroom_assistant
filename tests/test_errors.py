"""
404 and 422 validation error cases across all endpoints.
These tests do not depend on DB state and run against any environment.
"""
import pytest

from conftest import LEAD


# ── 404 — nonexistent job IDs ──────────────────────────────────────────────────

async def test_run_job_not_found(client):
    r = await client.get(f"{LEAD}/run/nonexistent-job-id")
    assert r.status_code == 404


async def test_draft_job_not_found(client):
    r = await client.get(f"{LEAD}/draft/nonexistent-job-id")
    assert r.status_code == 404


async def test_brief_job_not_found(client):
    r = await client.get(f"{LEAD}/brief/nonexistent-job-id")
    assert r.status_code == 404


async def test_approve_not_found(client):
    r = await client.post(f"{LEAD}/approve/nonexistent-job-id", json={})
    assert r.status_code == 404


# ── 422 — invalid days on POST /run ───────────────────────────────────────────

@pytest.mark.parametrize("days", [0, -1, 31, 100, -999])
async def test_run_invalid_days(client, days):
    r = await client.post(f"{LEAD}/run", json={"days": days})
    assert r.status_code == 422


async def test_run_missing_days_uses_default(client):
    # days has a default of 1, so omitting it is valid
    r = await client.post(f"{LEAD}/run", json={})
    assert r.status_code == 202


# ── 422 — invalid days on GET /emails ─────────────────────────────────────────

@pytest.mark.parametrize("days", [0, -1, 31, 100])
async def test_emails_invalid_days(client, days):
    r = await client.get(f"{LEAD}/emails", params={"days": days})
    assert r.status_code == 422


# ── 422 — approve draft that is not yet done ──────────────────────────────────

async def test_approve_requires_done_status(client):
    # Start a draft job and immediately try to approve — should be 422 (pending) or
    # 200 if the job completed instantly. Never 500.
    emails_r = await client.get(f"{LEAD}/emails", params={"days": 7})
    emails = emails_r.json()
    if not emails:
        pytest.skip("No emails in DB")

    r = await client.post(f"{LEAD}/draft", json={"email_id": emails[0]["id"]})
    job_id = r.json()["job_id"]

    approve_r = await client.post(f"{LEAD}/approve/{job_id}", json={})
    assert approve_r.status_code in (200, 422)


# ── Error response shape ───────────────────────────────────────────────────────

async def test_404_response_has_detail_field(client):
    r = await client.get(f"{LEAD}/draft/nonexistent-job-id")
    assert r.status_code == 404
    assert "detail" in r.json()


async def test_422_response_has_detail_field(client):
    r = await client.post(f"{LEAD}/run", json={"days": 99})
    assert r.status_code == 422
    assert "detail" in r.json()
