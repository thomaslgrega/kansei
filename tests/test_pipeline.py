import httpx
import pytest

from kansei import fetch_posting, is_candidate, validate


@pytest.mark.parametrize(
    ("title", "location", "expected"),
    [
        ("Software Engineer", "Tokyo, Japan", True),
        ("Backend Developer", "Remote - Japan", True),
        ("Account Executive", "Tokyo, Japan", False),
        ("Software Engineer", "Dublin, Ireland", False),
        ("SOFTWARE ENGINEER", "TOKYO", True),
        ("Engineering Manager", "Tokyo, Japan", True),
        ("バックエンドエンジニア・Robot Platform", "東京都中央区", True),
        ("シニア機械学習エンジニア・Energy Products", "東京都中央区", True),
        ("カスタマーサクセスマネージャー", "東京都中央区", False),
    ],
)
def test_is_candidate(make_posting, title, location, expected):
    assert is_candidate(make_posting(title, location)) is expected


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


async def test_fetch_posting_unescapes_html_entities():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"content": "R&amp;D team &lt;b&gt;Tokyo&lt;/b&gt;"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        content = await fetch_posting(client, "stripe", 42)

    assert content == "R&D team <b>Tokyo</b>"
    assert seen == ["https://boards-api.greenhouse.io/v1/boards/stripe/jobs/42"]


async def test_fetch_posting_raises_on_a_404():
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_posting(client, "ramp", 42)