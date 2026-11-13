from datetime import UTC, datetime, timedelta

import pytest

from kansei import save_postings, sha256
from kansei.config import settings
from kansei.db import Board, Extraction
from kansei.llm import PostingFacts, prompt_snapshot

FACTS = PostingFacts(
    role_summary="Builds payment services.",
    specialties=["backend"],
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
    assert [(row["posting"]["url"], row["facts"]["role_summary"]) for row in response.json()["postings"]] == [
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

    assert sorted(row["posting"]["url"] for row in response.json()["postings"]) == [
        "https://example.com/1", "https://example.com/2",
    ]


def test_list_postings_puts_the_newest_first_seen_first(client, session, make_posting):
    now = datetime.now(UTC)
    ids = save_postings(session, [make_posting(token="kansei-test")], now - timedelta(days=1))
    ids |= save_postings(session, [make_posting(token="kansei-test", id="2", url="https://example.com/2")], now)
    session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())

    response = client.get("/api/postings", params={"token": "kansei-test"})

    assert [row["posting"]["url"] for row in response.json()["postings"]] == ["https://example.com/2", "https://example.com/1"]


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

    listed = client.get("/api/postings", params={"token": "kansei-test"}).json()["postings"]
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


def test_a_posting_carries_its_boards_logo_url_or_null(client, session, make_posting):
    session.add_all([
        Board(source="greenhouse", token="kansei-test", logo_url="https://example.com/logo.png"),
        Board(source="greenhouse", token="no-logo"),
        Board(source="greenhouse", token="example.com", logo_url="https://example.com/board.png"),
    ])
    ids = save_postings(
        session,
        [
            make_posting(token="kansei-test"),
            make_posting(token="no-logo", id="2", url="https://example.com/2"),
            make_posting(source="url", token="example.com", id="3", url="https://example.com/3"),
        ],
        datetime.now(UTC),
    )
    session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())

    rows = client.get("/api/postings").json()["postings"]

    assert sorted(
        (row["posting"]["url"], row["posting"]["logo_url"]) for row in rows if row["posting"]["url"] in ids
    ) == [
        ("https://example.com/1", "https://example.com/logo.png"),
        ("https://example.com/2", None),
        ("https://example.com/3", None),
    ]


@pytest.fixture
def japanese_postings(session, make_posting):
    cases = [
        ("none", "preferred", "business", "not_stated"),
        ("not-stated", "not_stated", "not_stated", "not_stated"),
        ("basic", "required", "not_stated", "N4"),
        ("conversational", "required", "conversational", "not_stated"),
        ("business", "required", "not_stated", "not_stated"),
        ("native", "required", "native", "N1"),
    ]
    now = datetime.now(UTC)
    for hours_ago, (name, required, level, jlpt) in enumerate(cases):
        url = f"https://example.com/{name}"
        ids = save_postings(session, [make_posting(token="kansei-test", id=name, url=url)], now - timedelta(hours=hours_ago))
        facts = FACTS.model_copy(update={"japanese_required": required, "japanese_level": level, "jlpt": jlpt})
        session.add(make_extraction(ids[url], 6, name, facts=facts.model_dump(mode="json")))


def test_each_posting_carries_its_japanese_requirement(client, japanese_postings):
    response = client.get("/api/postings", params={"token": "kansei-test"})

    assert [(row["posting"]["url"], row["japanese_requirement"]) for row in response.json()["postings"]] == [
        ("https://example.com/none", "none"),
        ("https://example.com/not-stated", "not_stated"),
        ("https://example.com/basic", "basic"),
        ("https://example.com/conversational", "conversational"),
        ("https://example.com/business", "business"),
        ("https://example.com/native", "native"),
    ]


def test_my_japanese_keeps_postings_at_or_below_it_plus_none_and_not_stated(client, japanese_postings):
    choices = ["any", "none", "basic", "conversational", "business", "native", "fluent"]

    shown = {
        choice: [
            row["posting"]["url"].removeprefix("https://example.com/")
            for row in client.get("/api/postings", params={"token": "kansei-test", "japanese": choice}).json()["postings"]
        ]
        for choice in choices
    }

    assert shown == {
        "any": ["none", "not-stated", "basic", "conversational", "business", "native"],
        "none": ["none", "not-stated"],
        "basic": ["none", "not-stated", "basic"],
        "conversational": ["none", "not-stated", "basic", "conversational"],
        "business": ["none", "not-stated", "basic", "conversational", "business"],
        "native": ["none", "not-stated", "basic", "conversational", "business", "native"],
        "fluent": ["none", "not-stated", "basic", "conversational", "business", "native"],
    }


@pytest.fixture
def specialty_postings(session, make_posting):
    cases = [
        ("backend", ["backend"]),
        ("fullstack", ["fullstack"]),
        ("data-ml", ["data", "ml"]),
        ("sales-manager", ["management", "customer_facing"]),
        ("other", []),
    ]
    now = datetime.now(UTC)
    for hours_ago, (name, specialties) in enumerate(cases):
        url = f"https://example.com/{name}"
        ids = save_postings(session, [make_posting(token="kansei-test", id=name, url=url)], now - timedelta(hours=hours_ago))
        facts = PostingFacts.model_validate(FACTS.model_dump() | {"specialties": specialties})
        session.add(make_extraction(ids[url], 6, name, facts=facts.model_dump(mode="json")))


def test_specialty_keeps_postings_with_any_of_the_picks_and_other_keeps_those_with_none(client, specialty_postings):
    choices = [
        None, "backend", "frontend", "backend,ml", "", "bogus", "ml,bogus", "fullstack", "other", "customer_facing",
        "security,other",
    ]

    shown = {
        choice: [
            row["posting"]["url"].removeprefix("https://example.com/")
            for row in client.get(
                "/api/postings", params={"token": "kansei-test"} | ({} if choice is None else {"specialty": choice})
            ).json()["postings"]
        ]
        for choice in choices
    }

    assert shown == {
        None: ["backend", "fullstack", "data-ml", "sales-manager", "other"],
        "backend": ["backend", "fullstack"],
        "frontend": ["fullstack"],
        "backend,ml": ["backend", "fullstack", "data-ml"],
        "": [],
        "bogus": [],
        "ml,bogus": ["data-ml"],
        "fullstack": [],
        "other": ["other"],
        "customer_facing": ["sales-manager"],
        "security,other": ["other"],
    }


def test_a_postings_row_carries_no_sales_or_support_flag(client, specialty_postings):
    response = client.get("/api/postings", params={"token": "kansei-test", "specialty": "backend"})

    assert [sorted(row) for row in response.json()["postings"]] == [["facts", "japanese_requirement", "posting"]] * 2


@pytest.fixture
def paged_postings(session, make_posting):
    # 60 seen an hour ago, then 60 seen now; a Remote - USA posting in each batch is no candidate.
    now = datetime.now(UTC)
    for batch, seen_at in [("older", now - timedelta(hours=1)), ("newer", now)]:
        jobs = [
            make_posting(token="kansei-test", id=f"{batch}-{n}", url=f"https://example.com/{batch}-{n}")
            for n in range(60)
        ]
        jobs.insert(30, make_posting(
            token="kansei-test", id=f"{batch}-usa", url=f"https://example.com/{batch}-usa", location="Remote - USA"
        ))
        ids = save_postings(session, jobs, seen_at)
        session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())


def page_of(client, page: str) -> tuple[int, list[str]]:
    body = client.get("/api/postings", params={"token": "kansei-test", "page": page}).json()
    return body["page"], [row["posting"]["url"].removeprefix("https://example.com/") for row in body["postings"]]


def test_a_middle_page_holds_the_next_50_newest_first_then_by_id(client, paged_postings):
    assert page_of(client, "2") == (
        2,
        [f"newer-{n}" for n in range(9, -1, -1)] + [f"older-{n}" for n in range(59, 19, -1)],
    )


def test_the_last_page_holds_what_is_left(client, paged_postings):
    assert page_of(client, "3") == (3, [f"older-{n}" for n in range(19, -1, -1)])


def test_a_page_out_of_range_or_not_a_number_serves_the_nearest_page(client, paged_postings):
    first, last = page_of(client, "1"), page_of(client, "3")

    assert {page: page_of(client, page) for page in ["0", "-2", "two", "2.5", "", "4", "99999999999999999999"]} == {
        "0": first,
        "-2": first,
        "two": first,
        "2.5": first,
        "": first,
        "4": last,
        "99999999999999999999": last,
    }


def test_the_total_counts_every_page_under_the_filters(client, paged_postings, japanese_postings):
    totals = [
        client.get("/api/postings", params={"token": "kansei-test", "japanese": japanese}).json()["total"]
        for japanese in ["any", "none"]
    ]

    # 120 paged postings plus 6 Japanese ones; "none" keeps the 120 (not stated) and 2 of the 6.
    assert totals == [126, 122]


def test_checked_is_the_newest_board_posting_on_any_page_ignoring_pasted_ones(client, session, make_posting):
    now = datetime.now(UTC)
    seen_again = make_posting(token="kansei-test", id="seen-again", url="https://example.com/seen-again")
    ids = save_postings(session, [seen_again], now - timedelta(days=1))
    ids |= save_postings(session, [
        make_posting(token="kansei-test", id=f"{n}", url=f"https://example.com/{n}") for n in range(50)
    ], now - timedelta(hours=1))
    ids |= save_postings(session, [seen_again], now - timedelta(minutes=10))
    ids |= save_postings(session, [
        make_posting(source="url", token="kansei-test", id="pasted", url="https://example.com/pasted")
    ], now - timedelta(minutes=1))
    session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())

    pages = [client.get("/api/postings", params={"token": "kansei-test", "page": page}).json() for page in ["1", "2"]]

    assert [
        (
            [row["posting"]["url"].removeprefix("https://example.com/") for row in body["postings"]],
            datetime.fromisoformat(body["checked_at"]),
        )
        for body in pages
    ] == [
        (["pasted"] + [str(n) for n in range(49, 0, -1)], now - timedelta(minutes=10)),
        (["0", "seen-again"], now - timedelta(minutes=10)),
    ]


def test_no_postings_is_page_1_of_nothing(client):
    body = client.get("/api/postings", params={"token": "kansei-test", "page": "3"}).json()

    assert body == {"postings": [], "total": 0, "page": 1, "checked_at": None}
