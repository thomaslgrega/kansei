import json

import httpx
import pytest
from bs4 import BeautifulSoup

from kansei import JobPosting, is_candidate
from kansei.sources import (
    ASHBY_ORGANIZATION_QUERY,
    fetch_ashby,
    fetch_board_logo,
    fetch_board_name,
    fetch_url,
    from_ashby,
    from_greenhouse,
    from_hrmos,
    from_lever,
    from_url,
    html_to_text,
    page_text,
)

GREENHOUSE_RAW = {
    "id": 4419,
    "title": "software engineer",
    "absolute_url": "https://example.com/1",
    "updated_at": "2026-09-12T13:25:25-04:00",
    "location": {"name": "Tokyo"},
}
LEVER_RAW = {
    "id": "84925f74-a6aa-4b90-a92b-7006f1f88779",
    "text": "バックエンドエンジニア・Robot Platform Software",
    "hostedUrl": "https://example.com/1",
    "createdAt": 1788231211096,
    "categories": {"location": "東京都中央区"},
    "descriptionPlain": "ウーブン・バイ・トヨタについて",
    "lists": [
        {"text": "必須条件", "content": "<ul><li>Pythonでの開発経験3年以上</li></ul>"},
        {"text": "歓迎条件", "content": "<ul><li>英語でのコミュニケーション</li></ul>"},
    ],
    "additionalPlain": "応募について",
}
ASHBY_RAW = {
    "id": "7458d4e9-da2e-47bd-98cb-adfda43d42b2",
    "title": "Software Engineer, Payments",
    "department": "Engineering",
    "team": "Payments",
    "employmentType": "FullTime",
    "location": "San Francisco",
    "secondaryLocations": [
        {"location": "Tokyo", "address": {"postalAddress": {"addressCountry": "Japan"}}},
        {"location": "Remote - US", "address": {"postalAddress": {"addressCountry": "USA"}}},
    ],
    "publishedAt": "2026-10-04T14:29:08.532+00:00",
    "isListed": True,
    "isRemote": True,
    "workplaceType": "Hybrid",
    "address": {"postalAddress": {"addressCountry": "USA"}},
    "jobUrl": "https://jobs.ashbyhq.com/acme/7458d4e9-da2e-47bd-98cb-adfda43d42b2",
    "applyUrl": "https://jobs.ashbyhq.com/acme/7458d4e9-da2e-47bd-98cb-adfda43d42b2/application",
    "descriptionHtml": "<p>Build the ledger.</p>",
    "descriptionPlain": "Build the ledger.",
}


def test_every_adapter_produces_exactly_the_same_keys():
    assert (
        from_greenhouse(GREENHOUSE_RAW, "stripe").keys()
        == from_lever(LEVER_RAW, "woven-by-toyota").keys()
        == from_ashby(ASHBY_RAW, "acme").keys()
        == from_url(PAGE_WITHOUT_LD, "https://example.com/1").keys()
        == from_hrmos(PAGE_WITH_LD, "acme", "101", "SREエンジニア").keys()
    )


def test_from_lever_maps_the_fields_that_have_different_names():
    posting = from_lever(LEVER_RAW, "woven-by-toyota")

    assert posting["id"] == "84925f74-a6aa-4b90-a92b-7006f1f88779"
    assert posting["title"] == "バックエンドエンジニア・Robot Platform Software"
    assert posting["location"] == "東京都中央区"
    assert posting["source"] == "lever"

def test_from_lever_sends_the_requirements_not_just_the_company_blurd():
    description = from_lever(LEVER_RAW, "woven-by-toyota")["description"]

    assert "必須条件" in description
    assert "Pythonでの開発経験3年以上" in description
    assert "<li>" not in description


def test_from_ashby_maps_every_field():
    assert from_ashby(ASHBY_RAW, "acme") == {
        "source": "ashby",
        "token": "acme",
        "id": "7458d4e9-da2e-47bd-98cb-adfda43d42b2",
        "title": "Software Engineer, Payments",
        "url": "https://jobs.ashbyhq.com/acme/7458d4e9-da2e-47bd-98cb-adfda43d42b2",
        "posted_at": "2026-10-04T14:29:08.532+00:00",
        "location": "San Francisco / Tokyo / Remote - US",
        "company_name": None,
        "description": "Build the ledger.",
        "headline": None,
    }


@pytest.mark.parametrize(
    ("secondary", "location"),
    [
        pytest.param([], "Tokyo", id="none"),
        pytest.param([{"location": "Osaka"}], "Tokyo / Osaka", id="one"),
        pytest.param(
            [{"location": "Osaka"}, {"location": "Remote"}, {"location": "Fukuoka"}],
            "Tokyo / Osaka / Remote / Fukuoka",
            id="several, in order",
        ),
    ],
)
def test_from_ashby_joins_the_primary_and_secondary_locations_in_order(secondary, location):
    raw = {**ASHBY_RAW, "location": "Tokyo", "secondaryLocations": secondary}

    assert from_ashby(raw, "acme")["location"] == location


def test_an_ashby_job_whose_only_japan_location_is_secondary_is_a_candidate():
    posting = from_ashby(ASHBY_RAW, "acme")

    assert is_candidate(JobPosting.model_validate(posting)) is True


async def test_fetch_ashby_makes_one_request_for_the_whole_board():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(200, json={"apiVersion": "1", "jobs": [ASHBY_RAW]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_ashby(client, "acme") == [from_ashby(ASHBY_RAW, "acme")]
    assert requested == ["https://api.ashbyhq.com/posting-api/job-board/acme"]


def test_from_greenhouse_stringifies_the_integer_id():
    assert from_greenhouse(GREENHOUSE_RAW, "stripe")["id"] == "4419"


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        ("<p>Python</p><p>Go</p>", "Python\nGo"),
        ("<ul><li>3 years of Python</li><li>Business Japanese</li></ul>",
         "3 years of Python\nBusiness Japanese"),
        ("<div>R&amp;D team in <b>Tokyo</b></div>", "R&D team in Tokyo"),
        ("  <p>   Tokyo   </p>  ", "Tokyo"),
    ],
)
def test_html_to_text_keeps_the_words_and_drops_the_markup(fragment, expected):
    assert html_to_text(fragment) == expected


PAGE_WITH_LD = """
<html><head><title>Woven by Toyota - バックエンドエンジニア</title>
<style>.btn {background: #a80014;}</style>
<script type="application/ld+json">
{"@context": "http://schema.org", "@type": "JobPosting",
 "title": "バックエンドエンジニア",
 "datePosted": "2026-09-01",
 "hiringOrganization": {"@type": "Organization", "name": "Woven by Toyota"},
 "jobLocation": {"@type": "Place", "address": {"addressLocality": "東京都中央区"}},
 "description": "<p>必須条件</p><ul><li>Pythonでの開発経験3年以上</li></ul>"}
</script>
<script>window.__STATE__ = {"applied": false};</script>
</head>
<body><h1>バックエンドエンジニア</h1>
<p>必須条件</p><ul><li>Pythonでの開発経験3年以上</li></ul>
<noscript>JavaScriptを有効にしてください</noscript>
</body></html>
"""

PAGE_WITH_GRAPH = """
<html><head><title>Wantedly</title>
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "Organization", "name": "株式会社プラーナ"},
  {"@type": "JobPosting", "title": "事業開発",
   "datePosted": "2026-09-23T07:15:34.388Z",
   "jobLocation": {"@type": "Place", "address": {"addressCountry": "JP"}},
   "description": "心が動く仕事を選びませんか？"}]}
</script></head>
<body><h1>事業開発</h1><p>出店戦略と新業態を主導するポジションです。</p></body></html>
"""

PAGE_WITHOUT_LD = """
<html><head><title>Job Application for AI Engineer at GitLab</title></head>
<body><h1>AI Engineer</h1><p>Remote, Bangalore</p></body></html>
"""


def test_page_text_drops_everything_the_browser_never_shows():
    text = page_text(BeautifulSoup(PAGE_WITH_LD, "html.parser"))

    assert "Pythonでの開発経験3年以上" in text
    assert "window.__STATE__" not in text
    assert "@type" not in text
    assert "#a80014" not in text
    assert "JavaScriptを有効にしてください" not in text


def test_from_url_reads_the_fields_the_page_declares():
    posting = from_url(PAGE_WITH_LD, "https://jobs.lever.co/woven-by-toyota/abc123")

    assert posting["title"] == "バックエンドエンジニア"
    assert posting["posted_at"] == "2026-09-01"
    assert posting["location"] == "東京都中央区"
    assert posting["token"] == "jobs.lever.co"


def test_from_url_names_the_company_the_page_declares_as_hiring():
    posting = from_url(PAGE_WITH_LD, "https://jobs.lever.co/woven-by-toyota/abc123")

    assert posting["company_name"] == "Woven by Toyota"


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(PAGE_WITHOUT_LD, id="no ld+json"),
        pytest.param(PAGE_WITH_GRAPH, id="an organization in the graph but no hiringOrganization"),
        pytest.param(
            PAGE_WITH_LD.replace('"name": "Woven by Toyota"', '"name": " "'),
            id="a blank name",
        ),
    ],
)
def test_from_url_gives_no_company_name_when_the_page_declares_none(page):
    assert from_url(page, "https://example.com/1")["company_name"] is None


def test_from_url_finds_the_job_posting_inside_a_graph():
    posting = from_url(PAGE_WITH_GRAPH, "https://www.wantedly.com/projects/2576097")

    assert posting["title"] == "事業開発"
    assert posting["location"] == "JP"


def test_from_url_takes_the_body_from_the_page_not_the_json_ld_description():
    posting = from_url(PAGE_WITH_GRAPH, "https://www.wantedly.com/projects/2576097")

    assert "出店戦略と新業態を主導するポジションです。" in posting["description"]


def page_with_job_location(job_location) -> str:
    ld = json.dumps({"@type": "JobPosting", "title": "SRE", "jobLocation": job_location})
    return (
        f'<html><head><script type="application/ld+json">{ld}</script></head>'
        "<body><h1>SRE</h1></body></html>"
    )


@pytest.mark.parametrize(
    ("job_location", "location"),
    [
        pytest.param(
            [
                {"@type": "Place", "address": None},
                {"@type": "Place", "address": {}},
                {"@type": "Place"},
                {"@type": "Place", "address": {"@type": "PostalAddress"}},
                {"@type": "Place", "address": {"addressLocality": "東京都渋谷区"}},
                {"@type": "Place", "address": {"addressLocality": "大阪府大阪市"}},
            ],
            "東京都渋谷区",
            id="a list of places",
        ),
        pytest.param(
            {"@type": "Place", "address": {"addressLocality": "東京都渋谷区"}},
            "東京都渋谷区",
            id="a single place",
        ),
        pytest.param(
            [{"@type": "Place", "address": None}, {"@type": "Place", "address": {}}],
            "",
            id="a list of places with no address",
        ),
    ],
)
def test_from_url_takes_the_location_from_the_first_place_with_an_address(job_location, location):
    posting = from_url(page_with_job_location(job_location), "https://hrmos.co/pages/acme/jobs/1")

    assert posting == {
        "source": "url",
        "token": "hrmos.co",
        "id": "https://hrmos.co/pages/acme/jobs/1",
        "title": "SRE",
        "url": "https://hrmos.co/pages/acme/jobs/1",
        "posted_at": None,
        "location": location,
        "company_name": None,
        "description": "SRE",
        "headline": None,
    }


def test_from_url_still_produces_a_record_when_the_page_declares_nothing():
    posting = from_url(PAGE_WITHOUT_LD, "https://job-boards.greenhouse.io/gitlab/jobs/85566")

    assert posting["title"] == "AI Engineer"
    assert posting["posted_at"] is None
    assert posting["location"] == ""


@pytest.mark.parametrize(
    "response, reported",
    [
        (httpx.Response(200, json={"jobs": []}), "application/json"),
        (httpx.Response(200, content=b"%PDF-1.7"), "no content type"),
    ]
)
async def test_fetch_url_refuses_a_response_that_is_not_html(response, reported):
    transport = httpx.MockTransport(lambda request: response)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match=reported):
            await fetch_url(client, "https://example.com/1")


async def test_fetch_url_refuses_a_response_that_redirected_a_non_existing_post():
    def handler(request):
        if request.url.path == "/jobs/1":
            return httpx.Response(302, headers={"location": "https://example.com/jobs"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body>Current openings</body></html>")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match="redirected to"):
            await fetch_url(client, "https://example.com/jobs/1")


async def test_fetch_board_name_reads_the_greenhouse_board_name():
    def handler(request):
        assert request.url == "https://boards-api.greenhouse.io/v1/boards/anthropic"
        return httpx.Response(200, json={"name": "Anthropic", "content": "<p>About us</p>"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_board_name(client, "greenhouse", "anthropic") == "Anthropic"


async def test_fetch_board_name_reads_the_ashby_organization_name():
    def handler(request):
        assert request.method == "POST"
        assert request.url == (
            "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiOrganizationFromHostedJobsPageName"
        )
        assert json.loads(request.content)["variables"] == {
            "organizationHostedJobsPageName": "acme",
            "searchContext": "JobBoard",
        }
        return httpx.Response(200, json={"data": {"organization": {"name": " Acme Corp "}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_board_name(client, "ashby", "acme") == "Acme Corp"


def lever_page(head: str) -> httpx.Response:
    page = f"<html><head>{head}</head><body><h1>Open roles</h1></body></html>"
    return httpx.Response(200, headers={"content-type": "text/html"}, text=page)


async def test_fetch_board_name_reads_the_lever_page_title_not_og_title():
    def handler(request):
        assert request.url == "https://jobs.lever.co/woven-by-toyota"
        return lever_page(
            '<meta property="og:title" content="Woven by Toyota jobs">'
            "<title>\n  Woven by Toyota  \n</title>"
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_board_name(client, "lever", "woven-by-toyota") == "Woven by Toyota"


@pytest.mark.parametrize(
    "source, response",
    [
        ("lever", lever_page('<meta property="og:title" content="Mujin jobs">')),
        ("lever", lever_page("<title>  </title>")),
        ("greenhouse", httpx.Response(200, json={"name": " "})),
        ("greenhouse", httpx.Response(200, text="<html>Maintenance</html>")),
        ("greenhouse", httpx.Response(200, json=["Anthropic"])),
        ("greenhouse", httpx.Response(200, json={"name": 123})),
        ("ashby", httpx.Response(200, json={"data": {"organization": None}})),
        ("ashby", httpx.Response(200, json={"data": {"organization": {"name": ""}}})),
        ("ashby", httpx.Response(200, json={"data": None, "errors": [{"message": "Bad"}]})),
        ("ashby", httpx.Response(200, json={"data": {"organization": {"name": 123}}})),
        ("ashby", httpx.Response(200, json=["Acme"])),
        ("ashby", httpx.Response(200, text="<html>Maintenance</html>")),
    ],
)
async def test_fetch_board_name_gives_no_name_for_a_missing_blank_or_malformed_one(source, response):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
        assert await fetch_board_name(client, source, "mujininc") is None


def times_out(request):
    raise httpx.ReadTimeout("timed out", request=request)


@pytest.mark.parametrize(
    "source, handler",
    [
        ("lever", lambda request: httpx.Response(404, text="<title>Not found – 404 error</title>")),
        ("greenhouse", lambda request: httpx.Response(500, json={"name": "Anthropic"})),
        ("greenhouse", times_out),
        ("ashby", lambda request: httpx.Response(500, json={"data": {"organization": {"name": "Acme"}}})),
        ("ashby", times_out),
    ],
)
async def test_fetch_board_name_gives_no_name_when_the_request_fails(source, handler):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_board_name(client, source, "mujin") is None


ASHBY_LOGO = "https://app.ashbyhq.com/api/images/org-theme-logo/acme.png"
HRMOS_LOGO = "https://hrmos.co/images/acme/logo.png"
LEVER_LOGO = "https://lever-client-logos.s3.us-west-2.amazonaws.com/acme.png"
GREENHOUSE_LOGO = "https://s4-recruiting.cdn.greenhouse.io/external_greenhouse_job_boards/logos/acme.png?1763575446"


def html_page(body: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text=f"<html>{body}</html>")


@pytest.mark.parametrize(
    "source, url, response, logo",
    [
        pytest.param(
            "ashby",
            "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiOrganizationFromHostedJobsPageName",
            httpx.Response(200, json={"data": {"organization": {"theme": {"logoSquareImageUrl": ASHBY_LOGO}}}}),
            ASHBY_LOGO,
            id="ashby theme logo",
        ),
        pytest.param(
            "hrmos",
            "https://hrmos.co/pages/acme/jobs",
            html_page(
                f'<head><meta property="og:title" content="アクメ株式会社">'
                f'<meta property="og:image" content="{HRMOS_LOGO}"></head><body><h1>求人一覧</h1></body>'
            ),
            HRMOS_LOGO,
            id="hrmos og:image",
        ),
        pytest.param(
            "lever",
            "https://jobs.lever.co/acme",
            html_page(
                '<body><img src="https://example.com/banner.png" alt="Banner">'
                f'<div class="main-header-logo"><a href="https://acme.com"><img src="{LEVER_LOGO}" alt="Acme logo"></a></div>'
                "</body>"
            ),
            LEVER_LOGO,
            id="lever header logo",
        ),
        pytest.param(
            "greenhouse",
            "https://job-boards.greenhouse.io/acme",
            html_page(
                '<body><img src="https://example.com/office.jpg" alt="Our office">'
                f'<img src="{GREENHOUSE_LOGO}" alt="Acme Logo"></body>'
            ),
            GREENHOUSE_LOGO,
            id="greenhouse image alt ending in Logo",
        ),
        pytest.param(
            "greenhouse",
            "https://job-boards.greenhouse.io/acme",
            html_page('<body><img src="//s4-recruiting.cdn.greenhouse.io/logos/acme.png" alt="Acme Logo"></body>'),
            "https://s4-recruiting.cdn.greenhouse.io/logos/acme.png",
            id="greenhouse logo without a scheme",
        ),
        pytest.param(
            "greenhouse",
            "https://job-boards.greenhouse.io/acme",
            html_page('<body><img src="https://example.com/office.jpg" alt="Our office"></body>'),
            None,
            id="greenhouse page without a logo",
        ),
        pytest.param(
            "greenhouse",
            "https://job-boards.greenhouse.io/acme",
            httpx.Response(302, headers={"location": "https://acme.com/careers"}),
            None,
            id="greenhouse board that redirects to its own careers site",
        ),
        pytest.param(
            "lever",
            "https://jobs.lever.co/acme",
            html_page('<body><div class="main-header-logo"><img src="javascript:alert(1)"></div></body>'),
            None,
            id="lever logo that isn't an http URL",
        ),
        pytest.param(
            "ashby",
            "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiOrganizationFromHostedJobsPageName",
            httpx.Response(200, json={"data": {"organization": {"theme": None}}}),
            None,
            id="ashby without a theme",
        ),
    ],
)
async def test_fetch_board_logo_reads_each_ats_logo_url(source, url, response, logo):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_board_logo(client, source, "acme") == logo
    assert requested == [url]


async def test_fetch_board_logo_asks_ashby_for_the_theme_logo_of_the_board():
    def handler(request):
        body = json.loads(request.content)
        assert body["variables"] == {"organizationHostedJobsPageName": "acme", "searchContext": "JobBoard"}
        assert body["query"] == ASHBY_ORGANIZATION_QUERY
        return httpx.Response(200, json={"data": {"organization": {"theme": {"logoSquareImageUrl": ASHBY_LOGO}}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await fetch_board_logo(client, "ashby", "acme") == ASHBY_LOGO


@pytest.mark.parametrize("source", ["greenhouse", "lever", "ashby", "hrmos"])
async def test_fetch_board_logo_gives_none_when_the_request_fails(source):
    async with httpx.AsyncClient(transport=httpx.MockTransport(times_out)) as client:
        assert await fetch_board_logo(client, source, "acme") is None
