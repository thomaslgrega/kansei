import httpx
import pytest
from bs4 import BeautifulSoup

from kansei.sources import (
    fetch_url,
    from_greenhouse,
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


def test_every_adapter_produces_exactly_the_same_keys():
    assert (
        from_greenhouse(GREENHOUSE_RAW, "stripe").keys()
        == from_lever(LEVER_RAW, "woven-by-toyota").keys()
        == from_url(PAGE_WITHOUT_LD, "https://example.com/1").keys()
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


def test_from_url_finds_the_job_posting_inside_a_graph():
    posting = from_url(PAGE_WITH_GRAPH, "https://www.wantedly.com/projects/2576097")

    assert posting["title"] == "事業開発"
    assert posting["location"] == "JP"


def test_from_url_takes_the_body_from_the_page_not_the_json_ld_description():
    posting = from_url(PAGE_WITH_GRAPH, "https://www.wantedly.com/projects/2576097")

    assert "出店戦略と新業態を主導するポジションです。" in posting["description"]


def test_from_url_still_produces_a_record_when_the_page_declares_nothing():
    posting = from_url(PAGE_WITHOUT_LD, "https://job-boards.greenhouse.io/gitlab/jobs/85566")

    assert posting["title"] == "AI Engineer"
    assert posting["posted_at"] is None
    assert posting["location"] == ""


async def test_fetch_url_refuses_a_response_that_is_not_html():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"jobs": []}))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match="application/json"):
            await fetch_url(client, "https://example.com/1")