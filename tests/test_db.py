from datetime import UTC, datetime

from sqlalchemy import select

from kansei import extracted, save_postings, sha256
from kansei.db import Extraction, Posting


def test_save_postings_updates_a_posting_it_has_seen_before(session, make_posting):
    monday = datetime(2026, 10, 5, tzinfo=UTC)
    tuesday = datetime(2026, 10, 6, tzinfo=UTC)

    save_postings(session, [make_posting(title="Backend Engineer")], monday)
    save_postings(session, [make_posting(title="Senior Backend Engineer")], tuesday)

    rows = session.scalars(select(Posting).where(Posting.url == "https://example.com/1")).all()
    assert len(rows) == 1
    assert rows[0].title == "Senior Backend Engineer"
    assert rows[0].first_seen_at == monday
    assert rows[0].last_seen_at == tuesday

def test_save_postings_doesnt_crash_on_empty_postings(session, make_posting):
    monday = datetime(2026, 10, 5, tzinfo=UTC)
    save_postings(session, [], monday)

    rows = session.scalars(select(Posting).where(Posting.url == "https://example.com/1")).all()
    assert len(rows) == 0


def test_extracted_finds_a_text_only_under_the_model_and_prompt_that_read_it(session, make_posting):
    ids = save_postings(session, [make_posting()], datetime(2026, 10, 5, tzinfo=UTC))
    posting_id = ids["https://example.com/1"]
    session.add(Extraction(
        posting_id=posting_id,
        text="We need a Python engineer.",
        text_sha256=sha256("We need a Python engineer."),
        model="gpt-6-luna",
        prompt_sha="c876fc21",
        facts={},
    ))

    key = (posting_id, sha256("We need a Python engineer."))
    assert key in extracted(session, "gpt-6-luna", "c876fc21")
    assert key not in extracted(session, "gpt-6-luna", "70b7a0b0")
    assert key not in extracted(session, "gpt-5.6-luna", "c876fc21")
    