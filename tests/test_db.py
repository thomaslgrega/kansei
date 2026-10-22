from datetime import UTC, datetime

from sqlalchemy import create_engine, select, text
from sqlalchemy.pool import NullPool

from kansei import extracted, save_postings, sha256
from kansei.db import Extraction, Posting, engine


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


def test_engine_reconnects_after_the_database_drops_an_idle_connection():
    engine.dispose()
    with engine.connect() as connection:
        pid = connection.execute(text("select pg_backend_pid()")).scalar_one()
    with create_engine(engine.url, poolclass=NullPool).connect() as other:
        other.execute(text("select pg_terminate_backend(:pid)"), {"pid": pid})
    with engine.connect() as connection:
        assert connection.execute(text("select 1")).scalar_one() == 1
