import asyncio
import json

import httpx
import pytest

from kansei import is_candidate, model_input, validate
from kansei.sources import fetch_board_name, fetch_hrmos

BOARD = "https://hrmos.co/pages/acme/jobs"
TOKYO = [{"@type": "Place", "address": {
    "@type": "PostalAddress", "streetAddress": "芝1-1", "addressLocality": "港区",
    "addressRegion": "東京都", "postalCode": "105-0014",
}}]


def board_page(headlines: dict[str, str], pages: tuple[int, ...] = ()) -> str:
    items = "".join(
        f'<li class="pg-list-cassette"><a href="{BOARD}/{job_id}">'
        f"<h2>{headline}</h2><p>募集背景</p></a></li>"
        for job_id, headline in headlines.items()
    )
    pager = "".join(f'<li><a class="sg-button" href="{BOARD}?page={n}">{n}</a></li>' for n in pages)
    return (
        '<html><body><h1 class="sg-corporate-name"> アクメ株式会社 すべての求人一覧 </h1>'
        f'<ul>{items}</ul><nav class="pg-pagenation"><ol>{pager}</ol></nav></body></html>'
    )


def job_page(title: str, job_location=TOKYO, description: str = "<h3>業務内容</h3><p>APIの開発</p>") -> str:
    ld = json.dumps({
        "@context": "http://schema.org/",
        "@type": "JobPosting",
        "title": title,
        "datePosted": "2026-10-30T05:00:35.000Z",
        "description": description,
        "hiringOrganization": {"@type": "Organization", "name": "アクメ株式会社"},
        "jobLocation": job_location,
    }, ensure_ascii=False)
    return (
        f'<html><head><script type="application/ld+json">{ld}</script></head>'
        f"<body><h1>{title}</h1><p>応募する</p></body></html>"
    )


class FakeHrmos:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requested.append(str(request.url))
        page = self.pages.get(str(request.url))
        if page is None:
            return httpx.Response(404, text="<h1>Not Found</h1>")
        return httpx.Response(200, headers={"content-type": "text/html"}, text=page)


async def fetch(hrmos: FakeHrmos, token: str = "acme") -> list[dict]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(hrmos.handle)) as client:
        return await fetch_hrmos(client, token)


async def test_fetch_hrmos_reads_each_posting_from_its_job_page():
    hrmos = FakeHrmos({
        BOARD: board_page({"101": "【東京】バックエンドエンジニア（Go）"}),
        f"{BOARD}/101": job_page("バックエンドエンジニア"),
    })

    assert await fetch(hrmos) == [{
        "source": "hrmos",
        "token": "acme",
        "id": "101",
        "title": "バックエンドエンジニア",
        "url": "https://hrmos.co/pages/acme/jobs/101",
        "posted_at": "2026-10-30T05:00:35.000Z",
        "location": "東京都 港区",
        "company_name": None,
        "description": "業務内容\nAPIの開発",
        "headline": "【東京】バックエンドエンジニア（Go）",
    }]


def address(region, locality) -> dict:
    return {"@type": "Place", "address": {
        "@type": "PostalAddress", "streetAddress": None, "addressLocality": locality,
        "addressRegion": region, "postalCode": None,
    }}


@pytest.mark.parametrize(
    ("job_location", "location"),
    [
        pytest.param([address(None, None)], "", id="every field null"),
        pytest.param([], "", id="no places"),
        pytest.param(address("大阪府", "大阪市"), "大阪府 大阪市", id="a single place"),
        pytest.param([address("東京都", None)], "東京都", id="a region alone"),
        pytest.param(
            [address("東京都", "港区"), address("東京都", "港区"), address(None, None), address("福岡県", "福岡市")],
            "東京都 港区 / 福岡県 福岡市",
            id="several places, each named once",
        ),
    ],
)
async def test_fetch_hrmos_joins_the_region_and_locality_of_each_place(job_location, location):
    hrmos = FakeHrmos({
        BOARD: board_page({"101": "SREエンジニア"}),
        f"{BOARD}/101": job_page("SRE", job_location=job_location),
    })

    assert [job["location"] for job in await fetch(hrmos)] == [location]


async def test_an_hrmos_posting_is_a_candidate_by_its_headline_or_title_and_with_no_location():
    hrmos = FakeHrmos({
        BOARD: board_page({
            "101": "【エンジニア】オープンポジション",
            "102": "インフラエンジニア（リモート可）",
            "103": "【US拠点】Software Engineer",
            "104": "【開発】Web Developer",
        }),
        f"{BOARD}/101": job_page("オープンポジション"),
        f"{BOARD}/102": job_page("インフラエンジニア", job_location=[address(None, None)]),
        f"{BOARD}/103": job_page("Software Engineer", job_location=[address("California", "San Francisco")]),
        f"{BOARD}/104": job_page("Web Developer", job_location=[address("Remote - US", None)]),
    })
    jobs, invalid = validate(await fetch(hrmos))

    assert invalid == []
    assert [(job.id, is_candidate(job)) for job in jobs] == [
        ("101", True), ("102", True), ("103", False), ("104", False),
    ]


@pytest.mark.parametrize(
    ("description", "text"),
    [
        pytest.param(
            "<h3>業務内容</h3><p>APIの開発</p><ul><li>Go</li><li>AWS</li></ul>",
            "バックエンドエンジニア\n\n業務内容\nAPIの開発\nGo\nAWS",
            id="html",
        ),
        pytest.param(None, "バックエンドエンジニア\n\n", id="none"),
    ],
)
async def test_the_model_reads_the_title_and_the_plain_job_description(description, text):
    hrmos = FakeHrmos({
        BOARD: board_page({"101": "【東京】バックエンドエンジニア（Go）"}),
        f"{BOARD}/101": job_page("バックエンドエンジニア", description=description),
    })
    [job], _ = validate(await fetch(hrmos))

    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"should not have fetched {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(explode)) as http:
        assert await model_input(http, job) == text


@pytest.mark.parametrize(
    ("page", "name"),
    [
        pytest.param(board_page({}), "アクメ株式会社", id="the heading"),
        pytest.param(
            '<html><body><h1 class="sg-corporate-name"> アクメ株式会社 求人一覧 </h1></body></html>',
            "アクメ株式会社",
            id="the heading without すべての",
        ),
        pytest.param(
            '<html><body><h1 class="sg-corporate-name"> アクメ株式会社 </h1></body></html>',
            "アクメ株式会社",
            id="a heading without the suffix",
        ),
        pytest.param(
            '<html><body><h1 class="sg-corporate-name"> すべての求人一覧 </h1></body></html>',
            None,
            id="only the suffix",
        ),
        pytest.param("<html><body><p>メンテナンス中</p></body></html>", None, id="no heading"),
        pytest.param(None, None, id="not found"),
    ],
)
async def test_fetch_board_name_reads_the_hrmos_board_heading(page, name):
    hrmos = FakeHrmos({} if page is None else {BOARD: page})

    async with httpx.AsyncClient(transport=httpx.MockTransport(hrmos.handle)) as client:
        assert await fetch_board_name(client, "hrmos", "acme") == name
    assert hrmos.requested == [BOARD]


async def test_a_job_page_that_fails_counts_as_invalid_and_keeps_the_rest_of_the_board():
    hrmos = FakeHrmos({
        BOARD: board_page({"101": "SREエンジニア", "102": "QAエンジニア", "103": "iOSエンジニア"}),
        f"{BOARD}/101": job_page("SRE"),
        f"{BOARD}/103": job_page("iOS"),
    })

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/103"):
            raise httpx.ReadTimeout("timed out", request=request)
        return hrmos.handle(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        jobs, invalid = validate(await fetch_hrmos(client, "acme"))

    assert [job.id for job in jobs] == ["101"]
    assert [job_id for job_id, _ in invalid] == ["102", "103"]


async def test_fetch_hrmos_fails_for_a_token_hrmos_does_not_know():
    with pytest.raises(httpx.HTTPStatusError):
        await fetch(FakeHrmos({}), token="kansei-missing")


async def test_fetch_hrmos_reads_every_board_page():
    hrmos = FakeHrmos({
        BOARD: board_page({"101": "SREエンジニア"}, pages=(2, 3)),
        f"{BOARD}?page=2": board_page({"102": "QAエンジニア"}, pages=(1, 3)),
        f"{BOARD}?page=3": board_page({"103": "iOSエンジニア"}, pages=(1, 2)),
        f"{BOARD}/101": job_page("SRE"),
        f"{BOARD}/102": job_page("QA"),
        f"{BOARD}/103": job_page("iOS"),
    })

    assert [job["title"] for job in await fetch(hrmos)] == ["SRE", "QA", "iOS"]
    assert hrmos.requested == [
        BOARD, f"{BOARD}?page=2", f"{BOARD}?page=3", f"{BOARD}/101", f"{BOARD}/102", f"{BOARD}/103",
    ]


async def test_fetch_hrmos_opens_job_pages_only_for_engineering_headlines():
    hrmos = FakeHrmos({
        BOARD: board_page({
            "101": "【プライム上場】経理（月次決算）",
            "102": "【東京】Webアプリケーション開発",
            "103": "Customer Success Manager",
            "104": "Senior Software Engineer (Payments)",
        }),
        f"{BOARD}/102": job_page("Webアプリケーション開発"),
        f"{BOARD}/104": job_page("Software Engineer"),
    })

    assert [job["id"] for job in await fetch(hrmos)] == ["102", "104"]
    assert hrmos.requested == [BOARD, f"{BOARD}/102", f"{BOARD}/104"]


async def test_fetch_hrmos_keeps_at_most_four_requests_open_across_boards():
    pages = {}
    for token in ("acme", "globex"):
        board = f"https://hrmos.co/pages/{token}/jobs"
        pages[board] = board_page({str(n): "エンジニア" for n in range(6)}).replace(BOARD, board)
        pages |= {f"{board}/{n}": job_page("SRE") for n in range(6)}
    hrmos = FakeHrmos(pages)
    open_now, most_open = 0, 0

    async def slow(request: httpx.Request) -> httpx.Response:
        nonlocal open_now, most_open
        open_now += 1
        most_open = max(most_open, open_now)
        await asyncio.sleep(0.01)
        open_now -= 1
        return hrmos.handle(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
        jobs_per_board = await asyncio.gather(fetch_hrmos(client, "acme"), fetch_hrmos(client, "globex"))

    assert [len(jobs) for jobs in jobs_per_board] == [6, 6]
    assert most_open == 4
