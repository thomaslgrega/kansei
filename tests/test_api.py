from datetime import UTC, datetime, timedelta

import pytest

from kansei import save_postings, sha256
from kansei.api import why_empty
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
        facts = FACTS.model_copy(update={"role_summary": name, "japanese_required": required, "japanese_level": level, "jlpt": jlpt})
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
        facts = PostingFacts.model_validate(FACTS.model_dump() | {"role_summary": name, "specialties": specialties})
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


def test_checked_is_the_newest_board_posting_whatever_the_filters_ignoring_pasted_ones(client, session, make_posting):
    now = datetime.now(UTC)
    native = FACTS.model_copy(update={"japanese_required": "required", "japanese_level": "native"})
    ids = save_postings(session, [
        make_posting(token="kansei-test", id=f"{n}", url=f"https://example.com/{n}") for n in range(51)
    ], now - timedelta(days=1))
    unextracted = make_posting(token="kansei-other", id="unextracted", url="https://example.com/unextracted")
    ids |= save_postings(session, [unextracted], now - timedelta(days=2))
    ids |= save_postings(session, [unextracted], now)
    ids |= save_postings(session, [
        make_posting(source="url", token="kansei-test", id="pasted", url="https://example.com/pasted")
    ], now + timedelta(minutes=1))
    session.add_all(
        make_extraction(posting_id, 6, url, facts=native.model_dump(mode="json"))
        for url, posting_id in ids.items()
        if url != "https://example.com/unextracted"
    )

    filters = [
        {"token": "kansei-test"},
        {"token": "kansei-test", "page": "2"},
        {"token": "kansei-test", "japanese": "none"},
        {"token": "kansei-test", "specialty": "frontend"},
        {"token": "kansei-test", "japanese": "business", "specialty": "frontend"},
        {"token": "kansei-other"},
    ]
    bodies = [client.get("/api/postings", params=params).json() for params in filters]

    assert [(body["total"], body["page"], datetime.fromisoformat(body["checked_at"])) for body in bodies] == [
        (52, 1, now),
        (52, 2, now),
        (0, 1, now),
        (0, 1, now),
        (0, 1, now),
        (0, 1, now),
    ]


def test_no_postings_is_page_1_of_nothing(client):
    body = client.get("/api/postings", params={"token": "kansei-test", "page": "3"}).json()

    assert {key: value for key, value in body.items() if key != "checked_at"} == {
        "postings": [],
        "total": 0,
        "page": 1,
        "board": None,
        "matched_boards": [],
        "filtered_out": False,
    }


@pytest.fixture
def searched_postings(session, make_posting):
    session.add_all([
        Board(source="greenhouse", token="op-jobs", name="Orbit Pay"),
        Board(source="lever", token="zw-careers", name="Zetaworks K.K."),
        Board(source="greenhouse", token="gjp", name="Google Japan"),
    ])
    hrmos = {"source": "hrmos", "token": "kitsune"}
    cases = [
        ("orbit-backend", {"token": "op-jobs", "title": "Backend Engineer"}, "Builds payment APIs.", ["Ruby"]),
        ("orbit-frontend", {"token": "op-jobs", "title": "Frontend Engineer"}, "Builds the dashboard.", ["TypeScript"]),
        ("quokka", {"token": "quokka", "title": "Senior Backend Engineer"}, "Builds the ledger.", ["Go"]),
        (
            "zetaworks",
            {"source": "lever", "token": "zw-careers", "title": "Django Engineer"},
            "Maintains the shop.",
            ["GitHub Actions", "MongoDB"],
        ),
        (
            "umbra",
            {"source": "url", "token": "careers.example.co.jp", "company_name": "Umbra Labs"},
            "Builds Kubernetes operators.",
            ["Python"],
        ),
        (
            "firmware",
            hrmos | {"title": "オープンポジション", "headline": "Firmware Engineer", "location": ""},
            "Writes code for cameras.",
            ["C"],
        ),
        ("japanese", hrmos | {"title": "バックエンドエンジニア", "location": "東京都"}, "Builds the recommendation engine.", ["Java"]),
        ("google", {"token": "gjp", "title": "Site Reliability Engineer"}, "Runs the fleet.", ["C++"]),
        ("ruby-ja", hrmos | {"title": "シニアRubyエンジニア", "location": "東京都"}, "Builds the store.", ["Rails"]),
    ]
    now = datetime.now(UTC)
    for hours_ago, (name, posting, role_summary, skills) in enumerate(cases):
        url = f"https://example.com/{name}"
        ids = save_postings(session, [make_posting(**{"id": name, "url": url} | posting)], now - timedelta(hours=hours_ago))
        facts = FACTS.model_copy(update={"role_summary": role_summary, "must_have_skills": skills})
        session.add(make_extraction(ids[url], 6, role_summary, facts=facts.model_dump(mode="json")))


def test_a_search_keeps_postings_where_every_word_matches_a_field(client, searched_postings):
    queries = [
        "zetaworks", "zw", "quokka", "umbra", "frontend", "firmware", "github", "ledger", "ORBIT", "orbit backend",
        "kube", "go", "c++", "ruby", "エンジニア", "recommendation", "  orbit  ", "", "orbit ledger", "nothingmatches",
    ]

    shown = {
        query: [
            row["posting"]["url"].removeprefix("https://example.com/")
            for row in client.get("/api/postings", params={"q": query}).json()["postings"]
            if row["posting"]["url"].startswith("https://example.com/")
        ]
        for query in queries
    }

    assert shown == {
        "zetaworks": ["zetaworks"],
        "zw": ["zetaworks"],
        "quokka": ["quokka"],
        "umbra": ["umbra"],
        "frontend": ["orbit-frontend"],
        "firmware": ["firmware"],
        "github": ["zetaworks"],
        "ledger": ["quokka"],
        "ORBIT": ["orbit-backend", "orbit-frontend"],
        "orbit backend": ["orbit-backend"],
        "kube": ["umbra"],
        "go": ["quokka", "google"],
        "c++": ["google"],
        "ruby": ["orbit-backend", "ruby-ja"],
        "エンジニア": ["japanese", "ruby-ja"],
        "recommendation": ["japanese"],
        "  orbit  ": ["orbit-backend", "orbit-frontend"],
        "": ["orbit-backend", "orbit-frontend", "quokka", "zetaworks", "umbra", "firmware", "japanese", "google", "ruby-ja"],
        "orbit ledger": [],
        "nothingmatches": [],
    }


def test_a_search_combines_with_my_japanese_and_specialty(client, japanese_postings, specialty_postings):
    searches = [
        {"q": "basic"},
        {"q": "basic", "japanese": "basic"},
        {"q": "native", "japanese": "business"},
        {"q": "stated", "japanese": "none"},
        {"q": "ml", "specialty": "data"},
        {"q": "fullstack", "specialty": "backend"},
        {"q": "backend", "specialty": "frontend"},
    ]

    shown = [
        [
            row["posting"]["url"].removeprefix("https://example.com/")
            for row in client.get("/api/postings", params={"token": "kansei-test"} | search).json()["postings"]
        ]
        for search in searches
    ]

    assert shown == [["basic"], ["basic"], [], ["not-stated"], ["data-ml"], ["fullstack"], []]


def test_filtered_out_says_the_japanese_or_specialty_filters_hide_every_match(client, japanese_postings):
    searches = [
        {"q": "native", "japanese": "business"},
        {"q": "native", "specialty": "frontend"},
        {"specialty": "frontend"},
        {"q": "native"},
        {"q": "basic", "japanese": "business"},
        {"q": "nothingmatches", "japanese": "business"},
    ]

    answers = [
        (body["total"], body["filtered_out"])
        for body in (client.get("/api/postings", params={"token": "kansei-test"} | search).json() for search in searches)
    ]

    assert answers == [(0, True), (0, True), (0, True), (1, False), (1, False), (0, False)]


def test_a_search_names_the_boards_matching_it_exact_ones_first(client, session):
    session.add_all([
        Board(source="lever", token="kansei-orbital", name="Kansei Orbital"),
        Board(source="greenhouse", token="kansei-orbit", name="Kansei Orbit"),
        Board(source="ashby", token="kansei-gone", status="removed"),
        Board(source="ashby", token="kansei-orb", name="Orb", status="removed"),
    ])
    queries = ["kansei orbit backend", "kansei-gone", "kansei orb", ""]

    matched = {query: client.get("/api/postings", params={"q": query}).json()["matched_boards"] for query in queries}

    assert matched == {
        "kansei orbit backend": [
            {"source": "greenhouse", "token": "kansei-orbit", "company": "Kansei Orbit", "exact": True, "removed": False},
        ],
        "kansei-gone": [
            {"source": "ashby", "token": "kansei-gone", "company": "kansei-gone", "exact": True, "removed": True},
        ],
        "kansei orb": [
            {"source": "ashby", "token": "kansei-orb", "company": "Orb", "exact": True, "removed": True},
            {"source": "greenhouse", "token": "kansei-orbit", "company": "Kansei Orbit", "exact": False, "removed": False},
            {"source": "lever", "token": "kansei-orbital", "company": "Kansei Orbital", "exact": False, "removed": False},
        ],
        "": [],
    }


def test_a_search_is_paged_and_counted_after_the_candidate_check(client, paged_postings):
    body = client.get("/api/postings", params={"token": "kansei-test", "q": "older", "page": "2"}).json()

    assert (
        body["total"],
        body["page"],
        [row["posting"]["url"].removeprefix("https://example.com/") for row in body["postings"]],
    ) == (60, 2, [f"older-{n}" for n in range(9, -1, -1)])


def test_the_postings_answer_names_the_board_asked_for_and_whether_it_was_removed(client, session):
    session.add_all([
        Board(source="greenhouse", token="kansei-test", name="Kansei Test K.K."),
        Board(source="lever", token="kansei-unnamed"),
        Board(source="ashby", token="kansei-removed", name="Removed Co", status="removed"),
    ])
    asked = [
        {},
        {"source": "greenhouse", "token": "kansei-test"},
        {"source": "lever", "token": "kansei-unnamed"},
        {"source": "ashby", "token": "kansei-removed"},
        {"source": "greenhouse", "token": "kansei-missing"},
        {"source": "lever", "token": "kansei-test"},
        {"token": "kansei-test"},
    ]

    boards = [client.get("/api/postings", params=params).json()["board"] for params in asked]

    assert boards == [
        None,
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "removed": False, "why_empty": "just_added"},
        {"source": "lever", "token": "kansei-unnamed", "company": "kansei-unnamed", "removed": False, "why_empty": "just_added"},
        {"source": "ashby", "token": "kansei-removed", "company": "Removed Co", "removed": True, "why_empty": "removed"},
        None,
        None,
        None,
    ]


def test_a_board_narrows_the_postings_for_a_visitor_who_does_not_follow_it(client, session, make_posting, log_in_as):
    session.add_all([Board(source="greenhouse", token="kansei-test"), Board(source="ashby", token="kansei-test")])
    ids = save_postings(
        session,
        [make_posting(token="kansei-test"), make_posting(source="ashby", token="kansei-test", id="2", url="https://example.com/2")],
        datetime.now(UTC),
    )
    session.add_all(make_extraction(posting_id, 6, url) for url, posting_id in ids.items())
    board = {"source": "ashby", "token": "kansei-test"}

    logged_out = client.get("/api/postings", params=board).json()
    log_in_as("ada@example.com")
    logged_in = client.get("/api/postings", params=board).json()

    assert [[row["posting"]["url"] for row in body["postings"]] for body in (logged_out, logged_in)] == [
        ["https://example.com/2"],
        ["https://example.com/2"],
    ]


def test_a_board_with_nothing_shown_says_why_from_its_status_when_it_was_added_checked_and_its_candidates():
    checked = datetime(2026, 11, 17, 3, tzinfo=UTC)
    before, after = checked - timedelta(days=30), checked + timedelta(minutes=5)
    cases = [
        ("active", before, checked, 3, 2),
        ("active", after, checked, 0, 0),
        ("active", after, None, 0, 0),
        ("active", before, checked, 0, 0),
        ("active", checked, checked, 0, 0),
        ("active", before, checked, 3, 0),
        ("removed", before, checked, 0, 0),
        ("removed", after, checked, 0, 0),
        ("removed", before, checked, 2, 0),
        ("removed", before, checked, 2, 2),
    ]

    assert [why_empty(*case) for case in cases] == [
        None,
        "just_added",
        "just_added",
        "nothing_to_show",
        "nothing_to_show",
        "filtered_out",
        "removed",
        "removed",
        "filtered_out",
        None,
    ]


def test_the_postings_answer_says_why_a_board_shows_nothing(client, session, make_posting):
    now = datetime.now(UTC)
    session.add_all([
        Board(source="greenhouse", token="kansei-new", created_at=now + timedelta(minutes=5)),
        Board(source="greenhouse", token="kansei-pending", created_at=now - timedelta(days=30)),
        Board(source="greenhouse", token="kansei-test", created_at=now - timedelta(days=30)),
        Board(source="greenhouse", token="kansei-gone", status="removed", created_at=now - timedelta(days=30)),
    ])
    ids = save_postings(session, [
        make_posting(token="kansei-test", id="1", url="https://example.com/1"),
        make_posting(token="kansei-pending", id="2", url="https://example.com/2"),
    ], now)
    session.add(make_extraction(ids["https://example.com/1"], 6, "Backend."))
    asked = [
        {"token": "kansei-new"},
        {"token": "kansei-pending"},
        {"token": "kansei-test"},
        {"token": "kansei-test", "specialty": "frontend"},
        {"token": "kansei-test", "specialty": "backend", "q": "nowhere"},
        {"token": "kansei-gone"},
    ]

    bodies = [client.get("/api/postings", params={"source": "greenhouse", **params}).json() for params in asked]

    assert [(body["total"], body["board"]["why_empty"]) for body in bodies] == [
        (0, "just_added"),
        (0, "nothing_to_show"),
        (1, None),
        (0, "filtered_out"),
        (0, "filtered_out"),
        (0, "removed"),
    ]
