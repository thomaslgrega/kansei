import asyncio
import json

import httpx
import pytest
from sqlalchemy import select, update

from kansei.db import Board, User
from kansei.sources import (
    ASHBY_BOARD,
    ASHBY_GRAPHQL,
    GREENHOUSE_BOARD,
    GREENHOUSE_BOARD_INFO,
    GREENHOUSE_BOARD_PAGE,
    HRMOS_BOARD,
    HRMOS_JOB,
    LEVER_BOARD,
    LEVER_BOARD_PAGE,
)


def greenhouse_job(job_id: int, title: str, location: str) -> dict:
    return {
        "id": job_id,
        "title": title,
        "absolute_url": f"https://job-boards.greenhouse.io/kansei-test/jobs/{job_id}",
        "updated_at": "2026-11-01T00:00:00Z",
        "location": {"name": location},
    }


def serve_greenhouse_board(ats, token: str = "kansei-test", name: str = "Kansei Test K.K.") -> None:
    ats.pages[GREENHOUSE_BOARD.format(token=token)] = httpx.Response(200, json={"jobs": [
        greenhouse_job(1, "Backend Engineer", "Tokyo, Japan"),
        greenhouse_job(2, "Account Executive", "Tokyo, Japan"),
        greenhouse_job(3, "Frontend Engineer", "Berlin, Germany"),
        greenhouse_job(4, "Platform Engineer", "Remote"),
        greenhouse_job(5, "Designer", "Osaka, Japan"),
        greenhouse_job(6, "Data Engineer", "Osaka, Japan"),
    ]})
    ats.pages[GREENHOUSE_BOARD_INFO.format(token=token)] = httpx.Response(200, json={"name": name})


def test_probing_a_board_url_finds_the_board(client, log_in_as, ats):
    serve_greenhouse_board(ats)
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert response.status_code == 200
    assert response.json() == {
        "message": None,
        "hits": [{
            "source": "greenhouse",
            "token": "kansei-test",
            "company": "Kansei Test K.K.",
            "titles": ["Backend Engineer", "Platform Engineer", "Data Engineer"],
            "candidates": 3,
            "state": "not_on_kansei",
            "following": False,
            "logo_url": None,
        }],
    }


def test_a_probe_hit_lists_the_titles_of_its_first_three_candidates(client, log_in_as, ats):
    ats.pages[GREENHOUSE_BOARD.format(token="kansei-test")] = httpx.Response(200, json={"jobs": [
        greenhouse_job(1, "Account Executive", "Tokyo, Japan"),
        greenhouse_job(2, "Backend Engineer", "Tokyo, Japan"),
        greenhouse_job(3, "Frontend Engineer", "Berlin, Germany"),
        greenhouse_job(4, "Platform Engineer", "Remote"),
        greenhouse_job(5, "Data Engineer", "Osaka, Japan"),
        greenhouse_job(6, "Site Reliability Engineer", "Tokyo, Japan"),
    ]})
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert [(hit["titles"], hit["candidates"]) for hit in response.json()["hits"]] == [
        (["Backend Engineer", "Platform Engineer", "Data Engineer"], 4),
    ]


def transaction_open_at_each_request(ats, session) -> list[bool]:
    seen = []
    handle = ats.handle

    def watch(request: httpx.Request) -> httpx.Response:
        seen.append(session.in_transaction())
        return handle(request)

    ats.handle = watch
    return seen


def test_probing_holds_no_transaction_while_waiting_on_the_ats(client, session, log_in_as, ats):
    serve_greenhouse_board(ats)
    log_in_as("ada@example.com")
    seen = transaction_open_at_each_request(ats, session)

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert (response.status_code, seen) == (200, [False, False, False])


def serve_lever_board(ats, token: str = "kansei-lever") -> None:
    ats.pages[LEVER_BOARD.format(token=token)] = httpx.Response(200, json=[{
        "id": "a1",
        "text": "Site Reliability Engineer",
        "hostedUrl": f"https://jobs.lever.co/{token}/a1",
        "createdAt": 1793491200000,
        "categories": {"location": "Tokyo"},
        "descriptionPlain": "Keep it up.",
    }])
    ats.pages[LEVER_BOARD_PAGE.format(token=token)] = httpx.Response(200, text="<title>Kansei Lever</title>")


def serve_ashby_board(ats, token: str = "kansei-ashby") -> None:
    ats.pages[ASHBY_BOARD.format(token=token)] = httpx.Response(200, json={"jobs": [{
        "id": "b2",
        "title": "Robotics Engineer",
        "location": "San Francisco",
        "secondaryLocations": [{"location": "Tokyo"}],
        "publishedAt": "2026-11-01T00:00:00Z",
        "jobUrl": f"https://jobs.ashbyhq.com/{token}/b2",
        "descriptionPlain": "Build robots.",
    }]})
    ats.pages[ASHBY_GRAPHQL] = httpx.Response(200, json={"data": {"organization": {"name": "Kansei Ashby"}}})


def hrmos_job_page(title: str, region: str) -> str:
    ld = json.dumps({
        "@type": "JobPosting",
        "title": title,
        "datePosted": "2026-11-01T00:00:00Z",
        "description": "<p>開発</p>",
        "jobLocation": [{"@type": "Place", "address": {"addressRegion": region}}],
    }, ensure_ascii=False)
    return f'<html><head><script type="application/ld+json">{ld}</script></head></html>'


def serve_hrmos_board(ats, token: str = "visional") -> None:
    board = HRMOS_BOARD.format(token=token)
    headlines = {"101": "【東京】バックエンドエンジニア", "102": "経理", "103": "【US】SREエンジニア"}
    links = "".join(f'<a href="{board}/{job_id}"><h2>{headline}</h2></a>' for job_id, headline in headlines.items())
    ats.pages[board] = httpx.Response(200, text=f"<h1>ビジョナル株式会社 すべての求人一覧</h1>{links}")
    ats.pages[HRMOS_JOB.format(token=token, job_id="101")] = httpx.Response(
        200, text=hrmos_job_page("バックエンドエンジニア", "東京都"),
    )
    ats.pages[HRMOS_JOB.format(token=token, job_id="103")] = httpx.Response(
        200, text=hrmos_job_page("SREエンジニア", "California"),
    )


HRMOS_HIT = {
    "source": "hrmos",
    "token": "visional",
    "company": "ビジョナル株式会社",
    "titles": ["バックエンドエンジニア"],
    "candidates": 1,
}


@pytest.mark.parametrize(("serve", "url", "hit"), [
    (
        serve_greenhouse_board,
        "https://boards.greenhouse.io/kansei-test/jobs/1?gh_src=abc",
        {
            "source": "greenhouse",
            "token": "kansei-test",
            "company": "Kansei Test K.K.",
            "titles": ["Backend Engineer", "Platform Engineer", "Data Engineer"],
            "candidates": 3,
        },
    ),
    (
        serve_lever_board,
        "https://jobs.lever.co/kansei-lever/a1",
        {
            "source": "lever",
            "token": "kansei-lever",
            "company": "Kansei Lever",
            "titles": ["Site Reliability Engineer"],
            "candidates": 1,
        },
    ),
    (
        serve_lever_board,
        "jobs.lever.co/kansei-lever",
        {
            "source": "lever",
            "token": "kansei-lever",
            "company": "Kansei Lever",
            "titles": ["Site Reliability Engineer"],
            "candidates": 1,
        },
    ),
    (
        serve_ashby_board,
        "https://jobs.ashbyhq.com/kansei-ashby/b2/application",
        {
            "source": "ashby",
            "token": "kansei-ashby",
            "company": "Kansei Ashby",
            "titles": ["Robotics Engineer"],
            "candidates": 1,
        },
    ),
    (serve_hrmos_board, "https://hrmos.co/pages/visional/jobs", HRMOS_HIT),
    (serve_hrmos_board, "hrmos.co/pages/visional/jobs", HRMOS_HIT),
    (serve_hrmos_board, "https://hrmos.co/pages/visional/jobs/2070775774525681664", HRMOS_HIT),
])
def test_probing_a_single_job_url_finds_its_whole_board(client, log_in_as, ats, serve, url, hit):
    serve(ats)
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": url})

    assert response.json() == {"message": None, "hits": [{**hit, "state": "not_on_kansei", "following": False, "logo_url": None}]}


UNKNOWN_HOST = (
    "kansei can only add boards on boards.greenhouse.io, job-boards.greenhouse.io, "
    "jobs.lever.co, jobs.ashbyhq.com and hrmos.co."
)
NO_BOARD_IN_URL = "That URL doesn't name a board."


@pytest.mark.parametrize(("q", "message"), [
    ("https://example.com/kansei-test", UNKNOWN_HOST),
    ("https://boards.greenhouse.io.example.com/kansei-test", UNKNOWN_HOST),
    ("https://boards-api.greenhouse.io/v1/boards/kansei-test", UNKNOWN_HOST),
    ("example.com/careers", UNKNOWN_HOST),
    ("https://jobs.lever.co/", NO_BOARD_IN_URL),
    ("jobs.lever.co", NO_BOARD_IN_URL),
    ("https://jobs.lever.co/..", NO_BOARD_IN_URL),
    ("https://jobs.lever.co/.hidden", NO_BOARD_IN_URL),
    ("https://jobs.lever.co/kansei%2F..%2Fother", NO_BOARD_IN_URL),
    ("https://jobs.lever.co/kansei test", NO_BOARD_IN_URL),
    ("https://jobs.ashbyhq.com/カンセイ", NO_BOARD_IN_URL),
    ("hrmos.co", NO_BOARD_IN_URL),
    ("https://hrmos.co/pages/", NO_BOARD_IN_URL),
    ("https://hrmos.co/pages", NO_BOARD_IN_URL),
    ("https://hrmos.co/visional/jobs", NO_BOARD_IN_URL),
    ("https://hrmos.co/pages/../jobs", NO_BOARD_IN_URL),
])
def test_probing_a_url_that_isnt_a_board_is_refused_without_a_request(client, log_in_as, ats, q, message):
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": q})

    assert response.json() == {"hits": [], "message": message}
    assert ats.requested == []


@pytest.mark.parametrize(("status", "bob_follows", "ada_follows", "state", "following"), [
    ("active", False, False, "on_kansei", False),
    ("active", True, False, "on_kansei", False),
    ("active", False, True, "on_kansei", True),
    ("removed", False, False, "removed", False),
])
def test_probing_a_board_on_kansei_reports_its_state_and_name_on_kansei(
    client, session, log_in_as, ats, status, bob_follows, ada_follows, state, following
):
    serve_greenhouse_board(ats, name="Kansei Test K.K. (fetched)")
    session.add(Board(source="greenhouse", token="kansei-test", name="Kansei Test K.K."))
    session.flush()
    if bob_follows:
        log_in_as("bob@example.com")
        client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    log_in_as("ada@example.com")
    if ada_follows:
        client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    session.execute(update(Board).where(Board.token == "kansei-test").values(status=status))
    session.commit()

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert response.json() == {
        "message": None,
        "hits": [{
            "source": "greenhouse",
            "token": "kansei-test",
            "company": "Kansei Test K.K.",
            "titles": ["Backend Engineer", "Platform Engineer", "Data Engineer"],
            "candidates": 3,
            "state": state,
            "following": following,
            "logo_url": None,
        }],
    }


STORED_LOGO = "https://example.com/stored.png"
FETCHED_LOGO = "https://example.com/fetched.png"


@pytest.mark.parametrize(("stored", "stored_logo", "page_logo", "logo_url"), [
    (False, None, True, FETCHED_LOGO),
    (False, None, False, None),
    (True, STORED_LOGO, True, STORED_LOGO),
    (True, STORED_LOGO, False, STORED_LOGO),
    (True, None, True, FETCHED_LOGO),
    (True, None, False, None),
])
def test_a_probe_hit_carries_the_stored_logo_or_else_the_fetched_one(
    client, session, log_in_as, ats, stored, stored_logo, page_logo, logo_url
):
    serve_greenhouse_board(ats)
    if page_logo:
        serve_greenhouse_logo(ats)
    if stored:
        session.add(Board(source="greenhouse", token="kansei-test", name="Kansei Test K.K.", logo_url=stored_logo))
        session.flush()
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert [hit["logo_url"] for hit in response.json()["hits"]] == [logo_url]


def serve_greenhouse_logo(ats) -> None:
    ats.pages[GREENHOUSE_BOARD_PAGE.format(token="kansei-test")] = httpx.Response(
        200, text=f'<img alt="Kansei Test logo" src="{FETCHED_LOGO}">'
    )


def hold_name_and_logo_until_both_are_asked(ats) -> None:
    both = {GREENHOUSE_BOARD_INFO.format(token="kansei-test"), GREENHOUSE_BOARD_PAGE.format(token="kansei-test")}
    met = asyncio.Barrier(2)
    handle = ats.handle

    async def meet(request: httpx.Request) -> httpx.Response:
        if str(request.url) in both:
            await asyncio.wait_for(met.wait(), timeout=2)
        return handle(request)

    ats.handle = meet


def test_probing_fetches_the_name_and_the_logo_at_the_same_time(client, log_in_as, ats):
    serve_greenhouse_board(ats)
    log_in_as("ada@example.com")
    hold_name_and_logo_until_both_are_asked(ats)

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert [hit["company"] for hit in response.json()["hits"]] == ["Kansei Test K.K."]


def test_probing_a_board_with_no_readable_name_gives_no_company(client, log_in_as, ats):
    serve_greenhouse_board(ats)
    ats.pages[GREENHOUSE_BOARD_INFO.format(token="kansei-test")] = httpx.Response(500)
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/kansei-test"})

    assert response.json() == {
        "message": None,
        "hits": [{
            "source": "greenhouse",
            "token": "kansei-test",
            "company": None,
            "titles": ["Backend Engineer", "Platform Engineer", "Data Engineer"],
            "candidates": 3,
            "state": "not_on_kansei",
            "following": False,
            "logo_url": None,
        }],
    }


def test_a_board_on_kansei_is_found_whatever_the_case_of_the_pasted_token(client, session, log_in_as, ats):
    serve_greenhouse_board(ats, token="Kansei-Test")
    session.add(Board(source="greenhouse", token="kansei-test", name="Kansei Test K.K.", status="removed"))
    session.flush()
    log_in_as("ada@example.com")

    probed = client.get("/api/probe", params={"q": "https://job-boards.greenhouse.io/Kansei-Test"})
    added = client.post("/api/me/follows", json={"source": "greenhouse", "token": "Kansei-Test"})

    assert probed.json() == {
        "message": None,
        "hits": [{
            "source": "greenhouse",
            "token": "kansei-test",
            "company": "Kansei Test K.K.",
            "titles": ["Backend Engineer", "Platform Engineer", "Data Engineer"],
            "candidates": 3,
            "state": "removed",
            "following": False,
            "logo_url": None,
        }],
    }
    assert added.status_code == 409
    assert session.scalars(select(Board.token).where(Board.source == "greenhouse", Board.token.ilike("kansei-test"))).all() == [
        "kansei-test",
    ]


def test_an_hrmos_board_on_kansei_is_found_whatever_the_case_of_the_pasted_token(client, session, log_in_as, ats):
    serve_hrmos_board(ats, token="Visional")
    session.add(Board(source="hrmos", token="visional", name="ビジョナル"))
    session.flush()
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "https://hrmos.co/pages/Visional/jobs"})

    assert response.json() == {
        "message": None,
        "hits": [{**HRMOS_HIT, "company": "ビジョナル", "state": "on_kansei", "following": False, "logo_url": None}],
    }


@pytest.mark.parametrize(("url", "q"), [
    (LEVER_BOARD.format(token="kansei-missing"), "https://jobs.lever.co/kansei-missing"),
    (HRMOS_BOARD.format(token="kansei-missing"), "https://hrmos.co/pages/kansei-missing/jobs"),
])
@pytest.mark.parametrize("status", [404, 500])
def test_probing_a_board_the_ats_doesnt_serve_finds_nothing(client, log_in_as, ats, status, url, q):
    ats.pages[url] = httpx.Response(status)
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": q})

    assert response.json() == {"hits": [], "message": "No board found at that URL."}


TRY_THE_URL = "No board found for that name. Try pasting its Greenhouse, Lever, Ashby or HRMOS board URL."


def board_urls(*tokens: str) -> list[str]:
    return sorted(url.format(token=token) for url in (GREENHOUSE_BOARD, LEVER_BOARD, ASHBY_BOARD) for token in tokens)


@pytest.mark.parametrize(("name", "slugs"), [
    ("Acme", ["acme"]),
    ("  SmartHR  ", ["smarthr"]),
    ("Woven by Toyota, Inc.", ["wovenbytoyota", "woven-by-toyota"]),
    ("Kansei Test K.K.", ["kanseitest", "kansei-test"]),
    ("Toyota Motor Co., Ltd.", ["toyotamotor", "toyota-motor"]),
    ("Amazon Japan G.K.", ["amazonjapan", "amazon-japan"]),
    ("Mercari 株式会社", ["mercari"]),
    ("株式会社Mercari", ["mercari"]),
    ("Monday.com", ["mondaycom", "monday-com"]),
    ("Société Générale", ["societegenerale", "societe-generale"]),
    ("ＡＣＭＥ Corp", ["acme"]),
])
def test_probing_a_name_with_no_hits_tries_each_guessed_slug_on_every_source(client, log_in_as, ats, name, slugs):
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": name})

    assert response.json() == {"hits": [], "message": TRY_THE_URL}
    assert sorted(ats.requested) == board_urls(*slugs)


def test_probing_a_name_returns_the_board_its_slug_finds(client, log_in_as, ats):
    serve_lever_board(ats)
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "Kansei Lever Co., Ltd."})

    assert response.json() == {
        "message": None,
        "hits": [{
            "source": "lever",
            "token": "kansei-lever",
            "company": "Kansei Lever",
            "titles": ["Site Reliability Engineer"],
            "candidates": 1,
            "state": "not_on_kansei",
            "following": False,
            "logo_url": None,
        }],
    }


def test_probing_a_name_returns_every_board_it_finds_across_sources(client, session, log_in_as, ats):
    serve_greenhouse_board(ats)
    serve_ashby_board(ats, token="kanseitest")
    serve_lever_board(ats, token="kansei-test")
    ats.pages[GREENHOUSE_BOARD.format(token="kanseitest")] = httpx.Response(500)
    session.add(Board(source="lever", token="kansei-test", name="Kansei Test (Lever)", status="removed"))
    session.flush()
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": "Kansei Test K.K."})

    assert response.json() == {
        "message": None,
        "hits": [
            {
                "source": "greenhouse",
                "token": "kansei-test",
                "company": "Kansei Test K.K.",
                "titles": ["Backend Engineer", "Platform Engineer", "Data Engineer"],
                "candidates": 3,
                "state": "not_on_kansei",
                "following": False,
                "logo_url": None,
            },
            {
                "source": "lever",
                "token": "kansei-test",
                "company": "Kansei Test (Lever)",
                "titles": ["Site Reliability Engineer"],
                "candidates": 1,
                "state": "removed",
                "following": False,
                "logo_url": None,
            },
            {
                "source": "ashby",
                "token": "kanseitest",
                "company": "Kansei Ashby",
                "titles": ["Robotics Engineer"],
                "candidates": 1,
                "state": "not_on_kansei",
                "following": False,
                "logo_url": None,
            },
        ],
    }


@pytest.mark.parametrize("name", ["株式会社メルカリ", "", "   ", "K.K.", "Inc., Ltd."])
def test_probing_a_name_with_no_ascii_letters_or_digits_suggests_the_url_without_a_request(
    client, log_in_as, ats, name
):
    log_in_as("ada@example.com")

    response = client.get("/api/probe", params={"q": name})

    assert response.json() == {"hits": [], "message": TRY_THE_URL}
    assert ats.requested == []


def test_adding_a_board_not_on_kansei_creates_it_with_its_name_and_adder_and_follows_it(
    client, session, log_in_as, ats
):
    serve_greenhouse_board(ats)
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    ada = session.scalar(select(User.id).where(User.email == "ada@example.com"))
    board = session.scalar(select(Board).where(Board.token == "kansei-test"))
    assert (response.status_code, response.json()) == (
        201, {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None},
    )
    assert (board.source, board.name, board.status, board.added_by) == ("greenhouse", "Kansei Test K.K.", "active", ada)
    assert client.get("/api/me/follows").json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None},
    ]


def test_adding_an_hrmos_board_not_on_kansei_creates_it_and_follows_it(client, session, log_in_as, ats):
    serve_hrmos_board(ats)
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "hrmos", "token": "visional"})

    ada = session.scalar(select(User.id).where(User.email == "ada@example.com"))
    board = session.scalar(select(Board).where(Board.source == "hrmos"))
    assert (response.status_code, response.json()) == (
        201, {"source": "hrmos", "token": "visional", "company": "ビジョナル株式会社", "logo_url": None},
    )
    assert (board.token, board.name, board.status, board.added_by) == ("visional", "ビジョナル株式会社", "active", ada)
    assert client.get("/api/me/follows").json() == [
        {"source": "hrmos", "token": "visional", "company": "ビジョナル株式会社", "logo_url": None},
    ]


def test_adding_a_board_holds_no_transaction_while_waiting_on_the_ats(client, session, log_in_as, ats):
    serve_greenhouse_board(ats)
    log_in_as("ada@example.com")
    seen = transaction_open_at_each_request(ats, session)

    response = client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    assert (response.status_code, seen) == (201, [False, False, False])


def test_adding_a_board_not_on_kansei_stores_its_logo(client, session, log_in_as, ats):
    serve_greenhouse_board(ats)
    serve_greenhouse_logo(ats)
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    followed = {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": FETCHED_LOGO}
    assert (response.status_code, response.json()) == (201, followed)
    assert session.scalars(select(Board.logo_url).where(Board.token == "kansei-test")).all() == [FETCHED_LOGO]
    assert client.get("/api/me/follows").json() == [followed]


def test_adding_a_board_takes_its_logo_from_the_ats_not_the_client(client, session, log_in_as, ats):
    serve_greenhouse_board(ats)
    serve_greenhouse_logo(ats)
    log_in_as("ada@example.com")

    response = client.post(
        "/api/me/follows",
        json={"source": "greenhouse", "token": "kansei-test", "logo_url": "https://example.com/not-the-logo.png"},
    )

    assert (response.status_code, response.json()["logo_url"]) == (201, FETCHED_LOGO)
    assert session.scalars(select(Board.logo_url).where(Board.token == "kansei-test")).all() == [FETCHED_LOGO]


def test_adding_a_board_fetches_the_name_and_the_logo_at_the_same_time(client, log_in_as, ats):
    serve_greenhouse_board(ats)
    log_in_as("ada@example.com")
    hold_name_and_logo_until_both_are_asked(ats)

    response = client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    assert (response.status_code, response.json()["company"]) == (201, "Kansei Test K.K.")


def test_adding_a_board_whose_name_cant_be_read_leaves_the_name_for_the_ingest(client, session, log_in_as, ats):
    serve_lever_board(ats)
    ats.pages[LEVER_BOARD_PAGE.format(token="kansei-lever")] = httpx.Response(503)
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "lever", "token": "kansei-lever"})

    assert (response.status_code, response.json()) == (
        201, {"source": "lever", "token": "kansei-lever", "company": "kansei-lever", "logo_url": None},
    )
    assert session.scalar(select(Board.name).where(Board.token == "kansei-lever")) is None
    assert client.get("/api/me/follows").json() == [
        {"source": "lever", "token": "kansei-lever", "company": "kansei-lever", "logo_url": None},
    ]


def test_adding_a_board_the_ats_doesnt_serve_is_refused_after_one_fetch_and_creates_nothing(
    client, session, log_in_as, ats
):
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "ashby", "token": "kansei-missing"})

    assert (response.status_code, response.json()) == (404, {"detail": "No board kansei-missing on ashby."})
    assert ats.requested == [ASHBY_BOARD.format(token="kansei-missing")]
    assert session.scalar(select(Board).where(Board.token == "kansei-missing")) is None
    assert client.get("/api/me/follows").json() == []


@pytest.mark.parametrize("token", ["..", "kansei/../other", ".hidden", ""])
def test_adding_a_token_with_illegal_characters_is_refused_without_a_request(client, log_in_as, ats, token):
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "lever", "token": token})

    assert response.status_code == 422
    assert ats.requested == []
