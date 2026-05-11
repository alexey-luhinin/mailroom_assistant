import pytest

from conftest import LEAD, poll_until_done

RUN_STEPS = {"sorting", "briefing", "done", "failed"}


async def test_run_returns_202_with_job_id(client):
    r = await client.post(f"{LEAD}/run", json={"days": 1})
    assert r.status_code == 202
    data = r.json()
    assert data["job_id"]
    assert data["status"] == "pending"
    assert data["step"] == "sorting"


async def test_run_workflow_completes(client):
    r = await client.post(f"{LEAD}/run", json={"days": 1})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/run/{job_id}", timeout=300.0)

    assert result["status"] == "done"
    assert result["step"] == "done"
    assert isinstance(result["emails_classified"], int)
    assert isinstance(result["emails_skipped"], int)
    assert result["emails_classified"] >= 0
    assert result["emails_skipped"] >= 0


async def test_run_job_step_is_valid(client):
    r = await client.post(f"{LEAD}/run", json={"days": 1})
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/run/{job_id}", timeout=300.0)
    assert result["step"] in RUN_STEPS


async def test_run_poll_before_done_returns_valid_step(client):
    r = await client.post(f"{LEAD}/run", json={"days": 1})
    job_id = r.json()["job_id"]

    # First poll — may still be pending
    poll_r = await client.get(f"{LEAD}/run/{job_id}")
    assert poll_r.status_code == 200
    data = poll_r.json()
    assert data["status"] in ("pending", "done", "failed")
    assert data["step"] in RUN_STEPS


@pytest.mark.parametrize("days", [0, -1, 31, 100])
async def test_run_invalid_days(client, days):
    r = await client.post(f"{LEAD}/run", json={"days": days})
    assert r.status_code == 422


async def test_run_job_not_found(client):
    r = await client.get(f"{LEAD}/run/nonexistent-job-id")
    assert r.status_code == 404
