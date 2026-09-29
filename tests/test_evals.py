from datetime import UTC, datetime

import pytest

from kansei.evals import (
    LABELS,
    MANIFEST,
    POSTINGS,
    FrozenPosting,
    Label,
    ManifestEntry,
    add_new,
    load,
    manifest_entry,
    score,
)

THEN = datetime(2026, 9, 26, tzinfo=UTC)
LATER = datetime(2026, 10, 3, tzinfo=UTC)


def test_freezing_again_never_changes_a_posting_that_is_already_frozen():
    frozen = [FrozenPosting(url="https://a", title="A", text="必須条件: 日本語 N2", frozen_at=THEN)]
    fetched = [
        FrozenPosting(url="https://a", title="A", text="edited by the company since", frozen_at=LATER),
        FrozenPosting(url="https://b", title="B", text="a new posting", frozen_at=LATER),
    ]

    merged = add_new(frozen, fetched)

    assert [(p.url, p.text, p.frozen_at) for p in merged] == [
        ("https://a", "必須条件: 日本語 N2", THEN),
        ("https://b", "a new posting", LATER),
    ]


def test_every_label_uses_the_models_values_and_names_a_frozen_posting():
    frozen = {entry.url for entry in load(MANIFEST, ManifestEntry)}
    labels = load(LABELS, Label)
    urls = [label.url for label in labels]

    assert labels, f"no labels in {LABELS}"
    assert len(urls) == len(set(urls)), "a posting is labeled twice"
    assert set(urls) <= frozen, "a label names a posting that isn't frozen"


def test_the_local_postings_are_exactly_the_text_the_manifest_records():
    if not POSTINGS.exists():
        pytest.skip(f"{POSTINGS.name} is not in the repo; the posting text is kept private")

    postings = load(POSTINGS, FrozenPosting)

    assert [manifest_entry(p) for p in postings] == load(MANIFEST, ManifestEntry)


def answers(url: str, **fields: str) -> Label:
    return Label(**{
        "url": url,
        "seniority": "not_stated",
        "japanese_required": "not_stated",
        "japanese_level": "not_stated",
        "jlpt": "not_stated",
        "remote_policy": "not_stated",
        **fields,
    })

def test_score_pairs_each_prediction_with_its_label_by_url_not_by_position():
    labels = [answers("https://a", jlpt="N1"), answers("https://b")]
    predictions = [answers("https://b"), answers("https://a", jlpt="N2")]

    wrong = score(labels, predictions)

    assert wrong == {
        "seniority": [],
        "japanese_required": [],
        "japanese_level": [],
        "jlpt": ["https://a"],
        "remote_policy": [],
    }


def test_score_refuses_a_run_that_is_missing_a_labeled_posting():
    labels = [answers("https://a"), answers("https://b")]

    with pytest.raises(ValueError, match=r"^no prediction for https://b$"):
        score(labels, [answers("https://a")])


def test_every_labeled_skill_is_written_in_its_posting():
    if not POSTINGS.exists():
        pytest.skip(f"{POSTINGS.name} is not in the repo; the posting text is kept private")

    text = {p.url: p.text for p in load(POSTINGS, FrozenPosting)}
    not_found = [
        (label.url, skill)
        for label in load(LABELS, Label)
        for skill in label.must_have_skills or []
        if skill not in text[label.url]
    ]

    assert not_found == []
