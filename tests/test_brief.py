from conftest import LEAD, poll_until_done

SUMMARY_KEYS = {"total", "urgent", "action_needed", "fyi", "calendar", "newsletter", "promo", "spam"}


async def test_brief_returns_202_with_job_id(client):
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r.status_code == 202
    data = r.json()
    assert data["job_id"]
    assert data["status"] in ("pending", "done")


async def test_brief_job_completes(client):
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/brief/{job_id}", timeout=120.0)

    assert result["status"] == "done"
    assert result["content"]
    assert isinstance(result["content"], str)
    assert len(result["content"]) > 0


async def test_brief_summary_shape(client):
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/brief/{job_id}", timeout=120.0)

    summary = result["summary"]
    assert set(summary.keys()) >= SUMMARY_KEYS
    assert summary["total"] >= 0
    for key in SUMMARY_KEYS - {"total"}:
        assert isinstance(summary[key], int)
        assert summary[key] >= 0


async def test_brief_summary_counts_add_up(client):
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    job_id = r.json()["job_id"]

    result = await poll_until_done(client, f"{LEAD}/brief/{job_id}", timeout=120.0)
    s = result["summary"]

    label_sum = (
        s["urgent"] + s["action_needed"] + s["fyi"]
        + s["calendar"] + s["newsletter"] + s["promo"] + s["spam"]
    )
    assert label_sum == s["total"]


async def test_brief_get_by_job_id(client):
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    job_id = r.json()["job_id"]

    await poll_until_done(client, f"{LEAD}/brief/{job_id}", timeout=120.0)

    # Fetch again by id — should be cached as done
    r2 = await client.get(f"{LEAD}/brief/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "done"
    assert r2.json()["job_id"] == job_id


async def test_briefs_latest_returns_200_or_404(client):
    r = await client.get(f"{LEAD}/briefs/latest")
    assert r.status_code in (200, 404)


async def test_briefs_latest_shape_when_exists(client):
    # Ensure at least one brief exists
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    await poll_until_done(client, f"{LEAD}/brief/{r.json()['job_id']}", timeout=120.0)

    r = await client.get(f"{LEAD}/briefs/latest")
    assert r.status_code == 200
    data = r.json()
    assert data["content"]
    assert data["summary"]
    assert set(data["summary"].keys()) >= SUMMARY_KEYS


async def test_brief_cache_reuse_within_one_hour(client):
    # First call — may create new or reuse existing
    r1 = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r1.status_code == 202
    job_id_1 = r1.json()["job_id"]
    await poll_until_done(client, f"{LEAD}/brief/{job_id_1}", timeout=120.0)

    # Second call within 1 hour — must return same job_id, status done immediately
    r2 = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r2.status_code == 202
    data2 = r2.json()
    assert data2["status"] == "done"
    assert data2["job_id"] == job_id_1


async def test_brief_job_not_found(client):
    r = await client.get(f"{LEAD}/brief/nonexistent-job-id")
    assert r.status_code == 404
