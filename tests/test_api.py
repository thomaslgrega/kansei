from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from kansei import save_postings, sha256
from kansei.api import app, get_session
from kansei.config import settings
from kansei.db import Extraction
from kansei.llm import PostingFacts, prompt_snapshot

FACTS = PostingFacts(
    role_summary="Builds payment services.",
    seniority="mid",
    must_have_skills=["Python"],
    japanese_as_written=None,
    japanese_required="not_stated",
    japanese_level="not_stated",
    jlpt="not_stated",
    remote_policy="hybrid",
)


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides = {}


def make_extraction(posting_id: int, day: int, role_summary: str, **overrides) -> Extraction:
    return Extraction(**{
        "posting_id": posting_id,
        "text": role_summary,
        "text_sha256": sha256(role_summary),
        "model": settings.openai_model,
        "prompt_sha": prompt_snapshot()[0],
        "facts": FACTS.model_copy(update={"role_summary": role_summary}).model_dump(mode="json"),
        "created_at": datetime(2026, 10, day, tzinfo=UTC),
        **overrides,
    })


def test_list_postings_filters_by_token(client, session, make_posting):
    save_postings(
        session,
        [make_posting(token="kansei-test"), make_posting(token="other", id="2", url="https://example.com/2")],
        datetime(2026, 10, 5, tzinfo=UTC),
    )

    response = client.get("/postings", params={"token": "kansei-test"})

    assert response.status_code == 200
    assert [posting["url"] for posting in response.json()] == ["https://example.com/1"]


def test_get_posting_returns_404_for_a_posting_that_doesnt_exist(client):
    response = client.get("/postings/0")

    assert response.status_code == 404


def test_get_posting_returns_the_newest_extraction_for_the_current_model_and_prompt(client, session, make_posting):
    ids = save_postings(session, [make_posting()], datetime(2026, 10, 5, tzinfo=UTC))
    posting_id = ids["https://example.com/1"]
    session.add_all([
        make_extraction(posting_id, 5, "Earlier."),
        make_extraction(posting_id, 6, "Newest."),
        make_extraction(posting_id, 7, "Other model.", model="gpt-5.6-luna"),
        make_extraction(posting_id, 8, "Old promp.", prompt_sha="70b7a0b0", facts={}),
    ])

    response = client.get(f"/postings/{posting_id}")

    assert response.status_code == 200
    assert response.json()["extraction"]["facts"]["role_summary"] == "Newest."
