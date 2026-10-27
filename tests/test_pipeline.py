import httpx
import pytest

from kansei import (
    fetch_posting,
    is_candidate,
    is_sales_or_support,
    pending_extractions,
    sha256,
    validate,
)


@pytest.mark.parametrize(
    ("title", "location", "expected"),
    [
        ("Software Engineer", "Tokyo, Japan", True),
        ("Backend Developer", "Remote - Japan", True),
        ("Software Engineer", "Remote - USA", False),
        ("Software Engineer", "Remote, United Kingdom", False),
        ("Software Engineer", "Remote", True),
        ("Software Engineer", "Remote - Anywhere", True),
        ("Software Engineer", "Osaka", True),
        ("Software Engineer", "大阪市北区", True),
        ("ソフトウェアエンジニア", "静岡県裾野市", True),
        ("Software Engineer", "成都市", False),
        ("Account Executive", "Tokyo, Japan", False),
        ("Software Engineer", "Dublin, Ireland", False),
        ("SOFTWARE ENGINEER", "TOKYO", True),
        ("Engineering Manager", "Tokyo, Japan", True),
        ("バックエンドエンジニア・Robot Platform", "東京都中央区", True),
        ("シニア機械学習エンジニア・Energy Products", "東京都中央区", True),
        ("カスタマーサクセスマネージャー", "東京都中央区", False),
    ],
)
def test_is_candidate(title, location, expected):
    assert is_candidate(title, location) is expected


@pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Senior Sales Engineer - Telco", True),
            ("Technical Support Engineer II", True),
            ("Sr. Technical Solutions Engineer - Platform (Support)", True),
            ("Manager, Field Engineering", True),
            ("Senior Customer Success Engineer, Japan", True),
            ("（夜間専任）ロボットシステムサポートエンジニア", True),
            ("Senior AI Engineer - FDE (Forward Deployed Engineer)", False),
            ("ADAS HMI Engineer, Customer Application", False),
            ("Salesforce Engineer", False),
            ("物流自動化トータルソリューション・システムエンジニア", False),
        ],
)
def test_is_sales_or_support(title, expected):
    assert is_sales_or_support(title) is expected


def test_validate_keeps_the_good_records_and_names_the_bad_one():
    jobs = [
        {"source": "greenhouse", "token": "stripe", "id": "1", "title": "Software Engineer",
         "url": "https://example.com/1", "posted_at": "2026-09-19T00:00:00Z", "location": "Tokyo"},
        {"source": "greenhouse", "token": "stripe", "id": "2", "title": "Data Engineer",
         "url": "not-a-url", "posted_at": "2026-09-19T00:00:00Z", "location": "Tokyo"},
    ]
    passed, failed = validate(jobs)

    assert [job.id for job in passed] == ["1"]
    assert [job_id for job_id, _ in failed] == ["2"]


def test_validate_attributes_a_failure_with_no_id_at_all():
    passed, failed = validate([{"title": "Software Engineer"}])

    assert passed == []
    assert len(failed) == 1
    assert failed[0][0] == "unknown"


async def test_fetch_posting_returns_text_with_the_markup_removed():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"content": "R&amp;D team &lt;b&gt;Tokyo&lt;/b&gt;"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        content = await fetch_posting(client, "stripe", 42)

    assert content == "R&D team Tokyo"
    assert seen == ["https://boards-api.greenhouse.io/v1/boards/stripe/jobs/42"]


async def test_fetch_posting_raises_on_a_404():
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_posting(client, "ramp", 42)


IDS = {"https://example.com/a": 1, "https://example.com/b": 2, "https://example.com/c": 3,
       "https://example.com/d": 4}


def test_pending_extractions_sends_the_first_ones_up_to_the_cap():
    texts = {"https://example.com/a": "A", "https://example.com/b": "B", "https://example.com/c": "C"}

    assert pending_extractions(texts, IDS, cached=set(), cap=2) == (
        {"https://example.com/a": "A", "https://example.com/b": "B"},
        3,
    )


def test_pending_extractions_skips_already_extracted_candidates_without_using_the_cap():
    texts = {"https://example.com/a": "A", "https://example.com/b": "B", "https://example.com/c": "C",
             "https://example.com/d": "D"}
    cached = {(1, sha256("A")), (2, sha256("B")), (3, sha256("old C"))}

    assert pending_extractions(texts, IDS, cached, cap=2) == (
        {"https://example.com/c": "C", "https://example.com/d": "D"},
        2,
    )


def test_pending_extractions_sends_nothing_with_a_cap_of_zero():
    texts = {"https://example.com/a": "A", "https://example.com/b": "B"}

    assert pending_extractions(texts, IDS, cached=set(), cap=0) == ({}, 2)


def test_pending_extractions_skips_a_failed_fetch_without_using_the_cap():
    texts = {"https://example.com/a": httpx.ReadTimeout("timed out"), "https://example.com/b": "B",
             "https://example.com/c": "C"}

    assert pending_extractions(texts, IDS, cached=set(), cap=2) == (
        {"https://example.com/b": "B", "https://example.com/c": "C"},
        2,
    )
