from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from kansei import extracted, extraction_cap, save_postings, sha256
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


def test_the_database_rejects_a_posting_whose_company_name_is_the_empty_string(session, make_posting):
    with pytest.raises(IntegrityError, match="ck_postings_company_name"):
        save_postings(session, [make_posting(source="url", company_name="")], datetime.now(UTC))


NOW = datetime(2030, 1, 1, tzinfo=UTC)


@pytest.fixture
def add_extractions_at(session, make_posting):
    posting_id = save_postings(session, [make_posting()], NOW)["https://example.com/1"]

    def add(*created_at: datetime) -> None:
        session.add_all(
            Extraction(
                posting_id=posting_id,
                text=f"text {i}",
                text_sha256=sha256(f"text {i}"),
                model="gpt-6-luna",
                prompt_sha="c876fc21",
                facts={},
                created_at=when,
            )
            for i, when in enumerate(created_at)
        )
        session.flush()

    return add


def test_extraction_cap_takes_the_last_24_hours_off_the_daily_limit_including_the_boundary(session, add_extractions_at):
    add_extractions_at(NOW - timedelta(hours=1), NOW - timedelta(hours=23, minutes=59), NOW - timedelta(hours=24))

    assert extraction_cap(session, NOW, max_postings=300, daily_limit=300) == (297, 297)


def test_extraction_cap_ignores_extractions_older_than_24_hours(session, add_extractions_at):
    add_extractions_at(NOW - timedelta(hours=1), NOW - timedelta(hours=24, seconds=1), NOW - timedelta(days=3))

    assert extraction_cap(session, NOW, max_postings=300, daily_limit=300) == (299, 299)


@pytest.mark.parametrize("daily_limit", [3, 2, 0])
def test_extraction_cap_is_zero_once_the_daily_limit_is_used_up(session, add_extractions_at, daily_limit):
    add_extractions_at(NOW - timedelta(hours=1), NOW - timedelta(hours=2), NOW - timedelta(hours=3))

    assert extraction_cap(session, NOW, max_postings=300, daily_limit=daily_limit) == (0, 0)


def test_extraction_cap_keeps_the_per_run_cap_when_it_is_smaller(session, add_extractions_at):
    add_extractions_at(NOW - timedelta(hours=1))

    assert extraction_cap(session, NOW, max_postings=5, daily_limit=300) == (5, 299)
