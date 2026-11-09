from datetime import UTC, datetime, timedelta

from kansei import save_postings, sha256
from kansei.config import settings
from kansei.db import Board, Extraction
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


def test_list_postings_shows_each_open_candidate_once_with_its_newest_extraction(client, session, make_posting):
    now = datetime.now(UTC)
    ids = save_postings(
        session,
        [
            make_posting(token="kansei-test"),
            make_posting(token="kansei-test", id="2", url="https://example.com/remote-usa", location="Remote - USA"),
            make_posting(token="kansei-test", id="3", url="https://example.com/old-prompt"),
            make_posting(token="other", id="4", url="https://example.com/other-board"),
        ],
        now,
    )
    ids |= save_postings(
        session,
        [make_posting(token="kansei-test", id="5", url="https://example.com/closed")],
        now - timedelta(days=3),
    )
    session.add_all([
        make_extraction(ids["https://example.com/1"], 5, "Earlier."),
        make_extraction(ids["https://example.com/1"], 6, "Newest."),
        make_extraction(ids["https://example.com/1"], 7, "Other model.", model="gpt-5.6-luna"),
        make_extraction(ids["https://example.com/1"], 8, "Old prompt.", prompt_sha="70b7a0b0", facts={}),
        make_extraction(ids["https://example.com/remote-usa"], 6, "Remote USA."),
        make_extraction(ids["https://example.com/old-prompt"], 6, "Old prompt.", prompt_sha="70b7a0b0", facts={}),
        make_extraction(ids["https://example.com/closed"], 6, "Closed."),
        make_extraction(ids["https://example.com/other-board"], 6, "Other board."),
    ])

    response = client.get("/api/postings", params={"token": "kansei-test"})

    assert response.status_code == 200
    assert [(row["posting"]["url"], row["facts"]["role_summary"]) for row in response.json()] == [
        ("https://example.com/1", "Newest."),
    ]


def test_list_postings_shows_an_hrmos_candidate_by_its_headline_and_with_no_location(client, session, make_posting):
    hrmos = {"source": "hrmos", "token": "kansei-test"}
    ids = save_postings(
        session,
        [
            make_posting("オープンポジション", "東京都 港区", **hrmos, headline="【エンジニア】オープンポジション"),
            make_posting("インフラエンジニア", "", **hrmos, id="2", url="https://example.com/2"),
            make_posting("経理", "", **hrmos, id="3", url="https://example.com/3", headline="経理"),
        ],
        datetime.now(UTC),
    )
    session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())

    response = client.get("/api/postings", params={"token": "kansei-test"})

    assert sorted(row["posting"]["url"] for row in response.json()) == [
        "https://example.com/1", "https://example.com/2",
    ]


def test_list_postings_puts_the_newest_first_seen_first(client, session, make_posting):
    now = datetime.now(UTC)
    ids = save_postings(session, [make_posting(token="kansei-test")], now - timedelta(days=1))
    ids |= save_postings(session, [make_posting(token="kansei-test", id="2", url="https://example.com/2")], now)
    session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())

    response = client.get("/api/postings", params={"token": "kansei-test"})

    assert [row["posting"]["url"] for row in response.json()] == ["https://example.com/2", "https://example.com/1"]


def test_get_posting_returns_404_for_a_posting_that_doesnt_exist(client):
    response = client.get("/api/postings/0")

    assert response.status_code == 404


def test_get_posting_returns_the_newest_extraction_for_the_current_model_and_prompt(client, session, make_posting):
    ids = save_postings(session, [make_posting()], datetime(2026, 10, 5, tzinfo=UTC))
    posting_id = ids["https://example.com/1"]
    session.add_all([
        make_extraction(posting_id, 5, "Earlier."),
        make_extraction(posting_id, 6, "Newest."),
        make_extraction(posting_id, 7, "Other model.", model="gpt-5.6-luna"),
        make_extraction(posting_id, 8, "Old prompt.", prompt_sha="70b7a0b0", facts={}),
    ])

    response = client.get(f"/api/postings/{posting_id}")

    assert response.status_code == 200
    assert response.json()["extraction"]["facts"]["role_summary"] == "Newest."


def test_a_posting_whose_board_has_a_name_shows_that_name_everywhere(client, session, make_posting, log_in_as):
    session.add(Board(source="greenhouse", token="kansei-test", name="Kansei Test K.K."))
    ids = save_postings(session, [make_posting(token="kansei-test")], datetime.now(UTC))
    posting_id = ids["https://example.com/1"]
    session.add(make_extraction(posting_id, 6, "Named."))
    log_in_as("ada@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_id})

    listed = client.get("/api/postings", params={"token": "kansei-test"}).json()
    single = client.get(f"/api/postings/{posting_id}").json()
    tracked = client.get("/api/me/tracked").json()

    assert [row["posting"]["company"] for row in [*listed, single, *tracked]] == ["Kansei Test K.K."] * 3


def test_a_posting_whose_board_has_no_name_shows_its_token(client, session, make_posting):
    session.add(Board(source="greenhouse", token="kansei-test"))
    ids = save_postings(session, [make_posting(token="kansei-test")], datetime.now(UTC))

    response = client.get(f"/api/postings/{ids['https://example.com/1']}")

    assert response.json()["posting"]["company"] == "kansei-test"


def test_a_pasted_posting_shows_its_token_even_when_a_board_shares_it(client, session, make_posting):
    session.add(Board(source="greenhouse", token="example.com", name="Example K.K."))
    ids = save_postings(session, [make_posting(source="url", token="example.com")], datetime.now(UTC))

    response = client.get(f"/api/postings/{ids['https://example.com/1']}")

    assert response.json()["posting"]["company"] == "example.com"


def test_a_pasted_posting_shows_the_company_name_its_page_declared(client, session, make_posting):
    posting = make_posting(source="url", token="careers.example.co.jp", company_name="Example K.K.")
    ids = save_postings(session, [posting], datetime.now(UTC))

    response = client.get(f"/api/postings/{ids['https://example.com/1']}")

    assert response.json()["posting"]["company"] == "Example K.K."
