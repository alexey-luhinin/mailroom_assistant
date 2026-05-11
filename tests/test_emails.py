import pytest

from conftest import LEAD

VALID_LABELS = {"urgent", "action_needed", "fyi", "calendar", "newsletter", "promo", "spam"}


async def test_get_emails_returns_list(client):
    r = await client.get(f"{LEAD}/emails")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_emails_shape(client):
    r = await client.get(f"{LEAD}/emails")
    for e in r.json():
        assert "id" in e
        assert "from" in e
        assert "subject" in e
        assert "date" in e
        assert "label" in e
        assert "reason" in e
        assert e["label"] in VALID_LABELS


async def test_get_emails_label_filter(client):
    r = await client.get(f"{LEAD}/emails", params={"label": "urgent", "days": 7})
    assert r.status_code == 200
    for e in r.json():
        assert e["label"] == "urgent"


async def test_get_emails_label_filter_action_needed(client):
    r = await client.get(f"{LEAD}/emails", params={"label": "action_needed", "days": 7})
    assert r.status_code == 200
    for e in r.json():
        assert e["label"] == "action_needed"


@pytest.mark.parametrize("days", [1, 3, 7, 14, 30])
async def test_get_emails_valid_days(client, days):
    r = await client.get(f"{LEAD}/emails", params={"days": days})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_emails_wider_window_includes_narrower(client):
    r1 = await client.get(f"{LEAD}/emails", params={"days": 1})
    r7 = await client.get(f"{LEAD}/emails", params={"days": 7})
    ids_1 = {e["id"] for e in r1.json()}
    ids_7 = {e["id"] for e in r7.json()}
    # Every email from the last day should also appear in the last 7 days
    assert ids_1.issubset(ids_7)


@pytest.mark.parametrize("days", [0, -1, 31, 100])
async def test_get_emails_invalid_days(client, days):
    r = await client.get(f"{LEAD}/emails", params={"days": days})
    assert r.status_code == 422
