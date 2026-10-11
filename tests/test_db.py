from datetime import UTC, datetime

from sqlalchemy import select

from kansei import save_postings
from kansei.db import Posting


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
